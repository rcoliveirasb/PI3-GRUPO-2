# Texto pronto para os slides — Sprint 4

Bullets de uma linha, no formato das telas. É só colar.

---

## ATIVIDADE — O QUE AVANCEI

- Inspeção visual de 12 exames do conjunto de teste (meta era ≥10).
- Análise dos 5 piores casos com os 3 métodos lado a lado, fatia a fatia.
- Notebook `analise_piores_casos_grp2.ipynb` executado e commitado.
- Dataset LUNA16 completo baixado e validado: 178 TCs + 178 máscaras, 22 GB.

## EVIDÊNCIAS — A PROVA

- Os 3 métodos no pior caso — baseline deixa de marcar 354 mL de pulmão, region growing 494 mL, U-Net 71 mL.
  *(imagem: `slide_1_evidencia_visual.png`)*
- Ganho da U-Net por quartil de dificuldade — +0,0536 nos mais difíceis contra +0,0011 nos mais fáceis.
  *(imagem: `slide_2_ganho_por_dificuldade.png`)*
- Commit `e4e355e` · `docs/piores_casos/` · 6 exames, 3 fatias, 5 painéis cada.

## O QUE ME IMPEDIU DE AVANÇAR MAIS

- Download do LUNA16: 22 GB em ~1h, com limite de taxa do Kaggle.
- Ambiente montado do zero: venv, torch, token do Kaggle.
- Sem permissão de escrita no repositório — commit feito, ainda não publicado.
- Tela de comparação depende do front, ainda em desenvolvimento.

## CONCLUSÃO

- A média esconde o argumento: 2 pontos de Dice na média, 7× mais ganho nos casos difíceis.
- O erro dos métodos clássicos é **omissão** — descartam parênquima denso que não passa no limiar de −600 HU.
- O colapso do region growing (Dice 0,226) é bug de semente, corrigível — não limitação do método.
- A U-Net também erra: marcou 672 mL de ar da mesa do tomógrafo em um exame.

## PRÓXIMOS PASSOS

- Entregar a etapa 1 da tela de comparação dos 3 métodos, com dados de exemplo.
- Publicar o commit da análise no repositório.
- Corrigir a semente do region growing (exigir semente abaixo de −750 HU).
- Descartar componentes fora do tórax na saída da U-Net.

---

# ⚠️ Antes de montar o slide

**"Link do commit" ainda não existe.** O commit `e4e355e` está só na sua máquina — o
`git push` nunca foi feito. Sem publicar, não há URL para colar no slide. Resolver isso
é pré-requisito da seção EVIDÊNCIAS.

**As duas figuras do slide ainda não estão commitadas** (ficaram fora do `e4e355e`).

---

# As figuras

| Arquivo | Tamanho | Usar em |
|---|---|---|
| `slide_1_evidencia_visual.png` | 3135×1069 | EVIDÊNCIAS |
| `slide_2_ganho_por_dificuldade.png` | 2326×1090 | EVIDÊNCIAS |

Geradas por `scripts/gerar_figuras_slide.py`, a partir da raiz do repositório.

---

# Se perguntarem na apresentação

**"E onde a U-Net perde?"** Em 3 dos 26 exames, pior perda −0,045. Num deles marcou
672,5 mL de ar do colchão/mesa do tomógrafo — dez vezes o falso positivo do baseline. Os
métodos clássicos não caem nisso porque descartam o que toca a borda da imagem; a U-Net
não tem essa regra. **É corrigível com pós-processamento.**

**"O ganho não é só ruído dos piores casos?"** Não: a queda é monótona ao longo dos quatro
quartis e a correlação entre Dice do baseline e ganho é **−0,92**.

**"A U-Net ganha em mais alguma coisa?"** Sim, e não aparece no Dice: aprendeu a excluir a
traqueia (15,7% incluída, contra 84,6% do baseline), que a referência exclui de propósito.

---

# Notas técnicas das figuras

A Figura 1 destaca apenas o **falso negativo**, o que é fiel a este exame (onde ele domina
por uma ordem de grandeza); os valores de falso positivo estão no rodapé da figura.

Cores validadas: azul `#2a78d6` e laranja `#eb6834` — contraste 4,30:1 e 3,12:1 contra a
superfície, ΔE 33,6 (visão normal) e 24,5 (protanopia), acima dos pisos de 15 e 8.

Evitei escrever "48× maior" (razão entre o primeiro e o último quartil): com denominador
de +0,0011 o número é instável e convida à objeção óbvia. O **7×** do parágrafo compara os
3 piores exames contra os outros 23, que é a comparação robusta.
