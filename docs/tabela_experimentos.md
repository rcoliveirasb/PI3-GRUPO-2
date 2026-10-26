# Tabela única de experimentos

Uma linha por experimento: método, conjunto de teste, número de exames e Dice. Pedida na
orientação 6 do feedback da Sprint 4, para acabar com os números soltos entre os slides. Os
conjuntos de teste estão descritos em [`base_oficial.md`](base_oficial.md).

**Regra:** dois Dice só se comparam se estiverem no **mesmo conjunto de teste**. Os números
dos conjuntos A, B e do split antigo não se comparam entre si.

## Resultados

Dice médio por exame, com IC95% por bootstrap de 10.000 reamostras quando calculado.
"Pior" é o Dice do pior exame.

| ID | Método | Treino | Teste | N | Dice médio [IC95%] | Pior | Fonte | Situação |
|---|---|---|---|---|---|---|---|---|
| E1 | Baseline | — | Split antigo 60/20/20 | 35 | 0,9623 [0,9578; 0,9661] | — | `archive_split_v1_60_20_20/` | Histórico (é o "0,96" da pré-banca) |
| E2 | Region growing | — | Split antigo 60/20/20 | 35 | 0,9526 [0,9475; 0,9566] | — | `archive_split_v1_60_20_20/` | Histórico (é o "0,95" da pré-banca) |
| E3 | Baseline | — | Teste A | 26 | 0,9555 [0,9416; 0,9663] | 0,8468 | `tabela_resultados_finais.csv` | Válido, vira histórico |
| E4 | Region growing | — | Teste A | 26 | 0,9065 [0,8365; 0,9550] | 0,2263 | `tabela_resultados_finais.csv` | Válido, vira histórico |
| E5 | U-Net 2D antiga | 124 exames | Teste A | 26 | 0,9781 [0,9727; 0,9824] | 0,9281 | `tabela_resultados_finais.csv` | Válido, vira histórico |
| E6 | U-Net 2D antiga | 124 exames | Teste A | 26 | 0,9827 (IoU 0,9661) | — | Commit `ac855dc`, resumo expandido | **Não usar**: não bate com o CSV versionado (E5); origem a confirmar com o Roger |
| E7 | U-Net 2D antiga | 124 exames | Teste B | 99 | 0,9772 | 0,8268 | Slide da Sprint 4 | **A confirmar**: sem arquivo no repositório |
| E8 | U-Net 2D nova | 479 exames | Teste B | 99 | 0,9840 (máx. 0,9911) | 0,9527 | Slide da Sprint 4 | **A confirmar**: sem IC, sem arquivo no repositório, uma única semente |
| E9 | Baseline | — | Teste B | 99 | *a rodar* | | `sprint4_baseline_test_novo.csv` | Orientação 1 |
| E10 | Region growing | — | Teste B | 99 | *a rodar* | | `sprint4_region_growing_test_novo.csv` | Orientação 1 |
| E11 | U-Net 2D nova | 479 exames | Teste B | 99 | *a rodar com IC* | | `sprint_unet_test_novo.csv` | Orientação 1 |

**Comparação pareada válida hoje** (Teste A, Wilcoxon com correção de Holm, fonte
`comparacao_pareada_final.csv`):
- U-Net − baseline = **+0,0226** [0,0118; 0,0354], p < 0,001; U-Net melhor em 23 de 26
  exames.
- Region growing − baseline = **−0,0490**, p < 0,001.

## Quando os experimentos E9 a E11 forem rodados

Com o `split_novo.csv` do Roger em `data/luna16/` (colunas `uid` e `conjunto`) e os pesos da
U-Net nova, a partir da raiz do repositório:

```
python scripts/run_sprint4_evaluation.py --split data/luna16/split_novo.csv --sufixo _novo
python scripts/run_unet_evaluation.py --split data/luna16/split_novo.csv --checkpoint <pesos da U-Net nova> --sufixo _novo
python scripts/run_final_results.py --split data/luna16/split_novo.csv --sufixo _novo
```

O último comando confere se os três métodos rodaram exatamente nos mesmos 99 exames. Depois
gera `tabela_resultados_finais_novo.csv`, `comparacao_pareada_final_novo.csv` e os dois
gráficos. Os resultados dos 26 exames não são sobrescritos. Se o rótulo do teste no
`split_novo.csv` não for `test`, passe `--conjunto <rótulo>`.

## A segmentação apaga nódulos? (pedido da pré-banca)

Fonte: `scripts/run_nodulos_parede.py`, saídas `data/luna16/nodulos_parede_test.csv` e
`nodulos_parede_resumo.csv`.

- **Conjunto:** Teste A, os 43 nódulos anotados por radiologistas em 18 dos 26 exames. É a
  U-Net antiga.
- **Critério de nódulo preservado:** pelo menos 50% da esfera do nódulo (centro e diâmetro
  anotados) dentro da máscara.
- **Critério de "na borda":** a esfera encosta no limite do pulmão. Isso inclui a parede
  torácica e também o mediastino e o diafragma.

| Máscara | Nódulos preservados (todos, n = 43) | Na borda (n = 9) | No interior (n = 34) |
|---|---|---|---|
| Referência do LUNA16 | 42 | 8 | 34 |
| Baseline | 30 | **1** | 29 |
| Region growing | 28 | **1** | 27 |
| U-Net 2D antiga | **40** | **7** | 33 |

- **U-Net contra baseline:** a U-Net preserva 11 nódulos que o baseline apaga, e o contrário
  acontece em 1 caso (McNemar exato, p = 0,006).
- **U-Net contra region growing:** 13 a 1 (p = 0,002).
- **Onde estão as perdas:** o baseline perde nódulo em 8 dos 18 exames. As perdas se
  concentram nos exames com pulmão denso, os mesmos piores casos de Dice.
- **Ressalvas:**
  - a esfera é uma aproximação do contorno do nódulo;
  - nódulos do mesmo exame não são independentes, então o p é indicativo;
  - a própria referência do LUNA16 deixa de fora 1 nódulo de borda;
  - a U-Net também falha: perdeu um nódulo de 25 mm que o baseline manteve.

**Leitura:** no Dice a U-Net ganha só +0,023, mas para a etapa seguinte, a detecção, a
diferença é muito maior. O baseline apaga 13 de 43 nódulos (30%), quase todos os que encostam
na borda do pulmão, e a U-Net apaga 3. Como um nódulo apagado na segmentação nunca chega ao
detector, este é o argumento clínico mais forte do trabalho.

## Fora do escopo formal: detecção de nódulos

| ID | Experimento | Teste | Resultado | Situação |
|---|---|---|---|---|
| N1 | Blob detection (LoG) restrito ao pulmão | 20 exames, split antigo | Sensibilidade 75,9% (63/83), ~5.864 falsos positivos por exame | Histórico; não foi reprocessado no split novo |
| N2 | N1 + Random Forest para reduzir falsos positivos | 20 exames, split antigo | `sprint8c_resultados_finais.csv` | Histórico; inclusão no escopo a decidir |
