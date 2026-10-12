"""Avaliacao em lote e comparacao entre metodos (Sprint 4, secao 3.2 do doc):
Dice/IoU/sensibilidade/precisao com IC95% por bootstrap (min. 500 reamostras),
e comparacao pareada entre baseline e region growing no mesmo conjunto de
teste, mesmas metricas.
"""
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from .pipeline import run_pipeline_for_uid
from .metrics import bootstrap_ci, BootstrapResult


def evaluate_uids(
    uids: list[str],
    data_dir: Path,
    segment_fn: Callable,
    label: str = "",
    verbose: bool = True,
) -> pd.DataFrame:
    """Roda o pipeline completo (`run_pipeline_for_uid`) para cada uid e
    devolve uma tabela com uma linha por paciente."""
    rows = []
    total = len(uids)
    for i, uid in enumerate(uids, 1):
        r = run_pipeline_for_uid(uid, data_dir, segment_fn=segment_fn)
        rows.append(vars(r))
        if verbose:
            print(
                f"[{label} {i}/{total}] {uid[-10:]}  dice={r.dice:.4f}  iou={r.iou:.4f}  "
                f"tempo={r.tempo_segundos:.1f}s",
                flush=True,
            )
    return pd.DataFrame(rows)


def summarize_metric(df: pd.DataFrame, metric: str, n_resamples: int = 500, seed: int = 42) -> BootstrapResult:
    """Media + IC95% por bootstrap de uma metrica (ex: 'dice') sobre todos os
    pacientes da tabela."""
    return bootstrap_ci(df[metric].tolist(), n_resamples=n_resamples, seed=seed)


def compare_methods(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    label_a: str,
    label_b: str,
    metric: str = "dice",
    n_resamples: int = 500,
    seed: int = 42,
) -> dict:
    """Compara duas tabelas de resultados (mesmos pacientes, na mesma ordem
    de `uid`) numa metrica: media+IC95% de cada metodo, e a diferenca pareada
    (b - a) por paciente com seu proprio IC95% por bootstrap -- essa
    diferenca pareada e o jeito estatisticamente correto de comparar dois
    metodos no mesmo conjunto de teste (reduz variancia comparado a comparar
    os dois ICs isolados, porque usa o pareamento por paciente)."""
    merged = df_a[["uid", metric]].merge(df_b[["uid", metric]], on="uid", suffixes=(f"_{label_a}", f"_{label_b}"))
    assert len(merged) == len(df_a) == len(df_b), "os dois metodos precisam ter rodado exatamente nos mesmos uids"

    diffs = (merged[f"{metric}_{label_b}"] - merged[f"{metric}_{label_a}"]).tolist()

    return {
        "n_pacientes": len(merged),
        label_a: summarize_metric(df_a, metric, n_resamples, seed),
        label_b: summarize_metric(df_b, metric, n_resamples, seed),
        f"diferenca_pareada_{label_b}_menos_{label_a}": bootstrap_ci(diffs, n_resamples=n_resamples, seed=seed),
        "tabela_merged": merged,
    }
