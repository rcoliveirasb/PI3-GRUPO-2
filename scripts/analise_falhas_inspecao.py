"""Quantifica os dois padroes de erro observados na inspecao visual dos 12
exames (scripts/inspecao_visual_teste.py), para que o relato nao dependa so
de leitura de imagem:

  1. Traqueia/vias aereas centrais incluidas na predicao. A mascara de
     referencia rotula a traqueia como 5 e o projeto a exclui de proposito
     (traqueia nao e parenquima), mas o baseline a segmenta junto porque ela
     e ar e fica conectada aos pulmoes depois do fill 2D.

  2. Falso positivo abaixo do diafragma (ar gastrico/alcas intestinais).
     Testado geometricamente: o blob de FP esta abaixo da fatia mais inferior
     em que a referencia ainda tem pulmao?

Uso: python scripts/analise_falhas_inspecao.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd
import SimpleITK as sitk
from skimage import measure

from luna16.io import load_ct, load_reference_mask, TRACHEA_LABEL
from luna16.preprocessing import clean_hu, denoise, resample_isotropic
from luna16.baseline import segment_baseline

SEED = 42
DATA_DIR = Path("data/luna16")
OUT_DIR = Path("entrega/inspecao_visual")
TARGET = (1.0, 1.0, 1.0)
ML = float(np.prod(TARGET)) / 1000.0


def _to_sitk(a, ref, dtype):
    img = sitk.GetImageFromArray(a.astype(dtype))
    img.CopyInformation(ref)
    return img


def analisar(uid):
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

    pred = segment_baseline(vol)
    fp = pred & ~ref

    # z do pulmao na referencia (indice 0 = base do exame, LUNA16 e
    # inferior->superior, entao z menor = mais proximo do abdome)
    z_ref = np.where(ref.any(axis=(1, 2)))[0]
    z_base = int(z_ref.min())

    # blobs de FP >= 5 mL, classificados por posicao em relacao a base do pulmao
    lbl = measure.label(fp, connectivity=1)
    fp_subdiaf_ml = 0.0
    maior_subdiaf = None
    for p in measure.regionprops(lbl):
        if p.area * ML < 5.0:
            continue
        zc = p.centroid[0]
        if zc < z_base:  # centroide abaixo da fatia mais baixa com pulmao
            fp_subdiaf_ml += p.area * ML
            if maior_subdiaf is None or p.area > maior_subdiaf[0]:
                maior_subdiaf = (p.area, zc, z_base)

    tra_pred_ml = float((pred & tra).sum()) * ML
    return {
        "uid_curto": uid[-12:],
        "traqueia_ref_ml": round(float(tra.sum()) * ML, 1),
        "traqueia_dentro_pred_ml": round(tra_pred_ml, 1),
        "fp_total_ml": round(float(fp.sum()) * ML, 1),
        "fp_subdiafragmatico_ml": round(fp_subdiaf_ml, 1),
        "fp_subdiaf_fatias_abaixo_da_base": (
            round(float(maior_subdiaf[2] - maior_subdiaf[1]), 1) if maior_subdiaf else 0.0),
    }


def main():
    split = pd.read_csv(DATA_DIR / "split_full.csv")
    test = sorted(split.loc[split["conjunto"] == "test", "uid"].tolist())
    rng = np.random.default_rng(SEED)
    escolhidos = sorted(rng.choice(test, size=12, replace=False).tolist())

    linhas = []
    for i, uid in enumerate(escolhidos, 1):
        r = analisar(uid)
        r["ordem"] = i
        linhas.append(r)
        print(f"[{i}/12] {r['uid_curto']}  traqueia {r['traqueia_dentro_pred_ml']:.1f}/"
              f"{r['traqueia_ref_ml']:.1f} mL  |  FP total {r['fp_total_ml']:.1f} mL  "
              f"(subdiafragmatico {r['fp_subdiafragmatico_ml']:.1f} mL)", flush=True)

    df = pd.DataFrame(linhas)[
        ["ordem", "uid_curto", "traqueia_ref_ml", "traqueia_dentro_pred_ml",
         "fp_total_ml", "fp_subdiafragmatico_ml", "fp_subdiaf_fatias_abaixo_da_base"]]
    df.to_csv(OUT_DIR / "analise_falhas_quantitativa.csv", index=False)

    print("\n=== resumo dos 12 ===")
    print(f"traqueia incluida: {df['traqueia_dentro_pred_ml'].sum():.0f} mL de "
          f"{df['traqueia_ref_ml'].sum():.0f} mL rotulados (todos os 12 casos)")
    n_sub = int((df["fp_subdiafragmatico_ml"] > 0).sum())
    print(f"casos com FP abaixo do diafragma (>=5 mL): {n_sub}/12")
    print("CONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
