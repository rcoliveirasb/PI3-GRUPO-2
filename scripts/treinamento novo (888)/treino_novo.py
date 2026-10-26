#!/usr/bin/env python3
"""
Novo treino da U-Net 2D (LUNA16) com os exames FORA dos 177 usados antes.

Reproduz a receita do Colab (commit 45cb163), lida do codigo:
  - pre-processamento: clean_hu -> gaussiano 3D (sigma 0.5) -> reamostragem
    isotropica 1 mm (CT linear, mascara vizinho-mais-proximo)
  - mascara = rotulos 3 e 4 (parenquima; traqueia/5 fica de fora)
  - fatias axiais 2D: ate 20 COM pulmao + ate 6 SEM pulmao por exame,
    redimensionadas para 128x128 (hu_to_input -> [-1, 1])
  - SmallUNet2D(base_ch=32), BCE + Dice, Adam lr=1e-3, batch 16, 25 epocas
  - sem augmentation; pesos FINAIS salvos (como o treino antigo)
  - avaliacao: volume inteiro 1 mm, fatia a fatia, limiar 0.5, Dice 3D

Diferencas deliberadas (todas registradas e inofensivas para a comparacao):
  1. Treina com TODOS os exames de treino do split novo (o codigo antigo limitava
     a 124 por N_TRAIN_PATIENTS).
  2. Caminhos lidos do split_novo.csv (CTs e mascaras ficam no HD).
  3. Fatias de cada exame sorteadas com semente propria (SEED + uid), para o
     cache poder ser retomado exatamente.
  4. Extras que NAO mudam o treino: perda/Dice de validacao por epoca, checkpoint
     "best" por Dice de validacao, estado salvo a cada epoca para retomar.

Subcomandos:  selecao | cache | treinar | avaliar | comparar
Tudo grava em --saida (padrao no HD). Nunca sobrescreve sem --force.
"""
import argparse
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# ----------------------------------------------------------- receita (Colab, GPU)
SEED = 42
POS_SLICES_PER_PATIENT = 20
NEG_SLICES_PER_PATIENT = 6
EPOCHS = 25
BASE_CHANNELS = 32
BATCH_SIZE = 16
LEARNING_RATE = 1e-3
MAX_SLICE_SPACING_MM = 2.5   # criterio de selecao do projeto (selection.py)

DEV_SPLITS = ("treino", "validacao", "teste_interno")

PADRAO_SAIDA = r"D:\DATASET_LUNA16\treino_novo"
PADRAO_SPLIT = r"D:\DATASET_LUNA16\divisao_exames\split_novo.csv"
PADRAO_ANT = r"D:\DATASET_LUNA16\divisao_exames\anteriores_candidatos.csv"
PADRAO_CKPT_ANTIGO = r"resultados_177_backup\unet_baseline.pt"


# ------------------------------------------------------------------- utilidades
def pronto_para_gravar(caminho, force):
    if Path(caminho).exists() and not force:
        sys.exit(f"ERRO: {caminho} ja existe. Use --force ou outra --saida.")


def configurar_saida(a):
    saida = Path(a.saida)
    if getattr(a, "teste_rapido", False):
        saida = saida / "_teste_rapido"
    saida.mkdir(parents=True, exist_ok=True)
    return saida


def ler_split(a):
    sp = pd.read_csv(a.split)
    obrig = {"seriesuid", "split", "ct_path", "mask_path", "teste_26"}
    if not obrig <= set(sp.columns):
        sys.exit(f"ERRO: {a.split} sem colunas {obrig - set(sp.columns)}")
    return sp.rename(columns={"seriesuid": "uid"})


def ler_plano(a, saida):
    """Split + resultado da selecao. So exames com incluido=True entram no treino."""
    sp = ler_split(a)
    sel_path = Path(a.saida) / ("_teste_rapido" if getattr(a, "teste_rapido", False) else "") / "selecao_novos.csv"
    if sel_path.exists():
        sel = pd.read_csv(sel_path)[["uid", "incluido"]]
        sp = sp.merge(sel, on="uid", how="left")
        sp["incluido"] = sp["incluido"].fillna(sp["split"].eq("anterior"))
    else:
        print(f"AVISO: {sel_path} nao existe (rode 'selecao' antes). Seguindo sem o filtro.")
        sp["incluido"] = True
    return sp


def checar_vazamento(plano, a):
    """Interrompe se algum exame de treino/validacao for dos 177 anteriores ou do teste."""
    ant = set(pd.read_csv(a.anteriores)["seriesuid"])
    tr = set(plano.loc[plano.split == "treino", "uid"])
    va = set(plano.loc[plano.split == "validacao", "uid"])
    ti = set(plano.loc[plano.split == "teste_interno", "uid"])
    problemas = []
    if tr & ant:
        problemas.append(f"{len(tr & ant)} exames de TREINO estao nos 177 anteriores")
    if va & ant:
        problemas.append(f"{len(va & ant)} exames de VALIDACAO estao nos 177 anteriores")
    if tr & va or tr & ti or va & ti:
        problemas.append("sobreposicao entre treino/validacao/teste_interno")
    if problemas:
        sys.exit("ERRO DE VAZAMENTO -- treino interrompido:\n  " + "\n  ".join(problemas))
    print(f"Checagem de vazamento OK (treino {len(tr)}, validacao {len(va)}, "
          f"teste_interno {len(ti)}, anteriores {len(ant)}; nenhuma sobreposicao).")


# ---------------------------------------------------------------------- selecao
def cmd_selecao(a):
    import SimpleITK as sitk
    saida = configurar_saida(a)
    f_out = saida / "selecao_novos.csv"
    pronto_para_gravar(f_out, a.force)
    sp = ler_split(a)
    dev = sp[sp.split.isin(DEV_SPLITS)]
    if a.teste_rapido:
        dev = pd.concat([dev[dev.split == "treino"].head(6), dev[dev.split == "validacao"].head(3)])
    rows = []
    for i, (uid, ctp, mkp) in enumerate(zip(dev.uid, dev.ct_path, dev.mask_path), 1):
        r = sitk.ImageFileReader()
        r.SetFileName(str(ctp))
        r.ReadImageInformation()
        s, sz = r.GetSpacing(), r.GetSize()
        motivo = None
        if not Path(mkp).exists():
            motivo = "sem mascara de referencia"
        elif s[2] > MAX_SLICE_SPACING_MM:
            motivo = f"espacamento entre fatias > {MAX_SLICE_SPACING_MM}mm"
        rows.append({"uid": uid, "n_slices": sz[2], "rows": sz[1], "cols": sz[0],
                     "spacing_x": s[0], "spacing_y": s[1], "spacing_z": s[2],
                     "has_mask": Path(mkp).exists(), "motivo_exclusao": motivo,
                     "incluido": motivo is None})
        if i % 100 == 0 or i == len(dev):
            print(f"  [{i}/{len(dev)}] cabecalhos lidos", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(f_out, index=False)
    j = df.merge(dev[["uid", "split"]], on="uid")
    print("\nSelecao (mesmos criterios do treino antigo: mascara existe e espacamento z <= 2.5 mm):")
    print(pd.crosstab(j["split"], j["incluido"]).to_string())
    exc = j[~j.incluido]
    if len(exc):
        print("\nExcluidos:")
        print(exc[["uid", "split", "spacing_z", "motivo_exclusao"]].to_string(index=False))
    print(f"\nSalvo: {f_out}")


# ------------------------------------------------------------------------ cache
def _to_sitk(array, reference, dtype):
    import SimpleITK as sitk
    img = sitk.GetImageFromArray(array.astype(dtype))
    img.CopyInformation(reference)
    return img


def volume_preprocessado(ct_path, mask_path):
    """Mesma cadeia de load_preprocessed_volume (train_unet_baseline.py), com caminhos."""
    import SimpleITK as sitk
    from luna16.preprocessing import clean_hu, denoise, resample_isotropic

    ct_img = sitk.ReadImage(str(ct_path))
    ct_arr = sitk.GetArrayFromImage(ct_img)
    ref_mask = np.isin(sitk.GetArrayFromImage(sitk.ReadImage(str(mask_path))), (3, 4))
    ct_sitk = _to_sitk(ct_arr, ct_img, str(ct_arr.dtype))

    denoised = denoise(clean_hu(ct_arr), sigma=0.5)
    vol_sitk = _to_sitk(denoised, ct_sitk, "int16")
    vol = sitk.GetArrayFromImage(resample_isotropic(vol_sitk, (1.0, 1.0, 1.0), is_mask=False))
    ref_sitk = _to_sitk(ref_mask, ct_sitk, "uint8")
    ref = sitk.GetArrayFromImage(resample_isotropic(ref_sitk, (1.0, 1.0, 1.0), is_mask=True)).astype(bool)
    return vol, ref


def fatias_do_exame(uid, ct_path, mask_path):
    """Mesma escolha de fatias do treino antigo (20 com pulmao + 6 sem), semente por exame."""
    from skimage.transform import resize
    from luna16.unet import hu_to_input, INPUT_SIZE

    rng = np.random.default_rng([SEED, zlib.crc32(uid.encode())])
    volume, ref = volume_preprocessado(ct_path, mask_path)
    tem = ref.any(axis=(1, 2))
    pos, neg = np.where(tem)[0], np.where(~tem)[0]
    n_pos, n_neg = min(POS_SLICES_PER_PATIENT, len(pos)), min(NEG_SLICES_PER_PATIENT, len(neg))
    escolhidas = list(rng.choice(pos, size=n_pos, replace=False)) if n_pos else []
    escolhidas += list(rng.choice(neg, size=n_neg, replace=False)) if n_neg else []
    xs, ys = [], []
    for z in escolhidas:
        img = hu_to_input(volume[z]).astype(np.float32)
        img_r = resize(img, (INPUT_SIZE, INPUT_SIZE), order=1, anti_aliasing=True, preserve_range=True)
        m_r = resize(ref[z].astype(np.float32), (INPUT_SIZE, INPUT_SIZE), order=0,
                     anti_aliasing=False, preserve_range=True)
        xs.append(img_r.astype(np.float32))
        ys.append((m_r > 0.5).astype(np.uint8))
    return np.stack(xs), np.stack(ys), n_pos, n_neg


def cmd_cache(a):
    saida = configurar_saida(a)
    plano = ler_plano(a, saida)
    checar_vazamento(plano, a)
    alvo = plano[plano.split.isin(["treino", "validacao"]) & plano.incluido.astype(bool)]
    if a.teste_rapido:
        alvo = pd.concat([alvo[alvo.split == "treino"].head(6), alvo[alvo.split == "validacao"].head(3)])
    log = saida / "cache_log.csv"
    linhas = pd.read_csv(log).to_dict("records") if log.exists() else []
    t0, feitos = time.time(), 0
    for i, r in enumerate(alvo.itertuples(), 1):
        pasta = saida / "cache" / r.split
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"{r.uid}.npz"
        if destino.exists():
            continue
        t1 = time.time()
        x, y, n_pos, n_neg = fatias_do_exame(r.uid, r.ct_path, r.mask_path)
        tmp = destino.with_suffix(".tmp.npz")
        np.savez(tmp, x=x, y=y)
        tmp.replace(destino)
        feitos += 1
        linhas.append({"uid": r.uid, "split": r.split, "n_pos": n_pos, "n_neg": n_neg,
                       "segundos": round(time.time() - t1, 1)})
        pd.DataFrame(linhas).to_csv(log, index=False)
        print(f"[cache {i}/{len(alvo)}] {r.uid[-10:]} ({r.split}) +{len(x)} fatias  "
              f"{time.time() - t0:.0f}s decorridos", flush=True)
    print(f"\nCache pronto em {saida / 'cache'} ({feitos} exames novos nesta execucao).")


# ----------------------------------------------------------------------- treinar
def carregar_cache(saida, plano, split):
    uids = plano.loc[(plano.split == split) & plano.incluido.astype(bool), "uid"].tolist()
    xs, ys, ok = [], [], []
    for u in uids:
        f = saida / "cache" / split / f"{u}.npz"
        if f.exists():
            d = np.load(f)
            xs.append(d["x"]); ys.append(d["y"]); ok.append(u)
    if not xs:
        sys.exit(f"ERRO: nenhum arquivo de cache para '{split}'. Rode 'cache' antes.")
    return np.concatenate(xs), np.concatenate(ys), ok, len(uids)


def dice_fatias(logits, y):
    import torch
    p = (torch.sigmoid(logits) > 0.5).float()
    inter = (p * y).sum(dim=(1, 2, 3))
    den = p.sum(dim=(1, 2, 3)) + y.sum(dim=(1, 2, 3))
    return torch.where(den == 0, torch.ones_like(den), 2 * inter / den)


def cmd_treinar(a):
    import torch
    from luna16.unet import SmallUNet2D, BCEDiceLoss, DEVICE

    saida = configurar_saida(a)
    plano = ler_plano(a, saida)
    checar_vazamento(plano, a)
    epocas = 2 if a.teste_rapido else (a.epocas or EPOCHS)
    f_final, f_best = saida / "unet_novo_final.pt", saida / "unet_novo_best.pt"
    f_estado, f_hist = saida / "estado_treino.pt", saida / "historico_treino.csv"
    pronto_para_gravar(f_final, a.force)

    print(f"Dispositivo: {DEVICE}" + (f" ({torch.cuda.get_device_name(0)})" if DEVICE.type == "cuda" else ""))
    if DEVICE.type != "cuda" and not a.permitir_cpu:
        sys.exit("ERRO: sem GPU. Confira o PyTorch com CUDA (ou use --permitir-cpu).")

    xtr, ytr, uids_tr, n_tr_plan = carregar_cache(saida, plano, "treino")
    xva, yva, uids_va, _ = carregar_cache(saida, plano, "validacao")
    if len(uids_tr) < n_tr_plan and not a.teste_rapido:
        sys.exit(f"ERRO: cache de treino incompleto ({len(uids_tr)} de {n_tr_plan}). Rode 'cache' ate o fim.")
    print(f"Treino: {len(uids_tr)} exames, {len(xtr)} fatias | Validacao: {len(uids_va)} exames, {len(xva)} fatias")

    Xtr, Ytr = torch.from_numpy(xtr).unsqueeze(1), torch.from_numpy(ytr).unsqueeze(1)
    Xva, Yva = torch.from_numpy(xva).unsqueeze(1), torch.from_numpy(yva).unsqueeze(1)

    torch.manual_seed(SEED)
    model = SmallUNet2D(base_ch=BASE_CHANNELS).to(DEVICE)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Parametros da rede: {n_params:,}")
    loss_fn = BCEDiceLoss()
    opt = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

    inicio, hist, melhor = 1, [], -1.0
    if f_estado.exists() and not a.force:
        est = torch.load(f_estado, map_location=DEVICE, weights_only=False)
        model.load_state_dict(est["model"]); opt.load_state_dict(est["opt"])
        inicio, hist, melhor = est["epoca"] + 1, est["hist"], est["melhor"]
        print(f"Retomando da epoca {inicio} (estado salvo anterior).")

    def avaliar_val():
        model.eval()
        L, D, n = 0.0, [], len(Xva)
        with torch.no_grad():
            for i in range(0, n, 64):
                x, y = Xva[i:i + 64].to(DEVICE), Yva[i:i + 64].float().to(DEVICE)
                lg = model(x)
                L += loss_fn(lg, y).item() * x.size(0)
                D.append(dice_fatias(lg, y).cpu())
        model.train()
        return L / n, float(torch.cat(D).mean())

    def salvar(caminho, epoca):
        torch.save({"model_state": model.state_dict(), "base_ch": BASE_CHANNELS,
                    "train_uids": uids_tr, "epoca": epoca}, caminho)

    t_ini = time.time()
    g = torch.Generator().manual_seed(SEED)
    model.train()
    for ep in range(inicio, epocas + 1):
        t_ep = time.time()
        perm = torch.randperm(len(Xtr), generator=torch.Generator().manual_seed(SEED + ep))
        soma = 0.0
        for i in range(0, len(perm), BATCH_SIZE):
            idx = perm[i:i + BATCH_SIZE]
            x, y = Xtr[idx].to(DEVICE), Ytr[idx].float().to(DEVICE)
            opt.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            soma += loss.item() * x.size(0)
        loss_tr = soma / len(Xtr)
        loss_va, dice_va = avaliar_val()
        hist.append({"epoca": ep, "loss_treino": loss_tr, "loss_val": loss_va,
                     "dice_fatia_val": dice_va, "segundos": round(time.time() - t_ep, 1)})
        print(f"[epoca {ep}/{epocas}] loss treino={loss_tr:.4f} | val loss={loss_va:.4f} "
              f"dice_fatia_val={dice_va:.4f} | {time.time() - t_ep:.0f}s", flush=True)
        if dice_va > melhor:
            melhor = dice_va
            salvar(f_best, ep)
        pd.DataFrame(hist).to_csv(f_hist, index=False)
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "epoca": ep,
                    "hist": hist, "melhor": melhor}, f_estado)
    salvar(f_final, epocas)
    print(f"\nTreino concluido em {(time.time() - t_ini) / 60:.1f} min.")
    print(f"Pesos finais: {f_final}\nMelhor por validacao: {f_best}\nHistorico: {f_hist}")


# ----------------------------------------------------------------------- avaliar
def conjunto_de_exames(plano, conjunto):
    inc = plano.incluido.astype(bool)
    if conjunto == "teste_interno":
        m = (plano.split == "teste_interno") & inc
    elif conjunto == "teste_26":
        m = plano.teste_26.astype(bool)
    elif conjunto == "teste_133":
        m = (((plano.split == "teste_interno") & inc) | plano.teste_26.astype(bool))
    elif conjunto == "validacao":
        m = (plano.split == "validacao") & inc
    elif conjunto == "anteriores_177":
        m = plano.split == "anterior"
    else:
        sys.exit(f"conjunto desconhecido: {conjunto}")
    return plano[m]


def resultado_exame(uid, ct_path, mask_path, model):
    import functools
    from luna16.unet import segment_with_unet
    from luna16.metrics import dice_coefficient, iou_score, sensitivity, precision
    t0 = time.time()
    vol, ref = volume_preprocessado(ct_path, mask_path)
    pred = segment_with_unet(vol, model)
    return {"uid": uid, "dice": dice_coefficient(pred, ref), "iou": iou_score(pred, ref),
            "sensitivity": sensitivity(pred, ref), "precision": precision(pred, ref),
            "tempo_segundos": time.time() - t0, "pred_voxels": int(pred.sum()),
            "ref_voxels": int(ref.sum())}


def cmd_avaliar(a):
    from luna16.unet import load_trained_model
    saida = configurar_saida(a)
    plano = ler_plano(a, saida)
    if a.modelo == "antigo" and a.conjunto in ("anteriores_177", "validacao") and not a.permitir_vistos:
        sys.exit("ERRO: o modelo antigo foi treinado/validado em 151 desses exames. "
                 "Use teste_26, teste_interno ou teste_133 (ou --permitir-vistos, com ressalva).")
    ckpt = {"antigo": a.checkpoint or PADRAO_CKPT_ANTIGO,
            "novo_final": a.checkpoint or str(saida / "unet_novo_final.pt"),
            "novo_best": a.checkpoint or str(saida / "unet_novo_best.pt")}[a.modelo]
    if not Path(ckpt).exists():
        sys.exit(f"ERRO: checkpoint nao encontrado: {ckpt}")
    alvo = conjunto_de_exames(plano, a.conjunto)
    if a.teste_rapido:
        alvo = alvo.head(2)
    pasta = saida / "resultados"
    pasta.mkdir(exist_ok=True)
    f_out = pasta / f"avaliacao_{a.modelo}_{a.conjunto}.csv"
    feitos = pd.read_csv(f_out).to_dict("records") if f_out.exists() and not a.force else []
    ja = {r["uid"] for r in feitos}
    pend = alvo[~alvo.uid.isin(ja)]
    print(f"Modelo {a.modelo} ({ckpt}) | conjunto {a.conjunto}: {len(alvo)} exames, "
          f"{len(ja)} ja feitos, {len(pend)} pendentes", flush=True)
    model = load_trained_model(str(ckpt))
    for i, r in enumerate(pend.itertuples(), 1):
        res = resultado_exame(r.uid, r.ct_path, r.mask_path, model)
        res["modelo"], res["conjunto"] = a.modelo, a.conjunto
        feitos.append(res)
        pd.DataFrame(feitos).to_csv(f_out, index=False)
        print(f"[{a.modelo} {i}/{len(pend)}] {r.uid[-10:]} dice={res['dice']:.4f} "
              f"iou={res['iou']:.4f} tempo={res['tempo_segundos']:.1f}s", flush=True)
    d = pd.DataFrame(feitos)
    print(f"\nDice medio: {d.dice.mean():.4f} | mediana {d.dice.median():.4f} | n={len(d)}\nSalvo: {f_out}")


# ---------------------------------------------------------------------- comparar
def cmd_comparar(a):
    from scipy.stats import wilcoxon
    from luna16.metrics import bootstrap_ci
    saida = configurar_saida(a)
    pasta = saida / "resultados"
    A = pd.read_csv(pasta / f"avaliacao_{a.modelo_a}_{a.conjunto}.csv")
    B = pd.read_csv(pasta / f"avaliacao_{a.modelo_b}_{a.conjunto}.csv")
    m = A.merge(B, on="uid", suffixes=("_a", "_b"))
    if not (len(m) == len(A) == len(B)):
        sys.exit(f"ERRO: os dois modelos precisam ter os mesmos exames (A={len(A)}, B={len(B)}, em comum={len(m)}).")
    sufixo = ""
    if a.apenas:
        uids = set(conjunto_de_exames(ler_plano(a, saida), a.apenas)["uid"])
        m = m[m["uid"].isin(uids)]
        if m.empty:
            sys.exit(f"ERRO: nenhum exame de '{a.apenas}' nos resultados de '{a.conjunto}'.")
        sufixo = f"_apenas_{a.apenas}"
        print(f"Comparando so em '{a.apenas}': {len(m)} exames.")
    linhas = []
    for met in ("dice", "iou", "sensitivity", "precision"):
        for nome, col in ((a.modelo_a, f"{met}_a"), (a.modelo_b, f"{met}_b")):
            ci = bootstrap_ci(m[col].tolist(), seed=42)
            linhas.append({"metrica": met, "modelo": nome, "n": len(m), "media": ci.mean,
                           "ic95_baixo": ci.ci_low, "ic95_alto": ci.ci_high,
                           "mediana": m[col].median(), "desvio_padrao": m[col].std(ddof=1)})
    dif = (m["dice_b"] - m["dice_a"]).tolist()
    ci = bootstrap_ci(dif, seed=42)
    try:
        p = float(wilcoxon(dif).pvalue)
    except ValueError:
        p = float("nan")
    linhas.append({"metrica": "dice (diferenca pareada B - A)", "modelo": f"{a.modelo_b} - {a.modelo_a}",
                   "n": len(m), "media": ci.mean, "ic95_baixo": ci.ci_low, "ic95_alto": ci.ci_high,
                   "mediana": float(np.median(dif)), "desvio_padrao": float(np.std(dif, ddof=1)),
                   "wilcoxon_p": p})
    tab = pd.DataFrame(linhas)
    f_out = pasta / f"comparacao_{a.modelo_a}_vs_{a.modelo_b}_{a.conjunto}{sufixo}.csv"
    pronto_para_gravar(f_out, a.force)
    tab.to_csv(f_out, index=False)
    with pd.option_context("display.float_format", "{:.4f}".format, "display.width", 200):
        print(tab.to_string(index=False))
    print(f"\nSalvo: {f_out}")


# --------------------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)

    def comum(sp):
        sp.add_argument("--saida", default=PADRAO_SAIDA)
        sp.add_argument("--split", default=PADRAO_SPLIT)
        sp.add_argument("--anteriores", default=PADRAO_ANT)
        sp.add_argument("--teste-rapido", action="store_true",
                        help="roda com poucos exames/epocas em <saida>\\_teste_rapido")
        sp.add_argument("--force", action="store_true")

    for nome, fn in (("selecao", cmd_selecao), ("cache", cmd_cache)):
        sp = s.add_parser(nome); comum(sp); sp.set_defaults(func=fn)

    t = s.add_parser("treinar"); comum(t)
    t.add_argument("--epocas", type=int, help=f"padrao {EPOCHS} (igual ao Colab)")
    t.add_argument("--permitir-cpu", action="store_true")
    t.set_defaults(func=cmd_treinar)

    v = s.add_parser("avaliar"); comum(v)
    v.add_argument("--modelo", required=True, choices=["antigo", "novo_final", "novo_best"])
    v.add_argument("--conjunto", required=True,
                   choices=["teste_26", "teste_interno", "teste_133", "validacao", "anteriores_177"])
    v.add_argument("--checkpoint", help="caminho do .pt (padrao conforme --modelo)")
    v.add_argument("--permitir-vistos", action="store_true")
    v.set_defaults(func=cmd_avaliar)

    c = s.add_parser("comparar"); comum(c)
    c.add_argument("--modelo-a", default="antigo")
    c.add_argument("--modelo-b", default="novo_final")
    c.add_argument("--conjunto", required=True)
    c.add_argument("--apenas", choices=["teste_26", "teste_interno"],
                   help="restringe a comparacao a um subconjunto dos exames avaliados")
    c.set_defaults(func=cmd_comparar)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
