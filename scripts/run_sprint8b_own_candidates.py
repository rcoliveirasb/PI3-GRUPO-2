"""
Sprint 8b: corrige o descompasso de distribuicao do Sprint 8 -- em vez de
treinar o classificador de reducao de falsos positivos nos candidatos
OFICIAIS do LUNA16 (candidates.csv) e aplicar nos NOSSOS candidatos
(blob_log), este script gera candidatos com o NOSSO detector em pacientes de
treino/validacao, rotula por correspondencia com annotations.csv, e treina o
classificador direto nos nossos proprios candidatos -- mesma distribuicao de
treino e de aplicacao.

Retomavel: candidatos ficam cacheados por paciente em
data/luna16/nodule_candidates_cache/<uid>.csv (gerar e caro; reaproveitar e
gratis).

Uso: python scripts/run_sprint8b_own_candidates.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")

import pandas as pd

from luna16.nodules import (
    load_annotations, annotations_for_patient, generate_and_cache_candidates,
    label_candidates_by_match, match_candidates_to_annotations,
)
from luna16.nodule_features import (
    extract_patch_features, train_fp_reduction_classifier, evaluate_classifier,
    pick_threshold_for_sensitivity, FEATURE_COLUMNS,
)

DATA_DIR = Path("data/luna16")
N_TRAIN = 77  # todos os pacientes de treino com nodulo anotado disponivel
N_VAL = 30  # todos os pacientes de validacao com nodulo anotado disponivel
N_TEST = 15
THRESHOLD_DETECCAO = 0.1


def build_own_candidate_dataset(uids: list, ann: pd.DataFrame, label: str) -> pd.DataFrame:
    out_path = DATA_DIR / f"own_candidate_features_{label}.csv"
    if out_path.exists():
        return pd.read_csv(out_path)

    rows = []
    for i, uid in enumerate(uids, 1):
        t0 = time.time()
        candidates, origin, vol = generate_and_cache_candidates(uid, DATA_DIR, threshold=THRESHOLD_DETECCAO)
        pac_ann = annotations_for_patient(ann, uid)
        labels = label_candidates_by_match(candidates, pac_ann, origin, spacing_mm=1.0)

        for cand, lbl in zip(candidates, labels):
            feats = extract_patch_features(vol, (cand.z, cand.y, cand.x))
            if feats is None:
                continue
            feats["seriesuid"] = uid
            feats["class"] = lbl
            rows.append(feats)

        n_pos = sum(labels)
        print(f"[{label} {i}/{len(uids)}] {uid[-10:]}  candidatos={len(candidates)}  "
              f"positivos={n_pos}  tempo={time.time()-t0:.1f}s", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)
    return df


def main():
    ann = load_annotations(DATA_DIR)
    split = pd.read_csv(DATA_DIR / "split_full.csv")

    train_uids_all = set(split[split["conjunto"] == "train"]["uid"])
    val_uids_all = set(split[split["conjunto"] == "val"]["uid"])
    test_uids_all = set(split[split["conjunto"] == "test"]["uid"])

    train_counts = ann[ann["seriesuid"].isin(train_uids_all)]["seriesuid"].value_counts()
    val_counts = ann[ann["seriesuid"].isin(val_uids_all)]["seriesuid"].value_counts()
    test_counts = ann[ann["seriesuid"].isin(test_uids_all)]["seriesuid"].value_counts()

    train_uids = train_counts.index[:N_TRAIN].tolist()
    val_uids = val_counts.index[:N_VAL].tolist()
    test_uids = test_counts.index[:N_TEST].tolist()

    print("=== Gerando candidatos + rotulos: TREINO ===", flush=True)
    train_df = build_own_candidate_dataset(train_uids, ann, "train")

    print("=== Gerando candidatos + rotulos: VALIDACAO ===", flush=True)
    val_df = build_own_candidate_dataset(val_uids, ann, "val")

    print("=== Treinando classificador (nos nossos proprios candidatos) ===", flush=True)
    clf = train_fp_reduction_classifier(train_df)
    r_val = evaluate_classifier(clf, val_df)
    threshold_clf = pick_threshold_for_sensitivity(val_df, r_val["proba"], target_sensitivity=0.9)
    print(f"AUC-ROC (val): {r_val['auc_roc']:.4f}  threshold: {threshold_clf:.4f}", flush=True)

    print("=== Avaliando antes/depois nos pacientes de TESTE ===", flush=True)
    out_path = DATA_DIR / "sprint8b_resultados.csv"
    rows = []
    for i, uid in enumerate(test_uids, 1):
        t0 = time.time()
        candidates, origin, vol = generate_and_cache_candidates(uid, DATA_DIR, threshold=THRESHOLD_DETECCAO)
        pac_ann = annotations_for_patient(ann, uid)

        resultado_antes = match_candidates_to_annotations(candidates, pac_ann, origin, spacing_mm=1.0)

        feat_rows = []
        for cand in candidates:
            feats = extract_patch_features(vol, (cand.z, cand.y, cand.x))
            if feats is not None:
                feat_rows.append(feats)
        if feat_rows:
            feat_df = pd.DataFrame(feat_rows)
            proba = clf.predict_proba(feat_df[FEATURE_COLUMNS])[:, 1]
            candidatos_filtrados = [c for c, p in zip(candidates, proba) if p >= threshold_clf]
        else:
            candidatos_filtrados = []

        resultado_depois = match_candidates_to_annotations(candidatos_filtrados, pac_ann, origin, spacing_mm=1.0)

        row = {
            "uid": uid,
            "n_anotacoes": resultado_antes["n_anotacoes"],
            "candidatos_antes": resultado_antes["n_candidatos"],
            "tp_antes": resultado_antes["verdadeiros_positivos"],
            "sens_antes": resultado_antes["sensibilidade"],
            "candidatos_depois": resultado_depois["n_candidatos"],
            "tp_depois": resultado_depois["verdadeiros_positivos"],
            "sens_depois": resultado_depois["sensibilidade"],
            "tempo_segundos": time.time() - t0,
        }
        rows.append(row)
        print(
            f"[{i}/{len(test_uids)}] {uid[-10:]}  ANTES: cand={row['candidatos_antes']} sens={row['sens_antes']:.2f}  "
            f"DEPOIS: cand={row['candidatos_depois']} sens={row['sens_depois']:.2f}",
            flush=True,
        )
        pd.DataFrame(rows).to_csv(out_path, index=False)

    print("CONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
