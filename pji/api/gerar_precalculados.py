"""Gera api/resultados_precalculados/ para o modo API_MODO=precalculado.

Roda os tres metodos DE VERDADE, com o mesmo codigo do modo real
(src.luna16.inference.inferir: os metodos do artigo e a U-Net oficial,
semente 123), sobre tres exames do Teste A que estao no computador local
(data/luna16 na raiz do repositorio):

  - o pior caso do baseline;
  - o pior caso do region growing;
  - um caso tipico (Dice do baseline mediano).

Nenhum exame do Teste A entrou no treino da U-Net semente 123 (os 177 exames
da primeira fase ficaram em quarentena). As metricas sao do exame inteiro
(volume 3D, a 1 mm), calculadas como no modo real. A fatia salva e a de maior
erro do metodo que da nome ao caso, para a falha aparecer na tela; no caso
tipico, a de maior area de pulmao.

Uso, a partir da pasta pji/ (precisa de torch, SimpleITK e scikit-image):
    python api/gerar_precalculados.py
"""
import json
import os
import sys
import time
from pathlib import Path

PJI = Path(__file__).resolve().parents[1]
RAIZ = PJI.parent
sys.path.insert(0, str(PJI))

import numpy as np
import pandas as pd
import SimpleITK as sitk

from api.png import codificar_png
from api.servicos.real import PESOS_PADRAO, comparar, janela_uint8
from src.luna16 import inference
from src.luna16.preprocessing import ESPACAMENTO_ALVO, preparar_ct, preparar_referencia

SAIDA = PJI / "api" / "resultados_precalculados"
METODOS = ("baseline", "region_growing", "unet")
VOXEL_MM3 = float(np.prod(ESPACAMENTO_ALVO))


def escolher_exames():
    """(uid, papel, metodo cuja falha a fatia deve mostrar ou None)."""
    b = pd.read_csv("data/luna16/sprint4_baseline_test.csv").set_index("uid")["dice"]
    r = pd.read_csv("data/luna16/sprint4_region_growing_test.csv").set_index("uid")["dice"]
    tipico = (b - b.median()).abs().idxmin()
    return [
        (b.idxmin(), "pior caso do baseline", "baseline"),
        (r.idxmin(), "pior caso do region growing", "region_growing"),
        (tipico, "caso típico", None),
    ]


def ler_exame(uid):
    """Le o .mhd e a mascara do LUNA16 e prepara como a API faz com o DICOM."""
    ct_path = next(Path("data/luna16").glob(f"subset*/{uid}.mhd"))
    ct = sitk.ReadImage(str(ct_path))
    mascara = sitk.ReadImage(str(Path("data/luna16/seg-lungs-LUNA16") / f"{uid}.mhd"))
    return preparar_ct(ct), preparar_referencia(mascara, ct)


def main():
    os.chdir(RAIZ)  # caminhos relativos: o SimpleITK nao abre caminhos com acento no Windows
    SAIDA.mkdir(parents=True, exist_ok=True)
    modelo = inference.carregar_unet(PESOS_PADRAO)

    exames, metricas = [], {}
    for uid, papel, metodo_falha in escolher_exames():
        exame_id = f"teste-a-{uid[-6:]}"
        volume, referencia = ler_exame(uid)
        previstos, metricas[exame_id] = {}, {}
        for metodo in METODOS:
            inicio = time.perf_counter()
            previstos[metodo] = inference.inferir(metodo, volume, modelo, VOXEL_MM3)
            m = comparar(previstos[metodo], referencia, VOXEL_MM3)
            m["tempo_ms"] = round((time.perf_counter() - inicio) * 1000)
            metricas[exame_id][metodo] = m

        com_pulmao = referencia.reshape(len(referencia), -1).sum(axis=1)
        if metodo_falha is None:
            z = int(np.argmax(com_pulmao))
        else:
            erro = (previstos[metodo_falha] ^ referencia).reshape(len(referencia), -1).sum(axis=1)
            erro[com_pulmao == 0] = 0  # so fatias com pulmao
            z = int(np.argmax(erro))

        pasta = SAIDA / exame_id
        pasta.mkdir(exist_ok=True)
        (pasta / "fatia.png").write_bytes(codificar_png(janela_uint8(volume[z])))
        (pasta / "mascara_referencia.png").write_bytes(codificar_png(referencia[z].astype(np.uint8) * 255))
        for metodo in METODOS:
            (pasta / f"mascara_{metodo}.png").write_bytes(codificar_png(previstos[metodo][z].astype(np.uint8) * 255))

        exames.append({
            "id": exame_id,
            "nome": f"Exame {exame_id} (Teste A, {papel})",
            "uid": uid,
            "num_fatias": int(volume.shape[0]),
            "fatia_exemplo": z,
            "baixado": True,
        })
        print(f"{exame_id}: {papel}, fatia {z}  "
              + "  ".join(f"{m} Dice {metricas[exame_id][m]['dice']:.4f}" for m in METODOS), flush=True)

    (SAIDA / "exames.json").write_text(json.dumps(exames, ensure_ascii=False, indent=2), encoding="utf-8")
    (SAIDA / "metricas.json").write_text(json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"salvo em {SAIDA}")


if __name__ == "__main__":
    main()
