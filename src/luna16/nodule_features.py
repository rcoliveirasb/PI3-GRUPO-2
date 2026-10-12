"""Extracao de features e classificador de reducao de falsos positivos (FP)
para deteccao de nodulos -- a segunda etapa que `nodules.py` (geracao de
candidatos) deixa para depois, seguindo o mesmo desenho de duas etapas do
desafio LUNA16 original (geracao de candidatos + reducao de FP via
classificador treinado -- ver Setio et al. 2016).

Cada candidato (de `candidates.csv` ou gerado por `nodules.detect_nodule_candidates`)
vira um vetor de features simples, calculadas num pequeno recorte (patch) ao
redor do centro do candidato -- nao e um classificador de imagem (CNN), e sim
um classificador classico (Random Forest) sobre estatisticas do patch, no
mesmo espirito "classico" do resto do projeto.
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

from .io import load_ct
from .preprocessing import clean_hu, resample_isotropic
from .nodules import world_to_resampled_voxel

PATCH_RADIUS_VOX = 16  # cobre nodulos ate ~32mm de diametro (maior do dataset)
PAD_VALUE_HU = -750  # so para preencher patch perto da borda do volume (nao usado como limiar de forma)

# Limiar usado so para achar o "blob" local de forma/compacidade dentro do
# patch -- DIFERENTE do limiar de deteccao de candidatos (nodules.TISSUE_HU_MIN
# = -750, calibrado para nao perder nodulos pequenos diluidos por volume
# parcial). Um limiar tao permissivo aqui faz o "blob" vazar e preencher o
# patch inteiro (33x33x33 voxels -- o parenquima pulmonar ao redor ja passa
# de -750 boa parte do tempo), o que destroi o sinal de forma/compacidade
# (deixa de distinguir nodulo compacto de vaso alongado). -500 isola melhor
# um nucleo denso plausivel, mesmo sacrificando um pouco de sensibilidade do
# proprio calculo de forma para os nodulos mais diluidos (ver Sprint 8c).
TISSUE_HU_MIN = -500


def _safe_patch(volume: np.ndarray, center_zyx: tuple, radius: int) -> np.ndarray | None:
    """Recorte cubico ao redor do centro, com padding se cair perto da borda
    do volume. Devolve None se o centro estiver totalmente fora do volume
    (candidato com coordenada invalida/fora de alcance -- acontece em alguns
    poucos candidatos de candidates.csv; melhor descartar do que forcar um
    recorte sem sentido)."""
    z, y, x = center_zyx
    if not (0 <= z < volume.shape[0] and 0 <= y < volume.shape[1] and 0 <= x < volume.shape[2]):
        return None

    z0, z1 = z - radius, z + radius + 1
    y0, y1 = y - radius, y + radius + 1
    x0, x1 = x - radius, x + radius + 1

    pad_z0, pad_y0, pad_x0 = max(0, -z0), max(0, -y0), max(0, -x0)
    z0, y0, x0 = max(0, z0), max(0, y0), max(0, x0)
    z1, y1, x1 = min(volume.shape[0], z1), min(volume.shape[1], y1), min(volume.shape[2], x1)

    patch = volume[z0:z1, y0:y1, x0:x1]
    size = 2 * radius + 1
    if patch.shape != (size, size, size):
        padded = np.full((size, size, size), PAD_VALUE_HU, dtype=patch.dtype)
        pz, py, px = pad_z0, pad_y0, pad_x0
        padded[pz : pz + patch.shape[0], py : py + patch.shape[1], px : px + patch.shape[2]] = patch
        patch = padded
    return patch


def extract_patch_features(volume_hu: np.ndarray, center_zyx: tuple, radius: int = PATCH_RADIUS_VOX) -> dict | None:
    """Calcula um vetor de features simples num patch cubico ao redor do
    candidato:
      - estatisticas de intensidade (media, desvio, min, max, HU central)
      - tamanho do "blob" de tecido conectado ao centro (proxy de volume)
      - compacidade/esfericidade do blob (razao entre extensao nos 3 eixos --
        vasos sao alongados em 1 eixo, nodulos sao mais isotropicos)
      - magnitude media do gradiente (bordas nitidas vs. graduais)
    Devolve None se o centro cair fora do volume (candidato invalido)."""
    patch = _safe_patch(volume_hu, center_zyx, radius)
    if patch is None:
        return None
    patch = patch.astype(np.float32)
    center_idx = radius

    features = {
        "hu_central": float(patch[center_idx, center_idx, center_idx]),
        "hu_media": float(patch.mean()),
        "hu_desvio": float(patch.std()),
        "hu_min": float(patch.min()),
        "hu_max": float(patch.max()),
    }

    tissue = patch > TISSUE_HU_MIN
    from scipy import ndimage as ndi

    labeled, n = ndi.label(tissue)
    center_label = labeled[center_idx, center_idx, center_idx]
    if center_label == 0 or n == 0:
        # centro caiu em ar puro -- blob vazio, candidato provavelmente ruim
        features.update(
            {
                "blob_volume_vox": 0.0,
                "blob_extensao_z": 0.0,
                "blob_extensao_y": 0.0,
                "blob_extensao_x": 0.0,
                "blob_compacidade": 0.0,
                "gradiente_medio": 0.0,
            }
        )
        return features

    blob_mask = labeled == center_label
    coords = np.argwhere(blob_mask)
    volume_vox = len(coords)
    extensao = coords.max(axis=0) - coords.min(axis=0) + 1  # (z,y,x)

    # compacidade: volume real / volume da caixa delimitadora -- 1.0 = preenche
    # a caixa toda (mais isotropico/compacto), baixo = alongado/irregular
    bbox_vol = extensao[0] * extensao[1] * extensao[2]
    compacidade = volume_vox / bbox_vol if bbox_vol > 0 else 0.0

    gradiente = np.gradient(patch)
    gradiente_mag = np.sqrt(sum(g**2 for g in gradiente))

    features.update(
        {
            "blob_volume_vox": float(volume_vox),
            "blob_extensao_z": float(extensao[0]),
            "blob_extensao_y": float(extensao[1]),
            "blob_extensao_x": float(extensao[2]),
            "blob_compacidade": float(compacidade),
            "gradiente_medio": float(gradiente_mag.mean()),
        }
    )
    return features


FEATURE_COLUMNS = [
    "hu_central", "hu_media", "hu_desvio", "hu_min", "hu_max",
    "blob_volume_vox", "blob_extensao_z", "blob_extensao_y", "blob_extensao_x",
    "blob_compacidade", "gradiente_medio",
]


def build_feature_dataframe(candidates_df: pd.DataFrame, data_dir, verbose: bool = True) -> pd.DataFrame:
    """Extrai features para todos os candidatos de `candidates_df` (precisa
    ter seriesuid, coordX, coordY, coordZ, e opcionalmente 'class'),
    agrupando por paciente para carregar cada CT uma unica vez."""
    data_dir = Path(data_dir)
    rows = []
    uids = candidates_df["seriesuid"].unique()
    for i, uid in enumerate(uids, 1):
        t0 = time.time()
        try:
            ct = load_ct(uid, data_dir)
        except FileNotFoundError:
            continue
        cleaned = clean_hu(ct.array)
        ct_sitk = ct.to_sitk_image()
        vol_sitk = sitk.GetImageFromArray(cleaned.astype("int16"))
        vol_sitk.CopyInformation(ct_sitk)
        vol_resampled_sitk = resample_isotropic(vol_sitk, (1.0, 1.0, 1.0), is_mask=False)
        vol = sitk.GetArrayFromImage(vol_resampled_sitk)
        origin = vol_resampled_sitk.GetOrigin()

        pac_cands = candidates_df[candidates_df["seriesuid"] == uid]
        n_descartados = 0
        for _, row in pac_cands.iterrows():
            center = world_to_resampled_voxel((row["coordX"], row["coordY"], row["coordZ"]), origin, 1.0)
            feats = extract_patch_features(vol, center)
            if feats is None:
                n_descartados += 1
                continue
            feats["seriesuid"] = uid
            if "class" in row:
                feats["class"] = row["class"]
            rows.append(feats)
        if verbose and n_descartados:
            print(f"  ({uid[-10:]}: {n_descartados} candidatos descartados, fora do volume)", flush=True)

        if verbose and i % 20 == 0:
            print(f"[{i}/{len(uids)}] {uid[-10:]} ({len(pac_cands)} candidatos, {time.time()-t0:.1f}s)", flush=True)

    return pd.DataFrame(rows)


def train_fp_reduction_classifier(train_df: pd.DataFrame, seed: int = 42) -> RandomForestClassifier:
    """Treina um Random Forest para distinguir candidato real (nodulo) de
    falso positivo, a partir das features de `build_feature_dataframe`.

    `class_weight='balanced'` compensa o desbalanceamento severo (no
    LUNA16, candidatos reais sao ~0.4% do total) sem precisar subamostrar
    manualmente -- o Random Forest pondera o erro em exemplos da classe
    minoritaria mais pesado durante o treino."""
    X = train_df[FEATURE_COLUMNS]
    y = train_df["class"]
    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
    )
    clf.fit(X, y)
    return clf


def evaluate_classifier(clf: RandomForestClassifier, df: pd.DataFrame) -> dict:
    """AUC-ROC e importancia das features -- avaliacao padrao de ML sobre um
    conjunto separado (validacao ou teste)."""
    X = df[FEATURE_COLUMNS]
    y = df["class"]
    proba = clf.predict_proba(X)[:, 1]
    auc = roc_auc_score(y, proba)
    importances = dict(zip(FEATURE_COLUMNS, clf.feature_importances_))
    return {"auc_roc": auc, "importancias": importances, "proba": proba}


def pick_threshold_for_sensitivity(df: pd.DataFrame, proba: np.ndarray, target_sensitivity: float = 0.9) -> float:
    """Acha o menor limiar de probabilidade que ainda mantem pelo menos
    `target_sensitivity` de sensibilidade no conjunto dado (tipicamente
    validacao) -- o jeito padrao de escolher o ponto de operacao de um
    classificador quando o custo de falso negativo (perder um nodulo real)
    e mais alto que o de falso positivo (seção 5.2 do doc do projeto)."""
    y = df["class"].values
    positivos_proba = np.sort(proba[y == 1])
    if len(positivos_proba) == 0:
        return 0.5
    idx = int(np.floor((1 - target_sensitivity) * len(positivos_proba)))
    idx = min(idx, len(positivos_proba) - 1)
    return float(positivos_proba[idx])
