# PI3-GRUPO-2 — Segmentação do Parênquima Pulmonar em TC

Projeto Integrador III, Grupo 02. Repositório: https://github.com/rcoliveirasb/PI3-GRUPO-2
(branch `main`).

**Sumário**
1. [Nome e descrição](#1-nome-e-descrição)
2. [Funcionalidades principais](#2-funcionalidades-principais)
3. [Tecnologias usadas](#3-tecnologias-usadas)
4. [Como instalar e executar](#4-como-instalar-e-executar)
5. [Equipe e papéis](#5-equipe-e-papéis)
6. [Requisitos, ADRs e outros documentos](#6-requisitos-adrs-e-outros-documentos)

---

## 1. Nome e descrição

**Pulmo Scan: segmentação automática do parênquima pulmonar em tomografias de tórax.**

**O problema.** Antes de qualquer análise automática de nódulos pulmonares, o pulmão
(parênquima) precisa ser separado das estruturas vizinhas: coração, costelas, mediastino,
traqueia. Fazer isso à mão, fatia por fatia, é lento. Os algoritmos que funcionam bem em
laboratório nem sempre se mantêm em exames de equipamentos diferentes. Se a máscara do
pulmão deixar uma parte de fora, um nódulo nessa região some antes mesmo de ser procurado.

**O que o projeto faz.** Compara três formas de segmentar o pulmão em tomografias
computadorizadas (TC) do dataset público [LUNA16](https://luna16.grand-challenge.org/):

| Método | Ideia |
|---|---|
| Baseline | Limiar fixo de −600 HU (escala de Hounsfield) mais operações morfológicas |
| Region growing | Cresce a região a partir de sementes de ar dentro do tórax (abaixo de −750 HU) |
| U-Net 2D | Rede neural treinada fatia a fatia em 497 exames |

Cada método é medido contra as máscaras de referência oficiais do LUNA16 (Dice e IoU, com
intervalo de confiança de 95% por bootstrap e teste estatístico pareado). Uma API e uma
tela web mostram os três resultados lado a lado num mesmo exame.

**Para quem.**
- Pesquisadores e estudantes de visão computacional em imagens médicas, que precisam de
  uma comparação reprodutível entre métodos clássicos e aprendidos.
- Equipes que vão construir detecção de nódulos e precisam escolher a etapa de
  segmentação.
- Os avaliadores da disciplina, que conferem os resultados a partir dos arquivos do
  repositório.

> **Aviso.** Este é um trabalho acadêmico. **Não é um dispositivo médico** e não deve ser
> usado para diagnóstico.

### Resultados principais

Teste oficial: **107 exames** (`teste_interno` de
[`split_novo.csv`](data/luna16/split_novo/split_novo.csv), divisão 70/15/15 por paciente,
semente 42). Nenhum desses exames estava na primeira fase do projeto. A unidade é o exame
(Dice 3D), e o IC95% vem de bootstrap com 10.000 reamostras.

| Método | Dice [IC95%] | IoU [IC95%] | Sensibilidade | Pior exame | Exames < 0,85 |
|---|---|---|---|---|---|
| Baseline (−600 HU + morfologia) | 0,9492 [0,9336; 0,9604] | 0,9095 [0,8892; 0,9246] | 0,934 | 0,381 | 3 |
| Region growing | 0,9353 [0,9201; 0,9479] | 0,8855 [0,8645; 0,9034] | 0,901 | 0,530 | 6 |
| U-Net 2D (semente 123, 497 exames de treino) | **0,9838** [0,9827; 0,9847] | **0,9681** [0,9660; 0,9698] | 0,983 | 0,955 | 0 |

- **H1 (meta de Dice):** confirmada nos três métodos.
- **H2 (region growing melhor que o baseline):** refutada. A diferença foi de −0,0139
  [−0,0282; −0,0004], no sentido oposto ao previsto.
- **H3 (U-Net melhor que os clássicos):** confirmada. A U-Net foi melhor nos 107 exames.
- Com duas sementes de treino, a U-Net dá 0,9837 ± 0,0004 de Dice.

A tabela completa, com unidade, semente, commit e arquivo de origem de cada número, e o
histórico do Teste A (26 exames), está em
[`docs/tabela_experimentos.md`](docs/tabela_experimentos.md). As hipóteses estão em
[`docs/hipotese.md`](docs/hipotese.md).

---

## 2. Funcionalidades principais

- **Três métodos de segmentação** do pulmão sobre o mesmo exame: baseline, region growing e
  U-Net 2D.
- **Avaliação contra a referência oficial**: Dice, IoU, sensibilidade, precisão e tempo por
  exame, salvos em CSV, um por método.
- **Estatística**: IC95% por bootstrap e comparação pareada entre os métodos (Wilcoxon
  unilateral, correção de Holm).
- **Processo KDD num comando só**: as 5 etapas (seleção, pré-processamento, transformação,
  mineração, interpretação) rodam em ordem, salvam a evidência de cada etapa e terminam com
  o teste das hipóteses.
- **Conferência sem baixar dados**: a tabela oficial é recalculada a partir dos CSVs do
  repositório em cerca de 10 segundos.
- **API REST** (FastAPI) que lista os exames e devolve, por método, a máscara em PNG e as
  métricas. Tem três modos: `fixo` (valores inventados, só para testar a tela),
  `precalculado` (resultados reais de 3 exames, sem precisar dos dados) e `real` (modelos
  rodando ao vivo).
- **Tela web (Pulmo Scan)**: escolhe um exame, roda os três métodos, mostra as máscaras
  sobre a fatia lado a lado com a tabela de Dice, IoU, volume e tempo, e salva o resultado
  em JSON. Um selo no rodapé diz de qual modo da API vêm os números.
- **Análises de falha**: piores casos, traqueia marcada como pulmão e nódulos apagados pela
  máscara (pastas `docs/piores_casos/` e `docs/traqueia/`).
- **Extensão exploratória, fora do escopo formal**: detecção de nódulos dentro do pulmão
  segmentado ([`sprint7_deteccao_nodulos_grp2.ipynb`](sprint7_deteccao_nodulos_grp2.ipynb);
  seção 8 do [relatório](RELATORIO_FINAL_RASCUNHO.md)).

---

## 3. Tecnologias usadas

| Parte | Tecnologia | Versão |
|---|---|---|
| Linguagem do processamento e da API | Python | 3.11 ou mais novo (testado no 3.13) |
| Leitura das tomografias (`.mhd`/`.raw`) | SimpleITK | 2.5.8 |
| Processamento de imagem | NumPy, SciPy, scikit-image | 2.5.5, 1.18.1, 0.26.0 |
| Rede neural (U-Net 2D) | PyTorch | 2.15.0 (CPU; treino com GPU no Google Colab) |
| Tabelas e estatística | pandas, scikit-learn, SciPy | 3.1.1, 1.9.1, 1.18.1 |
| Gráficos | Matplotlib | 3.11.2 |
| Notebooks | Jupyter (ipykernel, nbconvert) | 7.4.0, 7.17.2 |
| Download dos dados | API do Kaggle | 2.2.5 |
| API | FastAPI + Uvicorn | ver [`pji/api/requirements.txt`](pji/api/requirements.txt) |
| Testes da API | pytest + httpx | pytest de 8.0 até antes do 9.2 |
| Tela | React + Vite | React 19.3, Vite 8.3 |
| Lint da tela | ESLint | 10.15 |
| Dados | LUNA16 (derivado do LIDC-IDRI) | 888 exames |
| Organização | Git + GitHub, Trello | — |

As versões exatas do Python estão em [`requirements.txt`](requirements.txt) e as da tela, em
[`frontend/package-lock.json`](frontend/package-lock.json). As escolhas estão justificadas
nos [ADRs](docs/adr/).

---

## 4. Como instalar e executar

Os passos seguem a ordem abaixo. Cada um diz o que precisa ter antes.

| Passo | O que faz | Precisa de | Tempo |
|---|---|---|---|
| 4.1 Instalar | Ambiente Python com as versões congeladas | Python 3.11+ e Git | ~5 min |
| 4.2 Conferir os resultados | Recalcula a tabela oficial a partir dos CSVs do repositório | Só o 4.1 (não precisa das tomografias) | ~10 s |
| 4.3 Rodar a API | Sobe a API que segmenta com os três métodos | 4.1; no modo real, as tomografias | ~1 min |
| 4.4 Abrir a tela | Interface web que consome a API | Node.js 20.19 ou 22.12 em diante (testado no 26) e a API rodando | ~2 min |
| 4.5 Refazer tudo do zero | Baixa os dados, avalia os três métodos e roda o KDD | Token do Kaggle e ~25 GB livres | horas |

Os comandos estão no PowerShell do Windows. No Linux ou no Mac, troque
`.venv\Scripts\activate` por `source .venv/bin/activate` e `$env:API_MODO="precalculado";`
por `API_MODO=precalculado`.

### 4.1 Instalar

```
git clone https://github.com/rcoliveirasb/PI3-GRUPO-2.git
cd PI3-GRUPO-2
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r pji/api/requirements.txt
```

Se o `pip` não conseguir instalar o `torch`, instale a versão para CPU:

```
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**No Windows, use uma pasta de caminho curto** (por exemplo, `C:\PI3-GRUPO-2`). O `torch`
tem arquivos com caminhos muito longos, e numa pasta funda a instalação falha com
`OSError: [Errno 2] No such file or directory` ou com `DLL load failed` ao importar. A outra
saída é ativar os caminhos longos do Windows
([instruções](https://pip.pypa.io/warnings/enable-long-paths)) e reinstalar.

### 4.2 Conferir os resultados sem baixar nada

Recalcula, a partir dos CSVs por exame já versionados, a tabela oficial dos 107 exames, com
IC95% e o teste pareado:

```
python scripts/run_final_results.py --split data/luna16/split_novo/split_novo.csv --conjunto teste_interno --sufixo _novo
```

Saída: `data/luna16/tabela_resultados_finais_novo.csv` e
`data/luna16/comparacao_pareada_final_novo.csv`. Os dois CSVs devem sair idênticos aos do
repositório (`git status` não mostra mudança neles). Os dois gráficos `.png` são regravados
e podem aparecer como modificados.

Para rodar as 5 etapas do KDD e o teste das hipóteses (~1 min):

```
python scripts/pipeline_kdd.py
```

As etapas 1 a 4 precisam dos subsets 0 e 1 do LUNA16 (passo 4.5). A etapa 5 roda só com os
CSVs.

### 4.3 Rodar a API

Os comandos rodam de dentro de `pji/`, com o ambiente do passo 4.1 ativado:

```
cd pji
$env:API_MODO="precalculado"; uvicorn api.main:app
```

- A API fica em http://127.0.0.1:8000, e a documentação interativa, em
  http://127.0.0.1:8000/docs.
- **Modos** (variável `API_MODO`):
  - `precalculado`: 3 exames reais do Teste A (o pior caso do baseline, o pior caso do region
    growing e um caso típico), processados pelo mesmo código do relatório e pela U-Net
    oficial. Não precisa dos dados. **Use este na demonstração.**
  - `real`: modelos rodando ao vivo. Precisa das tomografias; a pasta é definida por
    `API_RAIZ_DATASET`.
  - `fixo` (padrão, sem a variável): valores **inventados**, só para testar a tela.
- Testes da API: `python -m pytest` (37 passam e 5 são pulados quando as tomografias não
  estão na máquina).
- Rotas e formatos: [`docs/contrato_api.md`](docs/contrato_api.md). Mais detalhes em
  [`pji/README.md`](pji/README.md) e [`pji/api/README.md`](pji/api/README.md).

### 4.4 Abrir a tela (Pulmo Scan)

Com a API do passo 4.3 rodando, abra outro terminal na raiz do repositório:

```
cd frontend
npm install
npm run dev
```

- Abra http://localhost:5173.
- Em "Tomografia do servidor (LUNA16)", escolha um exame e clique em **Iniciar segmentação**.
  A tela mostra os três métodos lado a lado, com a máscara sobre a fatia e a tabela de Dice,
  IoU, volume e tempo do exame inteiro.
- O selo no rodapé diz de onde vêm os números. No modo `precalculado`, aparece "Resultados
  reais pré-calculados".
- A tela procura a API em `http://localhost:8000`. Para outro endereço, defina a variável
  `VITE_API_URL` antes do `npm run dev`.

### 4.5 Refazer tudo do zero

**Como obter os dados**
- **Primeira fase (177 exames):** subsets 0 e 1 do LUNA16, pelo Kaggle (comandos abaixo).
- **Base completa (888 exames):** baixe os subsets de 0 a 9 com o mesmo script, ou use a
  cópia do grupo no Google Drive: `backup_ct_preparados.zip` (exames pré-processados),
  `backup_mascaras.zip` (máscaras) e `backup_modelos_pesos.zip` (divisões e pesos das duas
  sementes), na
  [pasta compartilhada do grupo](https://drive.google.com/drive/folders/1FcWoRA4wSeGs4lUr_ZM628Ic9JkJSWz3).
- **Pesos da U-Net oficial** (semente 123): já estão no repositório, em
  `pji/modelos/unet_seed123/unet_novo_final.pt`.

**Passos**
1. Registrar o kernel Jupyter (uma vez só) e selecioná-lo em cada notebook:
   ```
   python -m ipykernel install --user --name=pi3-grupo2 --display-name="Python (PI3-GRUPO-2)"
   ```
2. Baixar os dados do LUNA16 (89 pacientes por subset, mais as máscaras de referência).
   Precisa de um token de API do Kaggle salvo em `~/.kaggle/access_token` (gerado em
   [kaggle.com/settings](https://www.kaggle.com/settings) → API → Create New Token). Cada
   subset ocupa ~12 GB em `data/luna16/`, pasta fora do Git.
   ```
   python scripts/download_luna16_subset.py 0
   python scripts/download_luna16_subset.py 1
   ```
3. Gerar a divisão treino/validação/teste (70/15/15 por paciente):
   ```
   python scripts/regenerate_split_70_15_15.py
   ```
4. Avaliar o baseline e o region growing no teste (~15 a 20 min; pode ser interrompido e
   retomado):
   ```
   python scripts/run_sprint4_evaluation.py
   ```
5. Treinar e avaliar a U-Net 2D. O recomendado é o Google Colab com GPU: suba o
   [`colab_treinar_unet.ipynb`](colab_treinar_unet.ipynb) e siga as células. Em CPU:
   ```
   python scripts/train_unet_baseline.py
   python scripts/run_unet_evaluation.py
   ```
6. Rodar o KDD completo: `python scripts/pipeline_kdd.py`.
7. Abrir os notebooks na ordem da tabela abaixo.

**Sementes**
- Semente 42 na divisão por paciente, no bootstrap e no sorteio de fatias.
- Treino da U-Net oficial com a semente 123. A semente 42 foi usada para medir a variação.

### Mapa do repositório

| Pasta ou arquivo | O que tem |
|---|---|
| [`src/luna16/`](src/luna16/) | Pacote Python com carregamento, seleção, divisão, pré-processamento, os três métodos e as métricas. Os notebooks e scripts importam daqui. |
| [`scripts/`](scripts/) | Scripts de download, avaliação, KDD, tabelas e figuras |
| [`pji/`](pji/) | API (FastAPI), seus testes e os pesos da U-Net oficial |
| [`frontend/`](frontend/) | Tela Pulmo Scan (React + Vite) |
| [`data/luna16/`](data/luna16/) | CSVs de resultados por exame, divisões e evidências do KDD (os volumes ficam fora do Git) |
| [`docs/`](docs/) | Requisitos, ADRs, hipótese, KDD, contrato da API, tabelas e análises |

### Notebooks (ordem de execução)

| Notebook | O que faz | Depende de |
|---|---|---|
| [`sprint2_hu_eda_grp2.ipynb`](sprint2_hu_eda_grp2.ipynb) | EDA da escala de Hounsfield (LIDC-IDRI via TCIA; exploratório, dataset diferente do LUNA16 usado depois) | nada |
| [`sprint3_baseline_luna16_grp2.ipynb`](sprint3_baseline_luna16_grp2.ipynb) | Seleção, divisão por paciente, pré-processamento, baseline e validação piloto | `subset0` |
| [`sprint4_region_growing_grp2.ipynb`](sprint4_region_growing_grp2.ipynb) | Region growing e comparação com o baseline | `subset0` + `subset1` e `run_sprint4_evaluation.py` |
| [`sprint5_falhas_e_reproducibilidade_grp2.ipynb`](sprint5_falhas_e_reproducibilidade_grp2.ipynb) | Métricas secundárias, casos de falha e checklist de reprodutibilidade | resultados do Sprint 4 |
| [`sprint6_resultados_finais_grp2.ipynb`](sprint6_resultados_finais_grp2.ipynb) | Tabela e gráficos finais (IC95%), desempenho × custo | resultados do Sprint 4 |
| [`sprint7_deteccao_nodulos_grp2.ipynb`](sprint7_deteccao_nodulos_grp2.ipynb) | **Extensão fora do escopo formal**: detecção de nódulos | `subset0` + `subset1` e `run_nodule_evaluation.py` |

### Scripts principais

- [`scripts/pipeline_kdd.py`](scripts/pipeline_kdd.py): as 5 etapas do KDD e o teste das hipóteses; saídas em `data/luna16/kdd/`.
- [`scripts/run_final_results.py`](scripts/run_final_results.py): tabela final com IC95% e comparação pareada a partir dos CSVs por exame.
- [`scripts/download_luna16_subset.py`](scripts/download_luna16_subset.py) `N`: baixa o subset N do LUNA16 pelo Kaggle.
- [`scripts/regenerate_split_70_15_15.py`](scripts/regenerate_split_70_15_15.py): gera a divisão 70/15/15 por paciente.
- [`scripts/run_sprint4_evaluation.py`](scripts/run_sprint4_evaluation.py): baseline e region growing no teste (retomável).
- [`scripts/train_unet_baseline.py`](scripts/train_unet_baseline.py) e [`scripts/run_unet_evaluation.py`](scripts/run_unet_evaluation.py): treino e avaliação da U-Net 2D.
- [`scripts/run_nodule_evaluation.py`](scripts/run_nodule_evaluation.py): detecção de nódulos (extensão).
- [`scripts/analise_traqueia.py`](scripts/analise_traqueia.py): quanto da traqueia cada método marca como pulmão.
- [`scripts/gerar_figura_resumo.py`](scripts/gerar_figura_resumo.py): Figura 1 do resumo expandido.

---

## 5. Equipe e papéis

| Integrante | Usuário no GitHub | Papel |
|---|---|---|
| Amabilly Riva Dutra | Amabilly Riva Dutra (Mabynha20) | Coordenação (Trello) e arquitetura. Pipeline de segmentação em `src/luna16/` (baseline e region growing), avaliação com IC95% e teste pareado, processo KDD e hipóteses, ligação da tela com a API e modo pré-calculado, relatório final, resumo expandido e documentação |
| Roger Caldeira de Oliveira | rcoliveirasb, Roger Oliveira | Dono do repositório. Download e guarda do LUNA16 completo (HD externo), migração para os 888 exames, treino da U-Net oficial com duas sementes, avaliação dos três métodos no teste de 107 exames e cópia dos dados no Google Drive |
| Rafael Cassiano Manchini | rodyneyh | Pergunta SMART, definição do problema, README inicial e API (FastAPI) com os modos fixo e real |
| Erica Souza Dos Santos | 11erica006, Erica souza | Telas no Figma e tela Pulmo Scan (React + Vite), slides da banca e comparação com a literatura |
| Ruan Matheus de Souza | RuaanSouza | Análise dos piores casos dos três métodos, inspeção visual de exames e publicação da API no repositório |
| Herbe Fragoso | herbefragoso | Análise dos piores casos, base e gabarito e escolha dos exames de demonstração |

O trabalho foi feito na branch `sprints-3-8` e levado à `main` por Pull Requests, que ficam
registrados no GitHub. A `main` é a versão de entrega.

---

## 6. Requisitos, ADRs e outros documentos

**Pedidos nesta entrega**
- [Requisitos do sistema](docs/requisitos.md): funcionais (RF), não funcionais (RNF) e de
  domínio (RD), com prioridade.
- [Registros de decisão de arquitetura (ADRs)](docs/adr/):
  - [0001 — Arquitetura do sistema](docs/adr/0001-arquitetura-do-sistema.md)
  - [0002 — Linguagem e frameworks](docs/adr/0002-linguagem-e-frameworks.md)
  - [0003 — Armazenamento em arquivos, sem banco de dados](docs/adr/0003-armazenamento-em-arquivos.md)
  - [0004 — Execução local, treino no Colab e modos da API](docs/adr/0004-execucao-e-hospedagem.md)

**Do projeto**
- [`DEFINICAO_DO_PROBLEMA.md`](DEFINICAO_DO_PROBLEMA.md): pergunta SMART e métricas.
- [`docs/hipotese.md`](docs/hipotese.md) e [`docs/kdd.md`](docs/kdd.md): hipóteses e processo KDD.
- [`docs/criterios_inclusao.md`](docs/criterios_inclusao.md): critérios de inclusão, parâmetros e divisão.
- [`docs/contrato_api.md`](docs/contrato_api.md): rotas e formatos da API.
- [`docs/tabela_experimentos.md`](docs/tabela_experimentos.md): todos os números, com origem.
- [`RELATORIO_FINAL_RASCUNHO.md`](RELATORIO_FINAL_RASCUNHO.md): relatório científico final.
- [`docs/resumo_expandido_corrigido.md`](docs/resumo_expandido_corrigido.md): resumo expandido.
- [`docs/perguntas_banca.md`](docs/perguntas_banca.md): perguntas esperadas da banca.

## Dataset e licença

[LUNA16](https://luna16.grand-challenge.org/) (TC em formato MetaImage `.mhd`/`.raw`,
derivado do [LIDC-IDRI](https://www.cancerimagingarchive.net/collection/lidc-idri/)),
baixado pelo mirror público `avc0706/luna16` no Kaggle. Os exames são anonimizados. Licença
do código: [`LICENSE`](LICENSE).
