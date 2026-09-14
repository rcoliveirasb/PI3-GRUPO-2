# Esboço de Apresentação — Grupo 02

> Rascunho de estrutura de slides, não os slides em si. Pensado pra servir tanto o
> Seminário 3 (foco: resultados do baseline vs. region growing) quanto a Banca Final
> (escopo completo) — os slides marcados **[Só Banca Final]** só entram na
> apresentação de final de semestre. Adaptem quantidade de slides ao tempo que
> vocês tiverem (peça o tempo alocado antes de fechar o número de slides).

---

**Slide 1 — Capa**
Título do projeto, nomes do grupo, disciplina, data.

**Slide 2 — Contexto e motivação**
Por que segmentar o parênquima pulmonar é o primeiro passo antes de qualquer análise
de nódulos. 1 imagem de TC de tórax com o pulmão destacado ajuda mais que texto aqui.

**Slide 3 — Pergunta de pesquisa / objetivo**
Comparar baseline (threshold + morfologia) vs. region growing, medindo Dice/IoU,
metas do projeto (≥0,85 / ≥0,75).

**Slide 4 — Dataset**
LUNA16, 177 pacientes (`subset0`+`subset1`), split por paciente (60/20/20),
35 no teste. Uma frase sobre por que split por paciente importa (evita vazamento).

**Slide 5 — Pipeline (visão geral)**
Diagrama simples: Seleção → Pré-processamento → Segmentação → Avaliação. Esse é o
slide "mapa" que ancora o resto da apresentação — voltem nele entre seções se a
banca perguntar "onde vocês estão nesse fluxo".

**Slide 6 — Baseline: threshold -600HU + morfologia**
1 imagem mostrando CT → máscara predita, lado a lado. Mencionar os 4 passos
(threshold, remoção de fundo, componentes, buracos+morfologia) em bullets curtos,
não em detalhe de código.

**Slide 7 — Region growing**
Mesma lógica do slide 6: 1 imagem, mecanismo em 2-3 bullets (sementes automáticas,
crescimento por tolerância de intensidade).

**Slide 8 — Resultados: tabela final**
A tabela de `sprint6_resultados_finais_grp2.ipynb` (Dice, IoU, sensibilidade,
precisão, tempo, com IC95%). Esse é provavelmente o slide mais importante — não
apressem ele.

**Slide 9 — Resultados: gráfico comparativo**
O gráfico de barras com IC95% (`grafico_dice_iou_final.png`) ou o gráfico pareado
por paciente (`grafico_comparacao_pareada.png`) — usem o que contar a história mais
clara pro tempo que tiverem.

**Slide 10 — O achado inesperado: um bug, não um caso clínico**
Vale um slide próprio. Conta bem: "esperávamos achar um caso clínico difícil, achamos
um bug de implementação" — mostra maturidade de investigação, não é um ponto fraco
esconder. 1 imagem antes/depois (máscara com o vazamento vs. corrigida) é o slide
mais visual da apresentação.

**Slide 11 — Discussão: por que o método simples venceu**
Explicação física (ar do pulmão é muito bem separado em HU) + a citação do doc do
projeto sobre método simples bem avaliado > método complexo mal documentado.

**Slide 11-B — Detecção de nódulos (o objetivo clínico)**
Este é o slide que responde "isso ajuda o médico?". 3 pontos: (1) usamos o pulmão
já segmentado pra restringir a busca; (2) sensibilidade real de ~76% em 83 nódulos
testados; (3) só funciona como **triagem** — ~5.864 falsos positivos por exame em
média, então precisaria de uma segunda etapa (classificador treinado) antes de
qualquer uso prático. Sejam diretos sobre isso, é uma resposta científica honesta,
não uma fraqueza a esconder.

**Slide 12 — Limitações**
3-4 bullets: dataset sem anotação clínica; nenhum modelo é dispositivo médico;
177/888 pacientes do LUNA16 usados; reprodutibilidade depende de token pessoal do
Kaggle.

**Slide 13 — Conclusão**
1 frase de fechamento + recomendação prática (qual método o grupo recomenda e por quê).

---

## **[Só Banca Final]** Slides adicionais

**Slide 14 — Linha do tempo do projeto**
Sprint 1 a 6, 1 linha por sprint, o que foi entregue em cada uma — mostra processo,
não só resultado final.

**Slide 15 — Metodologia KDD completa**
As 5 etapas (Seleção → Pré-processamento → Segmentação → Avaliação → Interpretação)
com 1 exemplo concreto do projeto em cada uma.

**Slide 16 — Reprodutibilidade**
Screenshot do README + menção rápida a seeds fixas, requirements congelado, scripts
versionados — mostra que reprodutibilidade foi tratada como valor, não burocracia.

**Slide 17 — Trabalhos futuros**
Classificador de redução de falsos positivos pra detecção de nódulos (usando
`candidates.csv`, já disponível — é o próximo passo mais natural e mais impactante);
U-Net pré-treinada para segmentação de pulmão (não explorada); validação em todo o
LUNA16 (888 pacientes); análise clínica manual dos casos com Dice relativamente
mais baixo.

**Slide 18 — Referências**
As 5 citações do relatório (van Ginneken 2006, Hofmanninger 2020, Ronneberger 2015,
Setio 2016, Armato 2011).

---

## Notas de preparação (não são slides)

- **Ensaiem com cronômetro** — este esboço não tem número de slides fixo porque isso
  depende do tempo alocado; cortem/expandam a lista acima proporcionalmente.
- Cada pessoa do grupo devia conseguir explicar o slide 10 (o bug) e o slide 11 (por
  que o método simples venceu) sem ler o slide — são os dois pontos mais prováveis
  de pergunta da banca.
- Se perguntarem "por que vocês não usaram U-Net": a resposta honesta é que o doc do
  projeto sugere region growing como mais viável para o nível da turma, e o grupo
  priorizou fazer uma comparação rigorosa entre 2 métodos bem avaliados em vez de 3
  métodos mal avaliados — consistente com a lição da seção 4.7 do próprio doc.
