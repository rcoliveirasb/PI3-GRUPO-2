"""Pipeline ponta a ponta (carregar -> pre-processar -> segmentar -> avaliar)
para um paciente, usado tanto no piloto do Sprint 3 quanto na escala para
>=20 TCs do Sprint 4. Mantido separado dos modulos individuais para que o
notebook so precise chamar uma funcao por paciente.
"""
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import SimpleITK as sitk

from .io import load_ct, load_reference_mask
from .preprocessing import clean_hu, denoise, resample_isotropic
from .baseline import segment_baseline
from .metrics import dice_coefficient, iou_score, sensitivity, precision


@dataclass
class PatientResult:
    uid: str
    dice: float
    iou: float
    sensitivity: float
    precision: float
    tempo_segundos: float
    pred_voxels: int
    ref_voxels: int


def _to_sitk(array: np.ndarray, reference: sitk.Image, dtype: str) -> sitk.Image:
    img = sitk.GetImageFromArray(array.astype(dtype))
    img.CopyInformation(reference)
    return img


def run_pipeline_for_uid(
    uid: str,
    data_dir: Path,
    segment_fn: Callable[[np.ndarray], np.ndarray] = segment_baseline,
    target_spacing: tuple = (1.0, 1.0, 1.0),
) -> PatientResult:
    """Roda o pipeline completo para um paciente e devolve as metricas.

    `segment_fn` recebe o volume HU (ja limpo, com ruido reduzido e
    reamostrado para espacamento isotropico) e devolve uma mascara booleana
    -- trocar essa funcao (ex: por region growing no Sprint 4) reusa todo o
    resto do pipeline sem mudanca nenhuma.
    """
    t0 = time.time()

    ct = load_ct(uid, data_dir)
    ref_mask = load_reference_mask(uid, data_dir)
    ct_sitk = ct.to_sitk_image()

    cleaned = clean_hu(ct.array)
    denoised = denoise(cleaned, sigma=0.5)

    vol_sitk = _to_sitk(denoised, ct_sitk, "int16")
    vol_resampled_sitk = resample_isotropic(vol_sitk, target_spacing, is_mask=False)
    vol_resampled = sitk.GetArrayFromImage(vol_resampled_sitk)

    ref_sitk = _to_sitk(ref_mask, ct_sitk, "uint8")
    ref_resampled_sitk = resample_isotropic(ref_sitk, target_spacing, is_mask=True)
    ref_resampled = sitk.GetArrayFromImage(ref_resampled_sitk).astype(bool)

    pred = segment_fn(vol_resampled)

    tempo = time.time() - t0

    return PatientResult(
        uid=uid,
        dice=dice_coefficient(pred, ref_resampled),
        iou=iou_score(pred, ref_resampled),
        sensitivity=sensitivity(pred, ref_resampled),
        precision=precision(pred, ref_resampled),
        tempo_segundos=tempo,
        pred_voxels=int(pred.sum()),
        ref_voxels=int(ref_resampled.sum()),
    )
