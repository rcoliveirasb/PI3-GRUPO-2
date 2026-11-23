"""
Traqueia na predição: quanto dela cada método marca como pulmão.

O gabarito do LUNA16 separa o pulmão (rótulos 3 e 4) da traqueia e das vias
aéreas centrais (rótulo 5), e o projeto avalia só o pulmão. A traqueia é ar,
então os métodos tendem a incluí-la. Isso quase não pesa no Dice, porque ela é
pequena perto do pulmão, mas é um erro anatômico sistemático (inspeção visual
de 12 exames, entrega/inspecao_visual/).

Para cada exame do Teste A (26 exames locais), mede o volume da traqueia
(rótulo 5) que fica dentro da máscara de cada método:
  - baseline e region growing do artigo;
  - U-Net oficial (semente 123, 497 exames de treino), com a limpeza de
    componentes fora do tórax.

Saídas:
  docs/traqueia/traqueia_por_exame.csv
  docs/traqueia/traqueia_3_metodos.png  (fatia com mais traqueia do exame com
                                         maior volume de traqueia)

Uso (a partir da raiz do repositório):
  python scripts/analise_traqueia.py              # mede os 26 exames (~25 min) e faz a figura
  python scripts/analise_traqueia.py --so-figura  # so a figura, a partir do CSV
"""
import argparse
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
os.chdir(RAIZ)
sys.path.insert(0, str(RAIZ / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np
import pandas as pd
import SimpleITK as sitk

from luna16.baseline import segment_baseline
from luna16.io import LUNG_LABELS, TRACHEA_LABEL, load_ct
from luna16.pipeline import _to_sitk
from luna16.preprocessing import clean_hu, denoise, resample_isotropic
from luna16.region_growing import segment_region_growing
from luna16.unet import load_trained_model, segment_with_unet

DATA_DIR = Path("data/luna16")
SPLIT = DATA_DIR / "split_full.csv"
PESOS = Path("pji/modelos/unet_seed123/unet_novo_final.pt")
SAIDA = Path("docs/traqueia")


def preparar(uid: str):
    ct = load_ct(uid, DATA_DIR)
    s = ct.to_sitk_image()
    vol = sitk.GetArrayFromImage(resample_isotropic(
        _to_sitk(denoise(clean_hu(ct.array), sigma=0.5), s, "int16"), (1.0, 1.0, 1.0), is_mask=False))
    rotulos = sitk.ReadImage(str(DATA_DIR / "seg-lungs-LUNA16" / f"{uid}.mhd"))
    rotulos = sitk.GetArrayFromImage(resample_isotropic(rotulos, (1.0, 1.0, 1.0), is_mask=True))
    return vol, np.isin(rotulos, LUNG_LABELS), rotulos == TRACHEA_LABEL


def medir(uids, metodos) -> pd.DataFrame:
    linhas = []
    for i, uid in enumerate(uids, 1):
        vol, _, traqueia = preparar(uid)
        linha = {"uid": uid, "traqueia_ref_ml": traqueia.sum() / 1000}  # voxel de 1 mm3
        for nome, fn in metodos.items():
            dentro = (fn(vol) & traqueia).sum()
            linha[f"{nome}_traqueia_ml"] = dentro / 1000
            linha[f"{nome}_traqueia_pct"] = 100 * dentro / max(traqueia.sum(), 1)
        linhas.append(linha)
        print(f"[{i}/{len(uids)}] ...{uid[-10:]}  traqueia {linha['traqueia_ref_ml']:.1f} mL  "
              + "  ".join(f"{n} {linha[f'{n}_traqueia_pct']:.0f}%" for n in metodos), flush=True)
    return pd.DataFrame(linhas)


def figura(df: pd.DataFrame, metodos) -> None:
    """Fatia com mais traqueia do exame com maior volume de traqueia."""
    uid = df.loc[df["traqueia_ref_ml"].idxmax(), "uid"]
    vol, pulmao, traqueia = preparar(uid)
    z = int(np.argmax(traqueia.reshape(len(traqueia), -1).sum(axis=1)))
    titulos = {"baseline": "Baseline", "region_growing": "Region growing", "unet": "U-Net (semente 123)"}
    fig, ax = plt.subplots(1, 3, figsize=(12, 4.8))
    for a, (n, fn) in zip(ax, metodos.items()):
        p = fn(vol)[z]
        a.imshow(vol[z], cmap="gray", vmin=-1000, vmax=400)
        a.imshow(np.ma.masked_where(~p, p), cmap=ListedColormap(["#ff8c00"]), alpha=0.45)
        a.imshow(np.ma.masked_where(~(p & traqueia[z]), p & traqueia[z]), cmap=ListedColormap(["#d62728"]), alpha=0.9)
        a.contour(pulmao[z], levels=[0.5], colors="cyan", linewidths=0.8)
        a.contour(traqueia[z], levels=[0.5], colors="white", linewidths=0.8, linestyles="dashed")
        pct = 100 * df[f"{n}_traqueia_ml"].sum() / df["traqueia_ref_ml"].sum()
        a.set_title(f"{titulos[n]}\n{pct:.0f}% da traqueia dentro da máscara ({len(df)} exames)", fontsize=10)
        a.axis("off")
    fig.text(0.5, 0.02,
             "Laranja: máscara do método. Vermelho: traqueia marcada como pulmão. "
             "Azul: pulmão da referência. Tracejado branco: traqueia (rótulo 5 do LUNA16, fora do gabarito).",
             ha="center", fontsize=8.5)
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(SAIDA / "traqueia_3_metodos.png", dpi=200)
    print(f"figura: exame ...{uid[-12:]}, fatia {z} -> {SAIDA / 'traqueia_3_metodos.png'}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--so-figura", action="store_true",
                        help="refaz so a figura, a partir do CSV ja salvo (~1 min em vez de ~25)")
    args = parser.parse_args()
    SAIDA.mkdir(parents=True, exist_ok=True)
    modelo = load_trained_model(str(PESOS))
    metodos = {
        "baseline": segment_baseline,
        "region_growing": segment_region_growing,
        "unet": lambda v: segment_with_unet(v, modelo),
    }
    csv = SAIDA / "traqueia_por_exame.csv"
    if args.so_figura:
        df = pd.read_csv(csv)
    else:
        df = medir(sorted(pd.read_csv(SPLIT).query("conjunto == 'test'")["uid"]), metodos)
        df.to_csv(csv, index=False)
    for n in metodos:
        dentro, total = df[f"{n}_traqueia_ml"].sum(), df["traqueia_ref_ml"].sum()
        print(f"{n:15s} {dentro:.0f} de {total:.0f} mL de traqueia dentro da máscara "
              f"({100 * dentro / total:.0f}%; mediana por exame {df[f'{n}_traqueia_pct'].median():.0f}%)")
    figura(df, metodos)


if __name__ == "__main__":
    main()
