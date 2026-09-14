"""Utilitarios de limpeza de mascaras de ar, compartilhados pelo baseline
(`baseline.py`) e pelo region growing (`region_growing.py`).

Ficam num modulo a parte porque os dois metodos de segmentacao precisam do
mesmo cuidado: separar o ar do pulmao do ar "de fundo" (externo ao corpo,
ou continuo com o ar externo via traqueia/boca/nariz). Ver `baseline.py`
para a explicacao completa do problema que `remove_background_per_slice`
resolve -- resumo: tem que ser fatia a fatia (2D), nao no volume 3D inteiro,
senao a traqueia liga o pulmao ao ar externo e o pulmao e descartado junto
com o fundo.
"""
import numpy as np
from scipy import ndimage
from skimage import measure


def remove_background_per_slice(binary: np.ndarray) -> np.ndarray:
    """Remove o ar "de fundo" fatia a fatia (2D), usando o **perimetro
    inteiro** de cada fatia (toda a borda -- topo, base, laterais) para
    identificar os rotulos de fundo, nao so os 4 pixels de canto.

    Achado real (Sprint 5, analise de falha): usar so os 4 cantos deixa
    passar um caso concreto -- a maca/mesa do tomografo cria uma regiao de
    ar (padding fora do FOV circular, convertido para ar em `clean_hu`) em
    formato de crescente que encosta na borda inferior da imagem sem tocar
    exatamente um dos 4 pixels de canto. Isso nao e removido pelo teste de
    canto, e se essa regiao se conectar em 3D a um dos pulmoes (comum perto
    da base do exame), ela e mantida junto com o pulmao -- inflando muito os
    falsos positivos (queda de precisao) mantendo a sensibilidade alta,
    exatamente o padrao observado nos piores casos do conjunto de teste.

    Usar o perimetro inteiro (nao so os cantos) resolve isso com seguranca em
    2D: ao contrario do eixo z (onde o pulmao real pode legitimamente tocar
    o plano de topo/base do exame, se o FOV for bem recortado ao torax -- ver
    Sprint 3), o pulmao real nunca encosta na borda lateral/superior/inferior
    do campo de visao em x/y -- ha sempre uma margem generosa de ar/tecido
    entre o pulmao e a borda da imagem reconstruida."""
    cleaned = np.zeros_like(binary)
    for z in range(binary.shape[0]):
        slice_labels = measure.label(binary[z], connectivity=1)
        if slice_labels.max() == 0:
            continue
        border_labels = set()
        border_labels.update(slice_labels[0, :].tolist())
        border_labels.update(slice_labels[-1, :].tolist())
        border_labels.update(slice_labels[:, 0].tolist())
        border_labels.update(slice_labels[:, -1].tolist())
        border_labels.discard(0)
        slice_clean = slice_labels.copy()
        for lbl in border_labels:
            slice_clean[slice_clean == lbl] = 0
        cleaned[z] = slice_clean > 0
    return cleaned


def keep_largest_components(binary: np.ndarray, n_keep: int = 2) -> np.ndarray:
    """Limpa o fundo (fatia a fatia) e mantem so os `n_keep` maiores
    componentes conexos em 3D -- tipicamente os dois pulmoes."""
    no_background = remove_background_per_slice(binary)

    labeled = measure.label(no_background, connectivity=1)
    if labeled.max() == 0:
        return np.zeros_like(binary, dtype=bool)

    sizes = np.bincount(labeled.ravel())
    sizes[0] = 0  # ignora o fundo
    keep_labels = np.argsort(sizes)[::-1][:n_keep]
    keep_labels = [l for l in keep_labels if sizes[l] > 0]

    return np.isin(labeled, keep_labels)


def label_largest_components(binary: np.ndarray, n_keep: int = 2) -> tuple[np.ndarray, list[int]]:
    """Como `keep_largest_components`, mas devolve o volume rotulado (cada
    componente com seu proprio inteiro) em vez de uma mascara booleana unica
    -- necessario quando o chamador precisa tratar os componentes
    separadamente (ex: um seed por pulmao no region growing)."""
    no_background = remove_background_per_slice(binary)
    labeled = measure.label(no_background, connectivity=1)
    if labeled.max() == 0:
        return labeled, []

    sizes = np.bincount(labeled.ravel())
    sizes[0] = 0
    keep_labels = [int(l) for l in np.argsort(sizes)[::-1][:n_keep] if sizes[l] > 0]
    return labeled, keep_labels


def fill_holes_per_slice(binary: np.ndarray) -> np.ndarray:
    """Preenche buracos fatia a fatia (eixo z) -- inclui vasos/nodulos
    (tecido, nao ar) dentro do parenquima, como a mascara de referencia
    espera."""
    filled = np.zeros_like(binary)
    for z in range(binary.shape[0]):
        filled[z] = ndimage.binary_fill_holes(binary[z])
    return filled
