# Processo KDD do Grupo 2

O projeto segue o processo de **Knowledge Discovery in Databases** (Fayyad, Piatetsky-Shapiro
e Smyth, 1996): cinco etapas em sequência que levam dos dados brutos ao conhecimento
validado. Aqui os "dados" são tomografias (TC) de tórax do LUNA16 e o "conhecimento" é a
resposta à hipótese do trabalho ([`hipotese.md`](hipotese.md)): qual método segmenta melhor
o parênquima pulmonar, e a que custo.

As cinco etapas estão implementadas em um único script, que roda tudo em ordem e salva a
evidência de cada etapa:

```
python scripts/pipeline_kdd.py                 # ~1 min (reexecuta os 3 métodos em 1 exame)
python scripts/pipeline_kdd.py --reexecutar 26 # refaz a mineração inteira (~40 min em CPU)
```

Saídas em `data/luna16/kdd/`, com um resumo legível em `data/luna16/kdd/relatorio_kdd.md`.

```
 Dados brutos        1. Seleção       2. Pré-proc.       3. Transformação     4. Mineração        5. Interpretação
 LUNA16 (.mhd/.raw) ─► critérios de ─► HU limpo,      ─► 1 mm isotrópico, ─► baseline,        ─► IC95% bootstrap,
 + máscaras ref.       inclusão,       ruído filtrado    fatias 128×128      region growing,     teste das hipóteses
                       split 70/15/15                    para a U-Net        U-Net 2D            H1, H2, H3
```

## 1. Seleção

**O que faz:** escolhe quais exames entram no estudo e separa treino, validação e teste.

- Lê só o cabeçalho de cada exame baixado (subset0 + subset1 do LUNA16).
- Critérios de exclusão: sem máscara de referência; máscara vazia; espaçamento entre
  fatias acima de 2,5 mm.
- Split **por paciente** (nunca por fatia, para não vazar o mesmo paciente entre treino e
  teste): 70/15/15, semente 42, com verificação programática de que os três conjuntos são
  disjuntos.

| Código | Evidência |
|---|---|
| [`src/luna16/selection.py`](../src/luna16/selection.py), [`src/luna16/splits.py`](../src/luna16/splits.py), [`scripts/regenerate_split_70_15_15.py`](../scripts/regenerate_split_70_15_15.py) | `kdd/etapa1_selecao.csv` (um exame por linha, com o motivo de exclusão); `data/luna16/split_full.csv` |

**Resultado:** 178 exames encontrados, 177 incluídos. O excluído (`…216652640878960522552873394709`)
tem espaçamento de 2,5000002 mm no cabeçalho, que passa do limite de 2,5 mm (é o "exame com
geometria divergente" de [`base_oficial.md`](base_oficial.md)). Split: 124 treino, 27
validação, 26 teste. Critérios detalhados em [`criterios_inclusao.md`](criterios_inclusao.md).

## 2. Pré-processamento

**O que faz:** limpa os valores de cada exame, mantendo a unidade física (HU), porque o
limiar de −600 HU do baseline só faz sentido em HU real.

- O valor de *padding* fora do campo de visão circular do tomógrafo (−2048/−3024 HU, não é
  tecido) vira ar (−1000 HU).
- Recorte para a faixa [−1000, +400] HU: acima disso é osso ou contraste, irrelevante para
  o pulmão.
- Filtro Gaussiano leve (σ = 0,5 voxel) para reduzir ruído sem borrar a borda do pulmão.

| Código | Evidência |
|---|---|
| [`src/luna16/preprocessing.py`](../src/luna16/preprocessing.py) (`clean_hu`, `denoise`) | `kdd/etapa2_3_preprocessamento_transformacao.json` e `.png` |

**Resultado (exame de exemplo):** HU bruto [−3024, 2211] → [−1000, 400]; 21% dos voxels
eram padding fora do campo de visão.

## 3. Transformação

**O que faz:** coloca todos os exames no mesmo formato, para que os métodos sejam
comparáveis e a U-Net receba sempre a mesma entrada.

- **Reamostragem isotrópica para 1 mm** (SimpleITK): os exames têm espaçamento entre
  fatias de 0,5 a 2,5 mm; sem isso, elementos estruturantes morfológicos e distâncias
  teriam tamanhos físicos diferentes em cada exame. Interpolação linear para a TC e
  vizinho mais próximo para a máscara de referência, que precisa continuar binária.
- **Para a U-Net:** cada fatia axial é normalizada para [−1, 1] e redimensionada para
  128 × 128.
- Mesma transformação para os três métodos e para a máscara de referência, então o Dice é
  sempre calculado no mesmo espaço.

| Código | Evidência |
|---|---|
| [`src/luna16/preprocessing.py`](../src/luna16/preprocessing.py) (`resample_isotropic`), [`src/luna16/unet.py`](../src/luna16/unet.py) (`hu_to_input`), [`src/luna16/pipeline.py`](../src/luna16/pipeline.py) | `kdd/etapa2_3_preprocessamento_transformacao.json` e `.png` |

**Resultado (exame de exemplo):** 161 × 512 × 512 voxels de 0,55 × 0,55 × 1,25 mm →
201 × 281 × 281 voxels de 1 mm.

## 4. Mineração de dados

**O que faz:** aplica os três métodos de segmentação e mede cada um contra a máscara de
referência, nos mesmos 26 exames de teste.

| Método | Ideia | Código |
|---|---|---|
| Baseline | Limiar global em −600 HU + remoção do fundo fatia a fatia + 2 maiores componentes + preenchimento de buracos + abertura morfológica | [`baseline.py`](../src/luna16/baseline.py), [`lung_air.py`](../src/luna16/lung_air.py) |
| Region growing | Semente automática dentro de cada pulmão (abaixo de −750 HU), crescimento com banda de ±200 HU em torno da semente | [`region_growing.py`](../src/luna16/region_growing.py) |
| U-Net 2D | Rede treinada (BCE + Dice, 25 épocas, GPU no Colab) nos 124 exames de treino, com limpeza espacial de componentes fora do tórax | [`unet.py`](../src/luna16/unet.py), [`train_unet_baseline.py`](../scripts/train_unet_baseline.py) |

Métricas por paciente: Dice, IoU, sensibilidade, precisão e tempo
([`metrics.py`](../src/luna16/metrics.py)).

| Evidência |
|---|
| `data/luna16/sprint4_baseline_test.csv`, `sprint4_region_growing_test.csv`, `sprint_unet_test.csv` (um paciente por linha) |
| `kdd/etapa4_mineracao_reprodutibilidade.csv`: o script **reexecuta** os três métodos do zero e confere que o Dice bate com o salvo (tolerância 0,0001) |

**Resultado:** a reexecução reproduz exatamente o Dice salvo nos três métodos. Isso foi
verificado em 16/11 e de novo em 22/11, com as bibliotecas atualizadas (SimpleITK 2.5.8).

**Teste novo (oficial, 107 exames).** O mesmo código também foi rodado nos 107 exames de
`teste_interno` do `split_novo.csv` (commit `a0ca409`).
- A U-Net usada é a **semente 123**, treinada nos 497 exames de treino da base de 888
  (`pji/modelos/unet_seed123`).
- Os volumes desses exames ficam no HD externo do Roger, por isso o script não os reexecuta.
  A etapa 5 parte dos CSVs por exame já salvos:
  `sprint4_baseline_test_novo.csv`, `sprint4_region_growing_test_novo.csv` e
  `sprint_unet_test_novo.csv`.
- **Nenhum dos 107 exames está entre os 177 da primeira fase.** Ou seja, o teste novo não
  inclui o Teste A, que foi inspecionado nas correções de 26/10.

## 5. Interpretação e avaliação

**O que faz:** transforma os números em conclusões, com incerteza explícita.

- Média de cada métrica com **IC95% por bootstrap** (10.000 reamostras).
- **Teste formal das hipóteses** H1, H2 e H3 (Wilcoxon unilateral pareado, correção de
  Holm, α = 0,05). Detalhes em [`hipotese.md`](hipotese.md).
- Análise qualitativa dos erros: piores casos ([`piores_casos/`](piores_casos/)), exames em
  que a U-Net discorda do gabarito ([`discordancia_unet/`](discordancia_unet/)) e nódulos
  apagados pela segmentação.

| Código | Evidência |
|---|---|
| [`src/luna16/hipotese.py`](../src/luna16/hipotese.py), [`scripts/run_final_results.py`](../scripts/run_final_results.py) | Teste novo: `kdd/etapa5_tabela_resultados_novo.csv`, `kdd/etapa5_teste_hipoteses_novo.csv`, `data/luna16/grafico_dice_iou_final_novo.png`. Teste A: `kdd/etapa5_tabela_resultados.csv`, `kdd/etapa5_teste_hipoteses.csv`, `data/luna16/grafico_dice_iou_final.png`. Os dois: `kdd/relatorio_kdd.md` |

**Resultado no teste novo (oficial, 107 exames):**

| Método | Dice [IC95%] | IoU [IC95%] | Pior exame | Exames < 0,85 | Tempo por exame* |
|---|---|---|---|---|---|
| Baseline | 0,9492 [0,9336; 0,9604] | 0,9095 [0,8892; 0,9246] | 0,381 | 3 | 6,3 s |
| Region growing | 0,9353 [0,9201; 0,9479] | 0,8855 [0,8645; 0,9034] | 0,530 | 6 | 8,0 s |
| U-Net 2D (semente 123) | **0,9838** [0,9827; 0,9847] | **0,9681** [0,9660; 0,9698] | 0,955 | 0 | 7,1 s |

\* Os tempos foram medidos na máquina do Roger e não se comparam com os do Teste A, que
foram medidos em outra máquina e com outra rede.

- **H1 confirmada:** os três métodos passam da meta.
- **H2 refutada:** o region growing foi pior que o baseline: −0,0139 [−0,0282; −0,0004].
  Ele foi melhor em só 15 dos 107 exames.
- **H3 confirmada:** a U-Net supera os dois métodos clássicos em **todos os 107 exames**
  (+0,0346 sobre o baseline e +0,0484 sobre o region growing).

**Histórico: Teste A (26 exames, U-Net antiga treinada com 124 exames):**

| Método | Dice [IC95%] | IoU [IC95%] | Tempo por exame |
|---|---|---|---|
| Baseline | 0,9555 [0,9416; 0,9663] | 0,9165 [0,8928; 0,9350] | 16 s |
| Region growing | 0,9354 [0,9006; 0,9582] | 0,8867 [0,8378; 0,9201] | 19 s |
| U-Net 2D | 0,9818 [0,9790; 0,9843] | 0,9644 [0,9590; 0,9691] | 62 s (CPU) |

As três conclusões são as mesmas nos dois conjuntos.

## Referência

FAYYAD, U.; PIATETSKY-SHAPIRO, G.; SMYTH, P. From data mining to knowledge discovery in
databases. *AI Magazine*, v. 17, n. 3, p. 37–54, 1996.
