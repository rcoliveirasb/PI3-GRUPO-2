"""
Sprint 8: aplica o classificador de reducao de falsos positivos (treinado em
candidates.csv) sobre os candidatos gerados pelo NOSSO detector (Sprint 7,
blob_log), em pacientes do conjunto de TESTE com anotacao disponivel.
Compara sensibilidade/FP antes e depois do filtro.

Uso: python scripts/run_sprint8_evaluation.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")

import numpy as np
import pandas as pd
import SimpleITK as sitk

from luna16.io import load_ct
from luna16.preprocessing import clean_hu, denoise, resample_isotropic
from luna16.baseline import segment_baseline
from luna16.nodules import (
    load_annotations, annotations_for_patient, detect_nodule_candidates,
    match_candidates_to_annotations,
)
from luna16.nodule_features import (
    extract_patch_features, train_fp_reduction_classifier, evaluate_classifier,
    pick_threshold_for_sensitivity, FEATURE_COLUMNS,
)

DATA_DIR = Path("data/luna16")
OUT_PATH = DATA_DIR / "sprint8_resultados.csv"
N_PACIENTES = 15
THRESHOLD_DETECCAO = 0.1


def main():
    print("Treinando classificador...", flush=True)
    train_df = pd.read_csv(DATA_DIR / "nodule_features_train.csv")
    val_df = pd.read_csv(DATA_DIR / "nodule_features_val.csv")
    clf = train_fp_reduction_classifier(train_df)
    r_val = evaluate_classifier(clf, val_df)
    threshold_clf = pick_threshold_for_sensitivity(val_df, r_val["proba"], target_sensitivity=0.9)
    print(f"Threshold do classificador (90% sens. na validacao): {threshold_clf:.4f}", flush=True)

    ann = load_annotations(DATA_DIR)
    split = pd.read_csv(DATA_DIR / "split_full.csv")
    test_uids = set(split[split["conjunto"] == "test"]["uid"])
    ann_test = ann[ann["seriesuid"].isin(test_uids)]
    counts = ann_test["seriesuid"].value_counts()
    uids = counts.index[:N_PACIENTES].tolist()
    print(f"{len(uids)} pacientes de teste selecionados (dos {len(counts)} com anotacao)", flush=True)

    if OUT_PATH.exists():
        done_df = pd.read_csv(OUT_PATH)
        done_uids = set(done_df["uid"])
    else:
        done_df = pd.DataFrame()
        done_uids = set()
    pending = [u for u in uids if u not in done_uids]
    print(f"{len(done_uids)} ja feitos, {len(pending)} pendentes", flush=True)

    rows = done_df.to_dict("records")
    for i, uid in enumerate(pending, 1):
        t0 = time.time()
        pac_ann = annotations_for_patient(ann, uid)

        ct = load_ct(uid, DATA_DIR)
        cleaned = clean_hu(ct.array)
        ct_sitk = ct.to_sitk_image()

        denoised = denoise(cleaned, sigma=0.5)
        denoised_sitk = sitk.GetImageFromArray(denoised.astype("int16")); denoised_sitk.CopyInformation(ct_sitk)
        vol_pulmao = sitk.GetArrayFromImage(resample_isotropic(denoised_sitk, (1.0, 1.0, 1.0), False))
        lung_mask = segment_baseline(vol_pulmao)

        cleaned_sitk = sitk.GetImageFromArray(cleaned.astype("int16")); cleaned_sitk.CopyInformation(ct_sitk)
        cleaned_resampled_sitk = resample_isotropic(cleaned_sitk, (1.0, 1.0, 1.0), False)
        vol_nodulo = sitk.GetArrayFromImage(cleaned_resampled_sitk)
        origin = cleaned_resampled_sitk.GetOrigin()

        candidatos = detect_nodule_candidates(vol_nodulo, lung_mask, spacing_mm=1.0, threshold=THRESHOLD_DETECCAO)

        # ANTES do filtro
        resultado_antes = match_candidates_to_annotations(candidatos, pac_ann, origin, spacing_mm=1.0)

        # extrai features de cada candidato e classifica
        feat_rows = []
        for cand in candidatos:
            feats = extract_patch_features(vol_nodulo, (cand.z, cand.y, cand.x))
            if feats is not None:
                feat_rows.append(feats)
        if feat_rows:
            feat_df = pd.DataFrame(feat_rows)
            proba = clf.predict_proba(feat_df[FEATURE_COLUMNS])[:, 1]
            candidatos_filtrados = [c for c, p in zip(candidatos, proba) if p >= threshold_clf]
        else:
            candidatos_filtrados = []

        # DEPOIS do filtro
        resultado_depois = match_candidates_to_annotations(candidatos_filtrados, pac_ann, origin, spacing_mm=1.0)

        row = {
            "uid": uid,
            "n_anotacoes": resultado_antes["n_anotacoes"],
            "candidatos_antes": resultado_antes["n_candidatos"],
            "tp_antes": resultado_antes["verdadeiros_positivos"],
            "fp_antes": resultado_antes["falsos_positivos"],
            "sens_antes": resultado_antes["sensibilidade"],
            "candidatos_depois": resultado_depois["n_candidatos"],
            "tp_depois": resultado_depois["verdadeiros_positivos"],
            "fp_depois": resultado_depois["falsos_positivos"],
            "sens_depois": resultado_depois["sensibilidade"],
            "tempo_segundos": time.time() - t0,
        }
        rows.append(row)
        print(
            f"[{i}/{len(pending)}] {uid[-10:]}  ANTES: cand={row['candidatos_antes']} sens={row['sens_antes']:.2f}  "
            f"DEPOIS: cand={row['candidatos_depois']} sens={row['sens_depois']:.2f}  tempo={row['tempo_segundos']:.1f}s",
            flush=True,
        )
        pd.DataFrame(rows).to_csv(OUT_PATH, index=False)

    print("CONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
