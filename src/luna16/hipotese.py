"""Teste formal das hipoteses do trabalho (ver docs/hipotese.md).

Hipotese geral: a segmentacao automatica do parenquima pulmonar em TC do
LUNA16 atinge sobreposicao util (Dice acima da meta do projeto) com metodos
classicos baseados na escala de Hounsfield, e um metodo aprendido (U-Net 2D)
supera os metodos classicos em sobreposicao.

Ela se divide em tres hipoteses testaveis, cada uma com H0 e H1 explicitas:

  H1 -- Meta do projeto (pergunta SMART): o Dice medio de cada metodo e maior
        que a meta (0,85 para os classicos, 0,75 para a U-Net).
  H2 -- Adaptativo x global: o region growing (limiar adaptativo ao redor de
        uma semente) tem Dice maior que o baseline (limiar global de -600 HU).
  H3 -- Aprendido x classico: a U-Net 2D tem Dice maior que cada metodo
        classico.

Por que Wilcoxon e nao teste t: ha casos extremos (no teste novo de 107
exames, o baseline tem um exame com Dice 0,38; no Teste A de 26, o region
growing tem um com 0,59), entao nao da para assumir normalidade das
diferencas. O teste de postos sinalizados de Wilcoxon nao assume isso.
Todos os testes sao UNILATERAIS (a hipotese alternativa tem direcao) e
pareados por paciente (os mesmos exames para os tres metodos). Dentro de cada
familia com mais de um teste, os p-valores sao corrigidos por Holm.
"""
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from .metrics import bootstrap_ci

ALFA = 0.05
SEED = 42
N_RESAMPLES = 10000
META_DICE_CLASSICOS = 0.85
META_DICE_UNET = 0.75

NOMES = {"baseline": "Baseline", "region_growing": "Region growing", "unet": "U-Net 2D"}


@dataclass
class ResultadoTeste:
    hipotese: str
    h0: str
    h1: str
    estatistica: str
    efeito: float
    ic95_inferior: float
    ic95_superior: float
    w: float
    p_valor: float
    p_valor_holm: float
    rejeita_h0: bool
    conclusao: str


def _holm(p_values: list[float]) -> list[float]:
    ordem = np.argsort(p_values)
    m = len(p_values)
    ajustados = np.empty(m)
    anterior = 0.0
    for posicao, idx in enumerate(ordem):
        anterior = max(anterior, min(1.0, (m - posicao) * p_values[idx]))
        ajustados[idx] = anterior
    return ajustados.tolist()


def _teste_meta(dice: np.ndarray, metodo: str, meta: float) -> dict:
    """H0: Dice medio <= meta. H1: Dice medio > meta (Wilcoxon de 1 amostra
    sobre Dice - meta, unilateral)."""
    r = bootstrap_ci(dice.tolist(), n_resamples=N_RESAMPLES, seed=SEED)
    t = wilcoxon(dice - meta, alternative="greater")
    nome = NOMES[metodo]
    return dict(
        hipotese=f"H1 ({nome})",
        h0=f"Dice medio do {nome} <= {meta}",
        h1=f"Dice medio do {nome} > {meta}",
        estatistica="Dice medio [IC95% bootstrap]",
        efeito=r.mean, ic95_inferior=r.ci_low, ic95_superior=r.ci_high,
        w=float(t.statistic), p_valor=float(t.pvalue),
    )


def _teste_par(dice_b: np.ndarray, dice_a: np.ndarray, b: str, a: str, rotulo: str) -> dict:
    """H0: mediana de (Dice_B - Dice_A) <= 0. H1: > 0 (Wilcoxon pareado,
    unilateral)."""
    diffs = dice_b - dice_a
    r = bootstrap_ci(diffs.tolist(), n_resamples=N_RESAMPLES, seed=SEED)
    t = wilcoxon(dice_b, dice_a, alternative="greater")
    return dict(
        hipotese=rotulo,
        h0=f"Dice do {NOMES[b]} <= Dice do {NOMES[a]}",
        h1=f"Dice do {NOMES[b]} > Dice do {NOMES[a]}",
        estatistica=f"Diferenca media de Dice ({NOMES[b]} - {NOMES[a]}) [IC95%]",
        efeito=r.mean, ic95_inferior=r.ci_low, ic95_superior=r.ci_high,
        w=float(t.statistic), p_valor=float(t.pvalue),
    )


def _concluir(linha: dict) -> str:
    if linha["rejeita_h0"]:
        return "H0 rejeitada: evidencia a favor de H1"
    # Nao rejeitar H0 nao prova H0; mas se o IC da diferenca fica inteiro
    # abaixo de zero, o efeito observado e o OPOSTO do previsto em H1.
    if linha["estatistica"].startswith("Diferenca") and linha["ic95_superior"] < 0:
        return "H0 nao rejeitada: o efeito observado e o oposto do previsto (IC95% inteiro abaixo de 0)"
    return "H0 nao rejeitada: sem evidencia suficiente para H1"


def testar_hipoteses(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Recebe {'baseline': df, 'region_growing': df, 'unet': df}, cada um com
    colunas uid e dice, os mesmos uids nos tres. Devolve uma linha por teste."""
    uids = [set(df["uid"]) for df in dfs.values()]
    assert all(u == uids[0] for u in uids), "os tres metodos precisam ter os mesmos pacientes"
    dice = {k: df.sort_values("uid")["dice"].to_numpy() for k, df in dfs.items()}

    familias = [
        [
            _teste_meta(dice["baseline"], "baseline", META_DICE_CLASSICOS),
            _teste_meta(dice["region_growing"], "region_growing", META_DICE_CLASSICOS),
            _teste_meta(dice["unet"], "unet", META_DICE_UNET),
        ],
        [_teste_par(dice["region_growing"], dice["baseline"], "region_growing", "baseline", "H2")],
        [
            _teste_par(dice["unet"], dice["baseline"], "unet", "baseline", "H3a"),
            _teste_par(dice["unet"], dice["region_growing"], "unet", "region_growing", "H3b"),
        ],
    ]

    linhas = []
    for familia in familias:
        for linha, p_holm in zip(familia, _holm([l["p_valor"] for l in familia])):
            linha["p_valor_holm"] = p_holm
            linha["rejeita_h0"] = p_holm < ALFA
            linha["conclusao"] = _concluir(linha)
            linhas.append(asdict(ResultadoTeste(**linha)))
    return pd.DataFrame(linhas)
