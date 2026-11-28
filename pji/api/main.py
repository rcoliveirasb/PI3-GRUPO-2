"""API de segmentacao pulmonar.

Subir, a partir da raiz do repositorio:
    uvicorn api.main:app --reload                       # API_MODO=fixo (padrao)
    API_MODO=real uvicorn api.main:app --reload         # modelos reais

API_MODO=fixo         -> respostas inventadas de api/dados_exemplo/ (sem dados do LUNA16)
API_MODO=precalculado -> resultados reais de api/resultados_precalculados/ (para a demonstracao)
API_MODO=real         -> api/servicos/real.py (U-Net e volumes carregados na subida)

Em qualquer modo: POST /analises recebe uma fatia (.png, .jpg ou .dcm) e roda
os tres metodos nela, com a U-Net treinada (ver api/analise_upload.py).
"""
import os
from contextlib import asynccontextmanager

import threading

from fastapi import Depends, FastAPI, File, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.erros import METODOS, metodo_invalido
from api.png import largura_altura

_servico = None
_analisador = None
_trava_analisador = threading.Lock()


def criar_servico():
    modo = os.getenv("API_MODO", "fixo").strip().lower()
    if modo == "fixo":
        from api.servicos.fixo import ServicoFixo
        return ServicoFixo()
    if modo == "precalculado":
        from api.servicos.fixo import ServicoPreCalculado
        return ServicoPreCalculado()
    if modo == "real":
        # import aqui dentro: o modo fixo nao precisa de torch nem SimpleITK
        from api.servicos.real import ServicoReal
        return ServicoReal()
    raise RuntimeError(f"API_MODO='{modo}' inválido. Use 'fixo', 'precalculado' ou 'real'.")


def obter_servico():
    global _servico
    if _servico is None:
        _servico = criar_servico()
    return _servico


def obter_analisador():
    global _analisador
    with _trava_analisador:
        if _analisador is None:
            from api.analise_upload import AnalisadorUpload
            _analisador = AnalisadorUpload()
        return _analisador


def _aquecer_analisador():
    """Carrega a U-Net em segundo plano, para a primeira analise nao esperar."""
    try:
        obter_analisador().modelo()
    except Exception as erro:  # a API continua servindo os exames mesmo sem o modelo
        print(f"[api] U-Net para envio de arquivos indisponível: {erro}", flush=True)


@asynccontextmanager
async def lifespan(app):
    obter_servico()  # carrega modelo e dados uma vez, na subida
    threading.Thread(target=_aquecer_analisador, daemon=True).start()
    yield


app = FastAPI(
    title="API de segmentação pulmonar",
    description="Ponte entre os métodos de segmentação e a tela. "
                "API_MODO=fixo (valores fixos) ou API_MODO=real (modelos reais).",
    version="0.2.0",
    lifespan=lifespan,
)

# Liberado para desenvolvimento: a tela do front roda em outra porta.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def validar_metodo(metodo):
    if metodo not in METODOS:
        raise metodo_invalido(metodo)


def png(dados):
    return Response(content=dados, media_type="image/png")


@app.get("/saude")
def saude(servico=Depends(obter_servico)):
    return {"status": "ok", "modo": servico.modo}


@app.get("/exames")
def listar_exames(servico=Depends(obter_servico)):
    return {"exames": servico.listar_exames()}


# Rotas sincronas (def): o FastAPI roda em thread, sem travar as outras requisicoes.
@app.get("/exames/{exame_id}/segmentacao/{metodo}")
def segmentar(exame_id: str, metodo: str, servico=Depends(obter_servico)):
    validar_metodo(metodo)
    indice, fatia_png = servico.fatia(exame_id)
    mascara_png, metricas = servico.segmentar(exame_id, metodo)
    largura, altura = largura_altura(fatia_png)
    mascara_largura, mascara_altura = largura_altura(mascara_png)
    return {
        "exame_id": exame_id,
        "metodo": metodo,
        "modo": servico.modo,
        "fatia": {
            "indice": indice,
            "largura": largura,
            "altura": altura,
            "url": f"/exames/{exame_id}/fatia.png",
        },
        "mascara": {
            "largura": mascara_largura,
            "altura": mascara_altura,
            "url": f"/exames/{exame_id}/segmentacao/{metodo}/mascara.png",
        },
        "metricas": metricas,
    }


@app.get("/exames/{exame_id}/fatia.png")
def fatia_png(exame_id: str, servico=Depends(obter_servico)):
    return png(servico.fatia(exame_id)[1])


@app.get("/exames/{exame_id}/segmentacao/{metodo}/mascara.png")
def mascara_png(exame_id: str, metodo: str, servico=Depends(obter_servico)):
    validar_metodo(metodo)
    return png(servico.segmentar(exame_id, metodo)[0])


# --- Envio de arquivo pela tela: uma fatia analisada pelos tres metodos ---

def _resposta_analise(registro):
    base = f"/analises/{registro['id']}"
    return {
        "analise_id": registro["id"],
        "arquivo": registro["arquivo"],
        "tipo": registro["tipo"],
        "modo": "modelo_real",
        "gabarito": registro["gabarito"],
        "avisos": registro["avisos"],
        "fatia": {"largura": registro["largura"], "altura": registro["altura"], "url": f"{base}/fatia.png"},
        "metodos": {
            metodo: {"metricas": metricas, "mascara": {"url": f"{base}/{metodo}/mascara.png"}}
            for metodo, metricas in registro["metodos"].items()
        },
    }


@app.post("/analises")
def analisar_arquivo(arquivo: UploadFile = File(...), analisador=Depends(obter_analisador)):
    dados = arquivo.file.read()
    return _resposta_analise(analisador.analisar(arquivo.filename, dados))


@app.get("/analises/{analise_id}")
def obter_analise(analise_id: str, analisador=Depends(obter_analisador)):
    return _resposta_analise(analisador.obter(analise_id))


@app.get("/analises/{analise_id}/fatia.png")
def analise_fatia_png(analise_id: str, analisador=Depends(obter_analisador)):
    return png(analisador.obter(analise_id)["fatia_png"])


@app.get("/analises/{analise_id}/{metodo}/mascara.png")
def analise_mascara_png(analise_id: str, metodo: str, analisador=Depends(obter_analisador)):
    validar_metodo(metodo)
    return png(analisador.obter(analise_id)["mascaras_png"][metodo])
