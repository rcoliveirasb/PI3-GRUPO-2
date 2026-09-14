"""Pre-processamento: normalizacao de HU, remocao de ruido, resampling
isotropico (Sprint 3, Etapa KDD: Pre-processamento).

Importante: o threshold do baseline (-600 HU) so faz sentido em unidades de
Hounsfield reais. Por isso "normalizar" aqui NAO significa reescalar para
[0,1] (isso destruiria o significado fisico do threshold) -- significa:
  1. Remover o valor de padding (-2048/-3024 HU, fora do FOV circular do
     scanner) que nao representa tecido real.
  2. Limitar (clip) valores extremos que nao aparecem em tecido pulmonar
     normal, para reduzir o efeito de outliers no filtro de ruido.
A funcao `normalize_for_display` (rescale para [0,1]) existe soh para
visualizacao, nunca para o pipeline de segmentacao em si.
"""
import numpy as np
import SimpleITK as sitk
from scipy import ndimage

PADDING_HU = -2048
CLIP_MIN_HU = -1000  # ar puro
CLIP_MAX_HU = 400  # acima disso e osso/contraste, irrelevante p/ pulmao


def clean_hu(volume_hu: np.ndarray) -> np.ndarray:
    """Substitui o valor de padding por ar (-1000 HU) e faz o clip para a
    faixa relevante ao pulmao. Mantem unidades de HU reais."""
    cleaned = volume_hu.copy()
    cleaned[cleaned <= PADDING_HU + 1] = CLIP_MIN_HU
    return np.clip(cleaned, CLIP_MIN_HU, CLIP_MAX_HU)


def denoise(volume_hu: np.ndarray, sigma: float = 0.5) -> np.ndarray:
    """Suaviza ruido de aquisicao com um filtro Gaussiano leve, aplicado em
    3D. `sigma` pequeno (0.5 voxel) preserva bordas do pulmao; valores muito
    maiores comecam a borrar a fronteira pulmao/tecido mole, que e justamente
    o que o threshold depois precisa distinguir."""
    return ndimage.gaussian_filter(volume_hu, sigma=sigma)


def normalize_for_display(volume_hu: np.ndarray, vmin: float = -1000, vmax: float = 400) -> np.ndarray:
    """Reescala HU para [0,1] -- so para visualizacao (ex: imshow), nunca
    para alimentar o threshold do baseline."""
    return np.clip((volume_hu - vmin) / (vmax - vmin), 0, 1)


def resample_isotropic(sitk_image: sitk.Image, target_spacing=(1.0, 1.0, 1.0), is_mask: bool = False) -> sitk.Image:
    """Reamostra um volume SimpleITK para espacamento isotropico (1mm por
    padrao). Interpolacao linear para CT (preserva gradientes de HU) e
    nearest-neighbor para mascaras (preserva valores de rotulo binarios/
    discretos -- interpolar uma mascara linearmente criaria valores
    fracionarios sem sentido)."""
    original_spacing = sitk_image.GetSpacing()
    original_size = sitk_image.GetSize()

    new_size = [
        int(round(osz * ospc / tspc))
        for osz, ospc, tspc in zip(original_size, original_spacing, target_spacing)
    ]

    resampler = sitk.ResampleImageFilter()
    resampler.SetOutputSpacing(target_spacing)
    resampler.SetSize(new_size)
    resampler.SetOutputOrigin(sitk_image.GetOrigin())
    resampler.SetOutputDirection(sitk_image.GetDirection())
    resampler.SetTransform(sitk.Transform())
    resampler.SetDefaultPixelValue(0 if is_mask else CLIP_MIN_HU)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor if is_mask else sitk.sitkLinear)

    return resampler.Execute(sitk_image)
