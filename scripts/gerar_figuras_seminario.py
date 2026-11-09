"""Figuras do seminario (Amabilly): tabela final dos 3 metodos depois das
correcoes e grafico de nodulos apagados por metodo. Cores do deck do grupo.

Uso (a partir da raiz): python scripts/gerar_figuras_seminario.py
Le:  data/luna16/sprint4_baseline_test.csv, sprint4_region_growing_test.csv,
     sprint_unet_test.csv, comparacao_pareada_final.csv,
     nodulos_apagados_teste.csv (se existir)
Salva em docs/seminario/
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

D = Path("data/luna16")
OUT = Path("docs/seminario")
OUT.mkdir(parents=True, exist_ok=True)

VINHO = "#4a2533"
ROSA = "#c0506a"
MALVA = "#7a5a63"
FUNDO = "#f8f4f3"
CINZA = "#e8e3e1"

tab = pd.read_csv(D / "tabela_resultados_finais.csv")
csvs = {
    "Baseline (limiar −600 HU)": "sprint4_baseline_test.csv",
    "Region growing": "sprint4_region_growing_test.csv",
    "U-Net 2D": "sprint_unet_test.csv",
}
antes = {"Baseline (limiar −600 HU)": "0,9555",
         "Region growing": "0,9065", "U-Net 2D": "0,9781"}


def br(x, n=4):
    return f"{x:.{n}f}".replace(".", ",")


linhas = []
for (nome, f), dice_ic in zip(csvs.items(), tab["Dice"]):
    d = pd.read_csv(D / f)
    ic = dice_ic.replace(".", ",").replace(", [", " [").replace(",  ", "; ")
    lo, hi = dice_ic.split("[")[1].rstrip("]").split(", ")
    linhas.append([
        nome,
        antes[nome],
        f"{br(d.dice.mean())} [{br(float(lo))}; {br(float(hi))}]",
        br(d.dice.min(), 3),
        f"{(d.dice < 0.85).sum()} de {len(d)}",
        f"{d.tempo_segundos.mean():.0f} s",
    ])
cab = ["Método", "Dice antes", "Dice agora [IC95%]", "Pior exame", "Dice < 0,85", "Tempo/TC"]

fig, ax = plt.subplots(figsize=(13, 3.0), dpi=200)
fig.patch.set_facecolor(FUNDO)
ax.axis("off")
t = ax.table(cellText=linhas, colLabels=cab, loc="center", cellLoc="left",
             colWidths=[0.33, 0.11, 0.27, 0.11, 0.12, 0.10])
t.auto_set_font_size(False)
t.set_fontsize(12)
t.scale(1, 2.3)
for (r, c), cell in t.get_celld().items():
    cell.set_edgecolor("#cfc6c4")
    if r == 0:
        cell.set_facecolor(CINZA)
        cell.set_text_props(weight="bold", color=VINHO)
    else:
        cell.set_facecolor("white")
        cell.set_text_props(color="#3a2a2f")
        if c == 1:
            cell.set_text_props(color="#9a8a8f")
        if r == 3 and c == 2:
            cell.set_text_props(weight="bold", color=ROSA)
fig.savefig(OUT / "tabela_3_metodos_pos_correcoes.png", bbox_inches="tight", facecolor=FUNDO)
plt.close(fig)
print("salvo", OUT / "tabela_3_metodos_pos_correcoes.png")

nod = D / "nodulos_apagados_teste.csv"
if nod.exists():
    n = pd.read_csv(nod)
    borda = n["posicao"] == "colado_na_borda"
    metodos = [("referencia", "Referência\nLUNA16"), ("baseline", "Baseline"),
               ("region_growing", "Region\ngrowing"), ("unet", "U-Net 2D")]
    ap_b = [int((~n.loc[borda, f"{m}_mantido"].astype(bool)).sum()) for m, _ in metodos]
    ap_i = [int((~n.loc[~borda, f"{m}_mantido"].astype(bool)).sum()) for m, _ in metodos]

    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200)
    fig.patch.set_facecolor(FUNDO)
    ax.set_facecolor(FUNDO)
    x = range(len(metodos))
    ax.bar(x, ap_b, color=ROSA, label=f"colados na borda (de {int(borda.sum())})", width=0.6)
    ax.bar(x, ap_i, bottom=ap_b, color=MALVA, label=f"no interior (de {int((~borda).sum())})", width=0.6)
    for i, (b, it) in enumerate(zip(ap_b, ap_i)):
        ax.text(i, b + it + 0.3, f"{b + it}", ha="center", va="bottom", fontsize=16,
                weight="bold", color=VINHO)
    ax.set_xticks(list(x), [l for _, l in metodos], fontsize=12, color=VINHO)
    ax.set_ylabel(f"Nódulos apagados (de {len(n)})", fontsize=12, color=VINHO)
    ax.set_ylim(0, max(a + b for a, b in zip(ap_b, ap_i)) * 1.25 + 1)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=VINHO)
    ax.legend(frameon=False, fontsize=11, labelcolor=VINHO)
    fig.savefig(OUT / "nodulos_apagados_por_metodo.png", bbox_inches="tight", facecolor=FUNDO)
    plt.close(fig)
    print("salvo", OUT / "nodulos_apagados_por_metodo.png")
