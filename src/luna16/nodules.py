"""Deteccao e segmentacao aproximada de nodulos pulmonares.

Etapa seguinte a segmentacao do parenquima (`baseline.py`/`region_growing.py`):
com o pulmao ja isolado do resto do torax, o objetivo aqui e achar as pequenas
estruturas densas *dentro* dele que podem ser nodulo.

Fonte da referencia (ground truth): `annotations.csv` do LUNA16 -- para cada
paciente, lista de nodulos anotados por radiologistas como (coordX, coordY,
coordZ) em mm (coordenadas do mundo, nao voxel) + diametro em mm. O LUNA16 NAO
fornece contorno/mascara exata do nodulo, so centro + diametro -- por isso a
"mascara de referencia" usada aqui e uma aproximacao esferica (padrao usado na
literatura quando se trabalha com esse dataset para segmentacao, ja que nao ha
contorno pixel-a-pixel disponivel).

Deteccao de candidatos: blob detection classico (Laplacian of Gaussian, via
skimage) sobre a regiao de tecido mole dentro do pulmao ja segmentado --
tecnica pre-deep-learning padrao para achar estruturas aproximadamente
esfericas em volumes 3D. Nodulos tem densidade de tecido mole (por volta de
-400 a +400 HU) e formato aproximadamente esferico; vasos sanguineos tambem
sao densos mas alongados, o que e uma fonte conhecida de falsos positivos
neste tipo de abordagem classica (documentado na avaliacao, nao escondido).
"""
import math
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk
from skimage.feature import blob_log

from .io import load_ct
from .preprocessing import clean_hu, denoise, resample_isotropic
from .baseline import segment_baseline

TISSUE_HU_MIN = -750  # ver Sprint 7: nodulos pequenos tem HU medido bem mais
# baixo do que o esperado para tecido solido (efeito de volume parcial -- uma
# estrutura de poucos voxels tem sua densidade "diluida" com o ar ao redor na
# reamostragem/suavizacao). -400 excluia a maioria dos nodulos < 7mm do
# dataset; -750 e mais permissivo o suficiente pra nao perde-los de cara,
# aceitando mais falsos positivos de textura pulmonar em troca.
TISSUE_HU_MAX = 400  # acima disso e osso/contraste, nao tecido mole
MIN_DIAMETER_MM = 3.0  # LUNA16 so anota nodulos >= 3mm
MAX_DIAMETER_MM = 33.0  # cobre o maior nodulo anotado no dataset (~32mm)


def load_annotations(data_dir) -> pd.DataFrame:
    """Le annotations.csv (nodulos de referencia, anotados por radiologistas)."""
    from pathlib import Path

    return pd.read_csv(Path(data_dir) / "annotations.csv")


def annotations_for_patient(annotations_df: pd.DataFrame, uid: str) -> pd.DataFrame:
    return annotations_df[annotations_df["seriesuid"] == uid]


@dataclass
class NoduleCandidate:
    z: int
    y: int
    x: int
    radius_mm: float


def world_to_resampled_voxel(coord_xyz: tuple, origin_xyz: tuple, spacing_mm: float = 1.0) -> tuple:
    """Converte uma coordenada do mundo (mm, ordem x,y,z) para indice de voxel
    (ordem z,y,x, a ordem do array numpy) no espaco ja reamostrado para
    `spacing_mm` isotropico. Assume direcao identidade (verdade para o
    LUNA16 -- TransformMatrix = 1 0 0 0 1 0 0 0 1 em todos os .mhd
    inspecionados)."""
    x, y, z = coord_xyz
    ox, oy, oz = origin_xyz
    vx = (x - ox) / spacing_mm
    vy = (y - oy) / spacing_mm
    vz = (z - oz) / spacing_mm
    return (int(round(vz)), int(round(vy)), int(round(vx)))


def build_reference_nodule_mask(
    shape: tuple,
    patient_annotations: pd.DataFrame,
    origin_xyz: tuple,
    spacing_mm: float = 1.0,
) -> np.ndarray:
    """Mascara booleana com uma esfera por nodulo anotado (raio =
    diametro_anotado/2), no espaco reamostrado isotropico. Aproximacao --
    o LUNA16 nao da o contorno real do nodulo, so centro+diametro."""
    mask = np.zeros(shape, dtype=bool)
    zz, yy, xx = np.ogrid[: shape[0], : shape[1], : shape[2]]
    for _, row in patient_annotations.iterrows():
        cz, cy, cx = world_to_resampled_voxel(
            (row["coordX"], row["coordY"], row["coordZ"]), origin_xyz, spacing_mm
        )
        radius_vox = (row["diameter_mm"] / 2) / spacing_mm
        dist2 = (zz - cz) ** 2 + (yy - cy) ** 2 + (xx - cx) ** 2
        mask |= dist2 <= radius_vox**2
    return mask


def detect_nodule_candidates(
    volume_hu: np.ndarray,
    lung_mask: np.ndarray,
    spacing_mm: float = 1.0,
    threshold: float = 0.15,
) -> list[NoduleCandidate]:
    """Acha candidatos a nodulo via blob detection (Laplacian of Gaussian)
    restrito a regiao de tecido mole dentro do pulmao ja segmentado.

    `threshold` controla a sensibilidade do blob_log (menor = mais candidatos,
    mais falsos positivos tambem) -- valor escolhido empiricamente (ver
    notebook do Sprint 7), nao e um numero mágico sem justificativa: e o
    ponto onde o numero de falsos positivos por exame ficou administravel
    sem derrubar demais a sensibilidade.
    """
    tissue = lung_mask & (volume_hu > TISSUE_HU_MIN) & (volume_hu < TISSUE_HU_MAX)
    masked = np.where(tissue, volume_hu, TISSUE_HU_MIN - 1).astype(np.float32)

    # normaliza para [0,1] -- blob_log espera imagem de intensidade positiva
    normalized = (masked - masked.min()) / (masked.max() - masked.min() + 1e-6)

    # relacao entre sigma do LoG e raio do blob detectado: r = sigma * sqrt(ndim)
    ndim = 3
    min_sigma = (MIN_DIAMETER_MM / 2) / spacing_mm / math.sqrt(ndim)
    max_sigma = (MAX_DIAMETER_MM / 2) / spacing_mm / math.sqrt(ndim)

    blobs = blob_log(
        normalized,
        min_sigma=min_sigma,
        max_sigma=max_sigma,
        num_sigma=6,
        threshold=threshold,
    )

    candidates = []
    for z, y, x, sigma in blobs:
        radius_mm = sigma * math.sqrt(ndim) * spacing_mm
        candidates.append(NoduleCandidate(z=int(z), y=int(y), x=int(x), radius_mm=float(radius_mm)))
    return candidates


def sphere_dice(dist_mm: float, radius_a_mm: float, radius_b_mm: float) -> float:
    """Dice entre duas esferas (formula fechada, sem rasterizar voxel a
    voxel -- exato e rapido). Usado para medir a qualidade da "segmentacao"
    aproximada de um candidato de nodulo (esfera do raio detectado) contra a
    esfera de referencia (raio = diametro anotado / 2), para os pares que
    ja foram casados por `match_candidates_to_annotations`.
    """
    r_small, r_large = sorted([radius_a_mm, radius_b_mm])
    if dist_mm >= radius_a_mm + radius_b_mm:
        intersection = 0.0
    elif dist_mm <= r_large - r_small:
        intersection = (4 / 3) * math.pi * r_small**3
    else:
        d = dist_mm
        intersection = (
            math.pi
            * (radius_a_mm + radius_b_mm - d) ** 2
            * (
                d**2
                + 2 * d * radius_b_mm
                - 3 * radius_b_mm**2
                + 2 * d * radius_a_mm
                + 6 * radius_b_mm * radius_a_mm
                - 3 * radius_a_mm**2
            )
            / (12 * d)
        )
    vol_a = (4 / 3) * math.pi * radius_a_mm**3
    vol_b = (4 / 3) * math.pi * radius_b_mm**3
    denom = vol_a + vol_b
    return 2 * intersection / denom if denom > 0 else 1.0


def match_candidates_to_annotations(
    candidates: list[NoduleCandidate],
    patient_annotations: pd.DataFrame,
    origin_xyz: tuple,
    spacing_mm: float = 1.0,
) -> dict:
    """Casa candidatos detectados com anotacoes de referencia (avaliacao
    estilo FROC, o padrao usado pelo proprio desafio LUNA16): um candidato e
    verdadeiro positivo se o centro cai dentro do raio anotado do nodulo (ou
    a uma distancia minima de 3mm, o que for maior -- nodulos pequenos tem
    raio anotado as vezes menor que a resolucao pratica de deteccao).
    Cada nodulo anotado conta no maximo 1 verdadeiro positivo (evita inflar
    contando o mesmo candidato pra varios nodulos por engano); candidatos
    sem par viram falso positivo.
    """
    ref_centers = []
    for _, row in patient_annotations.iterrows():
        cz, cy, cx = world_to_resampled_voxel(
            (row["coordX"], row["coordY"], row["coordZ"]), origin_xyz, spacing_mm
        )
        raio_mm = row["diameter_mm"] / 2
        raio_match = max(raio_mm, 3.0) / spacing_mm
        ref_centers.append(
            {"z": cz, "y": cy, "x": cx, "raio_mm": raio_mm, "raio_match_vox": raio_match, "matched": False}
        )

    true_positives = 0
    false_positives = 0
    dice_matches = []
    for cand in candidates:
        matched_this = False
        for ref in ref_centers:
            if ref["matched"]:
                continue
            dist_vox = math.sqrt((cand.z - ref["z"]) ** 2 + (cand.y - ref["y"]) ** 2 + (cand.x - ref["x"]) ** 2)
            if dist_vox <= ref["raio_match_vox"]:
                ref["matched"] = True
                matched_this = True
                true_positives += 1
                dice_matches.append(sphere_dice(dist_vox * spacing_mm, cand.radius_mm, ref["raio_mm"]))
                break
        if not matched_this:
            false_positives += 1

    n_annotations = len(ref_centers)
    false_negatives = n_annotations - true_positives

    return {
        "dice_medio_matches": float(np.mean(dice_matches)) if dice_matches else None,
        "n_anotacoes": n_annotations,
        "n_candidatos": len(candidates),
        "verdadeiros_positivos": true_positives,
        "falsos_positivos": false_positives,
        "falsos_negativos": false_negatives,
        "sensibilidade": true_positives / n_annotations if n_annotations > 0 else None,
    }


def _prepare_volumes_for_uid(uid: str, data_dir: Path):
    """Carrega e pre-processa um paciente, devolvendo os dois volumes que a
    deteccao de nodulo precisa: um suavizado (para segmentar o pulmao, igual
    ao Sprint 3) e outro sem suavizar (para detectar nodulo em si -- suavizar
    piora o contraste de estruturas ja pequenas e diluidas por volume
    parcial). Tambem devolve a origem (mm) do espaco reamostrado, necessaria
    para converter coordenadas do mundo (`annotations.csv`/`candidates.csv`)
    em indice de voxel."""
    ct = load_ct(uid, data_dir)
    ct_sitk = ct.to_sitk_image()
    cleaned = clean_hu(ct.array)

    denoised = denoise(cleaned, sigma=0.5)
    denoised_sitk = sitk.GetImageFromArray(denoised.astype("int16"))
    denoised_sitk.CopyInformation(ct_sitk)
    denoised_resampled_sitk = resample_isotropic(denoised_sitk, (1.0, 1.0, 1.0), is_mask=False)
    vol_para_pulmao = sitk.GetArrayFromImage(denoised_resampled_sitk)

    cleaned_sitk = sitk.GetImageFromArray(cleaned.astype("int16"))
    cleaned_sitk.CopyInformation(ct_sitk)
    cleaned_resampled_sitk = resample_isotropic(cleaned_sitk, (1.0, 1.0, 1.0), is_mask=False)
    vol_para_nodulo = sitk.GetArrayFromImage(cleaned_resampled_sitk)
    origin = cleaned_resampled_sitk.GetOrigin()

    return vol_para_pulmao, vol_para_nodulo, origin


def generate_and_cache_candidates(
    uid: str, data_dir, threshold: float = 0.1, cache_dir=None
) -> tuple[list[NoduleCandidate], tuple, np.ndarray]:
    """Gera candidatos a nodulo para um paciente (blob_log, a etapa cara --
    ~1-2min por paciente) e cacheia em disco (CSV por paciente), para nao
    precisar rodar a deteccao de novo toda vez que um classificador novo
    de reducao de falsos positivos for testado sobre os mesmos candidatos.

    Devolve (candidatos, origin, volume_para_nodulo) -- o volume e devolvido
    tambem porque `extract_patch_features` (nodule_features.py) precisa dele
    para extrair as features de cada candidato.
    """
    data_dir = Path(data_dir)
    cache_dir = Path(cache_dir) if cache_dir else data_dir / "nodule_candidates_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{uid}.csv"

    vol_pulmao, vol_nodulo, origin = _prepare_volumes_for_uid(uid, data_dir)

    if cache_path.exists():
        cached = pd.read_csv(cache_path)
        candidates = [
            NoduleCandidate(z=int(r.z), y=int(r.y), x=int(r.x), radius_mm=float(r.radius_mm))
            for r in cached.itertuples()
        ]
    else:
        lung_mask = segment_baseline(vol_pulmao)
        candidates = detect_nodule_candidates(vol_nodulo, lung_mask, spacing_mm=1.0, threshold=threshold)
        pd.DataFrame([{"z": c.z, "y": c.y, "x": c.x, "radius_mm": c.radius_mm} for c in candidates]).to_csv(
            cache_path, index=False
        )

    return candidates, origin, vol_nodulo


def label_candidates_by_match(
    candidates: list[NoduleCandidate],
    patient_annotations: pd.DataFrame,
    origin_xyz: tuple,
    spacing_mm: float = 1.0,
) -> list[int]:
    """Como `match_candidates_to_annotations`, mas devolve um rotulo (0/1)
    por candidato em vez de estatisticas agregadas -- usado para montar um
    conjunto de treino do classificador de reducao de falsos positivos a
    partir dos NOSSOS proprios candidatos (em vez dos candidatos oficiais de
    `candidates.csv`), evitando o descompasso de distribuicao entre um
    classificador treinado num gerador de candidatos e aplicado em outro."""
    ref_centers = []
    for _, row in patient_annotations.iterrows():
        cz, cy, cx = world_to_resampled_voxel(
            (row["coordX"], row["coordY"], row["coordZ"]), origin_xyz, spacing_mm
        )
        raio_match = max(row["diameter_mm"] / 2, 3.0) / spacing_mm
        ref_centers.append({"z": cz, "y": cy, "x": cx, "raio_match_vox": raio_match, "matched": False})

    labels = []
    for cand in candidates:
        label = 0
        for ref in ref_centers:
            if ref["matched"]:
                continue
            dist = math.sqrt((cand.z - ref["z"]) ** 2 + (cand.y - ref["y"]) ** 2 + (cand.x - ref["x"]) ** 2)
            if dist <= ref["raio_match_vox"]:
                ref["matched"] = True
                label = 1
                break
        labels.append(label)
    return labels


def run_nodule_pipeline_for_uid(
    uid: str, data_dir, annotations_df: pd.DataFrame, threshold: float = 0.1, cache_dir=None
) -> dict:
    """Pipeline completo de deteccao de nodulos para um paciente: gera (ou
    reaproveita do cache) candidatos e casa com as anotacoes de referencia."""
    t0 = time.time()
    candidates, origin, _ = generate_and_cache_candidates(uid, data_dir, threshold=threshold, cache_dir=cache_dir)
    pac_ann = annotations_for_patient(annotations_df, uid)
    resultado = match_candidates_to_annotations(candidates, pac_ann, origin, spacing_mm=1.0)
    resultado["uid"] = uid
    resultado["tempo_segundos"] = time.time() - t0
    return resultado
