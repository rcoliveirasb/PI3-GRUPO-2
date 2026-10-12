"""Abordagem avancada do Sprint 4 (secao 4.4): region growing.

Diferenca de mecanismo em relacao ao baseline (importante para a discussao
"desempenho x custo computacional" do projeto): o baseline aplica um UNICO
limiar global (-600 HU) em todo o volume. Region growing, em vez disso,
comeca de um ponto semente (seed) dentro de cada pulmao e cresce a regiao
incluindo vizinhos cuja intensidade e parecida com a da semente (banda de
tolerancia), voxel a voxel -- adaptativo ao redor de cada semente, nao um
corte fixo aplicado uniformemente ao volume inteiro.

Como nao ha clique manual do usuario (nao e uma ferramenta interativa), as
sementes sao escolhidas automaticamente: usamos um threshold auxiliar mais
permissivo (-320 HU, so para achar candidatos, nunca para decidir a fronteira
final) para localizar os dois maiores blobs de ar plausivelmente pulmonares,
e escolhemos como semente o ponto mais "interior" de cada um (o pico da
transformada de distancia -- o ponto mais longe de qualquer borda), a escolha
mais segura contra cair perto de uma fronteira ruidosa.

Igual ao baseline, a limpeza de fundo e feita fatia a fatia (`lung_air.py`) e
o crescimento fica restrito a essa regiao "seguramente pulmao ou vizinhanca" --
sem essa restricao, o crescimento por similaridade de intensidade vazaria pela
traqueia ate o ar externo (mesmo problema de conectividade descrito em
`baseline.py`), ja que ar tem intensidade parecida em qualquer lugar do corpo.
"""
import numpy as np
from scipy import ndimage
from skimage.segmentation import flood

from .lung_air import label_largest_components, fill_holes_per_slice

SEED_THRESHOLD_HU = -320  # mais permissivo que o baseline: so para achar sementes
FLOOD_TOLERANCE_HU = 200  # banda de similaridade ao redor do valor da semente
SAFE_BACKGROUND_VALUE = 400  # HU bem fora da faixa de ar -- barra o crescimento


def _find_seed_points(labeled: np.ndarray, keep_labels: list[int]) -> list[tuple]:
    """Um seed por componente: o voxel mais interior (pico da transformada de
    distancia) -- longe de qualquer borda do componente, a escolha mais
    robusta contra ruido na fronteira.

    A transformada de distancia e calculada so na caixa delimitadora (bounding
    box) do componente, nao no volume inteiro -- um pulmao tipicamente ocupa
    uma fracao pequena do volume total, entao isso evita processar milhoes de
    voxels de fundo a toa (from ~15s para <1s por semente)."""
    all_slices = ndimage.find_objects(labeled)  # 1 chamada so, indexado por rotulo-1
    seeds = []
    for lbl in keep_labels:
        slices = all_slices[lbl - 1]
        local_mask = labeled[slices] == lbl
        local_distance = ndimage.distance_transform_edt(local_mask)
        local_seed = np.unravel_index(np.argmax(local_distance), local_distance.shape)
        seed = tuple(local_seed[i] + slices[i].start for i in range(3))
        seeds.append(seed)
    return seeds


def segment_region_growing(
    volume_hu: np.ndarray,
    seed_threshold_hu: float = SEED_THRESHOLD_HU,
    tolerance_hu: float = FLOOD_TOLERANCE_HU,
    n_seeds: int = 2,
) -> np.ndarray:
    """Segmenta o parenquima pulmonar por region growing a partir de
    sementes automaticas (uma por pulmao).

    Mesma expectativa de entrada que `segment_baseline`: volume ja limpo
    (`preprocessing.clean_hu`) e reamostrado para espacamento isotropico.

    Retorna uma mascara booleana (z, y, x) do parenquima pulmonar.
    """
    seed_candidates = volume_hu < seed_threshold_hu
    labeled, keep_labels = label_largest_components(seed_candidates, n_keep=n_seeds)

    if not keep_labels:
        # nao achou nenhum candidato a pulmao -- caso degenerado
        return np.zeros_like(volume_hu, dtype=bool)

    seeds = _find_seed_points(labeled, keep_labels)

    # volume "seguro" para o flood crescer: fora da regiao candidata a
    # pulmao, empurra pra um HU bem alto (fora de qualquer tolerancia
    # plausivel), impedindo o crescimento de vazar pela traqueia ate o ar
    # externo ao corpo
    safe_domain = np.isin(labeled, keep_labels)
    flood_input = np.where(safe_domain, volume_hu, SAFE_BACKGROUND_VALUE)

    lungs = np.zeros_like(volume_hu, dtype=bool)
    for seed in seeds:
        grown = flood(flood_input, seed, tolerance=tolerance_hu)
        lungs |= grown

    lungs = fill_holes_per_slice(lungs)
    return lungs
