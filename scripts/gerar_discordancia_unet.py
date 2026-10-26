"""
Gera as imagens dos exames em que a U-Net mais discorda do gabarito
(seg-lungs-LUNA16), para o grupo julgar quem errou -- pedido do feedback da
Sprint 4: o gabarito vem de outro algoritmo, entao quando a rede discorda dele
nem sempre e a rede que esta errada.

Os exames sao ranqueados pelo volume de discordancia (mL so na U-Net + mL so
na referencia), calculado direto de data/luna16/sprint_unet_test.csv: com
voxels de 1 mm3, TP = Dice x (pred + ref) / 2. So os N primeiros sao
segmentados de novo para gerar as imagens.

Para cada exame, duas fatias axiais: a com mais voxels marcados so pela U-Net
(azul) e a com mais voxels marcados so pela referencia (laranja).

Uso (a partir da raiz do repositorio): python scripts/gerar_discordancia_unet.py
Salva em docs/discordancia_unet/:
  NN_<fim do uid>.png
  discordancia.csv  (com colunas veredito/comentario em branco, para o grupo)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import SimpleITK as sitk

from luna16.io import load_ct, load_reference_mask
from luna16.preprocessing import clean_hu, denoise, normalize_for_display, resample_isotropic
from luna16.unet import load_trained_model, segment_with_unet

DATA_DIR = Path("data/luna16")
OUT_DIR = Path("docs/discordancia_unet")
N_EXAMES = 6
AZUL = np.array([42, 120, 214]) / 255  # so a U-Net marca
LARANJA = np.array([235, 104, 52]) / 255  # so a referencia marca
VERDE = np.array([46, 160, 110]) / 255


def ranquear() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "sprint_unet_test.csv")
    tp = df["dice"] * (df["pred_voxels"] + df["ref_voxels"]) / 2
    df["so_unet_ml"] = ((df["pred_voxels"] - tp) / 1000).round(1)
    df["so_referencia_ml"] = ((df["ref_voxels"] - tp) / 1000).round(1)
    df["discordancia_ml"] = df["so_unet_ml"] + df["so_referencia_ml"]
    return df.sort_values("discordancia_ml", ascending=False).head(N_EXAMES).reset_index(drop=True)


def preparar(uid: str):
    ct = load_ct(uid, DATA_DIR)
    s = ct.to_sitk_image()

    def to_sitk(a, dtype):
        img = sitk.GetImageFromArray(a.astype(dtype))
        img.CopyInformation(s)
        return img

    vol = sitk.GetArrayFromImage(resample_isotropic(to_sitk(denoise(clean_hu(ct.array), 0.5), "int16"), (1.0, 1.0, 1.0), False))
    ref = sitk.GetArrayFromImage(resample_isotropic(to_sitk(load_reference_mask(uid, DATA_DIR), "uint8"), (1.0, 1.0, 1.0), True))
    return vol, ref.astype(bool)


def sobrepor(ct_s: np.ndarray, mascara: np.ndarray, cor: np.ndarray) -> np.ndarray:
    rgb = np.dstack([ct_s] * 3)
    rgb[mascara] = 0.55 * rgb[mascara] + 0.45 * cor
    return rgb


def figura(uid: str, linha: pd.Series, vol, ref, pred, caminho: Path) -> tuple[int, int]:
    so_unet = pred & ~ref
    so_ref = ref & ~pred
    z_unet = int(so_unet.sum(axis=(1, 2)).argmax())
    z_ref = int(so_ref.sum(axis=(1, 2)).argmax())

    fig, axes = plt.subplots(2, 4, figsize=(20, 10.5))
    for linha_ax, z, rotulo in [(axes[0], z_unet, "fatia com mais área só da U-Net"), (axes[1], z_ref, "fatia com mais área só da referência")]:
        ct_s = normalize_for_display(vol[z])
        disc = np.dstack([ct_s] * 3)
        disc[so_unet[z]] = AZUL
        disc[so_ref[z]] = LARANJA
        paineis = [
            (np.dstack([ct_s] * 3), "TC (janela de pulmão)"),
            (sobrepor(ct_s, ref[z], VERDE), "Referência (LUNA16)"),
            (sobrepor(ct_s, pred[z], VERDE), "U-Net"),
            (disc, "Discordância"),
        ]
        for ax, (img, titulo) in zip(linha_ax, paineis):
            ax.imshow(img)
            if linha_ax is axes[0]:
                ax.set_title(titulo, fontsize=15)
            ax.set_xticks([])
            ax.set_yticks([])
        linha_ax[0].set_ylabel(f"z = {z}\n{rotulo}", fontsize=13)

    fig.suptitle(
        f"Exame …{uid[-12:]} — Dice {linha['dice']:.4f}".replace(".", ",")
        + f" — só U-Net {linha['so_unet_ml']:.0f} mL, só referência {linha['so_referencia_ml']:.0f} mL",
        fontsize=17,
    )
    fig.text(
        0.5, 0.01,
        "Azul: a U-Net marca e a referência não. Laranja: a referência marca e a U-Net não. "
        "A referência também foi gerada por algoritmo: julgar quem está certo olhando a anatomia.",
        ha="center", fontsize=13,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(caminho, dpi=110)
    plt.close(fig)
    return z_unet, z_ref


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ranking = ranquear()
    modelo = load_trained_model(str(DATA_DIR / "unet_baseline.pt"))

    linhas = []
    for i, linha in ranking.iterrows():
        uid = linha["uid"]
        vol, ref = preparar(uid)
        pred = segment_with_unet(vol, modelo)
        arquivo = OUT_DIR / f"{i + 1:02d}_{uid[-12:]}.png"
        z_unet, z_ref = figura(uid, linha, vol, ref, pred, arquivo)
        linhas.append(
            {
                "posicao": i + 1,
                "uid": uid,
                "dice": round(float(linha["dice"]), 4),
                "so_unet_ml": linha["so_unet_ml"],
                "so_referencia_ml": linha["so_referencia_ml"],
                "z_mais_so_unet": z_unet,
                "z_mais_so_referencia": z_ref,
                "imagem": arquivo.name,
                "veredito": "",
                "comentario": "",
            }
        )
        print(f"[{i + 1}/{len(ranking)}] {uid[-12:]} -> {arquivo}", flush=True)

    pd.DataFrame(linhas).to_csv(OUT_DIR / "discordancia.csv", index=False)
    print("CONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
