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
investigação. Para (1), comparamos duas técnicas clássicas: um baseline de
limiarização em Unidades Hounsfield (HU) com operações morfológicas, e region
growing com sementes automáticas. Usando 177 pacientes do dataset público LUNA16
(35 reservados para teste, split por paciente), avaliamos ambos os métodos contra
as máscaras de referência oficiais, usando Dice Coefficient e IoU como métricas
primárias, com intervalos de confiança de 95% por bootstrap (500 reamostras). O
baseline atingiu Dice médio de 0,962 (IC95% [0,958; 0,966]) e o region growing
0,953 (IC95% [0,948; 0,957]) — diferença estatisticamente significativa a favor do
baseline, que também foi mais rápido; ambos superaram a meta do projeto (Dice ≥
0,85) em 100% dos pacientes de teste. Para (2), implementamos um detector de
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
segmentação médica com aprendizado profundo, não utilizada na abordagem principal
deste trabalho (ver seção 7, Limitações).

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
distância), incluindo vizinhos com intensidade dentro de uma banda de tolerância
(±200 HU) ao redor do valor da semente. O crescimento é restrito à mesma região
"segura" do baseline, pelo mesmo motivo (evitar vazamento pela via aérea).

### 2.5. Avaliação

Dice Coefficient e IoU como métricas primárias (metas do projeto: Dice ≥ 0,85, IoU
≥ 0,75); sensibilidade, precisão por pixel e tempo por TC como métricas secundárias.
Intervalos de confiança de 95% por bootstrap não-paramétrico (500 reamostras),
reportados para cada método isoladamente e para a diferença pareada por paciente
entre os dois métodos.

### 2.6. Detecção de nódulos

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
  vazamento de informação): 60% treino / 20% validação / 20% teste, embaralhado com
  seed fixa (42). Verificação programática de que os três conjuntos são disjuntos.
- **Conjunto de teste**: 35 pacientes, nunca utilizados em nenhuma decisão de
  metodologia (limiar, parâmetros de morfologia, tolerância do region growing) —
  todas essas escolhas foram feitas e validadas nos conjuntos de treino/piloto antes
  da avaliação final reportada aqui.
- **Reprodutibilidade**: seed fixa (42) em todas as etapas com componente aleatório
  (split, bootstrap); dependências com versão congelada (`requirements.txt`); código
  de segmentação e métricas em um pacote Python reutilizável (`src/luna16/`), não
  duplicado entre notebooks; scripts de download dos dados versionados.

## 4. Resultados

*(tabela extraída de `data/luna16/tabela_resultados_finais.csv`, gerada em
`sprint6_resultados_finais_grp2.ipynb` — colar a tabela/imagem exata dessa execução
aqui na versão final)*

| Método | Dice | IoU | Sensibilidade | Precisão | Tempo/TC (s) |
|---|---|---|---|---|---|
| Baseline | 0,962 [0,958; 0,966] | 0,928 [0,920; 0,935] | 0,943 [0,935; 0,950] | 0,982 [0,980; 0,984] | 15,1 |
| Region growing | 0,953 [0,948; 0,957] | 0,910 [0,901; 0,917] | 0,923 [0,914; 0,930] | 0,985 [0,983; 0,987] | 17,6 |

Diferença pareada (region growing − baseline) em Dice: −0,010 (IC95% [−0,013; −0,007])
— estatisticamente significativa a favor do baseline. Mesma direção para IoU e
sensibilidade. Region growing supera o baseline apenas em precisão, por margem pequena
(+0,002, IC95% [0,002; 0,003]).

**100% dos 35 pacientes de teste atingiram Dice ≥ 0,85 em ambos os métodos** — a meta
do projeto foi cumprida com folga por ambas as abordagens.

### 4.1. Detecção de nódulos

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

### 5.1. Por que o método mais simples venceu

O baseline superou o region growing nas duas métricas primárias do projeto, além de
ser mais rápido. Isso é consistente com a natureza do problema: o ar do parênquima
pulmonar é tão distintamente separado em HU (abaixo de -600) de qualquer outra
estrutura torácica que um limiar global bem construído já captura quase toda a
informação relevante de uma vez — a adaptatividade local do region growing não se
traduziu em vantagem prática aqui. Isso não invalida o region growing como técnica em
geral; sugere que sua vantagem relativa tende a aparecer em alvos com fronteiras
menos nítidas ou tecido mais heterogêneo, não neste problema específico.

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

O baseline domina em ambas as dimensões relevantes (Dice/IoU e tempo) — não há um
trade-off real a favor do region growing nesta tarefa específica. Tempo médio de
15,1s (baseline) e 17,6s (region growing) por TC, ambos compatíveis com uso em lote
fora de tempo real, mas o baseline oferece margem maior para escalonamento.

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
  (`subset0` + `subset1`) — suficiente para os requisitos mínimos do projeto (≥20 TCs
  de teste, com folga: 35), mas uma validação em todo o dataset daria maior potência
  estatística.

## 7. Conclusão

O trabalho entregou as duas etapas propostas: segmentação confiável do parênquima
pulmonar (baseline com Dice 0,962, superando a meta do projeto com folga em 100%
dos pacientes de teste) e um detector de candidatos a nódulo funcional sobre essa
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
