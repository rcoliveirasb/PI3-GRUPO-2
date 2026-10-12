"""Criterios de selecao/exclusao de TCs (Sprint 3, KDD: Selecao).

O LUNA16 ja aplica uma curadoria propria sobre o LIDC-IDRI (exclui series com
espessura de corte > 2.5mm e espacamento entre fatias inconsistente), entao
os criterios abaixo sao principalmente uma *verificacao* de que essa curadoria
se sustenta no nosso subconjunto (subset0), mais um criterio de integridade
que e nosso (mascara de referencia tem que existir e nao pode ser vazia).

Artefatos severos (pulmao colapsado, derrame pleural extremo etc.) sao dificeis
de detectar de forma confiavel so com metadados -- exigem inspecao visual.
Por isso o modulo tambem expoe `plot_qc_slices` para o grupo revisar
rapidamente os casos escolhidos antes de rodar o pipeline completo.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk

from .io import load_reference_mask

MAX_SLICE_SPACING_MM = 2.5  # criterio do doc do projeto (secao 4.4)


def build_header_table(data_dir: Path) -> pd.DataFrame:
    """Le so o cabecalho (.mhd) de cada CT de qualquer subsetN/ ja baixado --
    rapido, nao carrega os pixels -- e monta uma tabela com metadados usados
    nos criterios de selecao."""
    masks_dir = Path(data_dir) / "seg-lungs-LUNA16"
    rows = []
    for mhd in sorted(Path(data_dir).glob("subset*/*.mhd")):
        uid = mhd.stem
        reader = sitk.ImageFileReader()
        reader.SetFileName(str(mhd))
        reader.ReadImageInformation()
        size = reader.GetSize()
        spacing = reader.GetSpacing()
        rows.append(
            {
                "uid": uid,
                "n_slices": size[2],
                "rows": size[1],
                "cols": size[0],
                "spacing_x": spacing[0],
                "spacing_y": spacing[1],
                "spacing_z": spacing[2],
                "has_mask": (masks_dir / f"{uid}.mhd").exists(),
            }
        )
    return pd.DataFrame(rows)


def apply_selection_criteria(header_df: pd.DataFrame, data_dir: Path) -> pd.DataFrame:
    """Aplica os criterios de exclusao e devolve a tabela com uma coluna
    booleana `incluido` e uma coluna `motivo_exclusao` (None se incluido).

    Criterios:
      1. Precisa ter mascara de referencia (`has_mask`) -- sem isso nao da
         pra calcular Dice/IoU.
      2. Espacamento entre fatias (spacing_z) <= 2.5mm -- criterio explicito
         do doc do projeto; no LUNA16 curado isso ja e quase sempre verdade,
         mas verificamos mesmo assim.
      3. Mascara de referencia nao pode ser vazia (paciente sem nenhum voxel
         de pulmao anotado -- indicaria mascara corrompida/ausente de fato).
    """
    df = header_df.copy()
    df["motivo_exclusao"] = None

    sem_mascara = ~df["has_mask"]
    df.loc[sem_mascara, "motivo_exclusao"] = "sem mascara de referencia"

    espacamento_grande = df["spacing_z"] > MAX_SLICE_SPACING_MM
    df.loc[espacamento_grande & df["motivo_exclusao"].isna(), "motivo_exclusao"] = (
        f"espacamento entre fatias > {MAX_SLICE_SPACING_MM}mm"
    )

    # mascara vazia: so verificamos para quem passou nos criterios anteriores
    # (carregar a mascara tem custo, entao evitamos fazer isso a toa)
    candidatos = df[df["motivo_exclusao"].isna()]
    for uid in candidatos["uid"]:
        mask = load_reference_mask(uid, data_dir)
        if mask.sum() == 0:
            df.loc[df["uid"] == uid, "motivo_exclusao"] = "mascara de referencia vazia"

    df["incluido"] = df["motivo_exclusao"].isna()
    return df


def plot_qc_slices(volume_array: np.ndarray, uid: str, n_slices: int = 3):
    """Plota `n_slices` cortes axiais (inicio, meio, fim) para inspecao visual
    rapida de artefatos severos (pulmao colapsado, derrame pleural, ruido).
    Devolve a figura do matplotlib para o notebook exibir/salvar."""
    import matplotlib.pyplot as plt

    z = volume_array.shape[0]
    idxs = np.linspace(0, z - 1, n_slices, dtype=int)
    fig, axes = plt.subplots(1, n_slices, figsize=(4 * n_slices, 4))
    if n_slices == 1:
        axes = [axes]
    for ax, idx in zip(axes, idxs):
        ax.imshow(volume_array[idx], cmap="gray", vmin=-1000, vmax=400)
        ax.set_title(f"{uid[-8:]} slice {idx}/{z}")
        ax.axis("off")
    fig.tight_layout()
    return fig
