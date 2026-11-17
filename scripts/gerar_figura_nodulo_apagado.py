"""Figura "o nodulo apagado" (feedback final do professor: falta uma figura que
conte a historia do nodulo apagado).

Em cima: o mesmo corte de um exame do Teste A com um nodulo de 15 mm colado na
parede, e a mascara de cada metodo. O baseline e o region growing deixam o
nodulo fora do pulmao (ele nunca chega ao detector); a U-Net mantem.
Embaixo: os 43 nodulos anotados nos 26 exames do Teste A, um ponto por nodulo,
na mesma ordem nas tres linhas: mantido ou apagado por cada metodo.

Mesmos criterios de scripts/analise_nodulos_apagados.py (esfera do diametro
anotado, mantido se >= 50% dentro da mascara), mesmo codigo corrigido em 26/10.

Uso (a partir da raiz): python scripts/gerar_figura_nodulo_apagado.py
Le:    data/luna16/nodulos_apagados_teste.csv, annotations.csv, o exame do caso
Salva: docs/seminario/nodulo_apagado.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

from analise_nodulos_apagados import _esfera, _prep
from luna16.baseline import segment_baseline
from luna16.nodules import world_to_resampled_voxel
from luna16.region_growing import segment_region_growing
from luna16.unet import load_trained_model, segment_with_unet

D = Path("data/luna16")
OUT = Path("docs/seminario")
OUT.mkdir(parents=True, exist_ok=True)
CASO = "021509831276"  # nodulo de 15,4 mm colado na borda
JANELA_MM = 110

# cores do deck do grupo (gerar_figuras_seminario.py) + estados mantido/apagado
VINHO, MALVA, FUNDO, CINZA = "#4a2533", "#7a5a63", "#f8f4f3", "#d9d2d0"
MASCARA = "#2a78d6"
NODULO = "#eda100"
MANTIDO, APAGADO = "#0ca30c", "#d03b3b"

METODOS = [
    ("baseline", "Método simples\n(limiar −600 HU)"),
    ("region_growing", "Crescimento de região"),
    ("unet", "Rede U-Net 2D"),
]


def br(x, n=0):
    return f"{x:.{n}f}".replace(".", ",")


def main():
    nod = pd.read_csv(D / "nodulos_apagados_teste.csv")
    ann = pd.read_csv(D / "annotations.csv")
    uid = nod.loc[nod["uid"].str.endswith(CASO), "uid"].iloc[0]
    n = ann[ann["seriesuid"] == uid].sort_values("diameter_mm").iloc[-1]

    print("Segmentando o exame do caso...", flush=True)
    vol, ref, origem = _prep(uid)
    modelo = load_trained_model(str(D / "unet_baseline.pt"))
    mascaras = {
        "baseline": segment_baseline(vol),
        "region_growing": segment_region_growing(vol),
        "unet": segment_with_unet(vol, modelo),
    }
    centro = world_to_resampled_voxel((n["coordX"], n["coordY"], n["coordZ"]), origem)
    raio = n["diameter_mm"] / 2
    sl, esf = _esfera(vol.shape, centro, raio)
    cobertura = {m: float(mk[sl][esf].mean()) for m, mk in mascaras.items()}
    print({m: round(c, 3) for m, c in cobertura.items()})

    z, y, x = centro
    h = JANELA_MM // 2
    y0, x0 = max(y - h, 0), max(x - h, 0)
    corte = (slice(y0, y0 + JANELA_MM), slice(x0, x0 + JANELA_MM))
    img = np.clip((vol[z][corte] + 1350) / 1500, 0, 1)  # janela de pulmao
    cy, cx = y - y0, x - x0

    fig = plt.figure(figsize=(16, 9), dpi=150, facecolor=FUNDO)
    fig.text(0.04, 0.945, "Um nódulo apagado na segmentação nunca chega ao detector",
             fontsize=24, weight="bold", color=VINHO)
    fig.text(0.04, 0.905,
             f"Mesmo corte de um exame do teste: nódulo de {br(n['diameter_mm'], 1)} mm colado na parede "
             "do pulmão, anotado por radiologistas",
             fontsize=13, color=MALVA)

    largura, gap, esq, base, alt = 0.205, 0.025, 0.04, 0.37, 0.47
    paineis = [("ct", "Tomografia")] + METODOS
    for i, (m, titulo) in enumerate(paineis):
        ax = fig.add_axes([esq + i * (largura + gap), base, largura, alt])
        ax.imshow(img, cmap="gray", vmin=0, vmax=1)
        if m != "ct":
            mk = mascaras[m][z][corte]
            cor = np.zeros((*mk.shape, 4))
            cor[mk] = matplotlib.colors.to_rgba(MASCARA, 0.38)
            ax.imshow(cor)
            ax.contour(mk, levels=[0.5], colors=[MASCARA], linewidths=1.6)
        ax.add_patch(Circle((cx, cy), raio + 1.5, fill=False, ec=NODULO, lw=2.4,
                            ls="--" if m == "ct" else "-"))
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color(CINZA)
        ax.set_title(titulo, fontsize=14, color=VINHO, weight="bold", pad=8, loc="left")
        if m == "ct":
            ax.text(0.03, -0.075, "Sem máscara", transform=ax.transAxes, fontsize=12.5, color=MALVA, va="top")
            continue
        c = cobertura[m]
        ok = c >= 0.5
        ax.text(0.03, -0.065, ("✓ MANTIDO" if ok else "✗ APAGADO"), transform=ax.transAxes,
                fontsize=15, weight="bold", color=MANTIDO if ok else APAGADO, va="top")
        ax.text(0.03, -0.135, f"a máscara cobre {br(100 * c)}% do nódulo", transform=ax.transAxes,
                fontsize=12, color=MALVA, va="top")

    fig.legend(handles=[
        Line2D([], [], color=MASCARA, lw=6, alpha=0.6, label="Pulmão segundo o método (máscara)"),
        Line2D([], [], color=NODULO, lw=2.4, label="Nódulo anotado"),
    ], loc="upper right", bbox_to_anchor=(0.965, 0.89), ncol=2, frameon=False, fontsize=12,
        labelcolor=VINHO)

    # embaixo: os 43 nodulos, mesma ordem nas 3 linhas (borda primeiro, maior primeiro)
    ordem = nod.assign(borda=nod["posicao"] == "colado_na_borda").sort_values(
        ["borda", "diametro_mm"], ascending=[False, False]).reset_index(drop=True)
    nb = int(ordem["borda"].sum())
    ax = fig.add_axes([0.04, 0.035, 0.92, 0.2])
    ax.set_facecolor(FUNDO)
    fig.text(0.04, 0.262, f"Os {len(ordem)} nódulos anotados nos 26 exames do teste, um ponto por nódulo "
             "(mesma ordem nas três linhas)", fontsize=13.5, weight="bold", color=VINHO)
    x0_pontos = 9.0
    for r, (m, nome) in enumerate(METODOS):
        yrow = 2 - r
        k = ordem[f"{m}_mantido"].astype(bool).to_numpy()
        xs = x0_pontos + np.arange(len(ordem))
        ax.scatter(xs[k], [yrow] * k.sum(), s=95, color=MANTIDO, edgecolor=FUNDO, lw=1.5, zorder=3)
        ax.scatter(xs[~k], [yrow] * (~k).sum(), s=70, marker="X", color=APAGADO, edgecolor=FUNDO,
                   lw=0.8, zorder=3)
        ax.text(0, yrow, nome.split("\n")[0], fontsize=12.5, color=VINHO, va="center")
        ax.text(x0_pontos + len(ordem) + 0.8, yrow, f"apaga {(~k).sum()}", fontsize=13,
                weight="bold", color=VINHO if (~k).sum() > 3 else MALVA, va="center")
    ax.axvline(x0_pontos + nb - 0.5, color=CINZA, lw=1.2, ls=":", zorder=1)
    ax.text(x0_pontos + (nb - 1) / 2, 3.0, f"{nb} colados na borda", ha="center", fontsize=11, color=MALVA)
    ax.text(x0_pontos + nb + (len(ordem) - nb - 1) / 2, 3.0, f"{len(ordem) - nb} no interior",
            ha="center", fontsize=11, color=MALVA)
    ax.legend(handles=[
        Line2D([], [], ls="", marker="o", ms=9, color=MANTIDO, label="mantido"),
        Line2D([], [], ls="", marker="X", ms=8, color=APAGADO, label="apagado"),
    ], loc="lower right", bbox_to_anchor=(1.0, 0.86), ncol=2, frameon=False, fontsize=11,
        labelcolor=VINHO)
    ax.set_xlim(-0.3, x0_pontos + len(ordem) + 4.5)
    ax.set_ylim(-0.6, 3.5)
    ax.axis("off")

    fig.text(0.96, 0.008, "Teste A (26 exames, 43 nódulos do LUNA16), código corrigido em 26/10. "
             "Apagado = menos de 50% da esfera do nódulo dentro da máscara. "
             "Fonte: scripts/analise_nodulos_apagados.py", ha="right", fontsize=9, color=MALVA)
    fig.savefig(OUT / "nodulo_apagado.png", facecolor=FUNDO)
    print(f"Salvo: {OUT / 'nodulo_apagado.png'}")


if __name__ == "__main__":
    main()
