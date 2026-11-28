# Contrato da API (Pulmo Scan)

Formato da comunicação entre a API de segmentação (`pji/api/`) e a tela (Pulmo Scan).
Este documento descreve **o que a API implementada faz hoje**: cada exemplo abaixo é uma
resposta real dela. Os testes automáticos de `pji/api/tests/test_contrato.py` conferem esse
formato.

> **Histórico.** A versão 1.0 deste contrato (26/10/2026) foi o plano inicial, com as rotas
> `GET /exames/{uid}/fatias/{z}` e imagens em base64. A API acabou implementada de outro jeito
> (uma rota por método e imagens PNG servidas por URL), e o documento não foi atualizado na
> época. A versão 2.0 (23/11/2026) passou a descrever a API real. Esta versão 2.1 (28/11/2026)
> acrescenta o envio de arquivo (`POST /analises`): a tela manda uma fatia de tomografia e a API
> roda os três métodos nela.

## Convenções

- **Endereço:** `http://localhost:8000`. A tela lê o endereço da variável `VITE_API_URL`.
- **Formato:** JSON em UTF-8, com nomes de campo em português sem acento. Todas as rotas são
  `GET`, menos o envio de arquivo (`POST /analises`, em `multipart/form-data`).
- **CORS:** liberado para qualquer origem, porque a tela roda em outra porta (5173).
- **Fatia:** corte axial do volume já reamostrado para 1 mm isotrópico, o mesmo do pipeline do
  artigo. Cada exame tem uma fatia de exemplo (`fatia_exemplo`).
- **Imagens:** PNG em tons de cinza, de 8 bits, servidos por URL.
  - **Tomografia:** janela de −1000 a 400 HU.
  - **Máscara:** 0 = fora do pulmão e 255 = pulmão. Tem o mesmo tamanho da fatia.
- **Métodos:** `baseline`, `region_growing` e `unet`. São **os mesmos do artigo**: o modo real
  usa cópias idênticas de `src/luna16/`, e um teste confere isso.
- **Métricas:** nas rotas `/exames`, são do **exame inteiro** (volume 3D), contra a máscara de
  referência do LUNA16 (rótulos 3 e 4). A tela deve escrever "Dice do exame". Nas rotas
  `/analises`, são **da fatia enviada** (ver abaixo).

## Modos (variável `API_MODO`)

| Modo | `modo` na resposta | De onde vêm os números | Uso |
|---|---|---|---|
| `precalculado` | `pre_calculado` | Resultados **reais** de 3 exames do Teste A, salvos em `pji/api/resultados_precalculados/` | **Demonstração e vídeo** |
| `real` | `modelo_real` | Os três métodos rodando ao vivo sobre os DICOM do HD | Uso completo (precisa do HD) |
| `fixo` (padrão) | `valores_fixos` | Valores **inventados** de `pji/api/dados_exemplo/` | Só para desenvolver a tela |

A tela mostra o modo para quem está vendo saber de onde vêm os números.

O envio de arquivo (`/analises`) funciona **em qualquer modo**. Ele sempre roda os modelos ao
vivo (`modo: "modelo_real"`), com a U-Net oficial (semente 123), que a API carrega em segundo
plano ao subir. Não precisa do HD.

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

### `POST /analises`

Recebe **uma fatia de tomografia** enviada pela tela e roda os três métodos nela, ao vivo. O
arquivo vai no campo `arquivo` de um formulário `multipart/form-data`, com até 30 MB.

```
curl -F "arquivo=@fatia.png" http://localhost:8000/analises
```

| Formato | Como a API lê |
|---|---|
| `.dcm` | Fatia DICOM, já em HU. Passa pelo pré-processamento do treino: limpeza, filtro gaussiano e reamostragem para 1 mm. |
| `.png`, `.jpg`, `.jpeg` | Imagem em tons de cinza. **Não guarda HU**: o cinza é convertido de volta supondo a janela de −1000 a 400 HU, a mesma das fatias desta API e da entrada da U-Net. A área supõe 1 mm por pixel. |

Resposta real, para a fatia do exame 808059 que a própria API serve:

```json
{
  "analise_id": "b463c9c32c40",
  "arquivo": "tomografia_808059_pior_caso_baseline.png",
  "tipo": "imagem",
  "modo": "modelo_real",
  "gabarito": "teste-a-808059",
  "avisos": [
    "Imagem PNG/JPG não guarda valores Hounsfield: os tons de cinza foram convertidos supondo a janela de −1000 a 400 HU (a mesma das fatias do sistema).",
    "Área calculada supondo 1 mm por pixel (o tamanho das fatias do sistema)."
  ],
  "fatia": {"largura": 281, "altura": 281, "url": "/analises/b463c9c32c40/fatia.png"},
  "metodos": {
    "baseline": {
      "metricas": {"dice": 0.5288, "iou": 0.3595, "precisao": 0.9995, "revocacao": 0.3595,
                   "area_pulmonar_cm2": 36.7, "fracao_da_imagem": 0.0465, "tempo_ms": 5},
      "mascara": {"url": "/analises/b463c9c32c40/baseline/mascara.png"}
    },
    "region_growing": {
      "metricas": {"dice": 0.7057, "iou": 0.5452, "precisao": 0.9996, "revocacao": 0.5453,
                   "area_pulmonar_cm2": 55.7, "fracao_da_imagem": 0.0705, "tempo_ms": 6},
      "mascara": {"url": "/analises/b463c9c32c40/region_growing/mascara.png"}
    },
    "unet": {
      "metricas": {"dice": 0.9733, "iou": 0.9479, "precisao": 0.9856, "revocacao": 0.9612,
                   "area_pulmonar_cm2": 99.5, "fracao_da_imagem": 0.126, "tempo_ms": 33},
      "mascara": {"url": "/analises/b463c9c32c40/unet/mascara.png"}
    }
  }
}
```

- **`gabarito`**: se a fatia enviada for idêntica a uma das fatias do modo pré-calculado, a API
  usa a máscara de referência do LUNA16 dela e calcula Dice, IoU, precisão e revocação. Para
  qualquer outra imagem, `gabarito` é `null` e essas quatro métricas também são `null`: sem
  gabarito não há com o que comparar. A tela mostra então a área de pulmão.
- **`avisos`**: textos para a tela mostrar. Por exemplo, PNG sem HU, área suposta, ou quase
  nenhum pulmão encontrado (menos de 1% da imagem pela U-Net). Não há verificação de que a imagem
  é mesmo uma TC de tórax.
- **Uma fatia não é um exame.** A U-Net é 2D, então na fatia isolada dá o mesmo resultado que no
  exame inteiro: no exemplo acima, 0,9733 nos dois. O baseline e o region growing usam
  conectividade 3D, e com uma fatia só o resultado deles muda. No mesmo exemplo, o exame 3D dá
  0,719 e 0,585 nessa fatia. **Esses números não se comparam com a tabela do artigo.**
- A API guarda na memória só as últimas 30 análises.

### `GET /analises/{analise_id}`

Repete a resposta de `POST /analises`.

### `GET /analises/{analise_id}/fatia.png`

A fatia enviada, em PNG (no caso do DICOM, na janela de −1000 a 400 HU e a 1 mm).

### `GET /analises/{analise_id}/{metodo}/mascara.png`

A máscara do método na fatia enviada, em PNG, do mesmo tamanho da fatia.

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
| 400 | `arquivo_vazio` / `arquivo_invalido` | `POST /analises`: arquivo vazio ou imagem/DICOM que não abre |
| 413 | `arquivo_grande` | `POST /analises`: arquivo maior que 30 MB |
| 415 | `formato_nao_suportado` | `POST /analises`: extensão diferente de `.png`, `.jpg`, `.jpeg` e `.dcm` |
| 404 | `analise_inexistente` | `GET /analises/...`: id que não existe ou que já saiu da memória |
| 503 | `modelo_indisponivel` | `POST /analises`: pesos da U-Net não encontrados |

## Quem fez o quê

| Parte | Quem |
|---|---|
| API (FastAPI), modos fixo e real, testes | Rafael |
| Tela (React + Vite) | Érica |
| Ligação da tela com a API, modo pré-calculado e métodos da API iguais aos do artigo | Amabilly |
| Envio de arquivo (`POST /analises`) na API e na tela | Amabilly |
| U-Net oficial (semente 123) usada pela API | Roger |
