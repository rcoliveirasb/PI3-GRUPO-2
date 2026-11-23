"""
Figura 1 do resumo expandido: as etapas do baseline numa fatia axial.

Painéis: (a) fatia original pré-processada, na janela de pulmão; (b) limiar
HU < -600; (c) máscara final do baseline, depois da limpeza, com o contorno
da referência do LUNA16 por cima.

O exame é o de Dice mediano do baseline no Teste A (26 exames), para mostrar
um caso típico, nem o melhor nem o pior. A fatia é a do meio do pulmão.

Uso (a partir da raiz do repositório):
  python scripts/gerar_figura_resumo.py
Saída: docs/figura1_resumo_baseline.png
"""
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

from luna16.baseline import THRESHOLD_HU, segment_baseline
from luna16.io import load_ct, load_reference_mask
from luna16.metrics import dice_coefficient
from luna16.pipeline import _to_sitk
from luna16.preprocessing import clean_hu, denoise, resample_isotropic

DATA_DIR = Path("data/luna16")
SAIDA = Path("docs/figura1_resumo_baseline.png")


def exame_mediano() -> str:
    df = pd.read_csv(DATA_DIR / "sprint4_baseline_test.csv").sort_values("dice").reset_index(drop=True)
    return df.loc[len(df) // 2, "uid"]


def main():
    uid = exame_mediano()
    ct = load_ct(uid, DATA_DIR)
    ct_sitk = ct.to_sitk_image()
    vol = sitk.GetArrayFromImage(resample_isotropic(
        _to_sitk(denoise(clean_hu(ct.array), sigma=0.5), ct_sitk, "int16"), (1.0, 1.0, 1.0), is_mask=False))
    ref = sitk.GetArrayFromImage(resample_isotropic(
        _to_sitk(load_reference_mask(uid, DATA_DIR), ct_sitk, "uint8"), (1.0, 1.0, 1.0), is_mask=True)).astype(bool)

    pred = segment_baseline(vol)
    dice = dice_coefficient(pred, ref)
    z = int(np.median(np.nonzero(ref.any(axis=(1, 2)))[0]))

    fig, ax = plt.subplots(1, 3, figsize=(12, 4.3))
    ax[0].imshow(vol[z], cmap="gray", vmin=-1000, vmax=400)
    ax[0].set_title("(a) Fatia pré-processada")
    ax[1].imshow(vol[z] < THRESHOLD_HU, cmap="gray")
    ax[1].set_title(f"(b) Limiar: HU < {THRESHOLD_HU:.0f}")
    ax[2].imshow(vol[z], cmap="gray", vmin=-1000, vmax=400)
    ax[2].imshow(np.ma.masked_where(~pred[z], pred[z]), cmap=ListedColormap(["#ff8c00"]), alpha=0.5)
    ax[2].contour(ref[z], levels=[0.5], colors="cyan", linewidths=1.0)
    ax[2].set_title("(c) Máscara final do baseline")
    for a in ax:
        a.axis("off")
    dice_txt = f"{dice:.3f}".replace(".", ",")  # decimal com virgula, como no texto
    fig.text(0.5, 0.02,
             f"Em (c): laranja = máscara do baseline após a limpeza; contorno azul = referência do LUNA16. "
             f"Dice do exame = {dice_txt}.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    fig.savefig(SAIDA, dpi=200)
    print(f"exame ...{uid[-12:]}  fatia {z}  Dice {dice:.4f}  -> {SAIDA}")


if __name__ == "__main__":
    main()
