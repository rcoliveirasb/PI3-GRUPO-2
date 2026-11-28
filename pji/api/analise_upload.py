"""Analise de uma fatia enviada pela tela (POST /analises).

Funciona em qualquer API_MODO: carrega a U-Net treinada (seed 123) na primeira
analise e roda os tres metodos do artigo (src/luna16/inference.inferir) sobre a
fatia enviada.

Formatos aceitos:
  .dcm         fatia DICOM de TC: ja vem em HU. Passa pelo mesmo
               pre-processamento do treino (limpeza, filtro gaussiano, 1 mm).
  .png / .jpg  imagem em tons de cinza. Nao tem HU: o cinza e convertido de
               volta para HU supondo a janela de -1000 a 400 HU, a mesma das
               fatias que a API gera e da entrada da U-Net (unet.hu_to_input).
               Imagens exportadas com outra janela (ex.: janela de pulmao
               -1350 a 150) chegam com HU deslocado; a resposta avisa isso.

Diferenca importante para quem le o resultado:
  - a U-Net e 2D (fatia a fatia), entao numa fatia so ela da a mesma resposta
    que no exame inteiro;
  - baseline e region growing usam conectividade 3D (componentes, sementes);
    com uma fatia so eles perdem esse contexto e o resultado pode diferir do
    exame inteiro.

Dice e IoU so existem quando ha gabarito: se a fatia enviada for identica a
uma das fatias de api/resultados_precalculados/, usa a mascara de referencia
do LUNA16 dela. Para qualquer outra imagem, devolve so area e tempo.
"""
import io
import os
import tempfile
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path

import numpy as np
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from src.luna16 import inference

PASTA_PRECALCULADOS = Path(__file__).resolve().parent / "resultados_precalculados"
CLIP_MIN_HU, CLIP_MAX_HU = -1000, 400
EXTENSOES_IMAGEM = {".png", ".jpg", ".jpeg"}
EXTENSOES_DICOM = {".dcm"}
TAMANHO_MAXIMO = 30 * 1024 * 1024  # 30 MB
LADO_MAXIMO = 1024                 # pixels
MAX_ANALISES_EM_MEMORIA = 30
FRACAO_MINIMA_PULMAO = 0.01        # abaixo disso, provavelmente nao e TC de torax


def erro(status, codigo, mensagem):
    return HTTPException(status_code=status, detail={"codigo": codigo, "mensagem": mensagem})


def cinza_para_hu(cinza):
    return cinza.astype(np.float32) / 255.0 * (CLIP_MAX_HU - CLIP_MIN_HU) + CLIP_MIN_HU


def hu_para_cinza(hu):
    return ((np.clip(hu, CLIP_MIN_HU, CLIP_MAX_HU) - CLIP_MIN_HU)
            / (CLIP_MAX_HU - CLIP_MIN_HU) * 255).astype(np.uint8)


def png_bytes(matriz):
    saida = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(matriz, dtype=np.uint8)).save(saida, format="PNG")
    return saida.getvalue()


def ler_imagem(dados):
    try:
        imagem = Image.open(io.BytesIO(dados))
        imagem.load()
    except (UnidentifiedImageError, OSError):
        raise erro(400, "arquivo_invalido", "Não consegui abrir a imagem. Envie um PNG ou JPG válido.")
    cinza = np.array(imagem.convert("L"))
    if max(cinza.shape) > LADO_MAXIMO:
        escala = LADO_MAXIMO / max(cinza.shape)
        novo = (max(1, round(cinza.shape[1] * escala)), max(1, round(cinza.shape[0] * escala)))
        cinza = np.array(Image.fromarray(cinza).resize(novo, Image.BILINEAR))
    return cinza


def ler_dicom(dados):
    """Fatia DICOM -> (fatia em HU a 1 mm, pre-processada como no treino, espacamento original)."""
    import SimpleITK as sitk
    from skimage.transform import resize

    from src.luna16.preprocessing import clean_hu, denoise

    caminho = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".dcm", delete=False) as arquivo:
            arquivo.write(dados)
            caminho = arquivo.name
        imagem = sitk.ReadImage(caminho)
    except RuntimeError:
        raise erro(400, "arquivo_invalido", "Não consegui ler o DICOM. Envie uma fatia .dcm de tomografia.")
    finally:
        if caminho:
            os.unlink(caminho)

    volume = sitk.GetArrayFromImage(imagem)
    if volume.ndim == 3:
        volume = volume[volume.shape[0] // 2]  # DICOM multi-frame: fatia do meio
    if volume.ndim != 2:
        raise erro(400, "arquivo_invalido", "O DICOM enviado não é uma imagem 2D em tons de cinza.")
    esp_x, esp_y = imagem.GetSpacing()[:2]
    fatia = denoise(clean_hu(volume.astype(np.int16)[None]), sigma=0.5)[0].astype(np.float32)
    novo = (max(1, round(fatia.shape[0] * esp_y)), max(1, round(fatia.shape[1] * esp_x)))
    fatia = resize(fatia, novo, order=1, preserve_range=True, anti_aliasing=False).astype(np.float32)
    return fatia


def metricas_contra(previsto, referencia):
    vp = int(np.count_nonzero(previsto & referencia))
    fp = int(np.count_nonzero(previsto & ~referencia))
    fn = int(np.count_nonzero(~previsto & referencia))

    def razao(a, b):
        return round(a / b, 4) if b else 0.0

    return {"dice": razao(2 * vp, 2 * vp + fp + fn), "iou": razao(vp, vp + fp + fn),
            "precisao": razao(vp, vp + fp), "revocacao": razao(vp, vp + fn)}


class AnalisadorUpload:
    def __init__(self, pesos=None):
        from api.servicos.real import PESOS_PADRAO
        self.pesos = pesos or os.getenv("API_PESOS_UNET", PESOS_PADRAO)
        self._modelo = None
        self._trava_modelo = threading.Lock()
        self._trava_analises = threading.Lock()
        self.analises = OrderedDict()  # id -> dict
        self.gabaritos = self._carregar_gabaritos()

    @staticmethod
    def _carregar_gabaritos():
        """Fatias com mascara de referencia do LUNA16 (as 3 do modo pre-calculado)."""
        gabaritos = []
        for pasta in sorted(PASTA_PRECALCULADOS.glob("*")):
            fatia, referencia = pasta / "fatia.png", pasta / "mascara_referencia.png"
            if fatia.exists() and referencia.exists():
                gabaritos.append((pasta.name,
                                  np.array(Image.open(fatia).convert("L")),
                                  np.array(Image.open(referencia).convert("L")) > 0))
        return gabaritos

    def modelo(self):
        with self._trava_modelo:
            if self._modelo is None:
                if not os.path.exists(self.pesos):
                    raise erro(503, "modelo_indisponivel",
                               f"Pesos da U-Net não encontrados em '{self.pesos}'.")
                self._modelo = inference.carregar_unet(self.pesos)
            return self._modelo

    def _gabarito(self, cinza):
        for nome, fatia, referencia in self.gabaritos:
            if fatia.shape == cinza.shape and np.array_equal(fatia, cinza):
                return nome, referencia
        return None, None

    def analisar(self, nome_arquivo, dados):
        extensao = Path(nome_arquivo or "").suffix.lower()
        if not dados:
            raise erro(400, "arquivo_vazio", "O arquivo enviado está vazio.")
        if len(dados) > TAMANHO_MAXIMO:
            raise erro(413, "arquivo_grande", "Arquivo maior que 30 MB. Envie uma fatia só.")

        avisos = []
        if extensao in EXTENSOES_IMAGEM:
            cinza = ler_imagem(dados)
            fatia_hu = cinza_para_hu(cinza)
            tipo = "imagem"
            avisos.append("Imagem PNG/JPG não guarda valores Hounsfield: os tons de cinza foram "
                          "convertidos supondo a janela de −1000 a 400 HU (a mesma das fatias do sistema).")
        elif extensao in EXTENSOES_DICOM:
            fatia_hu = ler_dicom(dados)
            cinza = hu_para_cinza(fatia_hu)
            tipo = "dicom"
        else:
            raise erro(415, "formato_nao_suportado",
                       "Formato não suportado. Envie uma fatia de tomografia em .png, .jpg ou .dcm.")

        nome_gabarito, referencia = self._gabarito(cinza)
        modelo = self.modelo()
        volume = fatia_hu[None]  # (1, y, x): os metodos esperam um volume
        area_px = cinza.size

        metodos, mascaras = {}, {}
        for metodo in inference.METODOS:
            inicio = time.perf_counter()
            previsto = inference.inferir(metodo, volume, modelo)[0]
            tempo_ms = round((time.perf_counter() - inicio) * 1000)
            metricas = {"dice": None, "iou": None, "precisao": None, "revocacao": None}
            if referencia is not None:
                metricas.update(metricas_contra(previsto, referencia))
            pixels = int(np.count_nonzero(previsto))
            metricas.update({
                "area_pulmonar_cm2": round(pixels / 100, 1),  # 1 pixel = 1 mm²
                "fracao_da_imagem": round(pixels / area_px, 4),
                "tempo_ms": tempo_ms,
            })
            metodos[metodo] = metricas
            mascaras[metodo] = png_bytes(previsto.astype(np.uint8) * 255)

        if metodos["unet"]["fracao_da_imagem"] < FRACAO_MINIMA_PULMAO:
            avisos.append("Quase nenhum pulmão foi encontrado. Confira se a imagem é uma fatia axial "
                          "de tomografia de tórax.")
        if tipo == "imagem":
            avisos.append("Área calculada supondo 1 mm por pixel (o tamanho das fatias do sistema).")

        analise_id = uuid.uuid4().hex[:12]
        registro = {
            "id": analise_id,
            "arquivo": nome_arquivo,
            "tipo": tipo,
            "largura": int(cinza.shape[1]),
            "altura": int(cinza.shape[0]),
            "gabarito": nome_gabarito,
            "avisos": avisos,
            "metodos": metodos,
            "fatia_png": png_bytes(cinza),
            "mascaras_png": mascaras,
        }
        with self._trava_analises:
            self.analises[analise_id] = registro
            while len(self.analises) > MAX_ANALISES_EM_MEMORIA:
                self.analises.popitem(last=False)
        return registro

    def obter(self, analise_id):
        with self._trava_analises:
            registro = self.analises.get(analise_id)
        if registro is None:
            raise erro(404, "analise_inexistente",
                       f"Análise '{analise_id}' não encontrada (a API guarda só as últimas {MAX_ANALISES_EM_MEMORIA}).")
        return registro
