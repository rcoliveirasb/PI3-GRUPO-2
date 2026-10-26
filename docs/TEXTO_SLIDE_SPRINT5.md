# Texto para os slides — Sprint 5

Bullets de uma linha, no formato das telas. É só colar.

---

## ATIVIDADE — O QUE AVANCEI

- Corrigidos os 2 bugs que a análise da Sprint 4 tinha diagnosticado.
- Semente do region growing: agora exige voxel abaixo de −750 HU.
- Saída da U-Net: descarta componentes fora do tórax, reusando a regra que os métodos clássicos já tinham.
- Medição antes/depois nos 26 exames de teste, no mesmo volume e pré-processamento.

## EVIDÊNCIAS — A PROVA

- Region growing: Dice médio 0,9065 → 0,9355. O exame que colapsava foi de **0,226 para 0,978**.
- U-Net: **553 mL de falso positivo removidos** nos 26 exames, com sensibilidade média intacta (0,9742).
- Dice mínimo da U-Net: 0,9281 → 0,9628.
- Nenhuma regressão real: 0 exames pioraram no region growing, 1 variou −0,0003 na U-Net.
- Commit: `[link]`

## O QUE ME IMPEDIU DE AVANÇAR MAIS

- Medição completa leva ~20 min (26 exames × 2 métodos × 2 versões).
- Continuo sem permissão de escrita no repositório.
- Tela de comparação ainda depende do front.
- Figuras e notebook da Sprint 4 ainda citam os números antigos.

## CONCLUSÃO

- As correções são cirúrgicas: 24 dos 26 exames ficaram idênticos no region growing.
- A limpeza da U-Net tirou falso positivo sem custar sensibilidade — prova de que só removeu o que não era pulmão.
- Melhorou pouco na média e muito onde estava pior — o mesmo padrão que documentamos na Sprint 4.
- Os 2 piores casos do region growing continuam ruins — mas é outra falha (perde pulmão), não a semente.

## PRÓXIMOS PASSOS

- Regerar figuras e notebook com os números corrigidos.
- Publicar as correções no repositório.
- Entregar a etapa da tela de comparação dos 3 métodos.
- Remover a traqueia da predição — viés presente em 100% dos exames.

---

# Se perguntarem

**"O ganho de +0,0022 na U-Net não é irrelevante?"**
Na média sim, e é esperado. O que importa é o mínimo, que subiu de 0,9281 para 0,9628, e
os 553 mL de falso positivo removidos. É o mesmo padrão que a gente documentou na Sprint 4:
melhorou pouco na média e muito onde estava pior.

**"Como vocês sabem que a limpeza não comeu pulmão junto?"**
A sensibilidade média ficou idêntica até a quarta casa decimal (0,9742) nos 26 exames. Se
o filtro tivesse removido pulmão verdadeiro, ela teria caído.

**"Por que o region growing ainda tem exames ruins?"**
Porque são outra falha. Nos dois que sobraram a sensibilidade é 0,43 e 0,65 — o método
está perdendo pulmão, não marcando coisa errada. É o mesmo problema do baseline
(parênquima denso, fatia de 2,5 mm), que a correção da semente não alcança.

**"Vocês consertaram o concorrente?"**
Sim, de propósito. O region growing não é nosso método; corrigi-lo deixa a comparação mais
justa, não menos. Um trabalho que só conserta o método que defende é menos confiável.

---

# Números de apoio (não cabem no slide)

| | Region growing | U-Net |
|---|---|---|
| Dice médio | 0,9065 → 0,9355 | 0,9781 → 0,9804 |
| Dice mínimo | 0,2263 → 0,5941 | 0,9281 → 0,9628 |
| Melhoraram / pioraram / iguais | 2 / 0 / 24 | 7 / 1 / 18 |
| Falso positivo médio | 71,2 → 70,4 mL | 88,1 → 66,8 mL |
| Sensibilidade média | 0,8666 → 0,8986 | 0,9742 → 0,9742 |

Exames que mudaram na U-Net, com o falso positivo antes e depois:

| Exame | Dice | FP (mL) |
|---|---|---|
| `…696274044574` | 0,9281 → 0,9679 | 672,5 → 239,4 |
| `…280013275227` | 0,9673 → 0,9818 | 133,1 → 47,3 |
| `…604069960014` | 0,9687 → 0,9711 | 95,3 → 82,1 |
| `…326263147663` | 0,9777 → 0,9789 | 40,7 → 31,9 |

Dados completos em `data/luna16/comparacao_correcoes.csv`.
