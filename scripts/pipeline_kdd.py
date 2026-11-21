"""
Pipeline KDD (Knowledge Discovery in Databases) do Grupo 2, de ponta a ponta.

Roda as cinco etapas do KDD (Fayyad et al., 1996) em ordem, chamando o mesmo
codigo de src/luna16/ que os notebooks e os scripts de avaliacao usam, e
salva a evidencia de cada etapa em data/luna16/kdd/:

  1. Selecao            -> etapa1_selecao.csv
     Le os cabecalhos de todos os exames baixados, aplica os criterios de
     inclusao e confere que o split 70/15/15 e disjunto por paciente.
  2. Pre-processamento  -> etapa2_3_preprocessamento_transformacao.json/.png
     Limpeza de HU (padding -> ar, recorte em [-1000, 400]) e filtro
     Gaussiano, num exame de teste, com numeros de antes/depois.
  3. Transformacao      -> (mesmo arquivo da etapa 2)
     Reamostragem isotropica para 1 mm e, para a U-Net, fatia 128x128
     normalizada para [-1, 1].
  4. Mineracao          -> etapa4_mineracao_reprodutibilidade.csv
     Os tres metodos (baseline, region growing, U-Net). Por padrao usa os
     resultados ja salvos dos 26 exames de teste e REEXECUTA os tres metodos
     em N exames (--reexecutar N, padrao 1) para provar que os numeros
     salvos se reproduzem. Use --reexecutar 26 para refazer tudo (~40 min).
  5. Interpretacao/Avaliacao -> etapa5_tabela_resultados.csv,
     etapa5_teste_hipoteses.csv, relatorio_kdd.md
     IC95% por bootstrap e teste formal das hipoteses (docs/hipotese.md).

Uso (a partir da raiz do repositorio):
  python scripts/pipeline_kdd.py
  python scripts/pipeline_kdd.py --reexecutar 0     # so etapas 1-3 e 5, rapido
  python scripts/pipeline_kdd.py --reexecutar 26    # refaz a mineracao inteira
"""
import argparse
import functools
import json
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
os.chdir(RAIZ)
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import SimpleITK as sitk
from skimage.transform import resize

from luna16.baseline import segment_baseline
from luna16.hipotese import testar_hipoteses
from luna16.io import load_ct
from luna16.pipeline import _to_sitk, run_pipeline_for_uid
from luna16.preprocessing import CLIP_MAX_HU, CLIP_MIN_HU, PADDING_HU, clean_hu, denoise, resample_isotropic
from luna16.region_growing import segment_region_growing
from luna16.selection import apply_selection_criteria, build_header_table
from luna16.splits import Split, assert_no_leakage
from luna16.unet import INPUT_SIZE, hu_to_input, load_trained_model, segment_with_unet
from run_final_results import carregar_resultados, montar_tabela

DATA_DIR = Path("data/luna16")
SAIDA = DATA_DIR / "kdd"
SPLIT = DATA_DIR / "split_full.csv"
CHECKPOINT = DATA_DIR / "unet_baseline.pt"
TOLERANCIA_DICE = 1e-4  # reexecucao x valor salvo


def titulo(n: int, nome: str) -> float:
    print(f"\n{'=' * 70}\nETAPA {n} -- {nome}\n{'=' * 70}", flush=True)
    return time.time()


def etapa1_selecao() -> dict:
    t0 = titulo(1, "SELECAO")
    tabela = apply_selection_criteria(build_header_table(DATA_DIR), DATA_DIR)
    tabela.to_csv(SAIDA / "etapa1_selecao.csv", index=False)

    split = pd.read_csv(SPLIT)
    grupos = {c: split.loc[split["conjunto"] == c, "uid"].tolist() for c in ("train", "val", "test")}
    assert_no_leakage(Split(grupos["train"], grupos["val"], grupos["test"]))
    incluidos = set(tabela.loc[tabela["incluido"], "uid"])
    fora = set(split["uid"]) - incluidos
    assert not fora, f"{len(fora)} exames do split nao passaram nos criterios de inclusao"

    resumo = {
        "exames_encontrados": len(tabela),
        "exames_incluidos": int(tabela["incluido"].sum()),
        "exclusoes_por_motivo": tabela["motivo_exclusao"].value_counts().to_dict(),
        "spacing_z_mm_min_max": [float(tabela["spacing_z"].min()), float(tabela["spacing_z"].max())],
        "split": {c: len(u) for c, u in grupos.items()},
        "split_disjunto_por_paciente": True,
    }
    print(json.dumps(resumo, indent=2, ensure_ascii=False))
    print(f"({time.time() - t0:.0f}s)")
    return resumo


def etapas2_3_preprocessamento_transformacao(uid: str) -> dict:
    t0 = titulo(2, "PRE-PROCESSAMENTO  (+ ETAPA 3 -- TRANSFORMACAO)")
    ct = load_ct(uid, DATA_DIR)
    bruto = ct.array
    limpo = clean_hu(bruto)
    suave = denoise(limpo, sigma=0.5)

    vol_sitk = _to_sitk(suave, ct.to_sitk_image(), "int16")
    reamostrado = sitk.GetArrayFromImage(resample_isotropic(vol_sitk, (1.0, 1.0, 1.0)))

    z = reamostrado.shape[0] // 2
    # mesma transformacao que segment_with_unet aplica em cada fatia
    entrada_unet = resize(hu_to_input(reamostrado[z]).astype(np.float32), (INPUT_SIZE, INPUT_SIZE),
                          order=1, anti_aliasing=True, preserve_range=True)

    resumo = {
        "uid_exemplo": uid,
        "pre_processamento": {
            "hu_bruto_min_max": [int(bruto.min()), int(bruto.max())],
            "voxels_de_padding_fora_do_fov_pct": round(100 * float((bruto <= PADDING_HU + 1).mean()), 2),
            "hu_limpo_min_max": [int(limpo.min()), int(limpo.max())],
            "ruido_removido_desvio_hu": round(float(np.std(limpo.astype(np.float32) - suave)), 2),
        },
        "transformacao": {
            "spacing_original_xyz_mm": [round(s, 3) for s in ct.spacing],
            "shape_original_zyx": list(bruto.shape),
            "shape_isotropico_1mm_zyx": list(reamostrado.shape),
            "entrada_unet_shape": list(entrada_unet.shape),
            "entrada_unet_min_max": [round(float(entrada_unet.min()), 3), round(float(entrada_unet.max()), 3)],
        },
    }
    with open(SAIDA / "etapa2_3_preprocessamento_transformacao.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    z_bruto = int(round(z * 1.0 / ct.spacing[2]))
    z_bruto = min(z_bruto, bruto.shape[0] - 1)
    fig, axes = plt.subplots(1, 4, figsize=(18, 5))
    paineis = [
        (bruto[z_bruto], "1. Bruto (HU original)", "gray", None),
        (limpo[z_bruto], "2. Pre-proc.: HU limpo [-1000, 400]", "gray", (CLIP_MIN_HU, CLIP_MAX_HU)),
        (reamostrado[z], "3. Transf.: isotropico 1 mm + filtro", "gray", (CLIP_MIN_HU, CLIP_MAX_HU)),
        (entrada_unet, "3. Transf.: entrada U-Net 128x128 [-1,1]", "gray", (-1, 1)),
    ]
    for ax, (img, nome, cmap, lim) in zip(axes, paineis):
        ax.imshow(img, cmap=cmap, vmin=None if lim is None else lim[0], vmax=None if lim is None else lim[1])
        ax.set_title(nome, fontsize=10)
        ax.axis("off")
    plt.suptitle(f"KDD etapas 2 e 3 -- exame ...{uid[-12:]} (fatia central)")
    plt.tight_layout()
    plt.savefig(SAIDA / "etapa2_3_preprocessamento_transformacao.png", dpi=110)
    plt.close(fig)

    print(json.dumps(resumo, indent=2, ensure_ascii=False))
    print(f"({time.time() - t0:.0f}s)")
    return resumo


def etapa4_mineracao(test_uids: list[str], n_reexecutar: int) -> tuple[dict, dict]:
    t0 = titulo(4, "MINERACAO DE DADOS (baseline, region growing, U-Net 2D)")
    dfs = carregar_resultados(SPLIT, "test", "")
    print(f"Resultados salvos: {len(dfs['baseline'])} exames de teste, mesmos uids nos 3 metodos")

    metodos = {"baseline": segment_baseline, "region_growing": segment_region_growing}
    if n_reexecutar > 0:
        if CHECKPOINT.exists():
            metodos["unet"] = functools.partial(segment_with_unet, model=load_trained_model(str(CHECKPOINT)))
        else:
            print(f"AVISO: {CHECKPOINT} nao encontrado; a U-Net nao sera reexecutada")

    linhas = []
    for uid in test_uids[:n_reexecutar]:
        for chave, fn in metodos.items():
            r = run_pipeline_for_uid(uid, DATA_DIR, segment_fn=fn)
            salvo = float(dfs[chave].set_index("uid").loc[uid, "dice"])
            linhas.append({
                "uid": uid, "metodo": chave, "dice_reexecutado": r.dice, "dice_salvo": salvo,
                "diferenca": abs(r.dice - salvo), "reproduz": abs(r.dice - salvo) < TOLERANCIA_DICE,
                "tempo_s": round(r.tempo_segundos, 1),
            })
            print(f"  {chave:15s} ...{uid[-10:]}  dice={r.dice:.6f}  salvo={salvo:.6f}  "
                  f"{'OK' if linhas[-1]['reproduz'] else 'DIVERGE'}  ({r.tempo_segundos:.0f}s)", flush=True)

    repro = pd.DataFrame(linhas)
    if len(repro):
        repro.to_csv(SAIDA / "etapa4_mineracao_reprodutibilidade.csv", index=False)
    resumo = {
        "exames_reexecutados": n_reexecutar,
        "execucoes": len(repro),
        "todas_reproduzem": bool(repro["reproduz"].all()) if len(repro) else None,
    }
    print(json.dumps(resumo, indent=2))
    print(f"({time.time() - t0:.0f}s)")
    return resumo, dfs


def etapa5_interpretacao(dfs: dict) -> dict:
    t0 = titulo(5, "INTERPRETACAO / AVALIACAO")
    tabela = montar_tabela(dfs)
    tabela.to_csv(SAIDA / "etapa5_tabela_resultados.csv")
    print(tabela[["Dice", "IoU", "Tempo/TC (s)"]].to_string(), "\n")

    hip = testar_hipoteses(dfs)
    hip.to_csv(SAIDA / "etapa5_teste_hipoteses.csv", index=False)
    for _, l in hip.iterrows():
        print(f"{l['hipotese']:22s} H1: {l['h1']}")
        print(f"{'':22s} efeito={l['efeito']:+.4f} IC95%=[{l['ic95_inferior']:+.4f}, {l['ic95_superior']:+.4f}]  "
              f"p(Holm)={l['p_valor_holm']:.2e}  -> {l['conclusao']}")
    print(f"({time.time() - t0:.0f}s)")
    return {"tabela": tabela, "hipoteses": hip}


def escrever_relatorio(r1: dict, r23: dict, r4: dict, r5: dict) -> None:
    hip = r5["hipoteses"]
    linhas_hip = "\n".join(
        f"| {l.hipotese} | {l.h1} | {l.efeito:.4f} [{l.ic95_inferior:.4f}; {l.ic95_superior:.4f}] "
        f"| {l.p_valor_holm:.2e} | {l.conclusao} |"
        for l in hip.itertuples()
    )
    tab = r5["tabela"]
    linhas_tab = "\n".join(
        f"| {m} | {row['Dice']} | {row['IoU']} | {row['Tempo/TC (s)']} |" for m, row in tab.iterrows()
    )
    pre, tr = r23["pre_processamento"], r23["transformacao"]
    md = f"""# Relatorio do pipeline KDD (gerado automaticamente)

Gerado por `scripts/pipeline_kdd.py` em {time.strftime('%Y-%m-%d %H:%M')}. Nao editar a mao:
rode o script de novo. A explicacao de cada etapa esta em `docs/kdd.md` e a das
hipoteses em `docs/hipotese.md`.

## 1. Selecao
- Exames encontrados: {r1['exames_encontrados']}; incluidos: {r1['exames_incluidos']}
- Espacamento entre fatias: {r1['spacing_z_mm_min_max'][0]:.2f} a {r1['spacing_z_mm_min_max'][1]:.2f} mm (criterio: <= 2,5 mm)
- Split por paciente: treino {r1['split']['train']}, validacao {r1['split']['val']}, teste {r1['split']['test']} (disjunto: sim)

## 2. Pre-processamento (exame ...{r23['uid_exemplo'][-12:]})
- HU bruto: {pre['hu_bruto_min_max']} -> limpo: {pre['hu_limpo_min_max']}
- Voxels de padding fora do campo de visao: {pre['voxels_de_padding_fora_do_fov_pct']}%
- Filtro Gaussiano (sigma 0,5): desvio do ruido removido = {pre['ruido_removido_desvio_hu']} HU

## 3. Transformacao
- Espacamento original (x, y, z): {tr['spacing_original_xyz_mm']} mm -> 1 mm isotropico
- Volume (z, y, x): {tr['shape_original_zyx']} -> {tr['shape_isotropico_1mm_zyx']}
- Entrada da U-Net: {tr['entrada_unet_shape']}, valores em {tr['entrada_unet_min_max']}

Figura: `etapa2_3_preprocessamento_transformacao.png`

## 4. Mineracao de dados
- Tres metodos avaliados nos mesmos {r1['split']['test']} exames de teste.
- Reprodutibilidade: {r4['execucoes']} reexecucoes em {r4['exames_reexecutados']} exame(s);
  todas reproduzem o Dice salvo (tolerancia {TOLERANCIA_DICE}): {r4['todas_reproduzem']}

## 5. Interpretacao / avaliacao

| Metodo | Dice [IC95%] | IoU [IC95%] | Tempo/TC (s) |
|---|---|---|---|
{linhas_tab}

### Teste das hipoteses (Wilcoxon unilateral pareado, Holm, alfa = 0,05)

| Hipotese | H1 | Efeito [IC95%] | p (Holm) | Conclusao |
|---|---|---|---|---|
{linhas_hip}
"""
    (SAIDA / "relatorio_kdd.md").write_text(md, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reexecutar", type=int, default=1,
                        help="quantos exames de teste reexecutar na mineracao (0 = nenhum, 26 = todos)")
    args = parser.parse_args()
    SAIDA.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    test_uids = sorted(pd.read_csv(SPLIT).query("conjunto == 'test'")["uid"])
    r1 = etapa1_selecao()
    r23 = etapas2_3_preprocessamento_transformacao(test_uids[0])
    r4, dfs = etapa4_mineracao(test_uids, args.reexecutar)
    r5 = etapa5_interpretacao(dfs)
    escrever_relatorio(r1, r23, r4, r5)
    print(f"\nKDD CONCLUIDO em {time.time() - t0:.0f}s. Saidas em {SAIDA}/ (ver relatorio_kdd.md)")


if __name__ == "__main__":
    main()
