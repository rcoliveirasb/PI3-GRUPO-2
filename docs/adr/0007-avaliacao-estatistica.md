# 0007 - Avaliar por exame, com IC95% por bootstrap e Wilcoxon pareado

Status: Aceito
Data: 2026-10-05

## Contexto

As primeiras versões traziam médias de Dice soltas, sem intervalo e sem teste. No Checkpoint
1, o professor também apontou um erro conceitual: Kappa e acurácia são métricas de
classificação e não servem para comparar máscaras.

Os três métodos são avaliados **nos mesmos exames**, e as diferenças entre eles são
pequenas (centésimos de Dice). Sem estatística, não dá para dizer se uma diferença é real.
O Dice por exame não segue distribuição normal: a maioria fica acima de 0,95, com poucos
exames muito ruins.

## Decisão

- **Unidade: o exame** (Dice 3D sobre o volume inteiro), não a fatia.
- **Métricas**: Dice e IoU como primárias; sensibilidade, precisão e tempo como
  secundárias.
- **IC95% por bootstrap** com **10.000 reamostras** e semente 42, em toda média.
- **Comparação pareada** pelo **teste de Wilcoxon unilateral**, que não supõe normalidade,
  com **correção de Holm** para várias comparações e α = 0,05.
- Hipóteses com H0 e H1 escritas (`docs/hipotese.md`): H1 (meta de Dice), H2 (region
  growing > baseline) e H3 (U-Net > clássicos).
- Implementado em `scripts/run_final_results.py` e `src/luna16/hipotese.py`.

## Consequências

**Melhora**
- Cada afirmação do relatório tem intervalo e p-valor. Exemplo: o region growing ficou
  −0,0139 [−0,0282; −0,0004] abaixo do baseline, e por isso H2 foi refutada.
- O teste pareado usa o fato de os métodos serem medidos nos mesmos exames, o que dá mais
  poder que comparar duas médias.
- Qualquer pessoa recalcula tudo a partir dos CSVs, com o mesmo resultado.

**Piora**
- Um teste unilateral precisa da direção definida antes. Algumas hipóteses foram
  formalizadas depois dos primeiros resultados do Teste A, e isso está declarado como
  ressalva. O teste de 107 exames, que não tinha sido usado, reduz esse problema.
- A média esconde os piores casos. Por isso o projeto relata também o pior exame e quantos
  exames ficaram abaixo de 0,85, e analisa os piores casos à parte.
- Com 10.000 reamostras, o cálculo leva alguns segundos a mais, o que é aceitável.
