"""
Roda a deteccao de nodulos (Sprint 7) em ate 20 pacientes com anotacoes de
referencia disponiveis localmente. Retomavel (salva progresso por paciente).

Uso: python scripts/run_nodule_evaluation.py
"""
import sys
from pathlib import Path

sys.path.insert(0, "src")

import pandas as pd

from luna16.io import list_available_uids
from luna16.nodules import load_annotations, run_nodule_pipeline_for_uid

DATA_DIR = Path("data/luna16")
OUT_PATH = DATA_DIR / "sprint7_nodulos_resultados.csv"
N_PACIENTES = 20
THRESHOLD = 0.1


def main():
    ann = load_annotations(DATA_DIR)
    local_uids = set(list_available_uids(DATA_DIR))
    ann_local = ann[ann["seriesuid"].isin(local_uids)]
    counts = ann_local["seriesuid"].value_counts()
    uids = counts.index[:N_PACIENTES].tolist()
    print(f"Pacientes selecionados: {len(uids)} (dos {len(counts)} disponiveis com anotacao)", flush=True)

    if OUT_PATH.exists():
        done_df = pd.read_csv(OUT_PATH)
        done_uids = set(done_df["uid"])
    else:
        done_df = pd.DataFrame()
        done_uids = set()

    pending = [u for u in uids if u not in done_uids]
    print(f"{len(done_uids)} ja feitos, {len(pending)} pendentes", flush=True)

    rows = done_df.to_dict("records")
    for i, uid in enumerate(pending, 1):
        r = run_nodule_pipeline_for_uid(uid, DATA_DIR, ann_local, threshold=THRESHOLD)
        rows.append(r)
        print(
            f"[{i}/{len(pending)}] {uid[-10:]}  anotacoes={r['n_anotacoes']}  "
            f"candidatos={r['n_candidatos']}  TP={r['verdadeiros_positivos']}  "
            f"sens={r['sensibilidade']:.2f}  tempo={r['tempo_segundos']:.1f}s",
            flush=True,
        )
        pd.DataFrame(rows).to_csv(OUT_PATH, index=False)

    print("CONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
