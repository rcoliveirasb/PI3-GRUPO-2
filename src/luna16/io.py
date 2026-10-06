"""Carregamento de volumes de CT e mascaras de referencia do LUNA16.

Convencao de rotulos da mascara de referencia (seg-lungs-LUNA16), verificada
empiricamente (ver Sprint 3, secao 1 do notebook) em varios pacientes do
subset0:
    0 = fundo
    3 = pulmao direito
    4 = pulmao esquerdo
    5 = traqueia / vias aereas centrais

O projeto pede a segmentacao do *parenquima* pulmonar, entao a mascara de
referencia usada para Dice/IoU e a uniao dos rotulos 3 e 4 (rotulo 5 fica de
fora: traqueia nao e parenquima).
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import SimpleITK as sitk

LUNG_LABELS = (3, 4)  # pulmao direito e esquerdo na mascara seg-lungs-LUNA16
TRACHEA_LABEL = 5


@dataclass
class CTVolume:
    """Um volume de CT (ou mascara) com metadados de espacamento.

    array: numpy array (z, y, x) -- SimpleITK.GetArrayFromImage ja retorna
        nessa ordem (eixo mais lento primeiro).
    spacing: (x, y, z) em mm, na convencao do SimpleITK (mais rapido primeiro).
    origin, direction: preservados para permitir re-exportar como SimpleITK
        Image caso seja necessario (ex: salvar uma mascara predita).
    """

    array: np.ndarray
    spacing: tuple
    origin: tuple
    direction: tuple

    @property
    def spacing_zyx(self) -> tuple:
        """Espacamento na mesma ordem dos eixos do array (z, y, x)."""
        sx, sy, sz = self.spacing
        return (sz, sy, sx)

    def to_sitk_image(self) -> sitk.Image:
        img = sitk.GetImageFromArray(self.array)
        img.SetSpacing(self.spacing)
        img.SetOrigin(self.origin)
        img.SetDirection(self.direction)
        return img


def _read_volume(path: Path) -> CTVolume:
    img = sitk.ReadImage(str(path))
    array = sitk.GetArrayFromImage(img)
    return CTVolume(
        array=array,
        spacing=img.GetSpacing(),
        origin=img.GetOrigin(),
        direction=img.GetDirection(),
    )


def _find_ct_path(uid: str, data_dir: Path) -> Path:
    """Acha o .mhd do paciente em qualquer pasta subsetN/ ja baixada
    (o LUNA16 espalha os pacientes em varios subsets de ~89 cada)."""
    matches = list(Path(data_dir).glob(f"subset*/{uid}.mhd"))
    if not matches:
        raise FileNotFoundError(f"CT do paciente {uid} nao encontrada em nenhum subset* de {data_dir}")
    return matches[0]


def load_ct(uid: str, data_dir: Path) -> CTVolume:
    """Carrega o volume de CT (valores ja em HU, RescaleSlope/Intercept
    aplicados pelo proprio LUNA16 na curadoria) de `data_dir/subsetN/<uid>.mhd`."""
    return _read_volume(_find_ct_path(uid, data_dir))


def load_reference_mask(uid: str, data_dir: Path) -> np.ndarray:
    """Carrega a mascara de referencia binaria do parenquima pulmonar
    (uniao dos rotulos 3 e 4) para o paciente `uid`."""
    path = Path(data_dir) / "seg-lungs-LUNA16" / f"{uid}.mhd"
    vol = _read_volume(path)
    return np.isin(vol.array, LUNG_LABELS)


def list_available_uids(data_dir: Path) -> list[str]:
    """UIDs de pacientes (de qualquer subsetN/ ja baixado) que tem tanto CT
    quanto mascara de referencia disponiveis localmente."""
    ct_uids = {p.stem for p in Path(data_dir).glob("subset*/*.mhd")}
    masks_dir = Path(data_dir) / "seg-lungs-LUNA16"
    mask_uids = {p.stem for p in masks_dir.glob("*.mhd")}
    return sorted(ct_uids & mask_uids)
