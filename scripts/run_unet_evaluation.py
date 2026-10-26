"""Avalia o U-Net 2D de contingencia no mesmo conjunto de teste (split
70/15/15) e com o mesmo pipeline (pipeline.run_pipeline_for_uid) usado para
baseline e region growing -- garante que os tres metodos sejam comparados
sob exatamente as mesmas condicoes (mesmo pre-processamento, mesmas
metricas, mesmo conjunto de teste).

Pre-requisito: scripts/train_unet_baseline.py ja ter sido rodado (checkpoint
em data/luna16/unet_baseline.pt).

Uso: python scripts/run_unet_evaluation.py
Salva: data/luna16/sprint_unet_test.csv (mesmo formato de
data/luna16/sprint4_baseline_test.csv)

Split novo (888 exames), com o checkpoint treinado nele:
  python scripts/run_unet_evaluation.py --split data/luna16/split_novo.csv \
      --checkpoint <pesos da U-Net nova> --sufixo _novo
Salva data/luna16/sprint_unet_test_novo.csv.
"""
import argparse
import functools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd

from luna16.pipeline import run_pipeline_for_uid
from luna16.unet import load_trained_model, segment_with_unet

DATA_DIR = Path("data/luna16")
CHECKPOINT_PATH = DATA_DIR / "unet_baseline.pt"


def evaluate_resumable(uids, segment_fn, out_path: Path) -> pd.DataFrame:
    if out_path.exists():
        done_df = pd.read_csv(out_path)
        done_uids = set(done_df["uid"])
    else:
        done_df = pd.DataFrame()
        done_uids = set()

    pending = [u for u in uids if u not in done_uids]
    print(f"{len(done_uids)} ja feitos, {len(pending)} pendentes", flush=True)

    rows = done_df.to_dict("records")
    for i, uid in enumerate(pending, 1):
        r = run_pipeline_for_uid(uid, DATA_DIR, segment_fn=segment_fn)
        rows.append(vars(r))
        print(
            f"[unet {i}/{len(pending)}] {uid[-10:]}  dice={r.dice:.4f}  iou={r.iou:.4f}  "
            f"tempo={r.tempo_segundos:.1f}s",
            flush=True,
        )
        pd.DataFrame(rows).to_csv(out_path, index=False)

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", type=Path, default=DATA_DIR / "split_full.csv")
    parser.add_argument("--conjunto", default="test", help="valor da coluna 'conjunto' a avaliar")
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT_PATH)
    parser.add_argument("--sufixo", default="", help="sufixo do CSV de saida, ex: _novo")
    args = parser.parse_args()

    if not args.checkpoint.exists():
        raise FileNotFoundError(
            f"{args.checkpoint} nao existe -- rode scripts/train_unet_baseline.py primeiro."
        )

    split = pd.read_csv(args.split)
    test_uids = split.loc[split["conjunto"] == args.conjunto, "uid"].tolist()
    print(f"Conjunto '{args.conjunto}': {len(test_uids)} pacientes\n", flush=True)

    model = load_trained_model(str(args.checkpoint))
    segment_fn = functools.partial(segment_with_unet, model=model)

    evaluate_resumable(test_uids, segment_fn, DATA_DIR / f"sprint_unet_test{args.sufixo}.csv")
    print("\nCONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
