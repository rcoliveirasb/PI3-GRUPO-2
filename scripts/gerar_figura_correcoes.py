"""Figura antes/depois das duas correcoes da Sprint 5.

Uma linha por correcao, tres paineis: TC original, antes e depois. Mostra os
dois exames que motivaram cada conserto:

  linha 1 -- semente do region growing, no exame ...079549658100 (0,226 -> 0,978)
  linha 2 -- limpeza espacial da U-Net, no exame ...696274044574 (0,928 -> 0,968)

Os erros aparecem em cor sobre a TC: vermelho para falso positivo (marcou e
nao e pulmao) e azul para falso negativo (e pulmao e nao marcou). Nas duas
linhas o painel "depois" tem visivelmente menos cor -- e isso que a figura
precisa comunicar.

Uso: python scripts/gerar_figura_correcoes.py   (a partir da raiz do repositorio)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import SimpleITK as sitk

from luna16.io import load_ct, load_reference_mask
from luna16.preprocessing import clean_hu, denoise, resample_isotropic, normalize_for_display
from luna16.region_growing import segment_region_growing
from luna16.unet import load_trained_model, segment_with_unet
from luna16.metrics import dice_coefficient

DATA_DIR = Path("data/luna16")
OUT_DIR = Path("docs/piores_casos")
TARGET = (1.0, 1.0, 1.0)
P = "1.3.6.1.4.1.14519.5.2.1.6279.6001."

FP = np.array([1.0, 0.15, 0.15])   # marcou e nao e pulmao
FN = np.array([0.15, 0.45, 1.0])   # e pulmao e nao marcou
TINTA, TINTA_2, SUPERFICIE = "#0b0b0b", "#52514e", "#fcfcfb"


def _prep(uid):
    ct = load_ct(uid, DATA_DIR)
    s = ct.to_sitk_image()
    img = sitk.GetImageFromArray(denoise(clean_hu(ct.array), 0.5).astype("int16"))
    img.CopyInformation(s)
    vol = sitk.GetArrayFromImage(resample_isotropic(img, TARGET, is_mask=False))
    r = sitk.GetImageFromArray(load_reference_mask(uid, DATA_DIR).astype("uint8"))
    r.CopyInformation(s)
    ref = sitk.GetArrayFromImage(resample_isotropic(r, TARGET, is_mask=True)).astype(bool)
    return vol, ref


def _painel(ax, ct_s, pred_s, ref_s):
    over = np.dstack([ct_s * 0.85] * 3)
    over[pred_s & ~ref_s] = FP
    over[ref_s & ~pred_s] = FN
    ax.imshow(over)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    modelo = load_trained_model(str(DATA_DIR / "unet_baseline.pt"))

    print("preparando exames...", flush=True)
    casos = []

    # 1. semente do region growing
    uid = P + "162901839201654862079549658100"
    vol, ref = _prep(uid)
    casos.append(("Semente do region growing", uid, vol, ref,
                  segment_region_growing(vol, seed_max_hu=-1e9),
                  segment_region_growing(vol),
                  "semente caía em −602 HU", "semente abaixo de −750 HU"))

    # 2. limpeza espacial da U-Net
    uid = P + "238522526736091851696274044574"
    vol, ref = _prep(uid)
    casos.append(("Limpeza espacial da U-Net", uid, vol, ref,
                  segment_with_unet(vol, modelo, limpar_fora_do_torax=False),
                  segment_with_unet(vol, modelo),
                  "marcava ar da mesa do tomógrafo", "componentes fora do tórax descartados"))

    fig, axes = plt.subplots(2, 3, figsize=(15.5, 10.4), facecolor=SUPERFICIE)

    for i, (titulo, uid, vol, ref, antes, depois, leg_a, leg_d) in enumerate(casos):
        z = int(np.percentile(np.where(ref.any(axis=(1, 2)))[0], 50))
        ys, xs = np.where(ref[z])
        m = 24
        y0, y1 = max(0, ys.min() - m), min(ref.shape[1], ys.max() + m)
        x0, x1 = max(0, xs.min() - m), min(ref.shape[2], xs.max() + m)

        ct_s = normalize_for_display(vol[z])[y0:y1, x0:x1]
        ref_s = ref[z][y0:y1, x0:x1]

        axes[i, 0].imshow(ct_s, cmap="gray", vmin=0, vmax=1)
        axes[i, 0].set_xticks([]); axes[i, 0].set_yticks([])
        for sp in axes[i, 0].spines.values():
            sp.set_visible(False)
        axes[i, 0].set_ylabel(f"{titulo}\n…{uid[-12:]}", fontsize=13, fontweight="bold",
                              color=TINTA, labelpad=14)

        _painel(axes[i, 1], ct_s, antes[z][y0:y1, x0:x1], ref_s)
        _painel(axes[i, 2], ct_s, depois[z][y0:y1, x0:x1], ref_s)

        da, dd = dice_coefficient(antes, ref), dice_coefficient(depois, ref)
        axes[i, 1].set_title(f"ANTES — Dice {da:.3f}".replace(".", ","),
                             fontsize=16, fontweight="bold", color="#c53030", pad=10)
        axes[i, 2].set_title(f"DEPOIS — Dice {dd:.3f}".replace(".", ","),
                             fontsize=16, fontweight="bold", color="#1b7a3d", pad=10)
        axes[i, 0].set_title("TC original" if i == 0 else "", fontsize=16,
                             fontweight="bold", color=TINTA, pad=10)
        axes[i, 1].set_xlabel(leg_a, fontsize=12, color=TINTA_2, labelpad=8)
        axes[i, 2].set_xlabel(leg_d, fontsize=12, color=TINTA_2, labelpad=8)
        print(f"  {titulo}: {da:.4f} -> {dd:.4f}", flush=True)

    fig.legend(handles=[mpatches.Patch(color=FP, label="falso positivo (marcou e não é pulmão)"),
                        mpatches.Patch(color=FN, label="falso negativo (é pulmão e não marcou)")],
               loc="lower center", ncol=2, fontsize=13, frameon=False, bbox_to_anchor=(0.5, 0.005))
    fig.suptitle("As duas correções da Sprint 5", fontsize=23, fontweight="bold",
                 color=TINTA, y=0.985)
    fig.tight_layout(rect=[0, 0.045, 1, 0.955])
    cam = OUT_DIR / "slide_3_correcoes_antes_depois.png"
    fig.savefig(cam, dpi=140, bbox_inches="tight", facecolor=SUPERFICIE)
    plt.close(fig)
    print(f"-> {cam}")
    print("CONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
