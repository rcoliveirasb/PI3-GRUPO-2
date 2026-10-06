"""
Extrai features de todos os candidatos de candidates.csv (train/val/test,
usando o mesmo split de pacientes do Sprint 3/4) para treinar o classificador
de reducao de falsos positivos (Sprint 8).

Uso: python scripts/extract_nodule_features.py
"""
import sys
from pathlib import Path

sys.path.insert(0, "src")

import pandas as pd

from luna16.nodule_features import build_feature_dataframe

DATA_DIR = Path("data/luna16")


def main():
    cand = pd.read_csv(DATA_DIR / "candidates.csv")
    split = pd.read_csv(DATA_DIR / "split_full.csv")

    for conjunto in ["train", "val", "test"]:
        out_path = DATA_DIR / f"nodule_features_{conjunto}.csv"
        if out_path.exists():
            print(f"{conjunto}: ja existe, pulando ({out_path})", flush=True)
            continue
        uids = set(split[split["conjunto"] == conjunto]["uid"])
        sub = cand[cand["seriesuid"].isin(uids)]
        print(f"{conjunto}: {len(sub)} candidatos em {sub['seriesuid'].nunique()} pacientes", flush=True)

        feats = build_feature_dataframe(sub, DATA_DIR, verbose=True)
        feats.to_csv(out_path, index=False)
        print(f"{conjunto}: salvo em {out_path} ({len(feats)} linhas)", flush=True)

    print("CONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
