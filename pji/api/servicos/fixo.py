"""Modo fixo (API_MODO=fixo): respostas inventadas de api/dados_exemplo/.

Serve para a tela rodar sem os dados do LUNA16 nem torch/SimpleITK.
"""
import json
from pathlib import Path

from api.erros import exame_inexistente

PASTA_DADOS = Path(__file__).resolve().parents[1] / "dados_exemplo"


class ServicoFixo:
    modo = "valores_fixos"
    pasta = PASTA_DADOS

    def __init__(self):
        self.exames = self._ler("exames.json")
        self.metricas = self._ler("metricas.json")

    def _ler(self, nome):
        return json.loads((self.pasta / nome).read_text(encoding="utf-8"))

    def listar_exames(self):
        return self.exames

    def _exame(self, exame_id):
        for exame in self.exames:
            if exame["id"] == exame_id:
                return exame
        raise exame_inexistente(exame_id)

    def fatia(self, exame_id):
        """(indice, png) da fatia de exemplo."""
        exame = self._exame(exame_id)
        return exame["fatia_exemplo"], (self.pasta / exame_id / "fatia.png").read_bytes()

    def segmentar(self, exame_id, metodo):
        """(png da mascara, metricas) do metodo na fatia de exemplo."""
        self._exame(exame_id)
        png = (self.pasta / exame_id / f"mascara_{metodo}.png").read_bytes()
        return png, self.metricas[exame_id][metodo]


class ServicoPreCalculado(ServicoFixo):
    """Modo pre-calculado (API_MODO=precalculado): resultados REAIS salvos em
    api/resultados_precalculados/, gerados por api/gerar_precalculados.py com o
    mesmo codigo do modo real (os metodos do artigo e a U-Net oficial) sobre
    exames do Teste A. Serve para a demonstracao: numeros e imagens de verdade,
    resposta instantanea e sem precisar do HD nem do torch."""
    modo = "pre_calculado"
    pasta = Path(__file__).resolve().parents[1] / "resultados_precalculados"
