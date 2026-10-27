# Texto para os slides — Sprint 5

Versão final, já com os números da medição completa nos 26 exames. É só copiar.

---

## ATIVIDADE — O QUE AVANCEI

- Corrigidos os 2 bugs que a análise da Sprint 4 tinha diagnosticado.
- Semente do region growing: agora exige voxel abaixo de −750 HU.
- Saída da U-Net: descarta componentes fora do tórax, reusando a regra que os métodos clássicos já tinham.
- Medição antes/depois nos 26 exames, no mesmo volume e pré-processamento.
- Correções publicadas no repositório.

## EVIDÊNCIAS — A PROVA

- Region growing: Dice médio 0,9065 → 0,9355. O exame que colapsava foi de 0,226 para 0,978.
- U-Net: **963 mL de falso positivo removidos** nos 26 exames, com sensibilidade média intacta (0,9742).
- O exame em que a U-Net perdia virou o melhor dela: 0,9281 → **0,9864**, acima do baseline (0,9732).
- Nenhuma regressão real: 0 pioraram no region growing, 1 variou −0,0003 na U-Net.
- O ganho médio da U-Net é +0,0037 — parece pouco, mas 13 dos 26 exames melhoraram e o falso positivo médio caiu 42%.

## O QUE ME IMPEDIU DE AVANÇAR MAIS

- Medição completa leva ~40 min (26 exames × 2 métodos × 2 versões).
- A primeira versão da correção da U-Net tinha um bug e exigiu remedir tudo.
- Tela de comparação ainda no aguardo da API e design.

## CONCLUSÃO

- As correções são cirúrgicas: 24 dos 26 exames ficaram idênticos no region growing.
- A limpeza da U-Net tirou falso positivo sem custar sensibilidade — prova de que só removeu o que não era pulmão.
- Achar o bug da própria correção só foi possível porque olhamos a imagem, não só o número.
- Os 2 piores casos do region growing continuam ruins — mas é outra falha, não a semente.

## PRÓXIMOS PASSOS

- Regerar figuras e notebook com os números corrigidos.
- Entregar a etapa da tela de comparação dos 3 métodos.
- Remover a traqueia da predição — viés presente em 100% dos exames.

---

# Se perguntarem

**"O ganho de +0,0037 na U-Net não é irrelevante?"**
Na média sim, e é esperado. O que importa é que **13 dos 26 exames melhoraram**, o falso
positivo médio caiu de 88,1 para 51,1 mL, e o pior caso dela subiu de 0,9281 para 0,9864.
É o mesmo padrão da Sprint 4: melhorou pouco na média e muito onde estava pior.

**"Como vocês sabem que a limpeza não comeu pulmão junto?"**
A sensibilidade média ficou idêntica até a quarta casa (0,9742) nos 26 exames, enquanto
963 mL de falso positivo saíam. Se o filtro tivesse removido pulmão verdadeiro, ela teria
caído.

**"Vocês disseram que a U-Net perdia num exame. E agora?"**
Aquela perda era o próprio bug. Com o pós-processamento corrigido, aquele exame vai de
0,9281 para 0,9864 e o falso positivo dele cai de 672,5 para 50,0 mL — passou a ser o
melhor resultado da U-Net, acima do baseline.

**"Qual era o bug da primeira versão da correção?"**
Ela mantinha "os 2 maiores componentes". Mas na saída da rede os dois pulmões vêm grudados
num componente só, então a segunda vaga sobrava para o maior blob de ar da mesa. Trocamos
por "componentes de tamanho comparável ao maior" — dois pulmões têm tamanhos parecidos,
um blob espúrio é uma ordem de grandeza menor.

**"Por que o region growing ainda tem exames ruins?"**
Porque são outra falha. Nos dois que sobraram a sensibilidade é 0,43 e 0,65 — o método
está perdendo pulmão, não marcando coisa errada. É o mesmo problema do baseline
(parênquima denso, fatia de 2,5 mm), que a correção da semente não alcança.

---

# Números de apoio (não cabem no slide)

| | Region growing | U-Net |
|---|---|---|
| Dice médio | 0,9065 → 0,9355 | 0,9781 → 0,9818 |
| Dice mínimo | 0,2263 → 0,5941 | 0,9281 → 0,9628 |
| Melhoraram / pioraram / iguais | 2 / 0 / 24 | 13 / 1 / 12 |
| Falso positivo médio | 71,2 → 70,4 mL | 88,1 → 51,1 mL |
| Sensibilidade média | 0,8666 → 0,8986 | 0,9742 → 0,9742 |

Os quatro maiores ganhos da U-Net, com o falso positivo antes e depois:

| Exame | Dice | FP (mL) |
|---|---|---|
| `…696274044574` | 0,9281 → 0,9864 | 672,5 → 50,0 |
| `…280013275227` | 0,9673 → 0,9818 | 133,1 → 47,3 |
| `…604069960014` | 0,9687 → 0,9799 | 95,3 → 34,7 |
| `…360275453085` | 0,9769 → 0,9852 | 207,6 → 62,9 |

Dados completos em `data/luna16/comparacao_correcoes.csv`.

**Nota sobre o Dice mínimo da U-Net:** ele continua 0,9628 porque o exame com o pior
resultado passou a ser outro — o de fatia de 2,5 mm (`…021509831276`), que não tinha ar de
mesa e portanto não foi afetado pela correção.
