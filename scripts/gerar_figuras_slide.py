"""Gera as duas figuras de evidencia para o slide da apresentacao.

As figuras do notebook (3 fatias x 5 paineis, 100 dpi) sao densas demais para
projecao. Estas sao redesenhadas para serem lidas a distancia: poucos paineis,
fonte grande, recorte na caixa do pulmao e uma mensagem por figura.

  figura 1 (evidencia visual): 1 fatia x 4 paineis -- TC, baseline, region
    growing, U-Net -- destacando em laranja o parenquima que cada metodo
    DEIXOU DE MARCAR. Nesse exame o erro e quase todo falso negativo
    (354 mL contra 24 mL de falso positivo no baseline), entao destacar so o
    que foi perdido e um resumo fiel; os numeros de falso positivo vao no
    rodape para nao esconder nada.

  figura 2 (o padrao quantitativo): ganho medio da U-Net por quartil de
    dificuldade, nos 26 exames de teste.

Cores: paleta de referencia do skill dataviz. Azul #2a78d6 e laranja #eb6834
passam os gates (contraste 4,30:1 e 3,12:1 contra a superficie; deltaE
azul-laranja 33,6 normal / 24,5 protanopia, contra pisos de 15 e 8).

A cor de realce da figura 1 nao atinge 3:1 contra tom de cinza medio -- isso e
geometricamente inevitavel, porque os cinzas da TC cobrem todo o eixo de
luminancia e nenhuma cor unica contrasta com todos. A regra de alivio do skill
e atendida com rotulo visivel: cada painel traz o metodo, o Dice e o volume
perdido em mL, e a regiao destacada recebe contorno proprio.

Uso: python scripts/gerar_figuras_slide.py   (a partir da raiz do repositorio)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import SimpleITK as sitk

from luna16.io import load_ct, load_reference_mask
from luna16.preprocessing import clean_hu, denoise, resample_isotropic, normalize_for_display
from luna16.baseline import segment_baseline
from luna16.region_growing import segment_region_growing
from luna16.unet import load_trained_model, segment_with_unet
from luna16.metrics import dice_coefficient

DATA_DIR = Path("data/luna16")
OUT_DIR = Path("docs/piores_casos")
TARGET = (1.0, 1.0, 1.0)
ML = 0.001

UID = "1.3.6.1.4.1.14519.5.2.1.6279.6001.109002525524522225658609808059"

AZUL = "#2a78d6"
LARANJA = "#eb6834"
LARANJA_ESC = "#8f3415"   # contorno da regiao destacada
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
SUPERFICIE = "#fcfcfb"


def _to_sitk(a, ref, dtype):
    img = sitk.GetImageFromArray(a.astype(dtype))
    img.CopyInformation(ref)
    return img


def figura_1():
    print("figura 1: preparando volume...", flush=True)
    ct = load_ct(UID, DATA_DIR)
    s = ct.to_sitk_image()
    ref_bin = load_reference_mask(UID, DATA_DIR)

    vol = sitk.GetArrayFromImage(
        resample_isotropic(_to_sitk(denoise(clean_hu(ct.array), 0.5), s, "int16"), TARGET, False))
    ref = sitk.GetArrayFromImage(
        resample_isotropic(_to_sitk(ref_bin, s, "uint8"), TARGET, True)).astype(bool)

    modelo = load_trained_model(str(DATA_DIR / "unet_baseline.pt"))
    preds = {
        "Baseline": segment_baseline(vol),
        "Region growing": segment_region_growing(vol),
        "U-Net 2D": segment_with_unet(vol, modelo),
    }

    z_lung = np.where(ref.any(axis=(1, 2)))[0]
    z = int(np.percentile(z_lung, 50))

    # recorte na caixa do pulmao (com folga) -- sem isso metade do slide e ar
    ys, xs = np.where(ref[z])
    m = 28
    y0, y1 = max(0, ys.min() - m), min(ref.shape[1], ys.max() + m)
    x0, x1 = max(0, xs.min() - m), min(ref.shape[2], xs.max() + m)

    ct_s = normalize_for_display(vol[z])[y0:y1, x0:x1]
    r_s = ref[z][y0:y1, x0:x1]

    fig, axes = plt.subplots(1, 4, figsize=(21, 6.6), facecolor=SUPERFICIE)

    axes[0].imshow(ct_s, cmap="gray", vmin=0, vmax=1)
    axes[0].set_title("TC original", fontsize=21, fontweight="bold", color=TINTA, pad=14)
    axes[0].set_xlabel("as porções posteriores dos dois\npulmões aparecem acinzentadas",
                       fontsize=14.5, color=TINTA_2, labelpad=10)

    for ax, (nome, pred) in zip(axes[1:], preds.items()):
        p_s = pred[z][y0:y1, x0:x1]
        perdido = r_s & ~p_s

        base = np.dstack([ct_s * 0.82] * 3)
        base[perdido] = np.array([235, 104, 52]) / 255
        ax.imshow(base)
        # contorno: garante a fronteira em qualquer tom de cinza por baixo
        ax.contour(perdido.astype(float), levels=[0.5],
                   colors=[LARANJA_ESC], linewidths=1.6)

        d = dice_coefficient(pred, ref)
        ml = float((ref & ~pred).sum()) * ML
        ax.set_title(f"{nome}\nDice {d:.3f}".replace(".", ","),
                     fontsize=21, fontweight="bold", color=TINTA, pad=14)
        ax.set_xlabel(f"deixou de marcar {ml:,.0f} mL".replace(",", "."),
                      fontsize=16, color=TINTA_2, labelpad=10)

    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)

    fig.suptitle("Onde os métodos clássicos falham: parênquima denso demais para o limiar de −600 HU",
                 fontsize=25, fontweight="bold", color=TINTA, y=1.005)
    fig.text(0.5, -0.035,
             "Em laranja: pulmão que a referência marca e o método não — o erro que domina este exame. "
             "Falso positivo (não mostrado) é pequeno nos três: 24, 20 e 19 mL.\n"
             "Paciente …658609808059, fatia do meio do pulmão. Conjunto de teste, não visto no treino da U-Net.",
             ha="center", fontsize=14, color=TINTA_2)

    fig.tight_layout()
    cam = OUT_DIR / "slide_1_evidencia_visual.png"
    fig.savefig(cam, dpi=150, bbox_inches="tight", facecolor=SUPERFICIE)
    plt.close(fig)
    print(f"  -> {cam}", flush=True)


def figura_2():
    b = pd.read_csv(DATA_DIR / "sprint4_baseline_test.csv")[["uid", "dice"]].rename(columns={"dice": "base"})
    u = pd.read_csv(DATA_DIR / "sprint_unet_test.csv")[["uid", "dice"]].rename(columns={"dice": "unet"})
    m = b.merge(u, on="uid")
    m["ganho"] = m["unet"] - m["base"]
    m["q"] = pd.qcut(m["base"], 4, labels=["Mais difíceis", "2º quartil", "3º quartil", "Mais fáceis"])
    g = m.groupby("q", observed=True)["ganho"].mean()
    n = m.groupby("q", observed=True)["ganho"].size()

    fig, ax = plt.subplots(figsize=(12.5, 7.8), facecolor=SUPERFICIE)
    ax.set_facecolor(SUPERFICIE)
    # titulo e subtitulo posicionados na figura (nao no eixo): com set_title +
    # ax.text eles colidiam
    fig.subplots_adjust(top=0.82, left=0.11, right=0.98, bottom=0.17)

    cores = [LARANJA] + [AZUL] * 3  # laranja destaca a mensagem; identidade vem do eixo x
    barras = ax.bar(range(len(g)), g.values, color=cores, width=0.62, zorder=3)
    for b_, v in zip(barras, g.values):
        b_.set_linewidth(0)
        ax.text(b_.get_x() + b_.get_width() / 2, v + 0.0016, f"+{v:.4f}".replace(".", ","),
                ha="center", va="bottom", fontsize=19, fontweight="bold", color=TINTA)

    ax.set_xticks(range(len(g)))
    ax.set_xticklabels([f"{i}\n({k} exames)" for i, k in zip(g.index, n.values)],
                       fontsize=16, color=TINTA)
    ax.set_ylabel("Ganho médio de Dice da U-Net", fontsize=17, color=TINTA_2, labelpad=12)
    fig.text(0.012, 0.945, "O ganho da U-Net se concentra nos casos difíceis",
             fontsize=25, fontweight="bold", color=TINTA, va="top")
    fig.text(0.012, 0.873, "26 exames de teste, agrupados por quartil de Dice do baseline",
             fontsize=15.5, color=TINTA_2, va="top")

    ax.set_ylim(0, max(g.values) * 1.22)
    # separador decimal em virgula: o slide e em portugues
    ax.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.2f}".replace(".", ",")))
    ax.grid(axis="y", alpha=0.22, zorder=0, color=TINTA_2, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", labelsize=14, colors=TINTA_2, length=0)
    ax.tick_params(axis="x", length=0)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#d6d5d1")

    # Evitamos a razao entre o primeiro e o ultimo quartil: com denominador
    # quase zero (+0,0011) ela daria "48x", um numero instavel que convida a
    # objecao obvia. A queda monotonica e a correlacao dizem o mesmo com
    # robustez.
    corr = m["base"].corr(m["ganho"])
    # formata so o numero (virgula decimal, sinal de menos tipografico) -- um
    # .replace() na frase inteira trocaria tambem o ponto final
    corr_txt = f"{corr:.2f}".replace(".", ",").replace("-", "−")
    alto = f"{g.iloc[0]:+.4f}".replace(".", ",")
    baixo = f"{g.iloc[-1]:+.4f}".replace(".", ",")
    fig.text(0.012, 0.045,
             f"O ganho cai de forma monótona, de {alto} no quartil mais difícil para {baixo} no mais fácil. "
             f"Correlação entre Dice do baseline e ganho: {corr_txt}.",
             fontsize=15, color=TINTA_2)
    cam = OUT_DIR / "slide_2_ganho_por_dificuldade.png"
    fig.savefig(cam, dpi=150, bbox_inches="tight", facecolor=SUPERFICIE)
    plt.close(fig)
    print(f"  -> {cam}", flush=True)


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    figura_1()
    figura_2()
    print("CONCLUIDO", flush=True)
