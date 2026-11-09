# pji: API de segmentação pulmonar

API (FastAPI) que roda os três métodos do projeto (baseline, region growing e
U-Net) sobre as tomografias do LIDC-IDRI e devolve a máscara do pulmão e as
métricas (Dice, IoU, precisão, revocação, volume em mL) para a tela.

Todos os comandos são rodados **de dentro desta pasta** (`pji/`):

```bash
pip install -r api/requirements.txt

uvicorn api.main:app --reload                          # modo fixo (sem dados)
API_MODO=real uvicorn api.main:app --reload            # modo real (HD com DATASET_LUNA16)
python -m pytest                                       # testes
```

| pasta | o que tem |
|---|---|
| `api/` | rotas, modo fixo e modo real, testes. Documentação completa em [`api/README.md`](api/README.md) |
| `src/luna16/` | pré-processamento do treino, U-Net (`SmallUNet2D`) e `inferir()` |
| `modelos/unet_seed123/` | pesos da U-Net usados pela API (7,8 MB) e os CSVs do treino |

Esta pasta é independente do `src/luna16/` da raiz do repositório: a API usa
o próprio `pji/src/luna16/`.
