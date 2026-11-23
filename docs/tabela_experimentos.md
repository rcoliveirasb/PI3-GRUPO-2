# Tabela única de experimentos

Uma linha por número, pedida no feedback final ("uma tabela única de resultados"). Cada linha
diz o método, o conjunto, a **unidade** (exame ou fatia), a semente, a métrica, o valor, o
intervalo, o **commit** que gerou o arquivo e o arquivo de origem. Os conjuntos estão descritos
em [`base_oficial.md`](base_oficial.md). Atualizada em 22/11/2026.

**Regras:**
- Dois números só se comparam se tiverem o **mesmo conjunto e a mesma unidade**.
- IC95% por bootstrap de 10.000 reamostras sobre os exames.
- "Pior" é o Dice do pior exame.

## Conjuntos

| Conjunto | Exames | De onde vem | Papel |
|---|---|---|---|
| Split antigo | 35 | 60/20/20 sobre 177 exames (subset0 + subset1) | Histórico (pré-banca) |
| Teste A | 26 | 70/15/15 sobre os mesmos 177, semente 42 (`data/luna16/split_full.csv`) | Histórico a partir do teste novo |
| **Teste novo** | **107** | 70/15/15 sobre os 710 exames inéditos, semente 42 (`pji/modelos/unet_seed123/split_novo.csv`, rótulo `teste_interno`) | **Oficial para a banca** |

> **Atenção (107 e não 99):** a `base_oficial.md` fala em 99 exames de teste, depois de um
> filtro de espaçamento acima de 2,5 mm. Mas a rede final (`unet_novo_final.pt`) foi treinada
> com os **497** exames de treino, sem esse filtro (o checkpoint guarda os 497 `train_uids`),
> e foi avaliada nos **107** de `teste_interno`. Para os três métodos ficarem na mesma régua, o
> teste oficial é o de 107. O 99 vale só para o modelo do slide da Sprint 4 (linha H6).

## Resultados oficiais: teste novo (107 exames)

| ID | Método | Conjunto | Unidade | Semente | Métrica | Valor | IC95% | Pior | Commit | Arquivo | Situação |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | U-Net 2D nova (497 exames, 25 épocas) | Teste novo (107) | exame | 123 (split 42) | Dice | **0,9834** | [0,9820; 0,9845] | 0,9401 | `2f232ce` | `pji/modelos/unet_seed123/avaliacao_novo_final_teste_interno.csv` | Válido |
| R2 | U-Net 2D nova | Teste novo (107) | exame | 123 | IoU | 0,9673 | [0,9647; 0,9695] | 0,8870 | `2f232ce` | idem | Válido |
| R3 | U-Net 2D nova | Teste novo (107) | exame | 123 | Sensibilidade | 0,9827 | [0,9815; 0,9838] | 0,9618 | `2f232ce` | idem | Válido |
| R4 | U-Net 2D nova | Teste novo (107) | exame | 123 | Tempo por exame | 6,9 s | [6,5; 7,4] | — | `2f232ce` | idem | A máquina não está registrada no CSV. Em 17/11, um exame do teste levou 8,7 s em CPU na máquina da Amabilly. Se isso se confirmar, a rede nova (base 32, 25 épocas) **não** é 4× mais lenta que o baseline como a antiga (H5b): **remedir no R6** |
| R5 | U-Net 2D nova | Teste da rodada da semente 42 (125) | exame | 42 | Dice | 0,9840 | [0,9830; 0,9850] | 0,9527 | `78a5d9f` | `data/luna16/avaliacao_novo_final_seed42_teste_133.csv` | Válido, mas **outro conjunto**: 99 exames do teste novo + os 26 do Teste A |
| R5b | U-Net 2D nova | 99 exames em comum com o teste novo | exame | 42 × 123 | Dice | 0,9841 × 0,9834 | [0,9828; 0,9851] × [0,9819; 0,9846] | 0,9527 × 0,9401 | `78a5d9f` | idem + R1 | Comparação das sementes no mesmo conjunto |
| R6 | Baseline | Teste novo (107) | exame | — | Dice | **0,9492** | [0,9336; 0,9604] | 0,3806 | `a0ca409` | `data/luna16/sprint4_baseline_test_novo.csv` | Válido. IoU 0,9095; 3 exames abaixo de 0,85; 6,3 s por exame |
| R7 | Region growing | Teste novo (107) | exame | — | Dice | **0,9353** | [0,9201; 0,9479] | 0,5299 | `a0ca409` | `data/luna16/sprint4_region_growing_test_novo.csv` | Válido. IoU 0,8855; 6 exames abaixo de 0,85; 8,0 s por exame |
| R8 | U-Net 2D nova (pipeline do grupo) | Teste novo (107) | exame | 123 | Dice | **0,9838** | [0,9827; 0,9847] | 0,9550 | `a0ca409` | `data/luna16/sprint_unet_test_novo.csv` | Válido: é o número para comparar com R6 e R7. IoU 0,9681; 7,1 s por exame. Difere do R1 (0,9834) só no pós-processamento: 36 dos 107 exames têm Dice idêntico |
| R9 | U-Net − baseline / U-Net − region growing / region growing − baseline | Teste novo (107) | exame | 123 | Diferença de Dice (Wilcoxon + Holm) | +0,0346 / +0,0484 / −0,0139 | [0,0238; 0,0496] / [0,0362; 0,0631] / [−0,0282; −0,0004] | — | `a0ca409` | `data/luna16/comparacao_pareada_final_novo.csv` | Válido. U-Net melhor em 107 de 107; region growing melhor que o baseline em só 15 de 107. Teste bilateral |

**Sementes (pedido do feedback: média e variação na mesma unidade do artigo).** Roger
confirmou em 22/11 que o 0,9840 (semente 42) e o 0,9834 (semente 123) são Dice por exame (3D)
no teste, e não Dice por fatia na validação: o pico por fatia em `historico_treino.csv` fica
perto de 0,964. As duas sementes dão **0,9837 ± 0,0004** (média ± desvio-padrão, n = 2).
**Ressalva:** os dois números vêm de conjuntos diferentes. A semente 42 foi avaliada no
teste da própria rodada (125 exames), para não usar exames que podem ter entrado no treino
dela. Nos **99 exames em comum** (R5b), a comparação justa é 0,9841 × 0,9834, com média
0,9838 ± 0,0005. Uma terceira semente fecha o pedido de "duas ou três".

## Histórico: Teste A (26 exames) e split antigo

| ID | Método | Conjunto | Unidade | Versão do código | Métrica | Valor | IC95% | Pior | Commit | Arquivo | Situação |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | Baseline | Split antigo (35) | exame | antes das correções | Dice | 0,9623 | [0,9578; 0,9661] | — | — | `data/luna16/archive_split_v1_60_20_20/` | Histórico (é o "0,96" da pré-banca) |
| H2 | Region growing | Split antigo (35) | exame | antes das correções | Dice | 0,9526 | [0,9475; 0,9566] | — | — | idem | Histórico (é o "0,95" da pré-banca) |
| H3 | Baseline | Teste A (26) | exame | corrigido | Dice | **0,9555** | [0,9416; 0,9663] | 0,8468 | `6d3825d` | `data/luna16/tabela_resultados_finais.csv` | Válido, histórico |
| H4 | Region growing | Teste A (26) | exame | corrigido (semente nova) | Dice | **0,9354** | [0,9006; 0,9582] | 0,5941 | `6d3825d` | idem | Válido, histórico |
| H5 | U-Net 2D antiga (124 exames) | Teste A (26) | exame | corrigido (limpeza relativa) | Dice | **0,9818** | [0,9790; 0,9843] | 0,9628 | `6d3825d` | idem | **Válido: é o Dice da U-Net antiga** |
| H5b | U-Net 2D antiga | Teste A (26) | exame | corrigido | Tempo por exame (CPU) | 62,1 s | [57,5; 67,0] | — | `6d3825d` | idem | Baseline: 16,0 s; region growing: 19,4 s |
| H6 | U-Net 2D antiga | Teste A (26) | exame | **antes** da correção da limpeza | Dice | 0,9781 | [0,9727; 0,9824] | 0,9281 | `4c33cbd` | `tabela_resultados_finais.csv` naquela versão | Substituído por H5 |
| H7 | U-Net 2D antiga | Teste A (26) | exame | treino em GPU, pós-processamento do Colab | Dice | 0,9827 (IoU 0,9661) | — | — | `491233c` | `sprint_unet_test.csv` (26 linhas, na raiz naquele commit) e resumo expandido | Substituído por H5 |
| H8 | U-Net 2D antiga | 99 exames da fase 2 | exame | — | Dice | 0,9772 | — | 0,8268 | — | Slide da Sprint 4 | Sem arquivo; não usar |
| H9 | Region growing | Teste A (26) | exame | antes da correção da semente | Dice | 0,9065 | [0,8365; 0,9550] | 0,2263 | `4c33cbd` | idem | Substituído por H4 |
| T1 | Baseline / Region growing / U-Net 2D nova (semente 123) | Teste A (26) | exame | código corrigido | Traqueia (rótulo 5) dentro da máscara, % do volume total | 88% / 84% / 7% (1.062 / 1.017 / 85 de 1.208 mL) | — | — | *(este commit)* | `docs/traqueia/traqueia_por_exame.csv` | Válido. A U-Net semente 123 não treinou com nenhum exame do Teste A |

**Os três Dice da U-Net antiga viram um só, o H5 (0,9818).** São o mesmo modelo em três
versões do código:
- **H6 (0,9781):** antes da correção do Ruan na limpeza da máscara, que ficava com "os 2
  maiores componentes" e às vezes jogava fora um pedaço do pulmão.
- **H7 (0,9827):** rodada do Roger no Colab, com outro pós-processamento. O CSV por exame foi
  versionado no `491233c` (`sprint_unet_test.csv`, 26 exames).
- **H5 (0,9818):** código corrigido, mesmo pipeline dos outros dois métodos, CSV por exame
  versionado. É o número que vale.

**Comparação pareada no Teste A** (código corrigido, Wilcoxon com correção de Holm, fonte
`data/luna16/comparacao_pareada_final.csv`, commit `6d3825d`):
- U-Net − baseline = **+0,0263** [0,0176; 0,0378], p < 0,001; U-Net melhor em **26 de 26**
  exames.
- Region growing − baseline = **−0,0200** [−0,0434; −0,0064], p < 0,001.

## Como rodar R6 a R8 (no computador com o HD)

Desde 17/11, os scripts leem o `split_novo.csv` direto, com as colunas `seriesuid`/`split`.
Eles também aceitam `--dados`, a pasta que tem `subset*/<uid>.mhd` e `seg-lungs-LUNA16/`.
No HD as máscaras ficam em outra pasta, então antes de rodar crie um atalho uma única vez no
`cmd` do Windows:

```
mklink /J "D:\DATASET_LUNA16\ct_preparados\seg-lungs-LUNA16" "D:\DATASET_LUNA16\mascaras\seg-lungs-LUNA16\seg-lungs-LUNA16"
```

Depois, a partir da raiz do repositório:

```
python scripts/run_sprint4_evaluation.py --split pji/modelos/unet_seed123/split_novo.csv --conjunto teste_interno --dados D:/DATASET_LUNA16/ct_preparados --sufixo _novo
python scripts/run_unet_evaluation.py --split pji/modelos/unet_seed123/split_novo.csv --conjunto teste_interno --dados D:/DATASET_LUNA16/ct_preparados --checkpoint pji/modelos/unet_seed123/unet_novo_final.pt --sufixo _novo
python scripts/run_final_results.py --split pji/modelos/unet_seed123/split_novo.csv --conjunto teste_interno --sufixo _novo
```

- **O que o último comando faz:** confere se os três métodos rodaram exatamente nos mesmos
  107 exames e gera `tabela_resultados_finais_novo.csv`, `comparacao_pareada_final_novo.csv`
  e os gráficos. Os resultados dos 26 exames não são sobrescritos.
- **Se for interrompido:** os scripts retomam de onde pararam.
- **Por que rodar a U-Net de novo:** ela passa pelo mesmo script dos outros dois métodos, e
  não só pelo CSV da API, para que a limpeza da máscara seja igual nos três. A conferência foi
  feita em 17/11 com o único exame do teste que está fora do HD (`...2873394709`): o script
  deu Dice 0,9829 e o CSV da API dá 0,9829.

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
