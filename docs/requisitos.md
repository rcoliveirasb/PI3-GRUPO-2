# Requisitos do sistema — Pulmo Scan (PI3-GRUPO-2)

O que o sistema deve fazer e como deve se comportar. O sistema tem três partes: o
**pipeline de experimentos** (`src/luna16/` e `scripts/`), a **API** (`pji/`) e a **tela**
(`frontend/`). As decisões técnicas por trás destes requisitos estão nos [ADRs](adr/).

**Prioridade**
- **Alta**: sem isso, o projeto não responde à pergunta de pesquisa ou não pode ser
  conferido.
- **Média**: importante para usar ou demonstrar, mas o resultado científico continua de pé
  sem isso.
- **Baixa**: complemento ou extensão.

A coluna "Onde está" aponta o código ou o documento que atende ao requisito.

---

## Requisitos funcionais (RF)

O que o sistema faz.

### Dados e processamento

| ID | Requisito | Prioridade | Onde está |
|---|---|---|---|
| RF-01 | O sistema carrega exames de TC do LUNA16 (`.mhd`/`.raw`) e as máscaras de referência, com os valores em unidades de Hounsfield (HU). | Alta | `src/luna16/io.py` |
| RF-02 | O sistema seleciona os exames pelos critérios de inclusão e os divide em treino, validação e teste por paciente. | Alta | `src/luna16/selection.py`, `src/luna16/splits.py`, `scripts/regenerate_split_70_15_15.py` |
| RF-03 | O usuário pode baixar um subset do LUNA16 pelo Kaggle com um comando, informando o número do subset. | Média | `scripts/download_luna16_subset.py` |
| RF-04 | O sistema segmenta o pulmão pelo **baseline**: limiar de −600 HU mais operações morfológicas. | Alta | `src/luna16/baseline.py` |
| RF-05 | O sistema segmenta o pulmão por **region growing**, com sementes de ar dentro do tórax (abaixo de −750 HU). | Alta | `src/luna16/region_growing.py` |
| RF-06 | O sistema treina uma **U-Net 2D** e segmenta o pulmão com ela, removendo componentes fora do tórax. | Alta | `src/luna16/unet.py`, `colab_treinar_unet.ipynb` |

### Avaliação

| ID | Requisito | Prioridade | Onde está |
|---|---|---|---|
| RF-07 | Para cada exame e método, o sistema calcula Dice, IoU, sensibilidade, precisão e tempo, e salva um CSV com uma linha por exame. | Alta | `src/luna16/metrics.py`, `scripts/run_sprint4_evaluation.py`, `scripts/run_unet_evaluation.py` |
| RF-08 | O sistema calcula a média de cada métrica com IC95% por bootstrap e compara os métodos em pares (Wilcoxon unilateral, correção de Holm). | Alta | `scripts/run_final_results.py`, `src/luna16/hipotese.py` |
| RF-09 | O usuário pode recalcular a tabela oficial só a partir dos CSVs do repositório, sem baixar as tomografias. | Alta | `scripts/run_final_results.py` (README, passo 4.2) |
| RF-10 | O sistema roda as 5 etapas do KDD em ordem, com um comando, salva a evidência de cada etapa e termina com o teste das hipóteses H1, H2 e H3. | Alta | `scripts/pipeline_kdd.py`, `data/luna16/kdd/` |
| RF-11 | O sistema gera as análises de falha: piores casos, traqueia marcada como pulmão e nódulos apagados pela máscara. | Média | `scripts/analise_traqueia.py`, `scripts/analise_nodulos_apagados.py`, `docs/piores_casos/` |
| RF-12 | O sistema gera as figuras e tabelas usadas no relatório e no resumo expandido. | Baixa | `scripts/gerar_figura_*.py`, `scripts/run_final_results.py` |

### API

| ID | Requisito | Prioridade | Onde está |
|---|---|---|---|
| RF-13 | A API informa se está no ar e em qual modo está (`GET /saude`). | Média | `pji/api/main.py` |
| RF-14 | A API lista os exames disponíveis, com identificador, nome, número de fatias e fatia de exemplo (`GET /exames`). | Alta | `pji/api/main.py` |
| RF-15 | A API segmenta um exame com o método pedido (`baseline`, `region_growing` ou `unet`) e devolve Dice, IoU, volume, tempo e os endereços das imagens (`GET /exames/{id}/segmentacao/{metodo}`). | Alta | `pji/api/main.py`, `docs/contrato_api.md` |
| RF-16 | A API devolve a fatia de exemplo e a máscara de cada método em PNG. | Alta | `pji/api/main.py`, `pji/api/png.py` |
| RF-17 | A API funciona em três modos, escolhidos pela variável `API_MODO`: `fixo`, `precalculado` e `real`. | Média | `pji/api/main.py`, `pji/api/servicos/` |
| RF-18 | Quando o pedido é inválido, a API responde com um código HTTP e um JSON com `codigo` e `mensagem` (404 exame inexistente, 400 método inválido, 409 exame não baixado). | Média | `pji/api/erros.py` |
| RF-26 | A API recebe uma fatia de tomografia enviada (`.png`, `.jpg` ou `.dcm`, até 30 MB) e roda os três métodos nela, ao vivo, com a U-Net treinada, em qualquer modo (`POST /analises`). Devolve as máscaras, a área de pulmão e o tempo, e Dice e IoU quando a fatia tem gabarito. | Alta | `pji/api/analise_upload.py`, `pji/api/main.py`, `docs/contrato_api.md` |

### Tela

| ID | Requisito | Prioridade | Onde está |
|---|---|---|---|
| RF-19 | O usuário escolhe um exame do servidor e inicia a segmentação com um botão. Os três métodos rodam em paralelo. | Alta | `frontend/src/App.jsx`, `frontend/src/api.js` |
| RF-20 | A tela mostra os três métodos lado a lado, com a máscara de cada um pintada sobre a mesma fatia. | Alta | `frontend/src/Sobreposicao.jsx` |
| RF-21 | A tela mostra uma tabela com Dice, IoU, volume e tempo de cada método no exame inteiro. | Alta | `frontend/src/App.jsx` |
| RF-22 | A tela mostra um selo com o modo da API, para que valores inventados não sejam confundidos com resultados reais. | Alta | `frontend/src/App.jsx` |
| RF-23 | O usuário pode salvar o resultado da segmentação em JSON. | Baixa | `frontend/src/App.jsx` |
| RF-24 | A tela avisa quando a API está fora do ar ou quando a segmentação falha. | Média | `frontend/src/App.jsx` |
| RF-27 | O usuário envia uma imagem de tomografia pela tela (botão ou arrastando) e vê os três métodos aplicados a ela, com os avisos da API sobre as suposições feitas. | Alta | `frontend/src/App.jsx`, `frontend/src/api.js` |

### Extensão

| ID | Requisito | Prioridade | Onde está |
|---|---|---|---|
| RF-25 | O sistema detecta candidatos a nódulo dentro do pulmão segmentado e reduz os falsos positivos com um classificador (extensão exploratória, fora do escopo formal). | Baixa | `sprint7_deteccao_nodulos_grp2.ipynb`, `scripts/run_nodule_evaluation.py` |

---

## Requisitos não funcionais (RNF)

Qualidades do sistema, cada uma com um número que pode ser conferido. A coluna "Medido"
traz o valor obtido no projeto.

| ID | Requisito | Prioridade | Medido |
|---|---|---|---|
| RNF-01 | **Reprodutibilidade**: recalcular a tabela oficial a partir dos CSVs versionados gera CSVs 100% idênticos aos do repositório. | Alta | Idênticos (`git status` sem mudança nos CSVs), conferido em 23/11/2026 |
| RNF-02 | **Conferência rápida**: a tabela oficial é recalculada em até 30 s numa máquina comum, sem GPU e sem as tomografias. | Alta | ~10 s |
| RNF-03 | **KDD completo**: as 5 etapas rodam em até 2 min com os subsets 0 e 1. | Média | 59 s |
| RNF-04 | **Tempo de segmentação**: cada método segmenta um exame inteiro em até 15 s, em CPU. | Média | 6,3 s (baseline), 8,0 s (region growing) e 7,1 s (U-Net) por exame, nos 107 exames; máquina não registrada no CSV |
| RNF-05 | **Sem GPU**: avaliação, API e tela rodam só com CPU. A GPU é usada apenas no treino da U-Net. | Alta | Atendido; treino no Google Colab |
| RNF-06 | **Resposta da API** no modo `precalculado`: cada rota responde em até 1 s. | Média | No máximo 0,005 s em 21 requisições (cliente de teste, 23/11/2026) |
| RNF-07 | **Estabilidade da U-Net**: a diferença de Dice entre duas sementes de treino é de no máximo 0,005. | Média | 0,9837 ± 0,0004 |
| RNF-08 | **Testes da API**: 100% dos testes automáticos passam. Os que precisam das tomografias são pulados quando elas não estão na máquina. | Alta | 42 passaram e 5 foram pulados (pytest, 28/11/2026) |
| RNF-09 | **Versões congeladas**: 100% das bibliotecas Python do pipeline têm versão exata no `requirements.txt`, e as da tela estão travadas no `package-lock.json`. | Alta | Atendido |
| RNF-10 | **Portabilidade**: roda no Windows, Linux e Mac, com Python 3.11 ou mais novo e Node.js 20.19, 22.12 ou mais novo. | Média | Testado no Windows 11 com Python 3.13 e Node.js 26 |
| RNF-11 | **Instalação**: quem segue só o README tem a API e a tela no ar em até 15 min, sem precisar dos dados (modo `precalculado`). | Alta | Passos 4.1, 4.3 e 4.4 do README |
| RNF-12 | **Tamanho do repositório**: nenhuma tomografia no Git. Os volumes (~12 GB por subset) ficam fora do repositório e são obtidos pelo Kaggle ou pelo Drive. | Alta | Atendido (`.gitignore`) |
| RNF-13 | **Privacidade**: 0 dados pessoais de pacientes no repositório e na tela. Os exames do LUNA16 são anonimizados, e os nomes de pacientes da tela são fictícios. | Alta | Atendido |
| RNF-14 | **Qualidade do código da tela**: o lint (`npm run lint`) termina com 0 erros, e o build de produção gera menos de 500 KB de JavaScript. | Baixa | 0 erros; 239 KB (74 KB compactado) |

---

## Requisitos de domínio (RD)

Regras que vêm da área de imagem médica e da metodologia científica, e que valem para
qualquer parte do sistema.

| ID | Regra | Prioridade |
|---|---|---|
| RD-01 | A divisão em treino, validação e teste é feita **por paciente**, nunca por fatia: fatias vizinhas do mesmo exame são quase iguais, e separá-las vazaria informação do teste para o treino. A proporção é 70/15/15, com semente 42. | Alta |
| RD-02 | O conjunto de teste **não é usado** para treinar a U-Net nem para ajustar parâmetros dos métodos clássicos. | Alta |
| RD-03 | A unidade de avaliação é o **exame** (Dice 3D sobre o volume inteiro), e não a fatia. | Alta |
| RD-04 | A segmentação é avaliada por métricas de **sobreposição** (Dice e IoU). Acurácia e Kappa não são usadas: o pulmão ocupa só ~10 a 15% do volume, e uma máscara vazia teria acurácia alta e Dice 0. | Alta |
| RD-05 | **Metas**: Dice ≥ 0,85 para os métodos clássicos e ≥ 0,75 para a U-Net; IoU ≥ 0,75. | Alta |
| RD-06 | Toda média é apresentada com **IC95% por bootstrap** (no mínimo 500 reamostras; o projeto usa 10.000), nunca como um número sozinho. | Alta |
| RD-07 | Diferenças entre métodos são testadas com **teste pareado** sobre os mesmos exames (Wilcoxon unilateral, correção de Holm, α = 0,05), com H0 e H1 escritas antes. | Alta |
| RD-08 | A referência é a máscara oficial do LUNA16 (`seg-lungs-LUNA16`). Os rótulos 3 e 4 são pulmão; o rótulo 5 (traqueia) não é. | Alta |
| RD-09 | Os exames seguem os critérios do LUNA16: espessura de corte de até 3 mm e nódulos anotados de 3 mm ou mais. O grupo exige ainda espaçamento entre fatias de até 2,5 mm (`docs/criterios_inclusao.md`). | Média |
| RD-10 | **Falso negativo custa mais que falso positivo**: uma parte do pulmão fora da máscara pode apagar um nódulo. Por isso, a sensibilidade é sempre relatada junto com o Dice, e o pior exame de cada método é analisado. | Média |
| RD-11 | Os parâmetros dos métodos clássicos (limiar de −600 HU, limiar da semente, tamanho do elemento estruturante) são fixos e documentados. | Média |
| RD-12 | Valores **inventados** (modo `fixo` da API) nunca são apresentados como resultado. A tela mostra sempre o modo da API. | Alta |
| RD-13 | O sistema **não é um dispositivo médico**. Nenhuma tela ou documento sugere uso para diagnóstico. | Alta |
| RD-14 | A API usa **o mesmo código** dos experimentos do relatório, para que a tela mostre os mesmos números do artigo. Um teste confere que as cópias são idênticas. | Alta |
