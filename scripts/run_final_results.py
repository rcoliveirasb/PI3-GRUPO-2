"""
Consolida os resultados finais dos 3 metodos de segmentacao (baseline, region
growing, U-Net) no conjunto de teste do split 70/15/15 (26 pacientes): media +
IC95% por bootstrap de cada metrica, comparacao pareada entre os metodos com
teste de Wilcoxon, e os dois graficos finais.

Substitui, para o split novo, o que o notebook sprint6_resultados_finais_grp2
fazia para o split antigo (60/20/20, arquivado em
data/luna16/archive_split_v1_60_20_20/).

Uso (a partir da raiz do repositorio): python scripts/run_final_results.py

Le:
  data/luna16/sprint4_baseline_test.csv
  data/luna16/sprint4_region_growing_test.csv
  data/luna16/sprint_unet_test.csv
Salva:
  data/luna16/tabela_resultados_finais.csv
  data/luna16/comparacao_pareada_final.csv
  data/luna16/grafico_dice_iou_final.png
  data/luna16/grafico_comparacao_pareada.png
"""
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from luna16.metrics import bootstrap_ci

SEED = 42
# Regra do projeto: minimo 500 reamostras. Usamos mais porque o IC do region
# growing (que tem um caso extremo) ainda oscila na 3a casa com 500.
N_RESAMPLES = 10000
META_DICE = 0.85
META_IOU = 0.75
DATA_DIR = Path("data/luna16")

METODOS = [
    ("baseline", "Baseline (threshold -600HU + morfologia)", "Baseline", "sprint4_baseline_test.csv", "steelblue"),
    ("region_growing", "Region growing", "Region growing", "sprint4_region_growing_test.csv", "darkorange"),
    ("unet", "U-Net 2D", "U-Net 2D", "sprint_unet_test.csv", "seagreen"),
]
METRICAS = [
    ("dice", "Dice"),
    ("iou", "IoU"),
    ("sensitivity", "Sensibilidade"),
    ("precision", "Precisão"),
    ("tempo_segundos", "Tempo/TC (s)"),
]


def carregar_resultados() -> dict[str, pd.DataFrame]:
    """Le os 3 CSVs e garante que os 3 metodos rodaram exatamente nos mesmos
    pacientes do conjunto de teste -- sem isso a comparacao pareada nao vale."""
    split = pd.read_csv(DATA_DIR / "split_full.csv")
    test_uids = set(split.loc[split["conjunto"] == "test", "uid"])

    dfs = {}
    for chave, _, _, arquivo, _ in METODOS:
        df = pd.read_csv(DATA_DIR / arquivo)
        assert df["uid"].is_unique, f"{arquivo}: uid duplicado"
        assert set(df["uid"]) == test_uids, f"{arquivo}: pacientes diferentes do conjunto de teste do split"
        dfs[chave] = df.sort_values("uid").reset_index(drop=True)
    return dfs


def fmt(r) -> str:
    return f"{r.mean:.4f} [{r.ci_low:.4f}, {r.ci_high:.4f}]"


def montar_tabela(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    linhas = []
    for chave, nome, _, _, _ in METODOS:
        df = dfs[chave]
        linha = {"Método": nome}
        for metrica, rotulo in METRICAS:
            linha[rotulo] = fmt(bootstrap_ci(df[metrica].tolist(), n_resamples=N_RESAMPLES, seed=SEED))
        linha["N"] = len(df)
        linha["Dice mínimo"] = f"{df['dice'].min():.4f}"
        linha[f"Exames com Dice < {META_DICE}"] = int((df["dice"] < META_DICE).sum())
        linhas.append(linha)
    return pd.DataFrame(linhas).set_index("Método")


def holm(p_values: list[float]) -> list[float]:
    """Correcao de Holm-Bonferroni para comparacoes multiplas."""
    ordem = np.argsort(p_values)
    m = len(p_values)
    ajustados = np.empty(m)
    anterior = 0.0
    for posicao, idx in enumerate(ordem):
        anterior = max(anterior, min(1.0, (m - posicao) * p_values[idx]))
        ajustados[idx] = anterior
    return ajustados.tolist()


def comparar_pares(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Para cada par de metodos e para Dice e IoU: diferenca pareada por
    paciente (B - A) com IC95% por bootstrap e teste de Wilcoxon pareado
    (nao assume normalidade, adequado para n=26 com casos extremos)."""
    nomes = {chave: curto for chave, _, curto, _, _ in METODOS}
    linhas = []
    for metrica, rotulo in METRICAS[:2]:
        bloco = []
        for a, b in combinations([m[0] for m in METODOS], 2):
            diffs = dfs[b][metrica].to_numpy() - dfs[a][metrica].to_numpy()
            r = bootstrap_ci(diffs.tolist(), n_resamples=N_RESAMPLES, seed=SEED)
            teste = wilcoxon(dfs[b][metrica], dfs[a][metrica])
            bloco.append(
                {
                    "Métrica": rotulo,
                    "Comparação (B - A)": f"{nomes[b]} - {nomes[a]}",
                    "N": len(diffs),
                    "Diferença média": round(r.mean, 4),
                    "IC95% inferior": round(r.ci_low, 4),
                    "IC95% superior": round(r.ci_high, 4),
                    "Exames em que B > A": int((diffs > 0).sum()),
                    "Wilcoxon W": float(teste.statistic),
                    "p-valor": float(teste.pvalue),
                }
            )
        for linha, p_ajustado in zip(bloco, holm([l["p-valor"] for l in bloco])):
            linha["p-valor (Holm)"] = p_ajustado
            linha["Significativo (5%)"] = "sim" if p_ajustado < 0.05 else "não"
        linhas.extend(bloco)
    return pd.DataFrame(linhas)


def grafico_dice_iou(dfs: dict[str, pd.DataFrame], n: int) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    rotulos = [curto for _, _, curto, _, _ in METODOS]
    cores = [cor for *_, cor in METODOS]

    for ax, metrica, titulo, meta in [(axes[0], "dice", "Dice Coefficient", META_DICE), (axes[1], "iou", "IoU (Jaccard)", META_IOU)]:
        medias, erros_baixo, erros_alto = [], [], []
        for chave, *_ in METODOS:
            r = bootstrap_ci(dfs[chave][metrica].tolist(), n_resamples=N_RESAMPLES, seed=SEED)
            medias.append(r.mean)
            erros_baixo.append(r.mean - r.ci_low)
            erros_alto.append(r.ci_high - r.mean)

        barras = ax.bar(rotulos, medias, yerr=[erros_baixo, erros_alto], capsize=8, color=cores)
        ax.bar_label(barras, labels=[f"{m:.3f}" for m in medias], padding=14)
        ax.axhline(meta, color="red", linestyle="--", label=f"Meta do projeto ({meta})")
        ax.set_ylabel(titulo)
        ax.set_title(f"{titulo} médio ± IC95% (bootstrap, {n} TCs de teste)")
        ax.set_ylim(0, 1.1)
        ax.legend(loc="lower right")

    plt.tight_layout()
    plt.savefig(str(DATA_DIR / "grafico_dice_iou_final.png"), dpi=150)
    plt.close(fig)


def grafico_pareado(dfs: dict[str, pd.DataFrame], n: int) -> None:
    ordem = dfs["baseline"]["dice"].sort_values().index
    x = np.arange(n)

    fig, ax = plt.subplots(figsize=(10, 6))
    for (chave, _, curto, _, cor), marcador in zip(METODOS, ["o-", "s-", "^-"]):
        ax.plot(x, dfs[chave]["dice"].loc[ordem].to_numpy(), marcador, label=curto, color=cor)
    ax.axhline(META_DICE, color="red", linestyle="--", alpha=0.5, label=f"Meta ({META_DICE})")
    ax.set_xlabel("Paciente (ordenado por Dice do baseline)")
    ax.set_ylabel("Dice")
    ax.set_title(f"Dice por paciente — comparação pareada ({n} TCs de teste)")
    ax.set_ylim(0, 1.02)
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(str(DATA_DIR / "grafico_comparacao_pareada.png"), dpi=150)
    plt.close(fig)


def main():
    dfs = carregar_resultados()
    n = len(dfs["baseline"])
    print(f"N = {n} pacientes de teste, mesmos uids nos 3 metodos\n", flush=True)

    tabela = montar_tabela(dfs)
    tabela.to_csv(DATA_DIR / "tabela_resultados_finais.csv")
    print(tabela.to_string(), "\n", flush=True)

    comparacao = comparar_pares(dfs)
    comparacao.to_csv(DATA_DIR / "comparacao_pareada_final.csv", index=False)
    print(comparacao.to_string(index=False), "\n", flush=True)

    grafico_dice_iou(dfs, n)
    grafico_pareado(dfs, n)
    print("CONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
