"""Baseline obrigatorio (secao 4.3): threshold em -600 HU + operacoes
morfologicas (erosao + dilatacao).

So limiarizar em -600 HU nao basta: o resultado inclui o ar fora do corpo
(fundo da imagem), ar em outras cavidades (intestino) e fica com buracos onde
ha vasos/nodulos dentro do pulmao (que sao tecido, nao ar, mas devem contar
como parenquima). O algoritmo classico de segmentacao pulmonar (usado em
varios baselines da literatura, ex. tutoriais do Kaggle DSB2017) resolve isso
em 4 passos, implementados aqui:

  1. threshold: ar = HU < -600
  2. remover o ar "de fundo" (fora do corpo) fatia a fatia -- ver
     `lung_air.remove_background_per_slice` para o porque de ser 2D e nao 3D
  3. manter so os 1-2 maiores componentes restantes (os pulmoes)
  4. preencher buracos (fatia a fatia) para incluir vasos/nodulos, depois
     abertura morfologica (erosao seguida de dilatacao) para remover
     estruturas pequenas espurias sem distorcer o contorno do pulmao
"""
import numpy as np
from skimage import morphology

from .lung_air import keep_largest_components, fill_holes_per_slice

THRESHOLD_HU = -600


def segment_baseline(
    volume_hu: np.ndarray,
    threshold_hu: float = THRESHOLD_HU,
    opening_radius: int = 1,
    n_components: int = 2,
) -> np.ndarray:
    """Segmenta o parenquima pulmonar por threshold + morfologia.

    Espera um volume ja limpo (`preprocessing.clean_hu`) e, idealmente, ja
    reamostrado para espacamento isotropico -- `opening_radius` e em voxels,
    entao so tem significado fisico consistente se o voxel for aprox. cubico.

    Retorna uma mascara booleana (z, y, x) do parenquima pulmonar.
    """
    air = volume_hu < threshold_hu

    lungs = keep_largest_components(air, n_keep=n_components)
    lungs = fill_holes_per_slice(lungs)

    # abertura morfologica (erosao + dilatacao): remove saliencias/pontes
    # finas (ex: conexao residual com a traqueia) sem encolher o pulmao como
    # um todo, ja que a dilatacao seguinte desfaz a erosao nas regioes largas
    footprint = morphology.ball(opening_radius)
    lungs = morphology.erosion(lungs, footprint)
    lungs = morphology.dilation(lungs, footprint)

    return lungs
