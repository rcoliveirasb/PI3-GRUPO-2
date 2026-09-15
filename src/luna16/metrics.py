"""Metricas de avaliacao (secao 7.3): Dice, IoU, sensibilidade, precisao por
pixel, e bootstrap para intervalo de confianca 95% (minimo 500 reamostras).
"""
from dataclasses import dataclass

import numpy as np


def dice_coefficient(pred: np.ndarray, gt: np.ndarray) -> float:
    """2|A∩B| / (|A|+|B|). 1.0 se ambos vazios (convencao: sem pulmao
    predito e sem pulmao real = acerto, evita divisao por zero)."""
    pred, gt = pred.astype(bool), gt.astype(bool)
    intersection = np.logical_and(pred, gt).sum()
    denom = pred.sum() + gt.sum()
    if denom == 0:
        return 1.0
    return 2.0 * intersection / denom


def iou_score(pred: np.ndarray, gt: np.ndarray) -> float:
    """|A∩B| / |A∪B| (Jaccard). Sempre <= Dice; penaliza erro de forma mais."""
    pred, gt = pred.astype(bool), gt.astype(bool)
    intersection = np.logical_and(pred, gt).sum()
    union = np.logical_or(pred, gt).sum()
    if union == 0:
        return 1.0
    return intersection / union


def sensitivity(pred: np.ndarray, gt: np.ndarray) -> float:
    """Recall / taxa de verdadeiros positivos: fracao do pulmao real que foi
    identificada. Mede se o modelo esta deixando pulmao de fora."""
    pred, gt = pred.astype(bool), gt.astype(bool)
    true_positive = np.logical_and(pred, gt).sum()
    if gt.sum() == 0:
        return 1.0 if pred.sum() == 0 else 0.0
    return true_positive / gt.sum()


def precision(pred: np.ndarray, gt: np.ndarray) -> float:
    """Fracao dos pixels preditos como pulmao que realmente sao pulmao. Mede
    se o modelo esta incluindo estruturas que nao pertencem ao pulmao."""
    pred, gt = pred.astype(bool), gt.astype(bool)
    true_positive = np.logical_and(pred, gt).sum()
    if pred.sum() == 0:
        return 1.0 if gt.sum() == 0 else 0.0
    return true_positive / pred.sum()


@dataclass
class BootstrapResult:
    mean: float
    ci_low: float
    ci_high: float
    n_resamples: int

    def __repr__(self):
        return f"{self.mean:.4f} (IC95% [{self.ci_low:.4f}, {self.ci_high:.4f}], n={self.n_resamples} reamostras)"


def bootstrap_ci(values: list[float], n_resamples: int = 500, ci: float = 0.95, seed: int = 42) -> BootstrapResult:
    """Bootstrap nao-parametrico sobre uma lista de valores por paciente
    (ex: Dice de cada TC no conjunto de teste). Reamostra com reposicao
    `n_resamples` vezes, calcula a media de cada reamostra, e devolve a
    media original + o intervalo de confianca por percentil.

    Regra do projeto (secao 3.2): minimo 500 reamostras.
    """
    assert n_resamples >= 500, "o projeto exige minimo 500 reamostras no bootstrap"
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)

    means = np.empty(n_resamples)
    n = len(values)
    for i in range(n_resamples):
        sample = rng.choice(values, size=n, replace=True)
        means[i] = sample.mean()

    alpha = 1 - ci
    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return BootstrapResult(mean=float(values.mean()), ci_low=float(lo), ci_high=float(hi), n_resamples=n_resamples)
