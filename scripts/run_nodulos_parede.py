"""
Verifica se a segmentacao do pulmao apaga nodulos -- em especial os colados na
parede (justapleurais), que a pre-banca apontou como risco: o limiar de -600 HU
e a morfologia podem deixar o nodulo de fora da mascara, e ai o detector que
vem depois nunca o encontra.

Para cada nodulo anotado (annotations.csv, radiologistas) nos exames de teste
do split 70/15/15, mede que fracao da esfera do nodulo (centro + diametro
anotados) cai dentro da mascara de cada metodo -- baseline, region growing,
U-Net -- e da propria mascara de referencia (seg-lungs-LUNA16, que tambem e
gerada por algoritmo e pode excluir o nodulo).

Nodulo "na borda": a esfera encosta no limite do pulmao, ou seja, a distancia
do centro ate fora da referencia (com buracos preenchidos) e <= raio + 2 mm.
Inclui parede toracica e tambem mediastino/diafragma -- e uma aproximacao
geometrica, nao uma classificacao radiologica.

Uso (a partir da raiz do repositorio): python scripts/run_nodulos_parede.py
Retomavel: pula exames que ja estao no CSV de saida.
Salva:
  data/luna16/nodulos_parede_test.csv          (uma linha por nodulo)
  data/luna16/nodulos_parede_resumo.csv        (por metodo x borda/interior)
"""
import functools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd
import SimpleITK as sitk
from scipy import ndimage

from luna16.baseline import segment_baseline
from luna16.io import load_ct, load_reference_mask
from luna16.lung_air import fill_holes_per_slice
from luna16.nodules import annotations_for_patient, load_annotations, world_to_resampled_voxel
from luna16.preprocessing import clean_hu, denoise, resample_isotropic
from luna16.region_growing import segment_region_growing
from luna16.unet import load_trained_model, segment_with_unet

DATA_DIR = Path("data/luna16")
OUT_PATH = DATA_DIR / "nodulos_parede_test.csv"
RESUMO_PATH = DATA_DIR / "nodulos_parede_resumo.csv"
MARGEM_BORDA_MM = 2.0
# nodulo "preservado" se ao menos metade da esfera esta dentro da mascara
LIMIAR_COBERTURA = 0.5


def _to_sitk(array: np.ndarray, reference: sitk.Image, dtype: str) -> sitk.Image:
    img = sitk.GetImageFromArray(array.astype(dtype))
    img.CopyInformation(reference)
    return img


def preparar(uid: str):
    """Mesmo pre-processamento de pipeline.run_pipeline_for_uid, devolvendo
    tambem a origem do espaco reamostrado (para converter as coordenadas)."""
    ct = load_ct(uid, DATA_DIR)
    ct_sitk = ct.to_sitk_image()
    vol_sitk = resample_isotropic(_to_sitk(denoise(clean_hu(ct.array), 0.5), ct_sitk, "int16"), (1.0, 1.0, 1.0), False)
    ref_sitk = resample_isotropic(_to_sitk(load_reference_mask(uid, DATA_DIR), ct_sitk, "uint8"), (1.0, 1.0, 1.0), True)
    return sitk.GetArrayFromImage(vol_sitk), sitk.GetArrayFromImage(ref_sitk).astype(bool), vol_sitk.GetOrigin()


def esfera(shape, centro, raio):
    """Indices (z, y, x) dos voxels da esfera do nodulo, recortada ao volume."""
    r = int(np.ceil(raio))
    cz, cy, cx = centro
    zz, yy, xx = np.mgrid[cz - r : cz + r + 1, cy - r : cy + r + 1, cx - r : cx + r + 1]
    dentro = (zz - cz) ** 2 + (yy - cy) ** 2 + (xx - cx) ** 2 <= raio**2
    dentro &= (zz >= 0) & (zz < shape[0]) & (yy >= 0) & (yy < shape[1]) & (xx >= 0) & (xx < shape[2])
    return zz[dentro], yy[dentro], xx[dentro]


def avaliar_exame(uid: str, anotacoes: pd.DataFrame, metodos: dict) -> list[dict]:
    vol, ref, origem = preparar(uid)
    mascaras = {"referencia": ref} | {nome: fn(vol) for nome, fn in metodos.items()}
    # distancia (mm, espaco isotropico de 1 mm) de cada voxel ate fora do pulmao
    dist_borda = ndimage.distance_transform_edt(fill_holes_per_slice(ref))

    linhas = []
    for _, nod in anotacoes.iterrows():
        centro = world_to_resampled_voxel((nod["coordX"], nod["coordY"], nod["coordZ"]), origem)
        raio = nod["diameter_mm"] / 2
        zz, yy, xx = esfera(vol.shape, centro, raio)
        cz, cy, cx = (min(max(c, 0), s - 1) for c, s in zip(centro, vol.shape))
        dist = float(dist_borda[cz, cy, cx])
        linha = {
            "uid": uid,
            "diametro_mm": round(float(nod["diameter_mm"]), 2),
            "dist_borda_mm": round(dist, 1),
            "na_borda": dist <= raio + MARGEM_BORDA_MM,
        }
        for nome, m in mascaras.items():
            linha[f"cobertura_{nome}"] = round(float(m[zz, yy, xx].mean()), 3) if len(zz) else np.nan
        linhas.append(linha)
    return linhas


def resumir(df: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for nome in ["referencia", "baseline", "region_growing", "unet"]:
        col = f"cobertura_{nome}"
        for grupo, sub in [("todos", df), ("na borda", df[df["na_borda"]]), ("interior", df[~df["na_borda"]])]:
            linhas.append(
                {
                    "mascara": nome,
                    "grupo": grupo,
                    "n_nodulos": len(sub),
                    "preservados (>=50% dentro)": int((sub[col] >= LIMIAR_COBERTURA).sum()),
                    "perdidos (<50% dentro)": int((sub[col] < LIMIAR_COBERTURA).sum()),
                    "cobertura media": round(float(sub[col].mean()), 3) if len(sub) else np.nan,
                }
            )
    return pd.DataFrame(linhas)


def main():
    split = pd.read_csv(DATA_DIR / "split_full.csv")
    test_uids = set(split.loc[split["conjunto"] == "test", "uid"])
    anotacoes = load_annotations(DATA_DIR)
    uids = sorted(test_uids & set(anotacoes["seriesuid"]))
    print(f"{len(uids)} exames de teste com nodulo anotado", flush=True)

    feitos = pd.read_csv(OUT_PATH) if OUT_PATH.exists() else pd.DataFrame(columns=["uid"])
    linhas = feitos.to_dict("records")
    pendentes = [u for u in uids if u not in set(feitos["uid"])]

    modelo = load_trained_model(str(DATA_DIR / "unet_baseline.pt"))
    metodos = {
        "baseline": segment_baseline,
        "region_growing": segment_region_growing,
        "unet": functools.partial(segment_with_unet, model=modelo),
    }
    for i, uid in enumerate(pendentes, 1):
        novas = avaliar_exame(uid, annotations_for_patient(anotacoes, uid), metodos)
        linhas.extend(novas)
        pd.DataFrame(linhas).to_csv(OUT_PATH, index=False)
        print(f"[{i}/{len(pendentes)}] {uid[-12:]}  {len(novas)} nodulo(s)", flush=True)

    df = pd.DataFrame(linhas)
    resumo = resumir(df)
    resumo.to_csv(RESUMO_PATH, index=False)
    print("\n" + resumo.to_string(index=False), flush=True)
    print("\nCONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
