"""Gera as figuras e os diagnosticos da analise dos piores casos
(orientacao 5 do feedback da Sprint 3: "olhar onde os metodos erram, nao so
o quanto acertam").

Separado do notebook de proposito: rodar os 3 metodos em 6 exames leva varios
minutos, e um script e retomavel e nao perde progresso se o kernel cair. O
notebook analise_piores_casos_grp2.ipynb consome o que este script salva.

Para cada exame: roda o mesmo pipeline do Sprint 4 (clean_hu -> denoise ->
resample isotropico 1mm) e segmenta com os 3 metodos, salvando uma figura de
3 fatias x 5 paineis (TC, referencia, baseline, region growing, U-Net) com as
discordancias em cor.

Uso: python scripts/gerar_piores_casos.py
     Rodar a partir da raiz do repositorio -- caminho relativo (data/luna16),
     porque caminho absoluto quebra a leitura do SimpleITK nessa pasta.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import SimpleITK as sitk
from skimage import measure

from luna16.io import load_ct, load_reference_mask, TRACHEA_LABEL
from luna16.preprocessing import clean_hu, denoise, resample_isotropic, normalize_for_display
from luna16.baseline import segment_baseline
from luna16.region_growing import segment_region_growing
from luna16.unet import load_trained_model, segment_with_unet
from luna16.metrics import dice_coefficient, iou_score, sensitivity, precision

DATA_DIR = Path("data/luna16")
OUT_DIR = Path("docs/piores_casos")
TARGET = (1.0, 1.0, 1.0)
ML = float(np.prod(TARGET)) / 1000.0
PERCENTIS = (10, 50, 90)

P = "1.3.6.1.4.1.14519.5.2.1.6279.6001."

# (uid, rotulo curto, por que esta na lista)
CASOS = [
    (P + "109002525524522225658609808059", "pior-baseline",
     "Pior Dice do baseline (0,847). Region growing tambem falha (0,779); U-Net 0,967."),
    (P + "503980049263254396021509831276", "baixa-resolucao",
     "Fatias de 2,5 mm. Baseline 0,860, region growing desaba para 0,594, U-Net 0,963."),
    (P + "134996872583497382954024478441", "intermediario",
     "Caso dificil intermediario: 0,912 / 0,921 / 0,971 -- os tres metodos sofrem juntos."),
    (P + "162901839201654862079549658100", "falha-region-growing",
     "Baseline e U-Net vao bem (0,980 / 0,988) e o region growing colapsa (0,226)."),
    (P + "238522526736091851696274044574", "unet-perde",
     "Unico caso em que a U-Net perde feio: 0,973 / 0,968 / 0,928."),
    (P + "129055977637338639741695800950", "controle-bom",
     "CONTROLE: os tres metodos vao bem (0,982 / 0,976 / 0,990)."),
]

CORES = {  # discordancia em relacao a referencia
    "fp": np.array([1.0, 0.15, 0.15]),   # marcou e nao era pulmao
    "fn": np.array([0.15, 0.45, 1.0]),   # era pulmao e nao marcou
    "tp": np.array([0.10, 0.85, 0.25]),  # acerto
}


def _to_sitk(a, ref, dtype):
    img = sitk.GetImageFromArray(a.astype(dtype))
    img.CopyInformation(ref)
    return img


def preparar(uid, modelo):
    """Carrega, pre-processa e segmenta com os 3 metodos. Devolve tudo no
    espaco reamostrado de 1mm -- onde as metricas do projeto sao calculadas."""
    ct = load_ct(uid, DATA_DIR)
    ct_sitk = ct.to_sitk_image()
    ref_bin = load_reference_mask(uid, DATA_DIR)
    raw = sitk.GetArrayFromImage(sitk.ReadImage(str(DATA_DIR / "seg-lungs-LUNA16" / f"{uid}.mhd")))

    vol = sitk.GetArrayFromImage(
        resample_isotropic(_to_sitk(denoise(clean_hu(ct.array), 0.5), ct_sitk, "int16"), TARGET, False))
    ref = sitk.GetArrayFromImage(
        resample_isotropic(_to_sitk(ref_bin, ct_sitk, "uint8"), TARGET, True)).astype(bool)
    tra = sitk.GetArrayFromImage(
        resample_isotropic(_to_sitk(raw == TRACHEA_LABEL, ct_sitk, "uint8"), TARGET, True)).astype(bool)

    preds, tempos = {}, {}
    for nome, fn in [("baseline", lambda v: segment_baseline(v)),
                     ("region_growing", lambda v: segment_region_growing(v)),
                     ("unet", lambda v: segment_with_unet(v, modelo))]:
        t0 = time.time()
        preds[nome] = fn(vol)
        tempos[nome] = time.time() - t0
        print(f"      {nome}: {tempos[nome]:.1f}s", flush=True)

    return vol, ref, tra, preds, tempos, ct.spacing, ct.array.shape


def escolher_fatias(ref):
    z = np.where(ref.any(axis=(1, 2)))[0]
    if len(z) == 0:
        return [ref.shape[0] // 2] * 3
    return [int(np.percentile(z, p)) for p in PERCENTIS]


def metricas(pred, ref, tra):
    fp = pred & ~ref
    lbl = measure.label(fp, connectivity=1)
    tam = np.bincount(lbl.ravel())
    if tam.size > 1:
        tam[0] = 0
        maior_fp = int(tam.max())
    else:
        maior_fp = 0
    lblp = measure.label(pred, connectivity=1)
    tamp = np.bincount(lblp.ravel())
    if tamp.size > 1:
        tamp[0] = 0
        n_comp = int((tamp > 0).sum())
    else:
        n_comp = 0
    return {
        "dice": round(dice_coefficient(pred, ref), 4),
        "iou": round(iou_score(pred, ref), 4),
        "sensibilidade": round(sensitivity(pred, ref), 4),
        "precisao": round(precision(pred, ref), 4),
        "volume_ml": round(int(pred.sum()) * ML, 1),
        "fp_ml": round(int(fp.sum()) * ML, 1),
        "fn_ml": round(int((ref & ~pred).sum()) * ML, 1),
        "maior_blob_fp_ml": round(maior_fp * ML, 1),
        "n_componentes": n_comp,
        "frac_traqueia": round(float((pred & tra).sum() / tra.sum()), 4) if tra.sum() else 0.0,
    }


def montar_figura(vol, ref, preds, fatias, uid, rotulo, mets, caminho):
    metodos = [("baseline", "Baseline"), ("region_growing", "Region growing"), ("unet", "U-Net 2D")]
    fig, axes = plt.subplots(3, 5, figsize=(21, 12.8))
    linhas = ["Inicio do pulmao (p10)", "Meio do pulmao (p50)", "Fim do pulmao (p90)"]

    for i, z in enumerate(fatias):
        ct_s = normalize_for_display(vol[z])
        r = ref[z]

        axes[i, 0].imshow(ct_s, cmap="gray", vmin=0, vmax=1)
        axes[i, 0].set_ylabel(f"{linhas[i]}\nfatia z={z}", fontsize=10)

        over_ref = np.dstack([ct_s] * 3)
        over_ref[r] = 0.45 * over_ref[r] + 0.55 * np.array([1.0, 0.85, 0.1])
        axes[i, 1].imshow(over_ref)

        for j, (chave, _) in enumerate(metodos, start=2):
            p = preds[chave][z]
            over = np.dstack([ct_s] * 3)
            tp, fp_s, fn_s = p & r, p & ~r, r & ~p
            over[tp] = 0.55 * over[tp] + 0.45 * CORES["tp"]
            over[fp_s] = CORES["fp"]
            over[fn_s] = CORES["fn"]
            axes[i, j].imshow(over)
            axes[i, j].set_xlabel(f"Dice da fatia: {dice_coefficient(p, r):.4f}", fontsize=9)

        for j in range(5):
            axes[i, j].set_xticks([])
            axes[i, j].set_yticks([])

    titulos = ["TC original (HU)", "Referencia (seg-lungs)"] + [
        f"{nome}\nDice {mets[c]['dice']:.4f}" for c, nome in metodos]
    for j, t in enumerate(titulos):
        axes[0, j].set_title(t, fontsize=11, fontweight="bold")

    handles = [
        mpatches.Patch(color=CORES["tp"] * 0.8, label="acerto (concorda com a referencia)"),
        mpatches.Patch(color=CORES["fp"], label="falso positivo (marcou e nao e pulmao)"),
        mpatches.Patch(color=CORES["fn"], label="falso negativo (e pulmao e nao marcou)"),
        mpatches.Patch(color=[1.0, 0.85, 0.1], label="referencia (painel 2)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=10, frameon=False,
               bbox_to_anchor=(0.5, 0.005))
    fig.suptitle(f"[{rotulo}]  {uid}", fontsize=11)
    fig.tight_layout(rect=[0, 0.035, 1, 0.965])
    fig.savefig(caminho, dpi=100, bbox_inches="tight")
    plt.close(fig)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Carregando U-Net treinada...", flush=True)
    modelo = load_trained_model(str(DATA_DIR / "unet_baseline.pt"))

    linhas = []
    for i, (uid, rotulo, _) in enumerate(CASOS, 1):
        print(f"[{i}/{len(CASOS)}] {rotulo}  ...{uid[-12:]}", flush=True)
        vol, ref, tra, preds, tempos, spacing, shape0 = preparar(uid, modelo)
        fatias = escolher_fatias(ref)
        mets = {c: metricas(p, ref, tra) for c, p in preds.items()}

        png = OUT_DIR / f"{i:02d}_{rotulo}_{uid[-12:]}.png"
        montar_figura(vol, ref, preds, fatias, uid, rotulo, mets, png)

        for metodo, m in mets.items():
            linhas.append({
                "ordem": i, "rotulo": rotulo, "uid": uid, "uid_curto": uid[-12:],
                "metodo": metodo, "arquivo_png": png.name,
                "fatias": "|".join(map(str, fatias)),
                "spacing_z_mm": round(spacing[2], 4), "spacing_xy_mm": round(spacing[0], 4),
                "volume_ref_ml": round(int(ref.sum()) * ML, 1),
                "tempo_seg": round(tempos[metodo], 1), **m,
            })
        pd.DataFrame(linhas).to_csv(OUT_DIR / "metricas_piores_casos.csv", index=False)
        print(f"      -> {png.name}  "
              + "  ".join(f"{k}={v['dice']:.4f}" for k, v in mets.items()), flush=True)

    print("\nCONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
