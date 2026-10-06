"""U-Net 2D como contingencia para a etapa "Mineracao de Dados" do KDD
(sugestao explicita do professor no feedback do Checkpoint 1: modelo U-Net 2D,
loss BCE+Dice, meta Dice >= 0.75).

Isto NAO substitui o baseline (threshold+morfologia) nem o region growing --
o plano original do Grupo 2 trata os dois metodos classicos como a comparacao
oficial. Este modulo existe para ter um modelo treinado real disponivel caso
o professor exija isso literalmente para considerar a etapa de "Mineracao"
concluida (ver PROJETO.md, secao "Contexto academico").

Escopo original deliberadamente limitado (CPU, sem GPU na maquina local):
- Entrada 128x128 (fatias axiais redimensionadas) em vez da resolucao total
  (~266x266 apos reamostragem isotropica) -- mantem o treino em minutos, nao
  em horas, numa CPU comum.
- Rede pequena (16-256 canais) em vez de um U-Net "padrao" (64-1024) -- mesmo
  motivo.
- Treinado sobre um subconjunto de fatias por paciente (as que contem pulmao
  na mascara de referencia, mais algumas de fundo), nao o volume 3D inteiro.

Desde 14/09, `DEVICE` detecta GPU automaticamente (ex.: Colab) e
`scripts/train_unet_baseline.py` aumenta o escopo (mais pacientes, mais
epocas, rede maior) quando ha GPU disponivel -- o codigo continua
funcionando igual em CPU, so mais devagar e com o escopo original.

Isso e suficiente para produzir um numero real de Dice/IoU comparavel aos
outros metodos (mesmo pipeline de pre-processamento e mesmas metricas -- ver
`unet_segment_fn`). Resolucao maior e augmentation continuam como possiveis
melhorias futuras, mesmo com GPU.
"""
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

INPUT_SIZE = 128  # fatia redimensionada para NxN antes de entrar na rede

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class DiceLoss(nn.Module):
    """1 - Dice, calculado sobre os logits (via sigmoid) -- suave/diferenciavel,
    ao contrario do Dice booleano usado na avaliacao final (metrics.py)."""

    def __init__(self, smooth: float = 1.0):
        super().__init__()
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        probs = torch.sigmoid(logits)
        probs = probs.view(probs.size(0), -1)
        target = target.view(target.size(0), -1)
        intersection = (probs * target).sum(dim=1)
        union = probs.sum(dim=1) + target.sum(dim=1)
        dice = (2 * intersection + self.smooth) / (union + self.smooth)
        return 1 - dice.mean()


class BCEDiceLoss(nn.Module):
    """Loss pedida explicitamente no feedback do professor: BCE + Dice."""

    def __init__(self):
        super().__init__()
        self.bce = nn.BCEWithLogitsLoss()
        self.dice = DiceLoss()

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        return self.bce(logits, target) + self.dice(logits, target)


def _conv_block(in_ch: int, out_ch: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(in_ch, out_ch, 3, padding=1),
        nn.BatchNorm2d(out_ch),
        nn.ReLU(inplace=True),
        nn.Conv2d(out_ch, out_ch, 3, padding=1),
        nn.BatchNorm2d(out_ch),
        nn.ReLU(inplace=True),
    )


class SmallUNet2D(nn.Module):
    """U-Net 2D compacto (encoder 16->32->64, bottleneck 128, decoder
    espelhado com skip connections) -- reduzido de proposito para treinar em
    CPU em minutos. Entrada: (N, 1, H, W) HU normalizado; saida: logits
    (N, 1, H, W), aplicar sigmoid + threshold para binarizar."""

    def __init__(self, base_ch: int = 16):
        super().__init__()
        c1, c2, c3, cb = base_ch, base_ch * 2, base_ch * 4, base_ch * 8

        self.enc1 = _conv_block(1, c1)
        self.enc2 = _conv_block(c1, c2)
        self.enc3 = _conv_block(c2, c3)
        self.bottleneck = _conv_block(c3, cb)

        self.pool = nn.MaxPool2d(2)

        self.up3 = nn.ConvTranspose2d(cb, c3, 2, stride=2)
        self.dec3 = _conv_block(cb, c3)
        self.up2 = nn.ConvTranspose2d(c3, c2, 2, stride=2)
        self.dec2 = _conv_block(c3, c2)
        self.up1 = nn.ConvTranspose2d(c2, c1, 2, stride=2)
        self.dec1 = _conv_block(c2, c1)

        self.out_conv = nn.Conv2d(c1, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        b = self.bottleneck(self.pool(e3))

        d3 = self.dec3(torch.cat([self.up3(b), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))

        return self.out_conv(d1)


def hu_to_input(hu_slice: np.ndarray, vmin: float = -1000, vmax: float = 400) -> np.ndarray:
    """Normaliza uma fatia HU (ja limpa, ver preprocessing.clean_hu) para
    [-1, 1], a mesma faixa fisiologicamente relevante usada no resto do
    projeto para visualizacao -- nunca para o threshold do baseline."""
    clipped = np.clip(hu_slice, vmin, vmax)
    return ((clipped - vmin) / (vmax - vmin)) * 2 - 1


@dataclass
class UNetConfig:
    input_size: int = INPUT_SIZE
    base_channels: int = 16
    checkpoint_path: str = "data/luna16/unet_baseline.pt"


def load_trained_model(checkpoint_path: str = "data/luna16/unet_baseline.pt") -> SmallUNet2D:
    """Carrega o checkpoint treinado por scripts/train_unet_baseline.py.

    Usa GPU automaticamente se disponivel (DEVICE), tanto para carregar
    quanto para inferencia -- funciona igual em CPU, so mais devagar.
    """
    checkpoint = torch.load(checkpoint_path, map_location=DEVICE, weights_only=False)
    model = SmallUNet2D(base_ch=checkpoint.get("base_ch", 16))
    model.load_state_dict(checkpoint["model_state"])
    model.to(DEVICE)
    model.eval()
    return model


def segment_with_unet(volume_hu: np.ndarray, model: SmallUNet2D) -> np.ndarray:
    """Segmenta um volume 3D (ja limpo/reamostrado, mesma entrada esperada
    por segment_baseline/segment_region_growing) fatia a fatia com o U-Net.

    Cada fatia axial e redimensionada para INPUT_SIZE x INPUT_SIZE (o que a
    rede foi treinada para receber), passa pela rede, e a predicao volta pro
    tamanho original da fatia antes de empilhar -- assim a mascara final tem
    a mesma resolucao do volume de entrada, igual aos outros metodos.
    """
    from skimage.transform import resize

    z, h, w = volume_hu.shape
    mask = np.zeros((z, h, w), dtype=bool)

    model.to(DEVICE)
    with torch.no_grad():
        for i in range(z):
            img = hu_to_input(volume_hu[i]).astype(np.float32)
            img_r = resize(img, (INPUT_SIZE, INPUT_SIZE), order=1, anti_aliasing=True, preserve_range=True)
            x = torch.from_numpy(img_r).unsqueeze(0).unsqueeze(0).to(DEVICE)
            logits = model(x)
            probs = torch.sigmoid(logits).squeeze().cpu().numpy()
            probs_full = resize(probs, (h, w), order=1, anti_aliasing=True, preserve_range=True)
            mask[i] = probs_full > 0.5

    return mask
