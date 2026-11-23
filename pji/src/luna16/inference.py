"""Inferencia dos tres metodos sobre um volume ja pre-processado.

Entrada de `inferir`: volume (z, y, x) em HU, saido de
preprocessing.preparar_ct (limpo, suavizado, 1 mm isotropico) -- a mesma
entrada de pipeline.run_pipeline_for_uid no treino/avaliacao. Saida: mascara
booleana na mesma grade.

  baseline        -> baseline.segment_baseline (limiar -600 HU + morfologia)
  region_growing  -> region_growing.segment_region_growing
  unet            -> SmallUNet2D treinada, fatia a fatia, + limpeza de
                     componentes fora do torax (lung_air.keep_components_by_fraction)

Os tres metodos sao OS MESMOS dos experimentos do artigo: baseline.py,
region_growing.py e lung_air.py sao copias identicas de src/luna16/ da raiz
do repositorio (mantidas aqui para a API continuar independente). Assim a tela
mostra os mesmos numeros do relatorio. Se mudar um deles na raiz, copie de novo.

A implementacao antiga da API (api/segmentation.py) continua no repositorio,
mas nao e mais usada pelo modo real: o region growing dela era outro algoritmo
e dava resultados diferentes dos publicados (Dice ~0,98 contra ~0,93).
"""
from pathlib import Path

import numpy as np
import torch
from skimage.transform import resize

from src.luna16.baseline import segment_baseline
from src.luna16.lung_air import keep_components_by_fraction
from src.luna16.region_growing import segment_region_growing
from src.luna16.unet import INPUT_SIZE, SmallUNet2D, hu_to_input

METODOS = ("baseline", "region_growing", "unet")
DISPOSITIVO = torch.device("cuda" if torch.cuda.is_available() else "cpu")
LOTE_UNET = 32


def carregar_unet(caminho, dispositivo=DISPOSITIVO):
    """Carrega um checkpoint de train_unet_baseline.py / treino_novo
    ({"model_state", "base_ch", "train_uids", ...})."""
    checkpoint = torch.load(Path(caminho), map_location="cpu", weights_only=False)
    if not isinstance(checkpoint, dict) or "model_state" not in checkpoint:
        raise ValueError(
            f"'{caminho}' não é um checkpoint da SmallUNet2D (falta 'model_state'). "
            "Use um unet_novo_*.pt de D:\\DATASET_LUNA16\\treino_*."
        )
    modelo = SmallUNet2D(base_ch=checkpoint.get("base_ch", 16))
    modelo.load_state_dict(checkpoint["model_state"])
    modelo.to(dispositivo).eval()
    modelo.uids_treino = set(checkpoint.get("train_uids", []))
    modelo.epoca = checkpoint.get("epoca")
    # Aquecimento: a 1a passada na GPU inicializa o CUDA/cuDNN (~40 s); melhor
    # pagar isso na subida do que no tempo_ms do primeiro exame.
    with torch.inference_mode():
        modelo(torch.zeros(LOTE_UNET, 1, INPUT_SIZE, INPUT_SIZE, device=dispositivo))
    return modelo


def limpar_fora_do_torax(mascara, frac_min=0.15):
    """Mesma limpeza da avaliacao (src/luna16/unet.segment_with_unet): mantem
    os componentes com pelo menos frac_min do volume do maior, o que tira o ar
    da mesa do tomografo que a rede marca como pulmao. Se a limpeza zerar a
    mascara (caso degenerado), devolve a mascara crua."""
    if not mascara.any():
        return mascara
    limpa = keep_components_by_fraction(mascara, frac_min=frac_min)
    return limpa if limpa.any() else mascara


def segmentar_unet(modelo, volume_hu):
    """Igual a segment_with_unet do treino (mesmo resize do skimage, mesmo
    limiar 0.5), mas com as fatias em lotes para usar melhor a GPU."""
    z, h, w = volume_hu.shape
    mascara = np.zeros((z, h, w), dtype=bool)
    dispositivo = next(modelo.parameters()).device
    with torch.inference_mode():
        for inicio in range(0, z, LOTE_UNET):
            entrada = np.stack([
                resize(hu_to_input(fatia).astype(np.float32), (INPUT_SIZE, INPUT_SIZE),
                       order=1, anti_aliasing=True, preserve_range=True)
                for fatia in volume_hu[inicio:inicio + LOTE_UNET]
            ]).astype(np.float32)[:, None]
            probs = torch.sigmoid(modelo(torch.from_numpy(entrada).to(dispositivo)))[:, 0].cpu().numpy()
            for i, p in enumerate(probs):
                mascara[inicio + i] = resize(p, (h, w), order=1, anti_aliasing=True, preserve_range=True) > 0.5
    return mascara


def inferir(metodo, volume_hu, modelo_unet=None, voxel_mm3=1.0):
    """Funcao unica de inferencia: volume pre-processado -> mascara booleana."""
    if metodo == "baseline":
        return segment_baseline(volume_hu)
    if metodo == "region_growing":
        return segment_region_growing(volume_hu)
    if metodo == "unet":
        if modelo_unet is None:
            raise ValueError("método 'unet' precisa do modelo carregado (carregar_unet)")
        return limpar_fora_do_torax(segmentar_unet(modelo_unet, volume_hu))
    raise ValueError(f"método desconhecido: {metodo}")
