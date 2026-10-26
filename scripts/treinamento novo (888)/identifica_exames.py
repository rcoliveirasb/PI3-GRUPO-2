#!/usr/bin/env python3
"""
Migracao do treino da U-Net (LUNA16) -- identificacao, validacao e divisao.

Subcomandos (todos so LEEM os dados e escrevem em --saida; nunca sobrescrevem
sem --force):

  identificar : TESTE de hipotese "os usados antes sao os primeiros N por paciente".
                (No projeto real essa hipotese foi refutada; serve so de diagnostico.)
  anteriores  : monta a lista de exames usados no treino de 177 a partir de uma fonte
                real (um CSV de split antigo e/ou pastas subset0/subset1) e so grava se
                os 26 exames de teste conhecidos estiverem todos nela.
  validar     : inventario por exame (arquivos, geometria, extensao fisica em Z,
                voxels e rotulos da mascara). Marca 'ok', 'revisar' ou 'invalido';
                nao reamostra nem exclui nada.
  split       : divide por exame, apenas entre exames 'ok' que NAO estao em
                anteriores_candidatos.csv. Os anteriores ficam marcados.

Pasta de saida usada no projeto: D:\\DATASET_LUNA16\\divisao_exames
"""
import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk

# Ultimos 10 digitos do SeriesInstanceUID dos 26 exames do teste anterior
# (recuperados das saidas gravadas no notebook do treino de 177).
TESTE_26 = [
    "0275453085", "8746541371", "6779705509", "0281098509", "2130599234",
    "5595118048", "6274044574", "7290922949", "8609808059", "6263147663",
    "1509831276", "0209787179", "9549658100", "4069960014", "4024478441",
    "1695800950", "1835871780", "9031534291", "1404659845", "9172047718",
    "5216493273", "8781143514", "8828421281", "0013275227", "4419915089",
    "2378865145",
]

TOL_ESP, TOL_ORI, TOL_DIR = 1e-3, 1e-3, 1e-5
TOL_Z_MM = 1.0


# ------------------------------------------------------------------ utilidades
def checar_saida(caminho, force):
    if Path(caminho).exists() and not force:
        sys.exit(f"ERRO: {caminho} ja existe. Use --force ou outra --saida.")


def cabecalho(caminho):
    r = sitk.ImageFileReader()
    r.SetFileName(str(caminho))
    r.ReadImageInformation()
    return {"size": tuple(r.GetSize()), "spacing": tuple(r.GetSpacing()),
            "origin": tuple(r.GetOrigin()), "direction": tuple(r.GetDirection())}


def z_do_corte(h, k):
    """Coordenada Z (mm) do centro do corte k, usando origem, espacamento e direcao."""
    D = np.array(h["direction"]).reshape(3, 3)
    p = np.array(h["origin"]) + D @ (np.array(h["spacing"]) * np.array([0, 0, k]))
    return float(p[2])


def proximo(a, b, tol):
    return len(a) == len(b) and bool(np.allclose(a, b, atol=tol, rtol=0))


def achar_coluna(df, *chaves):
    for c in df.columns:
        if all(k in c.lower() for k in chaves):
            return c
    return None


def indexar_mhd(pasta):
    idx, dup = {}, 0
    for p in Path(pasta).rglob("*.mhd"):
        if p.stem in idx:
            dup += 1
        idx[p.stem] = p
    if dup:
        print(f"  AVISO: {dup} nome(s) repetido(s) em {pasta}")
    return idx


# ------------------------------------------------------------------ identificar
def cmd_identificar(a):
    saida = Path(a.saida)
    f_ver = saida / "verificacao_26.csv"
    f_ant = saida / "anteriores_candidatos.csv"
    checar_saida(f_ver, a.force)
    checar_saida(f_ant, a.force)

    meta = pd.read_csv(a.metadata)
    c_uid = achar_coluna(meta, "series", "uid")
    c_sub = achar_coluna(meta, "subject") or achar_coluna(meta, "patient")
    if not c_uid or not c_sub:
        sys.exit(f"ERRO: nao achei colunas de UID/paciente em {a.metadata}. "
                 f"Colunas: {list(meta.columns)}")
    meta = meta[[c_uid, c_sub]].drop_duplicates(c_uid).rename(
        columns={c_uid: "seriesuid", c_sub: "paciente"})

    uids = sorted(indexar_mhd(a.mascaras))
    df = pd.DataFrame({"seriesuid": uids}).merge(meta, on="seriesuid", how="left")
    faltam = int(df["paciente"].isna().sum())
    print(f"Mascaras: {len(df)} | sem paciente no metadata: {faltam}")
    if faltam:
        sys.exit("ERRO: ha mascaras sem correspondencia no metadata.csv; a ordenacao "
                 "ficaria incompleta. Corrija antes de continuar.")
    df = df.sort_values(["paciente", "seriesuid"]).reset_index(drop=True)
    df["posicao"] = np.arange(1, len(df) + 1)

    linhas = []
    for suf in TESTE_26:
        achados = df[df["seriesuid"].str.endswith(suf)]
        if len(achados) != 1:
            linhas.append({"sufixo": suf, "seriesuid": "", "paciente": "",
                           "posicao": np.nan, "obs": f"{len(achados)} correspondencias"})
        else:
            r = achados.iloc[0]
            linhas.append({"sufixo": suf, "seriesuid": r.seriesuid, "paciente": r.paciente,
                           "posicao": int(r.posicao), "obs": ""})
    ver = pd.DataFrame(linhas)
    saida.mkdir(parents=True, exist_ok=True)
    ver.to_csv(f_ver, index=False)

    nao_achados = int(ver["posicao"].isna().sum())
    fora = ver[ver["posicao"] > a.n_anterior]
    print(f"\nOs 26 do teste anterior: {26 - nao_achados} localizados, "
          f"posicao maxima = {ver['posicao'].max()}")
    print(ver.sort_values("posicao").to_string(index=False))
    if nao_achados or len(fora):
        print(f"\n*** HIPOTESE NAO CONFIRMADA: {nao_achados} nao localizado(s), "
              f"{len(fora)} fora das primeiras {a.n_anterior} posicoes. ***")
        print("A lista de anteriores NAO foi gerada. Recupere o split_full.csv do "
              "treino de 177 (GitHub, branch sprints-3-8, ou copia local).")
        sys.exit(2)

    ant = df[df["posicao"] <= a.n_anterior].copy()
    ant["teste_26"] = ant["seriesuid"].isin(set(ver["seriesuid"]))
    ant.to_csv(f_ant, index=False)
    print(f"\nTodos os 26 estao entre as primeiras {a.n_anterior} posicoes (CONSISTENTE).")
    print(f"Candidatos a 'usados antes': {len(ant)}  -> {f_ant}")
    print("ATENCAO: consistente nao e prova. O notebook registra 178 encontrados e 177 "
          "usados; o exame excluido nao pode ser identificado sem o split_full.csv. "
          "Por seguranca ele fica fora do desenvolvimento.")



# ------------------------------------------------------------------- anteriores
UID_PREFIXO = "1.3.6.1.4.1.14519.5.2.1.6279.6001."


def uids_de_csv(caminho):
    df = pd.read_csv(caminho)
    for c in df.columns:
        v = df[c].dropna().astype(str).str.strip()
        if len(v) and v.str.startswith(UID_PREFIXO).mean() > 0.9:
            return set(v), c, len(df)
    sys.exit(f"ERRO: nenhuma coluna de SeriesInstanceUID completo em {caminho}. "
             f"Colunas: {list(df.columns)}")


def cmd_anteriores(a):
    saida = Path(a.saida)
    f_ant = saida / "anteriores_candidatos.csv"
    checar_saida(f_ant, a.force)
    if not a.csv and not a.pastas:
        sys.exit("ERRO: informe --csv e/ou --pastas.")

    uids888 = set(indexar_mhd(a.mascaras))
    fontes = {}
    for c in a.csv or []:
        u, col, n = uids_de_csv(c)
        print(f"CSV {c}: coluna '{col}', {len(u)} UIDs distintos em {n} linhas")
        fontes[f"csv:{Path(c).name}"] = u
    if a.pastas:
        u = set()
        for pasta in a.pastas:
            uu = set(indexar_mhd(pasta))
            print(f"Pasta {pasta}: {len(uu)} arquivos .mhd")
            u |= uu
        fontes["pastas"] = u

    uniao = set().union(*fontes.values())
    fora = uniao - uids888
    usados = uniao & uids888
    print(f"\nUniao das fontes: {len(uniao)} | dentro dos 888: {len(usados)} | "
          f"fora dos 888: {len(fora)}")
    if fora:
        print("  AVISO: UIDs das fontes sem mascara nos 888 (nao entram no calculo):")
        for u in sorted(fora)[:5]:
            print("   ", u)
    if len(fontes) > 1:
        comuns = set.intersection(*fontes.values())
        print(f"  Presentes em TODAS as fontes: {len(comuns)}")

    # prova: os 26 do teste anterior precisam estar na lista
    faltam, ids26 = [], set()
    for suf in TESTE_26:
        ach = [u for u in uids888 if u.endswith(suf)]
        if len(ach) != 1:
            faltam.append(f"{suf} ({len(ach)} correspondencias)")
            continue
        ids26.add(ach[0])
        if ach[0] not in usados:
            faltam.append(f"{suf} (nao esta na lista)")
    if faltam:
        print(f"\n*** FONTE NAO CONFIRMADA: {len(faltam)} dos 26 do teste anterior "
              f"fora da lista: ***")
        for x in faltam:
            print("   ", x)
        print("Nada foi gravado. Use outra fonte.")
        sys.exit(2)

    df = pd.DataFrame({"seriesuid": sorted(usados)})
    df["teste_26"] = df["seriesuid"].isin(ids26)
    if a.metadata:
        meta = pd.read_csv(a.metadata)
        cu, cs = achar_coluna(meta, "series", "uid"), (achar_coluna(meta, "subject") or achar_coluna(meta, "patient"))
        if cu and cs:
            m = meta[[cu, cs]].drop_duplicates(cu).rename(columns={cu: "seriesuid", cs: "paciente"})
            df = df.merge(m, on="seriesuid", how="left")
    saida.mkdir(parents=True, exist_ok=True)
    df.to_csv(f_ant, index=False)
    print(f"\nOs 26 do teste anterior estao TODOS na lista (fonte CONFIRMADA).")
    print(f"Exames marcados como 'usados antes': {len(df)}  -> {f_ant}")
    print("Esperado pelo notebook: 177 usados (178 encontrados nos subsets 0 e 1). "
          + ("Contagem compativel." if len(df) in (177, 178) else
             "ATENCAO: contagem diferente; confira se a fonte esta completa."))


# ---------------------------------------------------------------------- validar
def cmd_validar(a):
    saida = Path(a.saida)
    f_inv = saida / "inventario_888.csv"
    checar_saida(f_inv, a.force)
    cts = indexar_mhd(a.ct)
    mks = indexar_mhd(a.mascaras)
    print(f"CTs: {len(cts)} | mascaras: {len(mks)} | com par: {len(set(cts) & set(mks))}")
    if not mks:
        sys.exit("ERRO: nenhuma mascara encontrada em --mascaras.")
    if len(set(cts) & set(mks)) < 0.5 * len(mks):
        print("AVISO: poucos nomes coincidem. Exemplos de nomes de CT:",
              list(cts)[:3], "| de mascara:", list(mks)[:3])
        print("       Se os CTs tem outro padrao de nome, informe-me para adaptar.")

    linhas = []
    for i, uid in enumerate(sorted(mks), 1):
        mk_p, ct_p = mks[uid], cts.get(uid)
        lin = {"seriesuid": uid, "ct_path": str(ct_p or ""), "mask_path": str(mk_p),
               "status": "", "motivo": ""}
        inval = []
        if ct_p is None:
            inval.append("sem_ct")
        else:
            if not ct_p.with_suffix(".raw").exists():
                inval.append("raw_ausente")
        if not (mk_p.with_suffix(".zraw").exists() or mk_p.with_suffix(".raw").exists()):
            inval.append("dados_mascara_ausentes")
        ch = mh = None
        if not inval:
            try:
                ch, mh = cabecalho(ct_p), cabecalho(mk_p)
            except Exception as e:
                inval.append(f"erro_leitura:{type(e).__name__}")
        if ch and mh:
            for pref, h in (("ct", ch), ("mk", mh)):
                lin[f"{pref}_size"] = str(h["size"])
                lin[f"{pref}_spacing"] = str(tuple(round(x, 5) for x in h["spacing"]))
                lin[f"{pref}_origin"] = str(tuple(round(x, 3) for x in h["origin"]))
                lin[f"{pref}_z_ini_mm"] = round(z_do_corte(h, 0), 3)
                lin[f"{pref}_z_fim_mm"] = round(z_do_corte(h, h["size"][2] - 1), 3)
            lin["delta_z_ini_mm"] = round(lin["mk_z_ini_mm"] - lin["ct_z_ini_mm"], 3)
            lin["delta_z_fim_mm"] = round(lin["mk_z_fim_mm"] - lin["ct_z_fim_mm"], 3)
            lin["delta_espac_z_mm"] = round(mh["spacing"][2] - ch["spacing"][2], 5)
            motivos = []
            if ch["size"] != mh["size"]:
                motivos.append("dimensoes")
            if not proximo(ch["spacing"], mh["spacing"], TOL_ESP):
                motivos.append("espacamento")
            if not proximo(ch["origin"], mh["origin"], TOL_ORI):
                motivos.append("origem")
            if not proximo(ch["direction"], mh["direction"], TOL_DIR):
                motivos.append("direcao")
            if not a.sem_conteudo:
                try:
                    arr = sitk.GetArrayFromImage(sitk.ReadImage(str(mk_p)))
                    por_corte = (arr > 0).reshape(arr.shape[0], -1).any(axis=1)
                    lin["mask_voxels"] = int((arr > 0).sum())
                    lin["mask_rotulos"] = ",".join(str(int(x)) for x in np.unique(arr)[:10])
                    if lin["mask_voxels"] == 0:
                        inval.append("mascara_vazia")
                    else:
                        k0, k1 = int(np.argmax(por_corte)), int(len(por_corte) - 1 - np.argmax(por_corte[::-1]))
                        lin["mask_corte_ini"], lin["mask_corte_fim"] = k0, k1
                        lin["mask_cortes_com_mascara"] = int(por_corte.sum())
                        lin["mask_vazios_inicio"] = k0
                        lin["mask_vazios_fim"] = int(arr.shape[0] - 1 - k1)
                        lin["mask_z_ini_mm"] = round(z_do_corte(mh, k0), 3)
                        lin["mask_z_fim_mm"] = round(z_do_corte(mh, k1), 3)
                except Exception as e:
                    inval.append(f"erro_leitura_mascara:{type(e).__name__}")
            if inval:
                lin["status"], lin["motivo"] = "invalido", "|".join(inval)
            elif motivos:
                lin["status"], lin["motivo"] = "revisar", "diverge:" + "+".join(motivos)
            else:
                lin["status"] = "ok"
        else:
            lin["status"], lin["motivo"] = "invalido", "|".join(inval)
        linhas.append(lin)
        if i % 50 == 0 or i == len(mks):
            print(f"  [{i}/{len(mks)}]")

    df = pd.DataFrame(linhas)
    saida.mkdir(parents=True, exist_ok=True)
    df.to_csv(f_inv, index=False)
    print("\n=== Resumo ===")
    print(df["status"].value_counts().to_string())
    nao_ok = df[df["status"] != "ok"]
    if len(nao_ok):
        print("\nCasos para inspecao individual (nada foi alterado ou excluido):")
        print(nao_ok[["seriesuid", "status", "motivo"]].head(20).to_string(index=False))
    print(f"\nInventario: {f_inv}")


# ------------------------------------------------------------------------ split
def cmd_split(a):
    saida = Path(a.saida)
    inv = pd.read_csv(saida / "inventario_888.csv")
    ant = pd.read_csv(saida / "anteriores_candidatos.csv")
    f_split, f_meta = saida / "split_novo.csv", saida / "split_novo_meta.json"
    checar_saida(f_split, a.force)

    if inv["seriesuid"].duplicated().any():
        sys.exit("ERRO: seriesuid duplicado no inventario.")
    set_ant = set(ant["seriesuid"])
    set_26 = set(ant.loc[ant["teste_26"], "seriesuid"])
    ok = inv[inv["status"] == "ok"]
    dev = sorted(set(ok["seriesuid"]) - set_ant)
    ant_ok = sorted(set(ok["seriesuid"]) & set_ant)
    print(f"Inventario: {len(inv)} | ok: {len(ok)} | anteriores ok: {len(ant_ok)} "
          f"de {len(set_ant)} | desenvolvimento: {len(dev)}")
    perdidos_26 = set_26 - set(ok["seriesuid"])
    if perdidos_26:
        print(f"  AVISO: {len(perdidos_26)} dos 26 de teste NAO estao 'ok' no inventario: "
              f"{sorted(perdidos_26)}")

    rng = random.Random(a.seed)
    emb = dev[:]
    rng.shuffle(emb)
    n = len(emb)
    n_val = round(a.val * n)
    if a.resto == "teste_interno":
        n_tr = round(a.treino * n)
        treino, val, interno = emb[:n_tr], emb[n_tr:n_tr + n_val], emb[n_tr + n_val:]
    else:
        treino, val, interno = emb[n_val:], emb[:n_val], []

    rot = {**{u: "treino" for u in treino}, **{u: "validacao" for u in val},
           **{u: "teste_interno" for u in interno}, **{u: "anterior" for u in ant_ok}}
    conj = [set(treino), set(val), set(interno), set(ant_ok)]
    for i in range(4):
        for j in range(i + 1, 4):
            assert not (conj[i] & conj[j]), "VAZAMENTO entre conjuntos!"
    assert sum(len(c) for c in conj) == len(dev) + len(ant_ok)

    out = ok[ok["seriesuid"].isin(rot)].copy()
    out["split"] = out["seriesuid"].map(rot)
    out["anterior_177"] = out["seriesuid"].isin(set_ant)
    out["teste_26"] = out["seriesuid"].isin(set_26)
    out[["seriesuid", "split", "anterior_177", "teste_26", "ct_path", "mask_path"]] \
        .sort_values(["split", "seriesuid"]).to_csv(f_split, index=False)

    meta = {"criado_em": datetime.now().isoformat(timespec="seconds"), "seed": a.seed,
            "seed_e_padrao_do_script": a.seed == 42, "resto": a.resto,
            "proporcoes": {"treino": a.treino, "validacao": a.val},
            "contagem": {"treino": len(treino), "validacao": len(val),
                         "teste_interno": len(interno), "anterior": len(ant_ok),
                         "teste_26_ok": len(set_26 - perdidos_26)},
            "unidade": "seriesuid (um exame por linha)"}
    f_meta.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print("\nContagem por conjunto:")
    print(out["split"].value_counts().to_string())
    print(f"\nSalvo: {f_split}\n       {f_meta}")
    if a.seed == 42:
        print("NOTA: seed=42 e so o padrao; a semente do split antigo nao foi confirmada.")


# ------------------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)

    i = s.add_parser("identificar")
    i.add_argument("--metadata", required=True)
    i.add_argument("--mascaras", required=True)
    i.add_argument("--saida", required=True)
    i.add_argument("--n-anterior", type=int, default=178)
    i.add_argument("--force", action="store_true")
    i.set_defaults(func=cmd_identificar)

    n = s.add_parser("anteriores")
    n.add_argument("--mascaras", required=True)
    n.add_argument("--saida", required=True)
    n.add_argument("--csv", action="append", help="CSV de split antigo (pode repetir)")
    n.add_argument("--pastas", nargs="+", help="pastas subset0 e subset1 com os .mhd")
    n.add_argument("--metadata", help="opcional: acrescenta a coluna paciente")
    n.add_argument("--force", action="store_true")
    n.set_defaults(func=cmd_anteriores)

    v = s.add_parser("validar")
    v.add_argument("--ct", required=True)
    v.add_argument("--mascaras", required=True)
    v.add_argument("--saida", required=True)
    v.add_argument("--sem-conteudo", action="store_true",
                   help="nao le os voxels das mascaras (mais rapido, menos checagens)")
    v.add_argument("--force", action="store_true")
    v.set_defaults(func=cmd_validar)

    d = s.add_parser("split")
    d.add_argument("--saida", required=True)
    d.add_argument("--seed", type=int, default=42)
    d.add_argument("--treino", type=float, default=0.70)
    d.add_argument("--val", type=float, default=0.15)
    d.add_argument("--resto", choices=["teste_interno", "treino"], default="teste_interno",
                   help="destino dos ~15%% restantes do desenvolvimento")
    d.add_argument("--force", action="store_true")
    d.set_defaults(func=cmd_split)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()