# Hipótese do trabalho — Grupo 2

## Hipótese geral

> **A segmentação automática do parênquima pulmonar em TC de tórax do LUNA16 atinge
> sobreposição útil (Dice acima da meta do projeto) com métodos clássicos baseados na
> escala de Hounsfield, e um método aprendido (U-Net 2D) supera os métodos clássicos em
> sobreposição com a máscara de referência, ao custo de mais tempo de processamento.**

O raciocínio por trás dela: o pulmão aerado tem densidade física muito diferente dos
tecidos vizinhos (cerca de −850 HU contra −100 a +400 HU), então um limiar de HU bem
escolhido já deveria separar a maior parte do parênquima. Os erros dos métodos clássicos
ficam nas fronteiras ambíguas: vasos e nódulos colados na parede, ar da mesa do tomógrafo
e via aérea. É nessas regiões que um modelo treinado, que aprende a forma do pulmão e não
só a densidade, deveria ganhar.

## Hipóteses testáveis

A hipótese geral se divide em três hipóteses, cada uma com hipótese nula (H0) e
alternativa (H1) explícitas. A unidade de análise é o **paciente** (Dice de cada um dos
26 exames do conjunto de teste, split 70/15/15). Os três métodos são avaliados nos
mesmos 26 exames, por isso os testes são pareados.

| | H0 (nula) | H1 (alternativa) | De onde vem |
|---|---|---|---|
| **H1** — meta do projeto | Dice médio ≤ meta | Dice médio > meta (0,85 para baseline e region growing; 0,75 para a U-Net) | Pergunta SMART e feedback do Checkpoint 1 |
| **H2** — adaptativo × global | Dice do region growing ≤ Dice do baseline | Dice do region growing > Dice do baseline | Plano das Sprints 3–4: o region growing foi escolhido como "abordagem avançada" por adaptar o limiar a cada pulmão |
| **H3** — aprendido × clássico | Dice da U-Net ≤ Dice do método clássico | Dice da U-Net > Dice do baseline (H3a) e > Dice do region growing (H3b) | Feedback do Checkpoint 1 (etapa de Mineração do KDD) |

### Como cada uma é testada

- **Teste de Wilcoxon** (postos sinalizados), **unilateral**, nível de significância
  α = 0,05. Usamos Wilcoxon e não o teste t porque, com 26 pacientes e casos extremos
  (o region growing tem um exame com Dice 0,59), não dá para assumir que as diferenças
  seguem uma distribuição normal.
  - H1: Wilcoxon de uma amostra sobre (Dice − meta).
  - H2 e H3: Wilcoxon pareado sobre (Dice do método B − Dice do método A), paciente a
    paciente.
- **Correção de Holm** dentro de cada família com mais de um teste (as três metas de H1;
  H3a e H3b), para controlar o falso positivo por comparações múltiplas.
- **Tamanho do efeito** com **IC95% por bootstrap** (10.000 reamostras, semente 42), para
  não depender só do p-valor.

Código: [`src/luna16/hipotese.py`](../src/luna16/hipotese.py). Executado pela etapa 5 de
[`scripts/pipeline_kdd.py`](../scripts/pipeline_kdd.py), que salva
`data/luna16/kdd/etapa5_teste_hipoteses.csv`.

## Resultado (26 exames de teste, código com as correções de 26/10)

| Hipótese | Efeito observado [IC95%] | p (Holm) | Decisão |
|---|---|---|---|
| H1 — Baseline > 0,85 | Dice médio 0,9555 [0,9416; 0,9663] | 6,0 × 10⁻⁸ | **H0 rejeitada** |
| H1 — Region growing > 0,85 | Dice médio 0,9354 [0,9006; 0,9582] | 1,9 × 10⁻⁵ | **H0 rejeitada** |
| H1 — U-Net > 0,75 | Dice médio 0,9818 [0,9790; 0,9843] | 4,5 × 10⁻⁸ | **H0 rejeitada** |
| H2 — Region growing > Baseline | Diferença −0,0200 [−0,0434; −0,0064] | 1,0 | **H0 não rejeitada** — o efeito é o **oposto** do previsto |
| H3a — U-Net > Baseline | Diferença +0,0263 [+0,0176; +0,0378] | 3,0 × 10⁻⁸ | **H0 rejeitada** |
| H3b — U-Net > Region growing | Diferença +0,0464 [+0,0254; +0,0790] | 3,0 × 10⁻⁸ | **H0 rejeitada** |

### Interpretação

- **H1 confirmada para os três métodos.** Até o método mais simples (limiar de −600 HU +
  morfologia) passa da meta de 0,85 com folga: o limite inferior do IC95% é 0,94. Isso
  confirma a primeira parte da hipótese geral: a física da TC (escala HU) já resolve a
  maior parte do problema.
- **H2 refutada.** O region growing foi **pior** que o baseline (só melhorou em 2 dos 26
  exames). No teste bilateral, essa piora é significativa (p = 7,0 × 10⁻⁵, ver
  `data/luna16/comparacao_pareada_final.csv`). A perda é de **sensibilidade**
  (0,899 contra 0,931 do baseline), com precisão praticamente igual (0,985 contra
  0,983): o region growing deixa pulmão de fora, não marca coisa errada. O mecanismo:
  a semente fica no parênquima aerado (abaixo de −750 HU, tipicamente −850 a −970), e
  a banda de ±200 HU faz o crescimento parar por volta de −650 a −770 HU, **mais
  restritivo** que o limiar global de −600 HU. O parênquima mais denso e o volume
  parcial em fatias de 2,5 mm ficam acima desse teto, então somem (nos dois piores
  exames a sensibilidade cai para 0,65 e 0,43; ver `docs/estudo_sprint5.md`, parte 4).
  "Adaptativo" não foi sinônimo de "melhor" aqui. É um resultado negativo legítimo e
  entra no relatório como tal.
- **H3 confirmada.** A U-Net supera os dois métodos clássicos em todos os 26 exames,
  e com variação muito menor (pior caso: Dice 0,963, contra 0,847 do baseline e 0,594 do
  region growing). O custo é o tempo: cerca de 62 s por exame em CPU, contra 16 s do
  baseline. Isso confirma a segunda parte da hipótese geral, incluindo o compromisso
  entre desempenho e custo computacional.

## Ressalvas (para o relatório)

1. **Quando as hipóteses foram escritas.** As metas (0,85 e 0,75) e a comparação
   baseline × region growing × U-Net foram definidas antes dos resultados (pergunta
   SMART de setembro e feedback do Checkpoint 1). A redação formal de H0/H1 e a escolha
   do teste unilateral foram escritas em 16/11, **depois** dos resultados existirem. O
   relatório deve dizer isso; não é uma pré-registração.
2. **Conjunto de teste inspecionado.** As correções de 26/10 (semente do region growing
   e limpeza da U-Net) foram diagnosticadas olhando exames do conjunto de teste. Elas
   corrigem defeitos com justificativa física, mas o ideal é confirmar as hipóteses num
   conjunto que não foi inspecionado (a base de 888 exames, ver
   [`base_oficial.md`](base_oficial.md)).
3. **n = 26.** Os p-valores são muito pequenos, mas a generalização para outros
   tomógrafos e hospitais não é testada aqui: todos os exames vêm do LIDC-IDRI.
4. **Referência imperfeita.** O "gabarito" (máscaras `seg-lungs-LUNA16`) também é gerado
   por algoritmo; em alguns exames a U-Net discorda do gabarito e parece estar certa
   (ver [`discordancia_unet/`](discordancia_unet/)). Parte da diferença entre os métodos
   pode ser erro do gabarito.
