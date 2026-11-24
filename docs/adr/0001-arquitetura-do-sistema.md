# 0001 - Separar o sistema em pipeline de experimentos, API e tela

Status: Aceito
Data: 2026-10-05 (revisado em 2026-11-23)

## Contexto

O projeto precisava de duas coisas ao mesmo tempo:

- **Um resultado científico conferível**: três métodos avaliados em centenas de exames, com
  intervalo de confiança e teste estatístico. Isso exige rodar lotes longos, guardar um CSV
  por exame e repetir a conta sempre que um parâmetro muda.
- **Uma demonstração**: alguém escolhe um exame e vê os três métodos lado a lado. Isso exige
  resposta rápida e uma interface simples.

Os integrantes trabalham em partes diferentes (pipeline, API, tela, U-Net) e em
computadores diferentes. Se tudo ficasse num só lugar, um esperaria o outro.

## Decisão

Dividir o sistema em três partes, ligadas por contratos escritos:

1. **Pipeline de experimentos** (`src/luna16/` e `scripts/`): um pacote Python com
   carregamento, seleção, divisão, pré-processamento, os três métodos e as métricas. Os
   scripts e notebooks importam esse pacote em vez de copiar o código. As saídas são CSVs por
   exame em `data/luna16/`.
2. **API REST** (`pji/`, FastAPI): expõe os exames e a segmentação de cada método. As rotas
   estão em [`docs/contrato_api.md`](../contrato_api.md).
3. **Tela** (`frontend/`, React + Vite): uma página que só conversa com a API, pelo endereço
   em `VITE_API_URL`.

**Revisão de 2026-11-23.** A primeira versão da API tinha uma implementação própria dos
métodos. Nos mesmos exames, ela dava Dice diferente do artigo: o region growing dava 0,980
na API e 0,934 no relatório, o que faria a tela contradizer a hipótese H2. A partir daí, a
API passou a usar **cópias idênticas** dos módulos de `src/luna16/` (em `pji/src/luna16/`), e
um teste automático (`test_metodos_iguais_ao_artigo.py`) confere que as cópias não
divergem.

## Consequências

**Melhora**
- Cada parte é feita e testada sozinha. A tela começou com dados inventados, antes de a API
  e os modelos ficarem prontos.
- O resultado científico não depende da API nem da tela: dá para conferir a tabela oficial
  só com os CSVs.
- A tela mostra os mesmos números do artigo, e o teste avisa se alguém mudar um lado sem o
  outro.

**Piora**
- Há código duplicado (`src/luna16/` e `pji/src/luna16/`). Uma correção precisa ser copiada
  para os dois lugares; o teste pega o esquecimento, mas não o evita.
- São três formas de instalar e rodar (Python, API e Node.js), o que deixa o README mais
  longo.
- O contrato da API precisa ser mantido em dia. A primeira versão descrevia rotas que nunca
  foram implementadas e teve de ser reescrita (versão 2.0).
