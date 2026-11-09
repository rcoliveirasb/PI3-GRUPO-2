"""A segmentacao do pulmao apaga nodulos?

Para cada nodulo anotado (annotations.csv) nos exames do conjunto de teste
(split 70/15/15), verifica se ele continua dentro da mascara de pulmao de cada
metodo -- baseline, region growing e U-Net (com as correcoes de 26/10) -- e da
mascara de referencia do LUNA16. Um nodulo que a mascara apaga nunca chega ao
detector de nodulos, entao essa e uma metrica que o Dice nao mostra: o Dice mede
o volume do pulmao inteiro, e um nodulo de 6 mm pesa quase nada nele.

Criterios (fixados antes de rodar):
  - Nodulo = esfera com o diametro anotado, no espaco reamostrado de 1 mm.
  - MANTIDO se >= 50% dos voxels da esfera estao dentro da mascara; senao, APAGADO.
  - COLADO NA BORDA (justapleural) se a esfera inflada em 2 mm toca tecido
    (HU > -300) fora da mascara de referencia, isto e, parede toracica ou
    mediastino. Senao, NO INTERIOR.
  - Comparacao pareada U-Net x baseline: teste exato de McNemar sobre os
    nodulos em que os dois metodos discordam.

Uso (a partir da raiz do repositorio):
  python scripts/analise_nodulos_apagados.py
Retomavel: os nodulos ja avaliados ficam em data/luna16/nodulos_apagados_teste.csv.
Salva:
  data/luna16/nodulos_apagados_teste.csv     (uma linha por nodulo)
  data/luna16/nodulos_apagados_resumo.csv    (tabela por metodo)
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd
import SimpleITK as sitk
from scipy.stats import binomtest

from luna16.baseline import segment_baseline
from luna16.io import load_ct, load_reference_mask
from luna16.nodules import world_to_resampled_voxel
from luna16.preprocessing import clean_hu, denoise, resample_isotropic
from luna16.region_growing import segment_region_growing
from luna16.unet import load_trained_model, segment_with_unet

DATA_DIR = Path("data/luna16")  # relativo: o "°" do caminho quebra o SimpleITK
SAIDA = DATA_DIR / "nodulos_apagados_teste.csv"
RESUMO = DATA_DIR / "nodulos_apagados_resumo.csv"
FRAC_MANTIDO = 0.5
MARGEM_BORDA_MM = 2.0
HU_TECIDO = -300
METODOS = ["referencia", "baseline", "region_growing", "unet"]
NOMES = {
    "referencia": "Referência do LUNA16",
    "baseline": "Baseline (limiar -600 HU)",
    "region_growing": "Region growing",
    "unet": "U-Net 2D",
}


def _prep(uid):
    """Mesmo pre-processamento da avaliacao oficial (pipeline.run_pipeline_for_uid)."""
    ct = load_ct(uid, DATA_DIR)
    s = ct.to_sitk_image()
    img = sitk.GetImageFromArray(denoise(clean_hu(ct.array), 0.5).astype("int16"))
    img.CopyInformation(s)
    vol_img = resample_isotropic(img, (1.0, 1.0, 1.0), is_mask=False)
    ref_img = sitk.GetImageFromArray(load_reference_mask(uid, DATA_DIR).astype("uint8"))
    ref_img.CopyInformation(s)
    ref = sitk.GetArrayFromImage(resample_isotropic(ref_img, (1.0, 1.0, 1.0), is_mask=True)).astype(bool)
    return sitk.GetArrayFromImage(vol_img), ref, vol_img.GetOrigin()


def _esfera(shape, centro, raio):
    """Recorte (slices) e mascara booleana de uma esfera, sem alocar o volume todo."""
    r = int(np.ceil(raio)) + 1
    lo = [max(c - r, 0) for c in centro]
    hi = [min(c + r + 1, n) for c, n in zip(centro, shape)]
    zz, yy, xx = np.ogrid[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    d2 = (zz - centro[0]) ** 2 + (yy - centro[1]) ** 2 + (xx - centro[2]) ** 2
    return tuple(slice(a, b) for a, b in zip(lo, hi)), d2 <= raio**2


def main():
    split = pd.read_csv(DATA_DIR / "split_full.csv")
    teste = set(split.loc[split["conjunto"] == "test", "uid"])
    ann = pd.read_csv(DATA_DIR / "annotations.csv")
    ann = ann[ann["seriesuid"].isin(teste)].reset_index(drop=True)
    uids = sorted(ann["seriesuid"].unique())
    print(f"{len(ann)} nodulos em {len(uids)} exames de teste", flush=True)

    feitos = pd.read_csv(SAIDA) if SAIDA.exists() else pd.DataFrame()
    linhas = feitos.to_dict("records")
    ja = set(feitos["uid"]) if len(feitos) else set()

    modelo = load_trained_model(str(DATA_DIR / "unet_baseline.pt"))
    for i, uid in enumerate(uids, 1):
        if uid in ja:
            continue
        t0 = time.time()
        vol, ref, origem = _prep(uid)
        mascaras = {
            "referencia": ref,
            "baseline": segment_baseline(vol),
            "region_growing": segment_region_growing(vol),
            "unet": segment_with_unet(vol, modelo),
        }
        for _, n in ann[ann["seriesuid"] == uid].iterrows():
            centro = world_to_resampled_voxel((n["coordX"], n["coordY"], n["coordZ"]), origem)
            raio = n["diameter_mm"] / 2
            sl, esf = _esfera(vol.shape, centro, raio)
            sl2, esf2 = _esfera(vol.shape, centro, raio + MARGEM_BORDA_MM)
            tecido_fora = (vol[sl2] > HU_TECIDO) & ~ref[sl2] & esf2
            linha = {
                "uid": uid,
                "uid_curto": uid[-12:],
                "diametro_mm": round(float(n["diameter_mm"]), 2),
                "posicao": "colado_na_borda" if tecido_fora.any() else "interior",
            }
            for m, mask in mascaras.items():
                frac = float(mask[sl][esf].mean())
                linha[f"{m}_frac"] = round(frac, 3)
                linha[f"{m}_mantido"] = frac >= FRAC_MANTIDO
            linhas.append(linha)
        pd.DataFrame(linhas).to_csv(SAIDA, index=False)
        print(f"[{i}/{len(uids)}] {uid[-12:]}  {len(ann[ann['seriesuid'] == uid])} nodulo(s)  "
              f"({time.time() - t0:.0f}s)", flush=True)

    d = pd.DataFrame(linhas)
    borda = d["posicao"] == "colado_na_borda"
    resumo = []
    for m in METODOS:
        k = d[f"{m}_mantido"].astype(bool)
        resumo.append({
            "Máscara": NOMES[m],
            f"Nódulos mantidos (de {len(d)})": int(k.sum()),
            f"Colados na borda mantidos (de {int(borda.sum())})": int(k[borda].sum()),
            f"No interior mantidos (de {int((~borda).sum())})": int(k[~borda].sum()),
            "Apagados": int((~k).sum()),
        })
    resumo = pd.DataFrame(resumo)
    resumo.to_csv(RESUMO, index=False)
    print("\n" + resumo.to_string(index=False))

    u, b = d["unet_mantido"].astype(bool), d["baseline_mantido"].astype(bool)
    so_unet, so_base = int((u & ~b).sum()), int((b & ~u).sum())
    if so_unet + so_base:
        p = binomtest(so_unet, so_unet + so_base, 0.5).pvalue
        print(f"\nU-Net mantem {so_unet} que o baseline apaga; baseline mantem {so_base} que a U-Net apaga "
              f"(McNemar exato, p = {p:.4f})")
    print("CONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
