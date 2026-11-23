# PI3-GRUPO-2 — Segmentação do Parênquima Pulmonar em TC

## Descrição

Investigar e comparar técnicas de segmentação automática do parênquima pulmonar em
imagens de tomografia computadorizada (TC) de tórax, como etapa necessária antes de
qualquer análise de nódulos pulmonares.

> **Nota de correção**: a versão anterior deste README trazia objetivos de
> classificação de nódulos (índice de Kappa, acurácia) que pertencem a outra seção
> do documento geral da disciplina, não ao escopo do Grupo 2. O escopo real do
> Grupo 2 é **segmentação** (não classificação), com Dice Coefficient e IoU como
> métricas — ver Objetivos abaixo.

## Objetivos

A partir de imagens de TC do dataset LUNA16: comparar um baseline clássico
(threshold de Hounsfield Units + morfologia), uma abordagem intermediária
(region growing) e uma U-Net 2D treinada — esta última exigida no feedback do
Checkpoint 1 para a etapa de Mineração do KDD — para segmentar o parênquima
pulmonar, medindo Dice Coefficient (meta: ≥ 0,85 para os métodos clássicos, ≥ 0,75
para a U-Net) e IoU contra as máscaras de referência oficiais do dataset, em pelo
menos 20 TCs de teste, com intervalo de confiança de 95% por bootstrap.

## Hipótese e processo KDD

**Hipótese:** métodos clássicos baseados na escala de Hounsfield já atingem Dice acima
da meta, e a U-Net 2D os supera, ao custo de mais tempo de processamento. Ela é testada
como três hipóteses com H0/H1 explícitas (meta, region growing × baseline, U-Net ×
clássicos). Ver [`docs/hipotese.md`](docs/hipotese.md).

**KDD:** as cinco etapas (seleção, pré-processamento, transformação, mineração,
interpretação) rodam em ordem num único script, que salva a evidência de cada etapa em
`data/luna16/kdd/` e termina com o teste das hipóteses:
```
python scripts/pipeline_kdd.py
```
Ver [`docs/kdd.md`](docs/kdd.md) para o que cada etapa faz, onde está o código e o resultado.

## Resultados

Teste oficial: **107 exames** (`teste_interno` de
[`split_novo.csv`](data/luna16/split_novo/split_novo.csv), 70/15/15 por paciente,
semente 42). Nenhum desses exames estava na primeira fase do projeto. A unidade é o
exame (Dice 3D), e o IC95% vem de bootstrap com 10.000 reamostras.

| Método | Dice [IC95%] | IoU [IC95%] | Sensibilidade | Pior exame | Exames < 0,85 |
|---|---|---|---|---|---|
| Baseline (−600 HU + morfologia) | 0,9492 [0,9336; 0,9604] | 0,9095 [0,8892; 0,9246] | 0,934 | 0,381 | 3 |
| Region growing | 0,9353 [0,9201; 0,9479] | 0,8855 [0,8645; 0,9034] | 0,901 | 0,530 | 6 |
| U-Net 2D (semente 123, 497 exames de treino) | **0,9838** [0,9827; 0,9847] | **0,9681** [0,9660; 0,9698] | 0,983 | 0,955 | 0 |

- **H1 (meta):** confirmada nos três métodos.
- **H2 (region growing > baseline):** refutada. A diferença foi de −0,0139
  [−0,0282; −0,0004], no sentido oposto ao previsto.
- **H3 (U-Net > clássicos):** confirmada. A U-Net foi melhor nos 107 exames.

Com duas sementes de treino, a U-Net dá 0,9837 ± 0,0004 de Dice.

Tabela completa, com unidade, semente, commit e arquivo de origem de cada número, e o
histórico do Teste A (26 exames): [`docs/tabela_experimentos.md`](docs/tabela_experimentos.md).

> **Nota de escopo**: o pulmão já segmentado poderia, em uma extensão futura, servir
> de base para detecção de nódulos pulmonares. O grupo implementou uma versão inicial
> dessa extensão (`sprint7_deteccao_nodulos_grp2.ipynb`), mas ela **não faz parte do
> escopo formal** desta entrega — tanto o documento oficial do projeto quanto o
> feedback do Checkpoint 1 pedem apenas a segmentação do parênquima. Ver `PROJETO.md`
> para o histórico e o status dessa extensão.

## Dataset

[LUNA16](https://luna16.grand-challenge.org/) (imagens de TC brutas em formato
MetaImage `.mhd`/`.raw`, derivadas do [LIDC-IDRI](https://www.cancerimagingarchive.net/collection/lidc-idri/)),
baixado via o mirror público `avc0706/luna16` no Kaggle. Critérios de inclusão,
estado real do download e proporção de split (70/15/15 por paciente) estão
documentados em [`docs/criterios_inclusao.md`](docs/criterios_inclusao.md); a
definição formal do problema (pergunta SMART, métricas) está em
[`DEFINICAO_DO_PROBLEMA.md`](DEFINICAO_DO_PROBLEMA.md).

## Como rodar (ambiente local, VSCode)

1. Criar e ativar um ambiente virtual Python 3.11+:
   ```
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   ```
2. Instalar as dependências (versões congeladas):
   ```
   pip install -r requirements.txt
   ```
3. Registrar o kernel Jupyter (uma vez só) e selecioná-lo em cada notebook (VSCode: seletor de kernel no canto superior direito):
   ```
   python -m ipykernel install --user --name=pi3-grupo2 --display-name="Python (PI3-GRUPO-2)"
   ```
4. Baixar os dados do LUNA16 (89 pacientes por subset + máscaras de referência). Requer um token de API do Kaggle salvo em `~/.kaggle/access_token` (gerado em [kaggle.com/settings](https://www.kaggle.com/settings) → API → Create New Token):
   ```
   python scripts/download_luna16_subset.py 0
   python scripts/download_luna16_subset.py 1
   ```
   Cada subset baixa ~12GB para `data/luna16/` (pasta fora do controle de versão — ver `.gitignore`). Os notebooks a partir do Sprint 3 esperam pelo menos o `subset0`; o Sprint 4 em diante também precisa do `subset1`.
5. Gerar o split treino/validação/teste (70/15/15 por paciente, conforme
   exigido no feedback do Checkpoint 1 — ver `docs/criterios_inclusao.md`):
   ```
   python scripts/regenerate_split_70_15_15.py
   ```
6. Rodar a avaliação em lote (baseline + region growing no conjunto de teste — pesada, ~15-20min, retomável se interrompida):
   ```
   python scripts/run_sprint4_evaluation.py
   ```
7. Treinar e avaliar a U-Net 2D (exigida no feedback do Checkpoint 1 para a etapa de
   Mineração — não é opcional; ver [`src/luna16/unet.py`](src/luna16/unet.py) para o
   porquê e as limitações de escopo em CPU). **Recomendado**: rodar no Google Colab
   com GPU em vez de local — o código detecta a GPU sozinho e usa mais dados/épocas
   automaticamente; ver [`colab_treinar_unet.ipynb`](colab_treinar_unet.ipynb) (basta
   subir esse notebook no Colab e seguir as células). Rodando local em CPU:
   ```
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   python scripts/train_unet_baseline.py     # ~15-20min
   python scripts/run_unet_evaluation.py     # ~15-25min
   ```
8. Rodar o pipeline KDD completo, que confere a reprodutibilidade e testa as hipóteses (~1 min):
   ```
   python scripts/pipeline_kdd.py
   ```
9. Abrir os notebooks **na ordem** (cada um pode depender de arquivos gerados pelo anterior — ver tabela abaixo).

## Notebooks (ordem de execução)

| Notebook | O que faz | Depende de |
|---|---|---|
| [`sprint2_hu_eda_grp2.ipynb`](sprint2_hu_eda_grp2.ipynb) | Configuração de ambiente + EDA da escala de Hounsfield Units (dataset LIDC-IDRI via TCIA — exploratório, dataset diferente do LUNA16 usado dali em diante) | nada |
| [`sprint3_baseline_luna16_grp2.ipynb`](sprint3_baseline_luna16_grp2.ipynb) | Critérios de seleção, split por paciente, pré-processamento, baseline (threshold -600HU + morfologia), validação piloto (5 TCs). Inclui o diagnóstico de um bug real encontrado no meio do processo | `subset0` baixado |
| [`sprint4_region_growing_grp2.ipynb`](sprint4_region_growing_grp2.ipynb) | Region growing, split estendido (`subset0`+`subset1`), comparação formal baseline vs. region growing em 35 TCs de teste | `subset0`+`subset1` baixados, `run_sprint4_evaluation.py` rodado |
| [`sprint5_falhas_e_reproducibilidade_grp2.ipynb`](sprint5_falhas_e_reproducibilidade_grp2.ipynb) | Métricas secundárias consolidadas, análise de casos de falha (correlação com resolução espacial), checklist de reprodutibilidade | resultados do Sprint 4 |
| [`sprint6_resultados_finais_grp2.ipynb`](sprint6_resultados_finais_grp2.ipynb) | Tabela e gráficos finais (IC95%), discussão desempenho x custo computacional | resultados do Sprint 4 |
| [`sprint7_deteccao_nodulos_grp2.ipynb`](sprint7_deteccao_nodulos_grp2.ipynb) | **Extensão opcional, fora do escopo formal** — detecção de nódulos: candidatos via blob detection dentro do pulmão segmentado, avaliação estilo FROC | `subset0`+`subset1`, `run_nodule_evaluation.py` rodado |

Ver também [`RELATORIO_FINAL_RASCUNHO.md`](RELATORIO_FINAL_RASCUNHO.md) — rascunho
do relatório científico final (contexto, metodologia, resultados, discussão,
limitações, referências), pra revisar e completar antes da entrega.

## Código reutilizável

Toda a lógica de carregamento de dados, seleção, split, pré-processamento,
segmentação (baseline e region growing) e métricas está em
[`src/luna16/`](src/luna16/) como um pacote Python — os notebooks importam essas
funções em vez de duplicar a implementação. Cada módulo tem um docstring
explicando o que faz e, principalmente, **por quê** (decisões de metodologia
comentadas inline).

## Scripts

- [`scripts/pipeline_kdd.py`](scripts/pipeline_kdd.py): roda as 5 etapas do KDD em ordem e testa as hipóteses do trabalho; saídas em `data/luna16/kdd/` (ver [`docs/kdd.md`](docs/kdd.md)).

- [`scripts/download_luna16_subset.py`](scripts/download_luna16_subset.py) `N`: baixa o subset N do LUNA16 (89 pacientes + máscaras de referência) via API do Kaggle.
- [`scripts/regenerate_split_70_15_15.py`](scripts/regenerate_split_70_15_15.py): (re)gera `split_full.csv` com a proporção 70/15/15 por paciente; arquiva o split/resultados anteriores (60/20/20) em `data/luna16/archive_split_v1_60_20_20/`.
- [`scripts/run_sprint4_evaluation.py`](scripts/run_sprint4_evaluation.py): roda baseline e region growing em todo o conjunto de teste (retomável — salva progresso por paciente, seguro de interromper e retomar).
- [`scripts/train_unet_baseline.py`](scripts/train_unet_baseline.py) / [`scripts/run_unet_evaluation.py`](scripts/run_unet_evaluation.py): treina e avalia o U-Net 2D de contingência (ver `src/luna16/unet.py`).
- [`scripts/run_nodule_evaluation.py`](scripts/run_nodule_evaluation.py): roda a detecção de nódulos em até 20 pacientes com anotação disponível (retomável).

## Estratégia de revisão e integração

A branch sprints-3-8 será revisada pelo grupo por meio de um Pull Request antes do merge para main. Essa abordagem permite revisar os commits, alterações de código e documentação das Sprints 3–8 antes de incorporá-las à branch principal.
