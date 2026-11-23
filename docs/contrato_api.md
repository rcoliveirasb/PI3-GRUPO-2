# Contrato da API (Pulmo Scan)

Formato da comunicação entre a API de segmentação (`pji/api/`) e a tela (Pulmo Scan).
Este documento descreve **o que a API implementada faz hoje**: cada exemplo abaixo é uma
resposta real dela. Os testes automáticos de `pji/api/tests/test_contrato.py` conferem esse
formato.

> **Histórico.** A versão 1.0 deste contrato (26/10/2026) foi o plano inicial, com as rotas
> `GET /exames/{uid}/fatias/{z}` e imagens em base64. A API acabou implementada de outro jeito
> (uma rota por método e imagens PNG servidas por URL), e o documento não foi atualizado na
> época. Esta versão 2.0 (23/11/2026) descreve a API real.

## Convenções

- **Endereço:** `http://localhost:8000`. A tela lê o endereço da variável `VITE_API_URL`.
- **Formato:** JSON em UTF-8, com nomes de campo em português sem acento. Só há rotas `GET`.
- **CORS:** liberado para qualquer origem, porque a tela roda em outra porta (5173).
- **Fatia:** corte axial do volume já reamostrado para 1 mm isotrópico, o mesmo do pipeline do
  artigo. Cada exame tem uma fatia de exemplo (`fatia_exemplo`).
- **Imagens:** PNG em tons de cinza, de 8 bits, servidos por URL.
  - **Tomografia:** janela de −1000 a 400 HU.
  - **Máscara:** 0 = fora do pulmão e 255 = pulmão. Tem o mesmo tamanho da fatia.
- **Métodos:** `baseline`, `region_growing` e `unet`. São **os mesmos do artigo**: o modo real
  usa cópias idênticas de `src/luna16/`, e um teste confere isso.
- **Métricas:** são do **exame inteiro** (volume 3D), contra a máscara de referência do LUNA16
  (rótulos 3 e 4). A tela deve escrever "Dice do exame".

## Modos (variável `API_MODO`)

| Modo | `modo` na resposta | De onde vêm os números | Uso |
|---|---|---|---|
| `precalculado` | `pre_calculado` | Resultados **reais** de 3 exames do Teste A, salvos em `pji/api/resultados_precalculados/` | **Demonstração e vídeo** |
| `real` | `modelo_real` | Os três métodos rodando ao vivo sobre os DICOM do HD | Uso completo (precisa do HD) |
| `fixo` (padrão) | `valores_fixos` | Valores **inventados** de `pji/api/dados_exemplo/` | Só para desenvolver a tela |

A tela mostra o modo para quem está vendo saber de onde vêm os números.

## Rotas

### `GET /saude`

```json
{"status": "ok", "modo": "pre_calculado"}
```

### `GET /exames`

Lista os exames disponíveis.

```json
{
  "exames": [
    {
      "id": "teste-a-808059",
      "nome": "Exame teste-a-808059 (Teste A, pior caso do baseline)",
      "num_fatias": 201,
      "fatia_exemplo": 61,
      "baixado": true
    }
  ]
}
```

- `baixado: false` indica, no modo real, um exame da lista que não está no HD.
- No modo pré-calculado, cada exame também traz o `uid` (SeriesInstanceUID do LUNA16).

### `GET /exames/{id}/segmentacao/{metodo}`

Segmenta o exame com um método e devolve as métricas e os endereços das imagens. No modo
real, a primeira chamada calcula, o que leva segundos, e as seguintes vêm do cache.

```json
{
  "exame_id": "teste-a-421281",
  "metodo": "unet",
  "modo": "pre_calculado",
  "fatia": {"indice": 89, "largura": 420, "altura": 420, "url": "/exames/teste-a-421281/fatia.png"},
  "mascara": {"largura": 420, "altura": 420, "url": "/exames/teste-a-421281/segmentacao/unet/mascara.png"},
  "metricas": {
    "dice": 0.9888,
    "iou": 0.9779,
    "precisao": 0.9867,
    "revocacao": 0.991,
    "volume_pulmonar_ml": 7604.0,
    "tempo_ms": 11384
  }
}
```

- `revocacao` é a sensibilidade.
- `tempo_ms` é o tempo da segmentação do exame inteiro. No modo pré-calculado, é o tempo
  medido quando os resultados foram gerados.
- As URLs são relativas ao endereço da API.

### `GET /exames/{id}/fatia.png`

A fatia de exemplo da tomografia, em PNG.

### `GET /exames/{id}/segmentacao/{metodo}/mascara.png`

A máscara do método nessa fatia, em PNG.

## Erros

Os erros vêm com o código HTTP e um JSON neste formato:

```json
{"detail": {"codigo": "exame_inexistente", "mensagem": "Exame 'x' não existe. Use GET /exames para ver os disponíveis."}}
```

| HTTP | `codigo` | Quando |
|---|---|---|
| 404 | `exame_inexistente` | O `id` não está na lista de `GET /exames` |
| 400 | `metodo_invalido` | O método não é `baseline`, `region_growing` nem `unet` |
| 409 | `exame_nao_baixado` | Modo real: o exame está na lista, mas não no HD |

## Quem fez o quê

| Parte | Quem |
|---|---|
| API (FastAPI), modos fixo e real, testes | Rafael |
| Tela (React + Vite) | Érica |
| Ligação da tela com a API, modo pré-calculado e métodos da API iguais aos do artigo | Amabilly |
| U-Net oficial (semente 123) usada pela API | Roger |
