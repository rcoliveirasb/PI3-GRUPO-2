"""Mede o efeito das duas correcoes nos 26 exames do conjunto de teste, antes
e depois, no mesmo exame e no mesmo pre-processamento.

  1. Semente do region growing: exigir que caia em voxel abaixo de -750 HU
     (`region_growing.SEED_MAX_HU`). Antes, o pico da transformada de distancia
     podia cair na franja de volume parcial e deslocar a banda de crescimento.

  2. Saida da U-Net: aplicar a mesma limpeza espacial que baseline e region
     growing ja faziam (`lung_air.keep_largest_components`), para descartar o
     que esta fora do torax.

Para cada metodo roda as duas versoes no mesmo volume, entao a diferenca e
atribuivel so a correcao -- nao a ruido de pre-processamento.

Uso: python scripts/medir_correcoes.py   (a partir da raiz do repositorio)
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd
import SimpleITK as sitk

from luna16.io import load_ct, load_reference_mask
from luna16.preprocessing import clean_hu, denoise, resample_isotropic
from luna16.region_growing import segment_region_growing
from luna16.unet import load_trained_model, segment_with_unet
from luna16.metrics import dice_coefficient, iou_score, sensitivity, precision

DATA_DIR = Path("data/luna16")
SAIDA = DATA_DIR / "comparacao_correcoes.csv"
TARGET = (1.0, 1.0, 1.0)
ML = 0.001

# desliga o corte de HU da semente == comportamento anterior a correcao
SEM_CORTE = -1e9


def _prep(uid):
    ct = load_ct(uid, DATA_DIR)
    s = ct.to_sitk_image()

    img = sitk.GetImageFromArray(denoise(clean_hu(ct.array), 0.5).astype("int16"))
    img.CopyInformation(s)
    vol = sitk.GetArrayFromImage(resample_isotropic(img, TARGET, is_mask=False))

    ref_img = sitk.GetImageFromArray(load_reference_mask(uid, DATA_DIR).astype("uint8"))
    ref_img.CopyInformation(s)
    ref = sitk.GetArrayFromImage(resample_isotropic(ref_img, TARGET, is_mask=True)).astype(bool)
    return vol, ref


def _m(pred, ref, metodo, versao):
    return {
        f"{metodo}_{versao}_dice": round(dice_coefficient(pred, ref), 4),
        f"{metodo}_{versao}_iou": round(iou_score(pred, ref), 4),
        f"{metodo}_{versao}_sens": round(sensitivity(pred, ref), 4),
        f"{metodo}_{versao}_prec": round(precision(pred, ref), 4),
        f"{metodo}_{versao}_fp_ml": round(float((pred & ~ref).sum()) * ML, 1),
    }


def main():
    split = pd.read_csv(DATA_DIR / "split_full.csv")
    uids = sorted(split.loc[split["conjunto"] == "test", "uid"].tolist())
    print(f"{len(uids)} exames de teste\n", flush=True)

    modelo = load_trained_model(str(DATA_DIR / "unet_baseline.pt"))

    linhas = []
    for i, uid in enumerate(uids, 1):
        t0 = time.time()
        vol, ref = _prep(uid)

        rg_antes = segment_region_growing(vol, seed_max_hu=SEM_CORTE)
        rg_depois = segment_region_growing(vol)
        un_antes = segment_with_unet(vol, modelo, limpar_fora_do_torax=False)
        un_depois = segment_with_unet(vol, modelo)

        linha = {"uid": uid, "uid_curto": uid[-12:]}
        linha.update(_m(rg_antes, ref, "rg", "antes"))
        linha.update(_m(rg_depois, ref, "rg", "depois"))
        linha.update(_m(un_antes, ref, "unet", "antes"))
        linha.update(_m(un_depois, ref, "unet", "depois"))
        linhas.append(linha)
        pd.DataFrame(linhas).to_csv(SAIDA, index=False)

        print(f"[{i}/{len(uids)}] {uid[-12:]}  "
              f"RG {linha['rg_antes_dice']:.4f}->{linha['rg_depois_dice']:.4f}   "
              f"U-Net {linha['unet_antes_dice']:.4f}->{linha['unet_depois_dice']:.4f}   "
              f"({time.time()-t0:.0f}s)", flush=True)

    d = pd.DataFrame(linhas)
    print("\n" + "=" * 62)
    for met, nome in [("rg", "REGION GROWING"), ("unet", "U-NET")]:
        a, p = d[f"{met}_antes_dice"], d[f"{met}_depois_dice"]
        print(f"\n{nome}")
        print(f"  Dice medio : {a.mean():.4f} -> {p.mean():.4f}   ({p.mean()-a.mean():+.4f})")
        print(f"  Dice minimo: {a.min():.4f} -> {p.min():.4f}")
        print(f"  abaixo 0,85: {(a<0.85).sum()} -> {(p<0.85).sum()} exames")
        print(f"  melhoraram : {(p>a+1e-4).sum()} | pioraram: {(p<a-1e-4).sum()} | iguais: {(abs(p-a)<=1e-4).sum()}")
        pior = (p - a).min()
        if pior < -1e-4:
            u = d.loc[(p - a).idxmin(), "uid_curto"]
            print(f"  pior regressao: {pior:+.4f} em ...{u}")
        fa, fp_ = d[f"{met}_antes_fp_ml"], d[f"{met}_depois_fp_ml"]
        print(f"  falso positivo medio: {fa.mean():.1f} -> {fp_.mean():.1f} mL")
        sa, sp = d[f"{met}_antes_sens"], d[f"{met}_depois_sens"]
        print(f"  sensibilidade media : {sa.mean():.4f} -> {sp.mean():.4f}")

    print(f"\nsalvo em {SAIDA}")
    print("CONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
