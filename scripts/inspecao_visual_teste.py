"""Inspecao visual de exames aleatorios do conjunto de teste (26 pacientes do
split 70/15/15, seed 42).

Para cada paciente sorteado, roda o mesmo pipeline do Sprint 4
(clean_hu -> denoise -> resample isotropico -> segment_baseline) e salva uma
figura com 3 fatias (inicio, meio e fim do pulmao) x 4 paineis:

    TC original | mascara predita | mascara de referencia | sobreposicao

A quarta coluna (sobreposicao) nao estava no pedido original mas e o painel
que mais ajuda a responder "o Dice esconde algum problema?": pinta falso
positivo em vermelho e falso negativo em azul sobre a TC, entao um erro
localizado (ex: traqueia incluida, um pulmao faltando num intervalo de
fatias) salta a vista mesmo quando o Dice global esta alto.

As fatias sao escolhidas nos percentis 10/50/90 da extensao do pulmao na
mascara de referencia, e nao na primeira/ultima fatia com pulmao: nos
extremos exatos o apice e a base aparecem com pouquissimos voxels, o que nao
permite julgar nada visualmente.

Alem das figuras, salva um CSV com diagnosticos que complementam Dice/IoU
(componentes conexos, vazamento para traqueia, pior fatia, etc).

Uso: python scripts/inspecao_visual_teste.py [N_PACIENTES]
     Rodar a partir da raiz do repositorio (caminhos relativos, ver nota em
     scripts/run_sprint4_evaluation.py).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import matplotlib

matplotlib.use("Agg")  # sem display: so salva arquivo
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import SimpleITK as sitk
from scipy import ndimage
from skimage import measure

from luna16.io import load_ct, load_reference_mask, LUNG_LABELS, TRACHEA_LABEL
from luna16.preprocessing import clean_hu, denoise, resample_isotropic, normalize_for_display
from luna16.baseline import segment_baseline
from luna16.metrics import dice_coefficient, iou_score, sensitivity, precision

SEED = 42
DATA_DIR = Path("data/luna16")
OUT_DIR = Path("entrega/inspecao_visual")
TARGET_SPACING = (1.0, 1.0, 1.0)
PERCENTIS_FATIAS = (10, 50, 90)  # inicio, meio, fim da extensao do pulmao


def _to_sitk(array: np.ndarray, reference: sitk.Image, dtype: str) -> sitk.Image:
    img = sitk.GetImageFromArray(array.astype(dtype))
    img.CopyInformation(reference)
    return img


def preparar_paciente(uid: str):
    """Roda o pipeline do Sprint 4 e devolve tudo o que a figura precisa, no
    espaco reamostrado (1mm isotropico) -- que e onde a predicao vive e onde
    as metricas do projeto sao calculadas."""
    ct = load_ct(uid, DATA_DIR)
    ct_sitk = ct.to_sitk_image()

    # mascara de referencia: binaria (rotulos 3+4) para as metricas, e o
    # rotulo 5 separado para checar vazamento para a traqueia
    ref_bin = load_reference_mask(uid, DATA_DIR)
    mask_raw = sitk.GetArrayFromImage(sitk.ReadImage(str(DATA_DIR / "seg-lungs-LUNA16" / f"{uid}.mhd")))
    trachea_bin = mask_raw == TRACHEA_LABEL

    cleaned = clean_hu(ct.array)
    denoised = denoise(cleaned, sigma=0.5)

    vol_res = sitk.GetArrayFromImage(
        resample_isotropic(_to_sitk(denoised, ct_sitk, "int16"), TARGET_SPACING, is_mask=False)
    )
    ref_res = sitk.GetArrayFromImage(
        resample_isotropic(_to_sitk(ref_bin, ct_sitk, "uint8"), TARGET_SPACING, is_mask=True)
    ).astype(bool)
    tra_res = sitk.GetArrayFromImage(
        resample_isotropic(_to_sitk(trachea_bin, ct_sitk, "uint8"), TARGET_SPACING, is_mask=True)
    ).astype(bool)

    t0 = time.time()
    pred = segment_baseline(vol_res)
    tempo = time.time() - t0

    return vol_res, pred, ref_res, tra_res, ct.spacing, ct.array.shape, tempo


def escolher_fatias(ref: np.ndarray) -> list[int]:
    """Fatias nos percentis 10/50/90 da extensao do pulmao na referencia."""
    z_com_pulmao = np.where(ref.any(axis=(1, 2)))[0]
    if len(z_com_pulmao) == 0:
        meio = ref.shape[0] // 2
        return [meio, meio, meio]
    return [int(np.percentile(z_com_pulmao, p)) for p in PERCENTIS_FATIAS]


def diagnosticos(pred: np.ndarray, ref: np.ndarray, tra: np.ndarray, spacing) -> dict:
    """Metricas que complementam Dice/IoU -- desenhadas para pegar problemas
    que uma media global esconde."""
    fp = pred & ~ref
    fn = ref & ~pred

    # componentes conexos 3D da predicao: o esperado anatomico e 1 (pulmoes
    # unidos pela traqueia/carina apos o fill) ou 2 (pulmoes separados).
    # Muito mais que isso indica fragmentos espurios.
    lbl_pred = measure.label(pred, connectivity=1)
    tam_comp = np.bincount(lbl_pred.ravel())
    tam_comp[0] = 0
    comps = np.sort(tam_comp[tam_comp > 0])[::-1]

    # maior blob de falso positivo: um FP grande e concentrado (um orgao
    # inteiro incluido) e um problema qualitativo diferente de FP difuso na
    # borda, mas os dois dao o mesmo Dice
    lbl_fp = measure.label(fp, connectivity=1)
    tam_fp = np.bincount(lbl_fp.ravel())
    tam_fp[0] = 0
    maior_fp = int(tam_fp.max()) if tam_fp.size > 1 and tam_fp.max() > 0 else 0

    lbl_fn = measure.label(fn, connectivity=1)
    tam_fn = np.bincount(lbl_fn.ravel())
    tam_fn[0] = 0
    maior_fn = int(tam_fn.max()) if tam_fn.size > 1 and tam_fn.max() > 0 else 0

    # Dice fatia a fatia: um Dice global alto pode conviver com um punhado de
    # fatias catastroficas (ex: um pulmao perdido perto da base)
    dices_z = []
    for z in range(ref.shape[0]):
        if ref[z].any() or pred[z].any():
            dices_z.append(dice_coefficient(pred[z], ref[z]))
    dices_z = np.array(dices_z) if dices_z else np.array([1.0])

    # vazamento para a traqueia (rotulo 5, que NAO e parenquima)
    tra_incluida = float((pred & tra).sum() / tra.sum()) if tra.sum() > 0 else 0.0

    vox_ml = float(np.prod(TARGET_SPACING)) / 1000.0  # mm3 -> mL

    return {
        "dice": dice_coefficient(pred, ref),
        "iou": iou_score(pred, ref),
        "sensibilidade": sensitivity(pred, ref),
        "precisao": precision(pred, ref),
        "voxels_pred": int(pred.sum()),
        "voxels_ref": int(ref.sum()),
        "volume_pred_ml": round(int(pred.sum()) * vox_ml, 1),
        "volume_ref_ml": round(int(ref.sum()) * vox_ml, 1),
        "fp_voxels": int(fp.sum()),
        "fn_voxels": int(fn.sum()),
        "maior_blob_fp_ml": round(maior_fp * vox_ml, 1),
        "maior_blob_fn_ml": round(maior_fn * vox_ml, 1),
        "n_componentes_pred": int(len(comps)),
        "frac_traqueia_incluida": round(tra_incluida, 4),
        "dice_fatia_min": round(float(dices_z.min()), 4),
        "dice_fatia_p05": round(float(np.percentile(dices_z, 5)), 4),
        "n_fatias_dice_abaixo_08": int((dices_z < 0.8).sum()),
        "n_fatias_avaliadas": int(len(dices_z)),
    }


def montar_figura(vol, pred, ref, fatias, uid, diag, caminho_png):
    fig, axes = plt.subplots(3, 4, figsize=(17, 12.5))
    rotulos_linha = ["Inicio do pulmao (p10)", "Meio do pulmao (p50)", "Fim do pulmao (p90)"]

    for i, z in enumerate(fatias):
        ct_slice = normalize_for_display(vol[z])
        p, r = pred[z], ref[z]

        axes[i, 0].imshow(ct_slice, cmap="gray", vmin=0, vmax=1)
        axes[i, 0].set_ylabel(f"{rotulos_linha[i]}\nfatia z={z}", fontsize=10)

        axes[i, 1].imshow(p, cmap="gray", vmin=0, vmax=1)
        axes[i, 2].imshow(r, cmap="gray", vmin=0, vmax=1)

        # sobreposicao: acerto em verde translucido, FP vermelho, FN azul
        over = np.dstack([ct_slice] * 3)
        tp, fp_s, fn_s = p & r, p & ~r, r & ~p
        over[tp] = 0.55 * over[tp] + 0.45 * np.array([0.1, 0.9, 0.2])
        over[fp_s] = np.array([1.0, 0.15, 0.15])
        over[fn_s] = np.array([0.15, 0.45, 1.0])
        axes[i, 3].imshow(over)

        d_z = dice_coefficient(p, r)
        axes[i, 3].set_xlabel(f"Dice da fatia: {d_z:.4f}", fontsize=9)

        for j in range(4):
            axes[i, j].set_xticks([])
            axes[i, j].set_yticks([])

    for j, t in enumerate(["TC original (HU)", "Mascara PREDITA (baseline)",
                           "Mascara de REFERENCIA", "Sobreposicao"]):
        axes[0, j].set_title(t, fontsize=11, fontweight="bold")

    fig.suptitle(
        f"{uid}\n"
        f"Dice {diag['dice']:.4f}  |  IoU {diag['iou']:.4f}  |  "
        f"Sensibilidade {diag['sensibilidade']:.4f}  |  Precisao {diag['precisao']:.4f}   "
        f"(vermelho = falso positivo, azul = falso negativo, verde = acerto)",
        fontsize=11,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.955])
    fig.savefig(caminho_png, dpi=105, bbox_inches="tight")
    plt.close(fig)


def main():
    n_pacientes = int(sys.argv[1]) if len(sys.argv) > 1 else 12

    split = pd.read_csv(DATA_DIR / "split_full.csv")
    test_uids = sorted(split.loc[split["conjunto"] == "test", "uid"].tolist())
    print(f"Conjunto de teste: {len(test_uids)} pacientes", flush=True)

    rng = np.random.default_rng(SEED)
    escolhidos = sorted(rng.choice(test_uids, size=n_pacientes, replace=False).tolist())
    print(f"Sorteados (seed={SEED}): {n_pacientes}\n", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    linhas = []
    for i, uid in enumerate(escolhidos, 1):
        t0 = time.time()
        vol, pred, ref, tra, spacing, shape_orig, t_seg = preparar_paciente(uid)
        fatias = escolher_fatias(ref)
        diag = diagnosticos(pred, ref, tra, spacing)

        png = OUT_DIR / f"caso_{i:02d}_{uid[-12:]}.png"
        montar_figura(vol, pred, ref, fatias, uid, diag, png)

        linha = {
            "ordem": i,
            "uid": uid,
            "uid_curto": uid[-12:],
            "arquivo_png": png.name,
            "fatias_plotadas": "|".join(map(str, fatias)),
            "shape_original_zyx": "x".join(map(str, shape_orig)),
            "spacing_z_mm": round(spacing[2], 4),
            "spacing_xy_mm": round(spacing[0], 4),
            "tempo_segmentacao_seg": round(t_seg, 1),
            **diag,
        }
        linhas.append(linha)
        pd.DataFrame(linhas).to_csv(OUT_DIR / "diagnosticos_inspecao_visual.csv", index=False)

        print(
            f"[{i}/{n_pacientes}] {uid[-12:]}  dice={diag['dice']:.4f}  "
            f"prec={diag['precisao']:.4f}  sens={diag['sensibilidade']:.4f}  "
            f"comp={diag['n_componentes_pred']}  traqueia={diag['frac_traqueia_incluida']:.3f}  "
            f"pior_fatia={diag['dice_fatia_min']:.3f}  ({time.time()-t0:.0f}s)",
            flush=True,
        )

    print(f"\nCONCLUIDO -- {n_pacientes} figuras em {OUT_DIR}/", flush=True)


if __name__ == "__main__":
    main()
