"""Modo pre-calculado: resultados reais salvos, servidos com o mesmo contrato."""
from fastapi.testclient import TestClient

from api import main
from api.erros import METODOS
from api.servicos.fixo import ServicoPreCalculado


def cliente_precalculado(monkeypatch):
    monkeypatch.setattr(main, "_servico", ServicoPreCalculado())
    return TestClient(main.app)


def test_lista_e_segmenta_os_exames_reais(monkeypatch):
    cliente = cliente_precalculado(monkeypatch)
    assert cliente.get("/saude").json()["modo"] == "pre_calculado"
    exames = cliente.get("/exames").json()["exames"]
    assert len(exames) == 3
    for exame in exames:
        for metodo in METODOS:
            resposta = cliente.get(f"/exames/{exame['id']}/segmentacao/{metodo}").json()
            assert resposta["modo"] == "pre_calculado"
            assert 0 < resposta["metricas"]["dice"] <= 1
            assert cliente.get(resposta["mascara"]["url"]).headers["content-type"] == "image/png"
        assert cliente.get(f"/exames/{exame['id']}/fatia.png").status_code == 200


def test_numeros_sao_os_do_artigo(monkeypatch):
    """O pior caso do baseline no Teste A tem Dice 0,8468 nos CSVs do artigo."""
    cliente = cliente_precalculado(monkeypatch)
    resposta = cliente.get("/exames/teste-a-808059/segmentacao/baseline").json()
    assert resposta["metricas"]["dice"] == 0.8468
