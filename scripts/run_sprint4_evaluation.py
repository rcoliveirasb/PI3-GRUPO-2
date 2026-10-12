"""
Roda a avaliacao pesada do Sprint 4 (baseline vs region growing, no conjunto
de teste, >=20 TCs) como um script separado do notebook -- mais robusto pra
uma execucao de ~20-25 minutos (retomavel: se um paciente ja tem resultado
salvo, pula ele; da pra interromper e rodar de novo sem perder progresso).

Uso: python scripts/run_sprint4_evaluation.py

Le data/luna16/split_subset0.csv (split do Sprint 3, imutavel) e estende com
os pacientes novos do subset1 (mesma seed/proporcoes), salvando
data/luna16/split_full.csv. Depois avalia baseline e region growing em todo
o conjunto de teste resultante, salvando:
  data/luna16/sprint4_baseline_test.csv
  data/luna16/sprint4_region_growing_test.csv
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd

from luna16.io import list_available_uids
from luna16.selection import build_header_table, apply_selection_criteria
from luna16.splits import patient_split, assert_no_leakage
from luna16.baseline import segment_baseline
from luna16.region_growing import segment_region_growing
from luna16.pipeline import run_pipeline_for_uid

SEED = 42
# Caminho relativo (nao absoluto): o nome da pasta do projeto tem um "°",
# e caminho absoluto com esse caractere quebra a leitura de arquivo do
# SimpleITK no Windows (mismatch de codepage). Rodar sempre a partir da raiz
# do repositorio.
DATA_DIR = Path("data/luna16")


def build_or_load_full_split() -> pd.DataFrame:
    split_full_path = DATA_DIR / "split_full.csv"
    if split_full_path.exists():
        print(f"split_full.csv ja existe, usando ({split_full_path})", flush=True)
        return pd.read_csv(split_full_path)

    sprint3_split = pd.read_csv(DATA_DIR / "split_subset0.csv")
    sprint3_uids = set(sprint3_split["uid"])
    print(f"Split do Sprint 3 (imutavel): {len(sprint3_split)} pacientes", flush=True)

    header_df = build_header_table(DATA_DIR)
    selection_df = apply_selection_criteria(header_df, DATA_DIR)
    all_included = set(selection_df.loc[selection_df["incluido"], "uid"])

    novos_uids = sorted(all_included - sprint3_uids)
    print(f"Pacientes novos (subset1, apos criterios de selecao): {len(novos_uids)}", flush=True)

    novo_split = patient_split(novos_uids, seed=SEED, train_frac=0.6, val_frac=0.2)
    assert_no_leakage(novo_split)

    novo_split_df = pd.DataFrame(
        [(uid, "train") for uid in novo_split.train]
        + [(uid, "val") for uid in novo_split.val]
        + [(uid, "test") for uid in novo_split.test],
        columns=["uid", "conjunto"],
    )

    full_split = pd.concat([sprint3_split, novo_split_df], ignore_index=True)
    assert full_split["uid"].is_unique, "uid duplicado apos concatenar splits"
    full_split.to_csv(split_full_path, index=False)
    print(f"split_full.csv salvo: {len(full_split)} pacientes", flush=True)
    return full_split


def evaluate_resumable(uids, segment_fn, out_path: Path, label: str) -> pd.DataFrame:
    if out_path.exists():
        done_df = pd.read_csv(out_path)
        done_uids = set(done_df["uid"])
    else:
        done_df = pd.DataFrame()
        done_uids = set()

    pending = [u for u in uids if u not in done_uids]
    print(f"[{label}] {len(done_uids)} ja feitos, {len(pending)} pendentes", flush=True)

    rows = done_df.to_dict("records")
    for i, uid in enumerate(pending, 1):
        r = run_pipeline_for_uid(uid, DATA_DIR, segment_fn=segment_fn)
        rows.append(vars(r))
        print(
            f"[{label} {i}/{len(pending)}] {uid[-10:]}  dice={r.dice:.4f}  iou={r.iou:.4f}  "
            f"tempo={r.tempo_segundos:.1f}s",
            flush=True,
        )
        # salva a cada paciente -- se interromper, nao perde o que ja rodou
        pd.DataFrame(rows).to_csv(out_path, index=False)

    return pd.DataFrame(rows)


def main():
    full_split = build_or_load_full_split()
    test_uids = full_split.loc[full_split["conjunto"] == "test", "uid"].tolist()
    print(f"\nConjunto de teste: {len(test_uids)} pacientes\n", flush=True)

    print("=== Baseline (threshold -600HU + morfologia) ===", flush=True)
    evaluate_resumable(test_uids, segment_baseline, DATA_DIR / "sprint4_baseline_test.csv", "baseline")

    print("\n=== Region growing ===", flush=True)
    evaluate_resumable(test_uids, segment_region_growing, DATA_DIR / "sprint4_region_growing_test.csv", "region_growing")

    print("\nCONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
