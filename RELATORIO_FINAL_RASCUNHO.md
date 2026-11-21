# Segmentação Automática do Parênquima Pulmonar em Tomografias Computadorizadas de Tórax

**Grupo 02 — Projeto Integrador III**

> **Nota do grupo**: este é um **rascunho estruturado**, gerado com apoio de IA a
> partir dos resultados reais dos notebooks (Sprints 3-6), para o grupo revisar,
> reescrever com as próprias palavras onde fizer sentido, e completar (autores,
> instituição, seção de agradecimentos, ajustes de estilo exigidos pela disciplina).
> Os números e conclusões são reais (extraídos das execuções dos notebooks), mas o
> texto em si deve ser lido criticamente e apropriado por vocês antes da entrega —
> especialmente porque vocês precisam conseguir defender cada afirmação na banca.

---

## Resumo

Este trabalho tem dois objetivos encadeados: (1) segmentar o parênquima pulmonar em
tomografias computadorizadas (TC) de tórax, isolando-o das estruturas adjacentes; e
(2), usando essa segmentação, **detectar nódulos pulmonares** — o objetivo que dá
sentido clínico ao projeto, auxiliando o médico a localizar pontos suspeitos para
investigação. Para (1), comparamos três métodos: um baseline de limiarização em
Unidades Hounsfield (HU) com operações morfológicas, region growing com sementes
automáticas e uma U-Net 2D treinada. Usando 177 pacientes do dataset público LUNA16
(split 70/15/15 por paciente, 26 de teste), avaliamos os três contra as máscaras de
referência oficiais, com Dice e IoU como métricas primárias e intervalos de confiança
de 95% por bootstrap. Dice médio: U-Net 0,9818 (IC95% [0,9790; 0,9843]), baseline
0,9555 ([0,9416; 0,9663]) e region growing 0,9354 ([0,9006; 0,9582]). A U-Net superou
os dois métodos clássicos em todos os 26 exames (Wilcoxon pareado com correção de
Holm, p < 0,001), mas com margem pequena sobre o baseline (+0,026) e cerca de 4 vezes
o tempo em CPU. A diferença aparece com mais força fora do Dice: dos 43 nódulos
anotados nos exames de teste, a máscara do baseline apaga 13 (8 dos 9 colados na
pleura) e a da U-Net apaga 3 (McNemar, p = 0,006). Para (2), implementamos um detector de
candidatos a nódulo via blob detection (Laplacian of Gaussian) restrito à região
pulmonar já segmentada, avaliado no padrão FROC (o mesmo usado pelo desafio LUNA16
original) em 20 pacientes com anotação disponível: sensibilidade de 75,9% (63/83
nódulos anotados corretamente localizados), ao custo de ~5.864 falsos positivos por
exame em média — resultado consistente com a literatura de detecção clássica de
nódulos, que documenta essa mesma limitação e motiva uma segunda etapa de redução
de falsos positivos via classificador treinado (fora do escopo de métodos
clássicos de visão computacional, mas discutida como trabalho futuro natural). Um
achado metodológico relevante do trabalho foi a identificação e correção de dois
bugs de implementação reais — um na segmentação pulmonar (tratamento incompleto do
ar de fundo, que derrubava artificialmente o Dice em ~29% dos pacientes) e outro na
faixa de densidade usada para candidatos a nódulo (excluía a maioria dos nódulos
pequenos por efeito de volume parcial) — ambos documentados como parte da análise
de casos de falha, incluindo o diagnóstico inicial incorreto antes da causa real
ser encontrada.

## 1. Contexto

[Preencher: 1-2 parágrafos sobre o contexto clínico do câncer de pulmão, a
relevância de TC de rastreamento, e por que segmentar o parênquima pulmonar é o
primeiro passo necessário antes de qualquer análise de nódulos — a seção 4.1 do
documento do projeto já traz a formulação-base:]

> "O parênquima pulmonar precisa ser isolado das estruturas adjacentes (coração,
> costelas, mediastino) antes de qualquer análise de nódulos. Este é um problema
> clássico de visão computacional aplicada à imagem médica, com impacto direto na
> qualidade de qualquer análise posterior realizada sobre a TC."

Trabalhos relacionados relevantes (ver seção 8, Referências): Armato et al. (2011)
descreve o dataset LIDC-IDRI, do qual o LUNA16 deriva; Setio et al. (2016) trata de
detecção de nódulos a partir de TCs já segmentadas; van Ginneken et al. (2006) e
Hofmanninger et al. (2020) tratam especificamente de segmentação pulmonar, o
segundo com foco em como a diversidade de dados (não a metodologia) é o principal
obstáculo prático; Ronneberger et al. (2015) introduz a U-Net, referência para
segmentação médica com aprendizado profundo, usada aqui como terceiro método
(seção 2.5), o método aprendido comparado aos dois clássicos.

## 2. Metodologia (Etapas do KDD)

O trabalho segue o processo de Knowledge Discovery in Databases (KDD) adaptado ao
domínio de imagem médica:

### 2.1. Seleção

Dataset: LUNA16 (subsets 0 e 1, 177 pacientes totais), formato `.mhd`/`.raw`,
acompanhado das máscaras de referência oficiais (`seg-lungs-LUNA16`). Critérios de
exclusão aplicados programaticamente: máscara de referência ausente ou vazia;
espessura de corte (espaçamento entre fatias) > 2,5mm. **Resultado**: 177/177
pacientes passaram nos critérios — o LUNA16 já aplica curadoria equivalente desde
sua derivação do LIDC-IDRI original.

### 2.2. Pré-processamento

Três etapas, aplicadas nesta ordem: (1) limpeza de HU — substituição do valor de
padding fora do campo de visão circular do scanner por ar (-1000 HU) e recorte para
a faixa [-1000, 400] HU; (2) redução de ruído — filtro Gaussiano leve (σ=0,5 voxel);
(3) reamostragem para espaçamento isotrópico de 1mm via SimpleITK, necessária porque
os exames do dataset têm espaçamento variável entre fatias (0,5mm a 2,5mm).

### 2.3. Baseline: threshold + morfologia

Limiarização em -600 HU seguida de: remoção do ar de fundo **fatia a fatia** (não no
volume 3D inteiro — necessário porque a via aérea pode formar um caminho contínuo até
o ar externo, o que uma limpeza 3D ingênua confundiria com o próprio pulmão);
manutenção dos 2 maiores componentes conexos resultantes; preenchimento de buracos
(inclui vasos e nódulos, que são tecido, não ar, mas contam como parênquima);
abertura morfológica (erosão seguida de dilatação, elemento estruturante esférico de
raio 1 voxel) para remover estruturas espúrias pequenas.

### 2.4. Region growing

Segunda técnica, com mecanismo distinto do baseline: em vez de um limiar global único,
cresce uma região a partir de um ponto semente por pulmão (escolhido automaticamente
como o ponto mais interior de cada componente candidato, via transformada de
distância, **entre os voxels abaixo de −750 HU**), incluindo vizinhos com intensidade
dentro de uma banda de tolerância (±200 HU) ao redor do valor da semente. O
crescimento é restrito à mesma região "segura" do baseline, pelo mesmo motivo (evitar
vazamento pela via aérea).

O corte de −750 HU na escolha da semente foi uma correção feita em 26/10 (ver seção
5.2): sem ele, a semente podia cair na franja de volume parcial ao redor dos vasos
(~−600 HU), deslocando a banda de crescimento para [−800, −400] HU, que não alcança o
parênquima aerado (~−850 HU).

### 2.5. U-Net 2D (método aprendido)

Atende à etapa de Mineração de Dados do KDD exigida no feedback do professor. Rede
U-Net 2D compacta aplicada a fatias axiais redimensionadas para 128×128, treinada com
perda BCE + Dice (Adam, taxa de aprendizado 1e-3, 25 épocas) nos 124 exames de
treino, com GPU no Google Colab (`colab_treinar_unet.ipynb`,
`scripts/train_unet_baseline.py`; checkpoint em `data/luna16/unet_baseline.pt`).

**Pós-processamento espacial**: a rede decide por aparência local e não tem noção de
"fora do corpo", por isso chegou a marcar o ar do colchão/mesa do tomógrafo como
pulmão. A saída passa por uma limpeza de componentes conexos que mantém os
componentes com pelo menos 15% do volume do maior
(`lung_air.keep_components_by_fraction`). Um número fixo de componentes ("os 2
maiores") não funciona, porque na saída da U-Net os dois pulmões costumam sair
conectados pela carina num único componente, e a segunda vaga ficava com o maior
blob espúrio.

### 2.6. Avaliação

Dice Coefficient e IoU como métricas primárias (metas do projeto: Dice ≥ 0,85, IoU
≥ 0,75); sensibilidade, precisão por pixel e tempo por TC como métricas secundárias.
Intervalos de confiança de 95% por bootstrap não-paramétrico (10.000 reamostras,
acima do mínimo de 500 do projeto), reportados para cada método. As diferenças entre
métodos são testadas de forma pareada por paciente (teste de Wilcoxon, com correção
de Holm para as três comparações) e acompanhadas do IC95% por bootstrap da diferença
média (`scripts/run_final_results.py`).

### 2.7. Detecção de nódulos

Etapa final do pipeline (o objetivo clínico do projeto): dentro da região pulmonar
já segmentada, detectar candidatos a nódulo via blob detection (Laplacian of
Gaussian, `skimage.feature.blob_log`), restrito a uma faixa de densidade de tecido
mole. A referência (ground truth) vem de `annotations.csv` do LUNA16 (centro +
diâmetro anotado por radiologistas) — o dataset não fornece contorno pixel-a-pixel
do nódulo, então a "máscara de referência" é uma aproximação esférica, declarada
como tal.

Um achado de metodologia real durante o desenvolvimento: nódulos pequenos (mediana
~6,4mm no dataset) têm densidade medida bem mais próxima do ar do que o esperado
para tecido sólido, por efeito de volume parcial (a densidade de uma estrutura de
poucos voxels "dilui" com o ar ao redor na reamostragem). Uma faixa de densidade
inicial mais estreita excluía a maioria dos nódulos pequenos antes mesmo da
detecção rodar — ajustada após esse diagnóstico.

Avaliação no padrão FROC (Free-response ROC), o mesmo usado pelo desafio LUNA16
original: candidato é acerto (verdadeiro positivo) se seu centro cai dentro do
raio anotado do nódulo (ou 3mm, o que for maior); candidatos sem par contam como
falso positivo. Para os acertos, a "segmentação" é avaliada via Dice entre a
esfera do raio detectado e a esfera de referência (fórmula fechada de interseção
de esferas, sem rasterização).

## 3. Protocolo Experimental

- **Split treino/validação/teste por paciente** (nunca por fatia/imagem, para evitar
  vazamento de informação): **70% treino / 15% validação / 15% teste** (124 / 27 / 26
  pacientes), conforme exigido no feedback do professor, embaralhado com seed fixa
  (42). Verificação programática de que os três conjuntos são disjuntos. (Uma versão
  anterior usava 60/20/20 com 35 pacientes de teste; os resultados dela estão
  arquivados em `data/luna16/archive_split_v1_60_20_20/` e não são usados aqui.)
- **Conjunto de teste**: 26 pacientes, os mesmos para os três métodos, nunca
  utilizados em decisões de metodologia (limiar, parâmetros de morfologia, tolerância
  do region growing, hiperparâmetros da U-Net). **Ressalva honesta**: as duas
  correções de 26/10 (semente do region growing e limpeza da U-Net) foram
  diagnosticadas olhando exames que falhavam *no conjunto de teste*. Elas corrigem
  defeitos de implementação com justificativa física/anatômica, e não ajustes de
  parâmetro para subir a nota, mas o ideal seria confirmá-las num conjunto que não
  tenha sido inspecionado (por exemplo, nos 888 exames completos).
- **Reprodutibilidade**: seed fixa (42) em todas as etapas com componente aleatório
  (split, bootstrap); dependências com versão congelada (`requirements.txt`); código
  de segmentação e métricas em um pacote Python reutilizável (`src/luna16/`), não
  duplicado entre notebooks; scripts de download dos dados versionados.

## 4. Resultados

Os 26 exames de teste (split 70/15/15) são os mesmos para os três métodos, e o código
inclui as correções de 26/10. Média com IC95% por bootstrap (10.000 reamostras).
Fonte: `data/luna16/tabela_resultados_finais.csv`, gerada por
`scripts/run_final_results.py` em 09/11. Gráficos: `data/luna16/grafico_dice_iou_final.png`
e `data/luna16/grafico_comparacao_pareada.png`.

| Método | Dice | IoU | Sensibilidade | Precisão | Tempo/TC (s) | Dice mín. | Exames ≥ 0,85 |
|---|---|---|---|---|---|---|---|
| Baseline | 0,9555 [0,9416; 0,9663] | 0,9165 [0,8928; 0,9350] | 0,9308 [0,9072; 0,9492] | 0,9834 [0,9809; 0,9858] | 16,0 | 0,8468 | 25 de 26 |
| Region growing | 0,9354 [0,9006; 0,9582] | 0,8867 [0,8378; 0,9201] | 0,8986 [0,8492; 0,9323] | 0,9848 [0,9821; 0,9874] | 19,4 | 0,5941 | 24 de 26 |
| U-Net 2D | **0,9818** [0,9790; 0,9843] | **0,9644** [0,9590; 0,9691] | **0,9742** [0,9689; 0,9786] | **0,9897** [0,9882; 0,9909] | 62,1 | 0,9628 | 26 de 26 |

Os três tempos foram medidos na mesma máquina, em CPU, com o pré-processamento incluído.
Em versões anteriores, o tempo da U-Net vinha de GPU no Colab e não era comparável com
os outros dois.

**Comparação pareada** (`data/luna16/comparacao_pareada_final.csv`; Wilcoxon pareado
com correção de Holm, IC95% por bootstrap da diferença média):

| Comparação | Δ Dice médio [IC95%] | Exames em que o 1º vence | p (Holm) |
|---|---|---|---|
| U-Net − baseline | +0,0263 [0,0176; 0,0378] | 26 de 26 | < 0,001 |
| U-Net − region growing | +0,0464 [0,0254; 0,0790] | 26 de 26 | < 0,001 |
| Region growing − baseline | −0,0200 [−0,0434; −0,0064] | 2 de 26 | < 0,001 |

A U-Net é melhor que os dois métodos clássicos em todos os 26 exames de teste, e a
diferença é estatisticamente significativa. Antes das correções ela vencia o baseline em
23 de 26: as três derrotas vinham do ar fora do tórax que a rede marcava como pulmão.
Na média, o ganho é pequeno (+0,026 de Dice), porque o baseline já é muito bom. Ele se
concentra nos casos difíceis, como mostra a análise dos piores casos.

**Efeito das correções de 26/10** (`data/luna16/comparacao_correcoes.csv`; resultados
anteriores arquivados em `data/luna16/archive_pre_correcoes_2026-10-26/`): o Dice médio
do region growing foi de 0,9065 para 0,9354, e o exame que colapsava passou de 0,226
para 0,978. O da U-Net foi de 0,9781 para 0,9818, com 963 mL de falso positivo
removidos e sensibilidade inalterada. O baseline não mudou.

### 4.1. A segmentação apaga nódulos?

O Dice mede o volume do pulmão inteiro, e um nódulo de 6 mm pesa quase nada nele.
Para a etapa seguinte do pipeline (detecção de nódulos), porém, o que importa é outra
coisa: um nódulo que a máscara apaga nunca chega ao detector. Por isso verificamos, para
cada um dos 43 nódulos anotados nos 18 exames de teste que têm nódulo, se ele continua
dentro da máscara de cada método (`scripts/analise_nodulos_apagados.py`; resultado em
`data/luna16/nodulos_apagados_teste.csv`). Critérios fixados antes de rodar: o nódulo é
uma esfera com o diâmetro anotado. Ele conta como **mantido** se pelo menos 50% da esfera
está dentro da máscara, e como **colado na borda** (justapleural) se a esfera, inflada em
2 mm, toca tecido (HU > −300) fora da máscara de referência.

| Máscara | Mantidos (de 43) | Colados na borda mantidos (de 9) | No interior mantidos (de 34) | Apagados |
|---|---|---|---|---|
| Referência do LUNA16 | 42 | 8 | 34 | 1 |
| Baseline (limiar −600 HU) | 30 | 1 | 29 | 13 |
| Region growing | 28 | 1 | 27 | 15 |
| U-Net 2D | 40 | 7 | 33 | 3 |

A U-Net mantém 11 nódulos que o baseline apaga, e o contrário acontece em só 1 caso
(McNemar exato, p = 0,006). A diferença está quase toda nos nódulos **colados na
borda**: o baseline e o region growing apagam 8 dos 9, e a U-Net apaga 2. Faz sentido
pelo mecanismo. Um nódulo justapleural é tecido denso (acima de −600 HU) encostado na
parede do tórax, então o limiar o classifica como "não pulmão", e o preenchimento de
buracos não o recupera, porque ele não é um buraco fechado: está aberto para a
parede. A U-Net aprendeu com a máscara de referência, que inclui esses nódulos, e por
isso os mantém.

**Por que isso importa**: no Dice, a U-Net ganha só +0,026 do baseline. Em nódulos
apagados, a diferença é de 13 contra 3. A métrica do projeto (Dice) subestima a
vantagem da U-Net justamente no que mais importa para a etapa seguinte. Esse resultado
foi obtido primeiro na Sprint 5 e reproduzido de forma independente em 09/11, com os
mesmos números.

### 4.2. Detecção de nódulos

Avaliação em 20 pacientes com anotação de referência disponível (83 nódulos no
total, dos 240 disponíveis nos 177 pacientes baixados):

| Métrica | Valor |
|---|---|
| Sensibilidade (micro, ponderada por nódulo) | 75,9% (63/83) |
| Sensibilidade (macro, média por paciente) | 74,9% |
| Falsos positivos por exame (média) | 5.864 |
| Dice médio nos nódulos corretamente detectados | 0,424 (desvio padrão 0,203) |
| Tempo médio por exame | 82,9s |

A sensibilidade obtida é real e substancial, mas ao custo de um número de falsos
positivos que inviabiliza uso direto sem uma etapa seguinte de triagem (ver seção
5.4).

## 5. Discussão

### 5.1. A U-Net vence, mas o baseline já resolve quase tudo

Entre os métodos clássicos, o baseline superou o region growing nas duas métricas
primárias e ainda foi mais rápido. Isso combina com a natureza do problema: o ar do
parênquima fica tão separado em HU (abaixo de −600) das outras estruturas do tórax que
um limiar global bem construído já captura quase toda a informação de uma vez. A
adaptatividade local do region growing não virou vantagem prática aqui.

A U-Net venceu os dois em todos os exames, mas a margem sobre o baseline é pequena
(+0,026 de Dice) e custa cerca de 4 vezes mais tempo em CPU, além de exigir treino e
dados rotulados. A contribuição do trabalho, portanto, não é "a rede ganha". É
quantificar quanto ela ganha, onde ganha (nos casos difíceis e na borda do pulmão) e o
que isso custa. O Dice médio do pulmão inteiro esconde a diferença que mais importa
para a detecção de nódulos, a da borda: o baseline apaga 13 de 43 nódulos e a U-Net
apaga 3 (seção 4.1).

### 5.2. O achado mais importante da análise de falha foi um bug, não um caso clínico

Ao investigar por que alguns pacientes tinham Dice muito abaixo da média (~0,55-0,80,
contra >0,95 da maioria), a causa raiz não foi uma condição clínica atípica — foi um
bug real na etapa de remoção do ar de fundo: a implementação original identificava o
"fundo" da imagem usando apenas os 4 pixels de canto de cada fatia; a mesa/maca do
tomógrafo cria uma região de ar que toca a borda da imagem sem tocar exatamente um
canto, escapando dessa checagem e "colando-se" a um dos pulmões em algumas fatias.
Corrigido usando o perímetro inteiro da fatia. Esse achado — documentado com o
diagnóstico inicial incorreto e a investigação que levou à causa real — é tratado
neste trabalho como parte legítima da análise de falha: mostra que erros de pipeline
podem imitar (e às vezes superar em impacto) limitações inerentes do método
escolhido, e reforça a importância de investigar antes de concluir.

### 5.3. Detecção de nódulos: sensibilidade real, mas precisão inviável sem uma segunda etapa

O resultado de 75,9% de sensibilidade com ~5.864 falsos positivos por exame não é
uma falha de implementação — é a estrutura conhecida do problema quando se usa
detecção clássica (não aprendida) de candidatos, e é exatamente por isso que o
próprio desafio LUNA16 divide a tarefa em duas etapas: geração de candidatos (o que
este trabalho implementa) e redução de falsos positivos via classificador treinado
(o tema de Setio et al., 2016 — leitura obrigatória do projeto). O LUNA16 disponibiliza
`candidates.csv`, uma lista de candidatos pré-gerados com rótulo binário, exatamente
para treinar essa segunda etapa — implementá-la é um projeto de aprendizado
supervisionado à parte (precisaria de um classificador, possivelmente uma CNN 3D,
sobre um conjunto de treino rotulado), fora do escopo de uma abordagem clássica de
visão computacional, mas é o caminho natural de continuação.

**O que este resultado demonstra, de forma honesta**: é possível construir, com
técnicas clássicas, um gerador de candidatos com sensibilidade real para apoiar uma
segunda etapa de triagem — mas não um detector de nódulos pronto para uso direto por
um médico sem essa etapa seguinte. Essa é uma conclusão científica legítima sobre o
alcance e o limite de métodos clássicos de visão computacional aplicados a este
problema, não uma limitação escondida.

### 5.4. Custo computacional

Tempo médio por TC na mesma máquina (CPU, pré-processamento incluído): baseline 16,0 s,
region growing 19,4 s e U-Net 62,1 s. Entre os clássicos, o baseline vence em
qualidade e em tempo. A U-Net troca cerca de 4 vezes mais tempo por +0,026 de Dice e
por manter mais nódulos de borda. Os três tempos são compatíveis com processamento em
lote fora de tempo real. Com GPU, o tempo da U-Net cai bastante, mas isso exige um
hardware que o baseline dispensa.

## 6. Limitações do Domínio

*(seção obrigatória do doc do projeto, adaptada ao escopo deste trabalho — seção 5)*

- **Acurácia isolada não foi usada como métrica** neste trabalho justamente por ser
  enganosa em contextos de baixa prevalência (o doc do projeto adverte especificamente
  sobre isso para classificação de nódulos); Dice e IoU, usados aqui, já ponderam
  sobreposição de forma mais robusta.
- **O dataset (LUNA16) não inclui anotação de condições clínicas** (pulmão colapsado,
  derrame pleural etc.) nos metadados disponíveis publicamente — a análise de falha
  por metadados de aquisição (seção 5.2 do notebook do Sprint 5, correlação entre
  resolução espacial e Dice) é uma aproximação quantitativa válida, mas uma análise
  clínica completa exigiria revisão radiológica manual, fora do escopo deste projeto.
- **Nenhum modelo deste trabalho é um dispositivo médico** e nenhum resultado aqui
  deve ser usado para decisões clínicas reais — uso clínico exigiria aprovação da
  ANVISA (RDC 657/2022), validação prospectiva multicêntrica e monitoramento
  pós-mercado, conforme a seção 5.4 do doc do projeto.
- **Reprodutibilidade tratada como valor central**: seeds fixas, dependências
  congeladas, código versionado — mas a reprodutibilidade externa (fora da máquina de
  quem rodou) depende de cada pessoa configurar seu próprio token de API do Kaggle
  para baixar os dados, uma etapa manual documentada no README.
- **Escopo de subsets**: o trabalho usa 177 dos 888 pacientes totais do LUNA16
  (`subset0` + `subset1`). Isso basta para o requisito mínimo do projeto (≥20 TCs de
  teste; aqui são 26), mas validar no dataset todo daria mais potência estatística. A
  migração para os 888 exames está em andamento (`scripts/treinamento novo (888)/`).
- **A máscara de referência não é anotação manual**: `seg-lungs-LUNA16` foi gerada
  por algoritmo automático pelos organizadores do LUNA16. Concordar com ela não é o
  mesmo que concordar com a anatomia real. A inspeção visual de 12 exames de teste
  (`entrega/inspecao_visual/`) mostrou vieses sistemáticos que o Dice médio não
  revela: a traqueia entra na máscara predita do baseline em 12 de 12 exames, o
  volume predito fica sempre abaixo do de referência (em média 5%, até 22%) e 22% das
  fatias têm Dice abaixo de 0,8, mesmo com média de 0,96 por paciente.

## 7. Conclusão

O trabalho entregou as duas etapas propostas: segmentação confiável do parênquima
pulmonar (todos os três métodos acima da meta de Dice ≥ 0,85 na média; a U-Net, com
0,9818, acima dela em 26 de 26 exames e apagando só 3 de 43 nódulos, contra 13 do
baseline) e um detector de candidatos a nódulo funcional sobre essa
segmentação (75,9% de sensibilidade). A contribuição mais honesta do trabalho não é
alegar um sistema pronto para uso clínico — é demonstrar, com evidência quantitativa
rigorosa (bootstrap, testes pareados, avaliação FROC), exatamente onde métodos
clássicos de visão computacional são suficientes (segmentação de pulmão) e onde eles
alcançam um teto real que só uma etapa aprendida resolveria (redução de falsos
positivos na detecção de nódulos) — um mapa claro de próximos passos para quem
continuar este trabalho, e uma resposta honesta à pergunta que motivou o projeto:
o pipeline auxilia a *localizar* candidatos a nódulo para revisão de um especialista,
mas não substitui esse especialista nem decide diagnóstico sozinho.

## 8. Referências

- van Ginneken, B. et al. (2006). Segmentation of anatomical structures in chest
  radiographs using supervised methods. *Medical Image Analysis*.
- Hofmanninger, J. et al. (2020). Automatic lung segmentation in routine imaging is
  a data diversity problem, not a methodology problem. *European Radiology
  Experimental*.
- Ronneberger, O., Fischer, P., Brox, T. (2015). U-Net: Convolutional Networks for
  Biomedical Image Segmentation. *MICCAI*.
- Setio, A. A. A. et al. (2016). Pulmonary nodule detection in CT images: false
  positive reduction using multi-view convolutional networks. *IEEE Transactions on
  Medical Imaging*.
- Armato, S. G. et al. (2011). The Lung Image Database Consortium (LIDC) and Image
  Database Resource Initiative (IDRI). *Medical Physics*.

---

*Rascunho gerado com apoio de Claude Code a partir dos resultados reais dos
notebooks `sprint3_baseline_luna16_grp2.ipynb` a `sprint6_resultados_finais_grp2.ipynb`.
Revisar, personalizar e validar cada afirmação antes da entrega — o grupo precisa
conseguir defender todo o conteúdo na banca.*
