"""Regenera data/luna16/split_full.csv com a proporcao 70/15/15 exigida no
feedback do professor (Checkpoint 1), substituindo o split 60/20/20 usado
entre os Sprints 3-8.

Ate agora o split era construido em duas etapas (split "imutavel" do Sprint 3
sobre subset0 + extensao do subset1 com a mesma proporcao antiga) -- ver
scripts/run_sprint4_evaluation.py::build_or_load_full_split. Como a propria
proporcao mudou por exigencia externa (nao e mais uma decisao interna do
grupo), nao ha razao para preservar aquela divisao em duas etapas: este
script recalcula um split unico e uniforme sobre todos os pacientes
atualmente disponiveis (subset0+subset1, apos os criterios de seleccao).

O split anterior (60/20/20) e preservado em
data/luna16/archive_split_v1_60_20_20/ para auditoria/comparacao, junto com
os resultados que dependiam dele (ja que a composicao do conjunto de teste
muda com a nova proporcao).

Uso: python scripts/regenerate_split_70_15_15.py
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd

from luna16.selection import build_header_table, apply_selection_criteria
from luna16.splits import patient_split, assert_no_leakage

SEED = 42
DATA_DIR = Path("data/luna16")
ARCHIVE_DIR = DATA_DIR / "archive_split_v1_60_20_20"

# Arquivos que dependem da composicao do split e ficam invalidos com a nova
# proporcao -- movidos para o arquivo, nao apagados.
DEPENDENT_FILES = [
    "split_full.csv",
    "sprint4_baseline_test.csv",
    "sprint4_region_growing_test.csv",
    "tabela_resultados_finais.csv",
    "grafico_dice_iou_final.png",
    "grafico_comparacao_pareada.png",
]


def archive_old_split():
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for name in DEPENDENT_FILES:
        src = DATA_DIR / name
        if src.exists():
            dest = ARCHIVE_DIR / name
            shutil.move(str(src), str(dest))
            print(f"Arquivado: {src} -> {dest}", flush=True)


def main():
    archive_old_split()

    print("Lendo cabecalhos de subset0+subset1...", flush=True)
    header_df = build_header_table(DATA_DIR)
    selection_df = apply_selection_criteria(header_df, DATA_DIR)
    included = sorted(selection_df.loc[selection_df["incluido"], "uid"])
    print(f"Pacientes incluidos apos criterios de selecao: {len(included)}", flush=True)

    split = patient_split(included, seed=SEED, train_frac=0.7, val_frac=0.15)
    assert_no_leakage(split)

    split_df = pd.DataFrame(
        [(uid, "train") for uid in split.train]
        + [(uid, "val") for uid in split.val]
        + [(uid, "test") for uid in split.test],
        columns=["uid", "conjunto"],
    )
    out_path = DATA_DIR / "split_full.csv"
    split_df.to_csv(out_path, index=False)
    print(
        f"\nsplit_full.csv (70/15/15) salvo: {len(split.train)} treino / "
        f"{len(split.val)} validacao / {len(split.test)} teste "
        f"(total {len(split_df)})",
        flush=True,
    )


if __name__ == "__main__":
    main()
