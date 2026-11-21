# Contrato da API (Pulmo Scan)

Formato combinado entre a API (Rafael), a tela (Ruan e Herbe) e a inferência (Roger). Pedido
na orientação 5 do feedback da Sprint 4: com o formato por escrito, a tela e a API avançam
sem esperar uma pela outra. **Se algo aqui mudar, quem mudou atualiza este arquivo e avisa
os outros dois.**

## Meta mínima antes do Checkpoint 3

Escolher um exame → a API devolve as três máscaras → a tela mostra os três métodos lado a
lado.

Pode começar com **valores fixos**: um exame de demonstração e algumas fatias salvas em
arquivo. Os dados reais entram depois sem mudar o formato.

## Convenções

- **Base:** `http://localhost:8000`. Tudo em JSON, UTF-8, nomes de campo em português sem
  acento.
- **Fatia:** corte axial no espaço já reamostrado para 1 mm isotrópico, o mesmo do pipeline
  (`run_pipeline_for_uid`). `z` vai de `0` a `n_fatias - 1`, de baixo (pés) para cima
  (cabeça).
- **Imagens:** PNG em base64, sem o prefixo `data:`.
  - TC: tons de cinza em janela de pulmão, de −1000 a 400 HU, como `normalize_for_display`.
  - Máscaras: PNG de 1 canal, 0 = fora e 255 = pulmão, do mesmo tamanho da TC.
- **Métodos:** `baseline`, `region_growing`, `unet`. A `referencia` (máscara do LUNA16)
  também vem, para a tela poder mostrar onde cada método erra.
- **Dice:** é o Dice **do exame inteiro**, lido dos CSVs de avaliação, e não calculado na
  fatia. A tela deve escrever "Dice do exame".

## Endpoints

### `GET /saude`

```json
{"status": "ok", "versao_contrato": "1.0"}
```

### `GET /exames`

Lista os exames de demonstração.

```json
[
  {
    "uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.109002525524522225658609808059",
    "rotulo": "Pior caso do baseline",
    "conjunto": "Teste A",
    "n_fatias": 312
  }
]
```

### `GET /exames/{uid}`

Resumo do exame, com o Dice de cada método.

```json
{
  "uid": "1.3.6...808059",
  "rotulo": "Pior caso do baseline",
  "conjunto": "Teste A",
  "n_fatias": 312,
  "largura": 340,
  "altura": 260,
  "dice_exame": {"baseline": 0.8468, "region_growing": 0.7790, "unet": 0.9671}
}
```

### `GET /exames/{uid}/fatias/{z}`

Uma fatia com a TC e as quatro máscaras. É o que a tela chama ao mover o seletor de fatia.

```json
{
  "uid": "1.3.6...808059",
  "z": 156,
  "tc_png": "<base64>",
  "mascaras_png": {
    "referencia": "<base64>",
    "baseline": "<base64>",
    "region_growing": "<base64>",
    "unet": "<base64>"
  }
}
```

### Erros

Código HTTP mais JSON `{"erro": "<mensagem>"}`:
- `404`: exame ou fatia inexistente;
- `500`: falha na inferência.

## Quem faz o quê

| Parte | Responsável | Começa com |
|---|---|---|
| API (FastAPI) com estes endpoints | Rafael | Valores fixos: um exame, algumas fatias em PNG salvas em pasta |
| Tela consumindo estes endpoints | Ruan e Herbe | Um JSON de exemplo copiado deste arquivo, sem esperar a API |
| Inferência real (`src/luna16/inference.py`) que gera TC e máscaras de uma fatia | Roger | Funções que já existem: `segment_baseline`, `segment_region_growing`, `segment_with_unet` |
| Exames de demonstração (incluindo um caso de falha) | Herbe | Exames já analisados em `docs/piores_casos/` |

**Evidência para a próxima sprint** (pedido do professor ao Rafael): um print da API
respondendo `GET /exames/{uid}/fatias/{z}`, mesmo com valores fixos.

## Dúvidas em aberto

- **Desempenho:** gerar as três máscaras de um exame leva de ~10 a ~25 s por método em CPU.
  Sugestão: pré-calcular as máscaras dos exames de demonstração e servir do disco, em vez de
  segmentar a cada pedido.
- **U-Net:** qual a API vai servir, a antiga (`unet_baseline.pt`, 124 exames) ou a nova (479
  exames)? Depende de os pesos novos estarem no repositório.
