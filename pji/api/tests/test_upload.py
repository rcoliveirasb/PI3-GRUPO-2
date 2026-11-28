"""POST /analises: a tela envia uma fatia e a API roda os tres metodos nela."""
import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api import main
from api.analise_upload import PASTA_PRECALCULADOS, AnalisadorUpload
from api.erros import METODOS
from api.servicos.real import PESOS_PADRAO

pytestmark = pytest.mark.skipif(not PASTA_PRECALCULADOS.exists(), reason="sem resultados pré-calculados")


@pytest.fixture(scope="module")
def cliente():
    import os
    if not os.path.exists(PESOS_PADRAO):
        pytest.skip("pesos da U-Net ausentes")
    main._analisador = AnalisadorUpload()
    return TestClient(main.app)


def enviar(cliente, nome, dados):
    return cliente.post("/analises", files={"arquivo": (nome, dados, "application/octet-stream")})


def test_fatia_do_sistema_tem_gabarito_e_unet_igual_ao_exame_inteiro(cliente):
    fatia = (PASTA_PRECALCULADOS / "teste-a-808059" / "fatia.png").read_bytes()
    resposta = enviar(cliente, "fatia.png", fatia)
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["gabarito"] == "teste-a-808059"
    assert set(corpo["metodos"]) == set(METODOS)
    # A U-Net e 2D: na fatia isolada ela repete a mascara do exame inteiro.
    assert corpo["metodos"]["unet"]["metricas"]["dice"] == pytest.approx(0.9733, abs=0.002)
    for metodo in METODOS:
        url = corpo["metodos"][metodo]["mascara"]["url"]
        assert cliente.get(url).headers["content-type"] == "image/png"
    assert cliente.get(corpo["fatia"]["url"]).status_code == 200


def test_imagem_qualquer_roda_sem_dice(cliente):
    fatia = np.array(Image.open(PASTA_PRECALCULADOS / "teste-a-421281" / "fatia.png").convert("L"))
    saida = io.BytesIO()
    Image.fromarray(fatia).convert("RGB").save(saida, format="JPEG", quality=90)  # outra imagem: JPG
    corpo = enviar(cliente, "exame.jpg", saida.getvalue()).json()
    assert corpo["gabarito"] is None
    assert corpo["metodos"]["unet"]["metricas"]["dice"] is None
    assert corpo["metodos"]["unet"]["metricas"]["area_pulmonar_cm2"] > 50


def test_imagem_sem_pulmao_gera_aviso(cliente):
    branca = io.BytesIO()
    Image.new("L", (200, 200), 200).save(branca, format="PNG")
    corpo = enviar(cliente, "branca.png", branca.getvalue()).json()
    assert any("Quase nenhum pulmão" in aviso for aviso in corpo["avisos"])


def test_formato_invalido(cliente):
    resposta = enviar(cliente, "notas.txt", b"nada")
    assert resposta.status_code == 415
    assert "Formato não suportado" in resposta.json()["detail"]["mensagem"]


def test_analise_inexistente(cliente):
    assert cliente.get("/analises/naoexiste").status_code == 404
