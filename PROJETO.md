# PROJETO.md — Histórico do Projeto

> Arquivo de acompanhamento mantido automaticamente ao longo das sessões de trabalho
> com IA neste repositório. Atualizado sempre que houver uma mudança relevante de
> escopo, decisão técnica ou marco de resultado — não é necessário pedir.

---

## Contexto

**Projeto**: Projeto Integrador III (disciplina do 4º semestre, curso de IA) —
**Grupo 02**. Repositório: [PI3-GRUPO-2](https://github.com/rcoliveirasb/PI3-GRUPO-2)
(branch `main`), clonado diretamente na pasta de trabalho local. Trello do grupo:
https://trello.com/b/A68BBq87/grupo-02-projeto-integrador-iii.

**Objetivo geral**: segmentação automática do parênquima pulmonar em tomografias
computadorizadas (TC) de tórax, comparando uma técnica clássica baseline com uma
técnica mais avançada — usando essa segmentação como base para, em seguida,
**detectar nódulos pulmonares** (o objetivo que dá sentido clínico ao projeto).

**Dataset**: [LUNA16](https://luna16.grand-challenge.org/) (`.mhd`/`.raw`,
derivado do LIDC-IDRI), baixado via mirror público `avc0706/luna16` no Kaggle.
Um dataset diferente (LIDC-IDRI genérico via API do TCIA, manifest
`TCIA_LIDC-IDRI_20200921.tcia`) foi usado só na EDA exploratória inicial
(Sprint 2) e **não** é usado a partir do Sprint 3 — não tem máscaras de
referência, então não serve para o pipeline de avaliação real. Ver "Decisões
tomadas" abaixo.

**Escopo atual do projeto** (duas fases encadeadas):
1. **Segmentação do pulmão**: baseline (threshold -600HU + morfologia) vs.
   region growing (sementes automáticas + tolerância de intensidade). Métricas
   primárias: Dice (meta ≥0,85) e IoU (meta ≥0,75) contra as máscaras de
   referência oficiais (`seg-lungs-LUNA16`), com IC95% via bootstrap (≥500
   reamostras). Avaliado em ≥20 TCs de teste, split por paciente (nunca por
   fatia, para evitar vazamento).
2. **Detecção de nódulos** (usando o pulmão já segmentado): candidatos via blob
   detection (Laplacian of Gaussian), avaliados no padrão FROC (o mesmo do
   desafio LUNA16 original). Com um classificador (Random Forest) treinado para
   reduzir falsos positivos dos candidatos.

**Decisões tomadas**:
- Ambiente local em VSCode (não Colab/Kaggle): venv `.venv/`, kernel Jupyter
  `pi3-grupo2`, dependências pinadas em `requirements.txt`.
- Fonte de dados definida como LUNA16 via Kaggle (`avc0706/luna16`), baixado por
  arquivo individual (não o dataset completo de ~120GB) via
  `scripts/download_luna16_subset.py`. Resolve a inconsistência identificada no
  início do projeto entre o notebook de EDA (LIDC-IDRI/TCIA) e o que o pipeline
  de fato precisa (LUNA16 com máscaras de referência).
- Split treino/validação/teste **70/15/15 por paciente**, seed fixa (42) —
  proporção oficial exigida pelo professor no feedback do Checkpoint 1 (ver
  "Contexto acadêmico" e log de 2026-09-14). O grupo usou 60/20/20 entre os
  Sprints 3–8; a função `patient_split` já foi atualizada para 70/15/15 em
  2026-09-02, mas os artefatos de split e os resultados publicados ainda
  refletem a proporção antiga — precisa regenerar (ver Próximos passos).
- Toda a lógica reutilizável (I/O, seleção, split, pré-processamento,
  segmentação, nódulos, métricas) foi extraída para o pacote `src/luna16/` em
  vez de duplicada nos notebooks.
- Segunda etapa de classificação (redução de falsos positivos dos candidatos a
  nódulo) não estava no escopo formal original do Grupo 2 (que previa só
  segmentação + comparação de métodos), mas foi incorporada como extensão
  natural para dar sentido clínico ao trabalho — precisa ser validada com o
  restante do grupo antes da entrega final (ver Próximos passos).
- Nada do pipeline novo (`src/`, `scripts/`, notebooks Sprint 3–7, relatórios)
  havia sido commitado/enviado ao GitHub até o momento — ver Log de mudanças.

**Restrições/lembretes de domínio a respeitar em qualquer texto do projeto**:
acurácia sozinha é enganosa dada a baixa prevalência de nódulos; falso negativo
custa muito mais que falso positivo (sensibilidade é a métrica clínica
prioritária); concordância entre radiologistas é só ~75-80% (scores "perfeitos"
em dados pequenos provavelmente indicam overfitting ao estilo de um anotador);
nada aqui é um dispositivo médico certificado — nunca dar a entender o
contrário.

## Contexto acadêmico — avaliação do professor (autoridade sobre o escopo)

O professor da disciplina avalia por ciclo (Checkpoint) e Sprint, com nota
individual e nota de grupo. **O feedback do professor tem precedência sobre
qualquer versão anterior do escopo informal do grupo** quando os dois
conflitam (ex.: proporção de split — ver Log de 2026-09-14).

**Ciclo avaliado até agora**: Checkpoint 1 / Sprint 1 / Fechamento do Ciclo.
Nota do grupo: **8,5**. Notas individuais: Roger 9,0 (download do LUNA16 —
133GB no HD externo —, licença de acesso, repositório GitHub); Amabilly 8,8
(Trello, coordenação, arquitetura Lambda, correção do artigo comparativo);
Rafael 8,8 (pergunta SMART, Definição do Problema, README); Érica 8,5 (Drive,
artigo Lambda vs. Federated Learning); Ruan 8,5 (pesquisa arquitetura Kappa,
avaliação de fontes de dados alternativas); Herb 8,5 (pesquisa Federated
Learning, fluxograma Kappa).

**Onde o professor via o grupo no KDD, em 2026-09-14** (baseado só no que foi
entregue/commitado — o professor não tinha visibilidade do trabalho local dos
Sprints 3–8, porque nada tinha sido enviado ao GitHub ainda):
- Seleção: concluída parcialmente (LUNA16 baixado, faltava documentar critério
  de inclusão formalmente).
- Pré-processamento: em andamento (HU + morfologia demonstrados em algumas
  imagens, não escalado a toda a base, parâmetros não documentados).
- Transformação, Mineração, Interpretação: marcadas como pendentes pelo
  professor — na realidade já avançadas localmente (ver log de
  2026-08-31/09-01 e 09-02), mas invisíveis para ele até serem commitadas.

**Pontos de atenção formais do professor** (com status atual):
1. Erro conceitual nas métricas (Kappa/acurácia em vez de Dice/IoU) — **já
   corrigido** no README (nota de correção) e agora também no
   `DEFINICAO_DO_PROBLEMA.md` criado em 2026-09-14.
2. Sprint 2 não entregue ao professor — **pendente**: o grupo precisa
   apresentar, mesmo que informalmente, o que foi feito nesse período (hipótese
   a confirmar com o grupo: o gap de commits entre 16/08 e 31/08 pode
   corresponder a essa sprint — ver Próximos passos).
3. Parâmetros do pipeline não documentados (threshold HU, kernel morfológico)
   — **corrigido** em `docs/criterios_inclusao.md` (criado em 2026-09-14).
4. Atribuição individual obrigatória a partir da Sprint 3 (formato Atividade/
   Evidência/Conclusão/Próximos Passos por integrante) — **pendente**, não é
   algo que este repositório resolve sozinho; é responsabilidade de
   apresentação do grupo a cada sprint.

**Orientações do professor para Sprints 3 e 4** (a autoridade atual sobre o
que falta): ver Próximos passos abaixo — cada item do feedback foi mapeado
1:1 para uma ação/gap concreto no repositório.

---

## Log de mudanças

### 2026-08-03 — Bootstrap do repositório
Commit inicial do grupo (`ffe908d`) no GitHub.

### 2026-08-14 — Licença
Adicionada licença MIT ao projeto (`be19c93`).

### 2026-08-16 — README inicial
Primeira versão do README com objetivos do projeto (`219f5fe`).

### 2026-08-31 — EDA exploratória (LIDC-IDRI/TCIA) commitada por outro integrante
Commit "primeiro commit" (`c7c823c`, autor: rodyneyh) trouxe
`sprint2_hu_eda_grp2.ipynb`, o manifest `TCIA_LIDC-IDRI_20200921.tcia` e a pasta
`entrega/` (EDA reproduzível em Colab). **Por quê**: primeira exploração de
dados de TC (escala de HU) antes de decidir a fonte definitiva de dados.
Identificado nesta mesma janela que esse dataset (LIDC-IDRI genérico via TCIA)
não tem máscaras de referência e por isso não serve para o pipeline de
avaliação (Dice/IoU) — só para a EDA exploratória.

### 2026-08-31/09-01 — Ambiente local + pipeline LUNA16 completo (ainda não commitado)
Criado o ambiente local (venv, kernel `pi3-grupo2`, `.gitignore`) e todo o
pipeline de segmentação sobre dados reais do LUNA16:
- `src/luna16/`: pacote com seleção, split, pré-processamento, baseline,
  region growing, detecção de nódulos, métricas.
- `scripts/download_luna16_subset.py`: download idempotente por subset via API
  do Kaggle (resolve a fonte de dados definitiva — LUNA16, não LIDC-IDRI/TCIA).
- Baixados `subset0` (89 pacientes) + `subset1` (88 pacientes) = 177 pacientes,
  `seg-lungs-LUNA16` (máscaras de referência), `annotations.csv`,
  `candidates.csv`.
- `sprint3_baseline_luna16_grp2.ipynb`: split inicial (89 pacientes), baseline
  threshold -600HU + morfologia, piloto em 5 TCs. Um bug real foi diagnosticado
  e documentado no processo.
- `sprint4_region_growing_grp2.ipynb`: split estendido para 177 pacientes
  (106/36/35), region growing, comparação formal em 35 TCs de teste via
  `scripts/run_sprint4_evaluation.py` (retomável).
- **Resultado obtido**: baseline Dice médio 0,962 (IC95% [0,958; 0,966]) vs.
  region growing 0,953 (IC95% [0,948; 0,957]) — diferença estatisticamente
  significativa a favor do baseline, que também foi mais rápido. Ambos
  superaram a meta do projeto (Dice ≥0,85) em 100% dos pacientes de teste.
- `sprint5_falhas_e_reproducibilidade_grp2.ipynb`: métricas secundárias,
  análise de casos de falha (correlação com resolução espacial), checklist de
  reprodutibilidade. Um bug real de segmentação (tratamento incompleto do ar de
  fundo) foi encontrado e corrigido — derrubava o Dice em ~29% dos pacientes.
- `sprint6_resultados_finais_grp2.ipynb`: tabela e gráficos finais consolidados
  (`tabela_resultados_finais.csv`, `grafico_dice_iou_final.png`,
  `grafico_comparacao_pareada.png`).
- `sprint7_deteccao_nodulos_grp2.ipynb` + `scripts/run_nodule_evaluation.py`:
  primeira versão da detecção de nódulos (blob detection/LoG restrito ao pulmão
  segmentado), avaliação FROC em 20 pacientes anotados. **Resultado obtido**:
  sensibilidade de 75,9% (63/83 nódulos localizados corretamente), ~5.864 falsos
  positivos por exame em média — consistente com a literatura de detecção
  clássica, motivando a etapa de redução de falsos positivos (ver abaixo). Um
  segundo bug foi encontrado nesta etapa: a faixa de densidade usada para
  candidatos excluía a maioria dos nódulos pequenos por efeito de volume
  parcial.
- Documentação escrita: `RELATORIO_ETL.md` (pipeline de dados
  Extract/Transform/Load), `RELATORIO_FINAL_RASCUNHO.md` (rascunho do relatório
  científico final, com apoio de IA a partir dos resultados reais — precisa
  revisão e reescrita pelo grupo antes da entrega), `ESBOCO_APRESENTACAO.md`
  (estrutura de slides para Seminário 3 e Banca Final).
- **Por quê**: essa é a entrega central do projeto (comparação baseline vs.
  método avançado com métricas rigorosas) — conforme o plano oficial do Grupo 2.
- **Estado**: por instrução explícita do grupo nesta janela, nada disso foi
  commitado/enviado ao GitHub ou Trello ainda — aguardando revisão do grupo.

### 2026-09-02 — Extensão: redução de falsos positivos na detecção de nódulos
Adicionados `scripts/extract_nodule_features.py`,
`scripts/run_sprint8_evaluation.py`, `scripts/run_sprint8b_own_candidates.py` e
o módulo `src/luna16/nodule_features.py`. Treinado um classificador
`RandomForestClassifier` (`class_weight='balanced'`) sobre features extraídas de
cada candidato a nódulo (recorte 33×33×33 voxels, 11 features de HU/forma/
gradiente), com treino/threshold/teste em conjuntos separados (sem vazamento).
Classificador serializado em `data/luna16/classificador_fp_reduction.joblib`.
Resultados em `sprint8_resultados.csv`, `sprint8b_resultados.csv`,
`sprint8c_resultados_finais.csv` (antes/depois do filtro). **Por quê**: a taxa
de falsos positivos da detecção pura por blob detection (Sprint 7) era alta
demais para uso prático — passo natural de refinamento antes de fechar a fase 2
do projeto. **Nota**: essa etapa amplia o escopo formal original do Grupo 2
(que prezia só segmentação); precisa alinhamento com o restante do grupo/
orientação antes da entrega final.

### 2026-09-14 — Criação deste arquivo de histórico (PROJETO.md)
Criado a pedido de Amabilly para manter contexto, log de mudanças e pendências
do projeto de forma persistente e legível pelo grupo, atualizado automaticamente
a cada mudança relevante daqui em diante.

### 2026-09-14 — Segunda opinião: notebook alternativo de um colega
Amabilly pediu a um colega uma segunda visão independente do problema, já que o
progresso do próprio grupo estava travado. Ele entregou
`contrib/colega_segmentacao_passo_a_passo.ipynb` (notebook Colab, 47 células,
movido para `contrib/` em 2026-09-14 para não se confundir com os notebooks
oficiais do grupo),
comparando o mesmo baseline (−600HU + erosão) com um método B próprio (máscara
de corpo + region growing 3D + reconstrução morfológica), em 20 exames do
LIDC-IDRI casados com as máscaras do `seg-lungs-LUNA16` pelo SeriesInstanceUID
(via download individual pela API do TCIA, não pelo mirror do Kaggle usado pelo
pipeline do grupo).
- **Resultado**: Método A (baseline "puro", sem remoção de fundo) Dice 0,264
  [0,221–0,313] — reproduz de forma independente o mesmo bug do ar de fundo que
  o Sprint 5 do grupo já tinha diagnosticado e corrigido. Método B: Dice 0,969
  [0,936–0,986], consistente com o region growing do grupo (0,953).
  Inclui também análise de ablação (Passo 14) e tabela de modos de falha
  (Passo 16) que o pipeline do grupo ainda não tem.
- **Por quê**: buscar uma validação cruzada externa e destravar o progresso.
- **Decisão pendente**: não substitui o pipeline oficial do grupo — os números
  primários de segmentação continuam sendo os do próprio pipeline (mais exames
  de teste, já com o fix do fundo desde o início). Avaliado como fonte de
  conteúdo complementar (ablação, limitações, reprodutibilidade) para o
  relatório final, e como validação cruzada do bug já corrigido — não como um
  segundo resultado concorrente. Ver Próximos passos.

### 2026-09-14 — Feedback oficial do professor recebido e processado
Amabilly trouxe dois documentos do professor: `Feedback_Grupo_2.pdf`
(avaliação formal do Checkpoint 1/Sprint 1, com notas individuais/de grupo,
critérios avaliados, pontos de atenção e orientações para Sprints 3-4) e
`ciclo_1 (1).pdf` (o fechamento de ciclo que o grupo efetivamente entregou).
Pediu para seguir as instruções do professor à risca e adaptar o projeto.
- **Achado mais importante**: o professor avalia por aquilo que é entregue no
  GitHub — como nada dos Sprints 3-8 tinha sido commitado (ver log de
  31/08-01/09 e 02/09), o professor via o grupo travado na Seleção/
  Pré-processamento, quando na realidade a Interpretação (avaliação Dice/IoU)
  já estava concluída havia duas semanas. Reforça a urgência do primeiro item
  de "Próximos passos".
- **Descoberta de uma inconsistência já parcialmente corrigida**: o professor
  exige split 70/15/15 por paciente, documentado em
  `docs/criterios_inclusao.md`. Ao investigar, `src/luna16/splits.py` **já
  tinha sido atualizado para 70/15/15 em 2026-09-02** (docstring da função
  cita explicitamente "com o dataset completo (888 pacientes, via HD
  externo) passamos para 70/15/15") — mas o artefato `split_full.csv` e todos
  os resultados publicados (Sprints 4-8) ainda usam o split antigo (60/20/20
  sobre 177 pacientes). A mudança de código não tinha sido propagada.
- **Conflito de escopo identificado**: o professor sugere explicitamente um
  modelo **U-Net 2D** (BCE+Dice loss, meta Dice ≥0,75) para a etapa de
  "Mineração de Dados" do KDD na Sprint 4. O plano original do Grupo 2 (seção
  4 do documento do projeto) tratava o baseline threshold+morfologia e o
  region growing como os dois métodos *oficiais* a comparar, com U-Net
  citado só como extensão opcional (Sprint 5, "se não houver atraso"). Não
  está resolvido se o professor aceita a comparação clássica (baseline vs.
  region growing) como a etapa de "Mineração", ou se exige literalmente um
  modelo treinado (U-Net) além disso — ver Próximos passos.
- **Ações tomadas nesta sessão**: criados `DEFINICAO_DO_PROBLEMA.md` (SMART
  corrigido, métricas corrigidas, sem Kappa/acurácia) e
  `docs/criterios_inclusao.md` (critérios de inclusão formais, estado real do
  download frente aos 888 exames-alvo, parâmetros do pipeline documentados —
  itens 0, 1 e parte do 2 das "Orientações para o Próximo Ciclo" do
  professor). Seção "Contexto acadêmico" adicionada acima com o resumo do
  feedback e das notas.
- **Por quê**: alinhar o repositório ao que o professor efetivamente cobra,
  já que essa nota substitui/tem precedência sobre o entendimento informal de
  escopo que o grupo vinha usando.

### 2026-09-14 — Execução das decisões do feedback: split 70/15/15, U-Net de contingência, commit local
Com as respostas de Amabilly às 3 decisões em aberto (split, U-Net, commit),
executado nesta mesma sessão:
- **Split regenerado**: `scripts/regenerate_split_70_15_15.py` (novo) recalcula
  o split sobre os 177 pacientes disponíveis com 70/15/15 (**124 treino / 27
  validação / 26 teste**), usando a função `patient_split` que já estava
  correta desde 02/09. O split antigo (60/20/20) e os resultados que
  dependiam dele (`sprint4_*_test.csv`, `tabela_resultados_finais.csv`,
  gráficos finais) foram arquivados em
  `data/luna16/archive_split_v1_60_20_20/`, não apagados.
- **Baseline + region growing reavaliados** no novo conjunto de teste (26
  pacientes) via `scripts/run_sprint4_evaluation.py` — rodando em background
  no momento deste commit; resultados em `sprint4_baseline_test.csv` /
  `sprint4_region_growing_test.csv` (novos, sobre o split correto).
- **U-Net 2D de contingência implementado**: `src/luna16/unet.py` (modelo
  compacto, `BCEDiceLoss` — exatamente a loss sugerida pelo professor),
  `scripts/train_unet_baseline.py` e `scripts/run_unet_evaluation.py`.
  Escopo deliberadamente limitado por rodar em CPU (sem GPU local
  disponível): 40 dos 124 pacientes de treino, entrada 128×128, rede pequena,
  6 épocas — suficiente para um número real de Dice/IoU comparável aos outros
  métodos (mesmo pipeline de pré-processamento, mesmas métricas), não uma
  versão final otimizada. `torch==2.14.0+cpu` adicionado a
  `requirements.txt`. Treino rodando em background no momento deste commit.
- **`contrib/colega_segmentacao_passo_a_passo.ipynb`**: notebook do colega
  movido para essa pasta (antes na raiz) para não se confundir com os
  notebooks oficiais do grupo. Confirmado que os rótulos de máscara que ele
  usa (3/4/5) são consistentes com `src/luna16/io.py` (3 e 4 = pulmão, 5 =
  traqueia; só a atribuição esquerdo/direito entre 3 e 4 é trocada entre os
  dois, sem efeito no Dice/IoU).
- **Commit local feito** (sem push) com todo o trabalho pendente dos Sprints
  3-8 + as correções desta sessão — ver hash no histórico do git.
- **Por quê**: aplicar as decisões tomadas por Amabilly diante do feedback do
  professor, deixando o repositório coerente com a proporção de split exigida
  e com uma resposta concreta (ainda que inicial) ao pedido de um modelo
  treinado para a etapa de "Mineração de Dados".
- **Pendente**: os resultados de segmentação (baseline/region growing/U-Net)
  sobre o split novo ainda estavam sendo calculados no momento deste commit —
  conferir os CSVs finais antes de atualizar `RELATORIO_FINAL_RASCUNHO.md`,
  `tabela_resultados_finais.csv` e os slides com os números definitivos. A
  detecção de nódulos (Sprints 7-8) **não** foi reprocessada com o novo split
  ainda — os resultados dessa etapa (`sprint7_nodulos_resultados.csv`,
  `sprint8*_resultados.csv`) continuam do split antigo até decisão sobre se
  essa extensão entra no escopo formal (ver item já registrado abaixo).

---

## Próximos passos / pendências em aberto

### Do feedback oficial do professor (prioridade alta — ver "Contexto acadêmico")

- [x] **Corrigir métricas-alvo (Kappa/acurácia → Dice/IoU)** — feito no
  README e em `DEFINICAO_DO_PROBLEMA.md` (2026-09-14).
- [x] **Documentar critérios de inclusão + parâmetros do pipeline** — feito em
  `docs/criterios_inclusao.md` (2026-09-14).
- [x] **Regenerar o split com a proporção correta (70/15/15)** — feito em
  2026-09-14 sobre os 177 pacientes já baixados (124/27/26). Migrar para os
  888 pacientes completos (HD externo do Roger) fica como melhoria futura, não
  bloqueante.
- [ ] **Conferir os resultados finais de baseline/region growing/U-Net sobre o
  split novo** (rodando em background no momento do commit de 2026-09-14) e
  atualizar `tabela_resultados_finais.csv`, os gráficos e
  `RELATORIO_FINAL_RASCUNHO.md` com os números definitivos — os que estão lá
  hoje são do split antigo (60/20/20), arquivado em
  `data/luna16/archive_split_v1_60_20_20/`.
- [x] **U-Net 2D de contingência implementado e treinamento iniciado** (ver
  `src/luna16/unet.py`, `scripts/train_unet_baseline.py`,
  `scripts/run_unet_evaluation.py`) — escopo inicial deliberadamente limitado
  (CPU, 40 pacientes, 128×128, 6 épocas). Falta: (a) conferir o Dice/IoU
  final assim que a avaliação terminar; (b) **esclarecer com o professor se
  isso satisfaz a exigência da etapa "Mineração"** ou se ele espera algo mais
  robusto (mais dados/épocas/resolução) antes de investir mais tempo de CPU
  nisso.
- [ ] **Reprocessar a detecção de nódulos (Sprints 7-8) com o split novo**,
  se essa extensão for confirmada como parte do escopo da entrega (ver item
  abaixo) — hoje ainda reflete o split 60/20/20 antigo.
- [ ] **Reconstruir/apresentar a Sprint 2** que o professor marcou como não
  entregue — mesmo que informalmente. Hipótese a confirmar com o grupo: o
  hiato de commits entre 16/08 (README) e 31/08 (EDA) pode ser o conteúdo
  dessa sprint.
- [ ] **Manter o formato de atribuição individual** (Atividade/Evidência/
  Conclusão/Próximos Passos por integrante) em toda apresentação de sprint
  daqui em diante, exigência explícita a partir da Sprint 3.
- [ ] Avaliar se vale reorganizar os caminhos do código para os nomes que o
  professor sugeriu no feedback (`src/preprocessing/segmentar_parenquima.py`)
  — recomendação: manter a estrutura atual, mais completa
  (`src/luna16/*.py`), e só deixar a correspondência documentada (já feito em
  `docs/criterios_inclusao.md`), em vez de renomear um pacote que já funciona
  e é usado por 6 notebooks e 6 scripts.

### Do trabalho geral do grupo (ver entradas anteriores do Log)

- [x] **Commitar o trabalho pendente** — feito localmente em 2026-09-14 (ver
  log). **Ainda falta o `git push` para o GitHub** — decisão explicitamente
  deixada para Amabilly confirmar separadamente antes de tornar isso visível
  ao resto do grupo/professor. Decidir também estratégia de branch/PR.
- **Revisar e reescrever `RELATORIO_FINAL_RASCUNHO.md`** com as próprias
  palavras do grupo antes da entrega — o rascunho foi gerado com apoio de IA a
  partir dos números reais, mas precisa ser algo que o grupo consiga defender na
  banca.
- **Alinhar com o grupo/orientação se a etapa de detecção de nódulos + redução
  de falsos positivos (Sprints 7-8) entra no escopo formal da entrega**, já que
  não estava no plano original do Grupo 2 (que prezia só a comparação de
  métodos de segmentação).
- **Atualizar `RELATORIO_ETL.md`**: a seção 3.2 diz que o classificador não é
  persistido em disco, mas isso já não é verdade desde 2026-09-02
  (`classificador_fp_reduction.joblib` existe) — e falta documentar
  `sprint8c_resultados_finais.csv` na tabela de artefatos.
- **Confirmar volume de dados anotados usado na avaliação FROC** (20 pacientes)
  é suficiente/representativo, ou se vale ampliar antes da entrega final.
- **Decidir se o `.tcia`/notebook de EDA do LIDC-IDRI (Sprint 2) permanece só
  como exploratório no relatório final**, já que o pipeline real usa LUNA16 —
  evitar que a banca confunda os dois datasets.
- **Preparar os slides reais** a partir de `ESBOCO_APRESENTACAO.md` (o esboço
  cobre Seminário 3 e Banca Final; falta produzir o material visual e definir
  tempo alocado com a disciplina).
- **Decidir o que fazer com `contrib/colega_segmentacao_passo_a_passo.ipynb`** (notebook
  do colega, ver log de 2026-09-14): (a) ~~confirmar se os rótulos
  3/4/5 batem com `src/luna16/io.py`~~ **conferido em 2026-09-14: consistente**
  — ambos usam os rótulos 3 e 4 como pulmão (o colega chama 3 de "esquerdo" e
  4 de "direito", o `io.py` do grupo chama 3 de "direito" e 4 de "esquerdo" —
  troca cosmética de nomenclatura, sem efeito no Dice/IoU, já que a máscara
  usada é a união {3,4} nos dois casos) e 5 como traqueia (excluída); (b) portar a análise de ablação e a
  tabela de modos de falha para o relatório final/slides; (c) deixar explícito
  no relatório que o "Método A" dele é a versão *sem* a correção do fundo
  (ilustração pedagógica do bug), não um segundo resultado de baseline
  concorrente com o do grupo; (d) decidir se a via de dados alternativa dele
  (TCIA + máscara casada por UID) vira um fallback documentado ou fica só como
  registro pontual.
