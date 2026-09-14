# Relatório de ETL — Pipeline de Dados do Projeto

**Grupo 02 — Segmentação e Detecção de Nódulos Pulmonares**

> Documenta o fluxo completo de dados do projeto: de onde vieram (Extract), que
> transformações foram aplicadas (Transform) e onde os resultados ficam armazenados
> (Load). Serve como referência técnica complementar ao relatório científico
> (`RELATORIO_FINAL_RASCUNHO.md`), focada na engenharia de dados, não nos resultados
> científicos em si.

---

## 1. EXTRACT (Extração)

### 1.1. Fontes de dados

| Fonte | Conteúdo | Uso no projeto |
|---|---|---|
| TCIA (`services.cancerimagingarchive.net`) | Séries DICOM do LIDC-IDRI, via manifest `TCIA_LIDC-IDRI_20200921.tcia` | Só EDA exploratória inicial (Sprint 2) — dataset descontinuado a partir do Sprint 3 |
| Kaggle — mirror `avc0706/luna16` | LUNA16 completo: `.mhd`/`.raw` (10 subsets), `seg-lungs-LUNA16` (máscaras de referência do pulmão), `annotations.csv` (nódulos anotados), `candidates.csv` (candidatos rotulados) | Fonte principal a partir do Sprint 3 |

### 1.2. O que foi extraído (volume real baixado)

| Item | Quantidade | Tamanho em disco |
|---|---|---|
| `subset0` (.mhd/.raw) | 89 pacientes | ~12 GB |
| `subset1` (.mhd/.raw) | 88 pacientes | ~11 GB |
| `seg-lungs-LUNA16` (máscaras de referência) | 89 pacientes (correspondentes aos 2 subsets) | ~87 MB |
| `annotations.csv` | 1.186 nódulos anotados (240 nos pacientes baixados) | 137 KB |
| `candidates.csv` | 551.065 candidatos rotulados (110.143 nos pacientes baixados) | 55 MB |

**Total de pacientes extraídos: 177** dos 888 do LUNA16 completo (subsets 0 e 1).

### 1.3. Mecanismo de extração

- Autenticação via token de API do Kaggle (pessoal, por integrante — não versionado).
- Download por arquivo individual via `kaggle.api.dataset_download_file` (não o dataset inteiro de uma vez — evita baixar os ~120GB completos do LUNA16 quando só uma fração é necessária).
- Script: [`scripts/download_luna16_subset.py`](scripts/download_luna16_subset.py) `N` — idempotente (pula arquivo já baixado), descompacta automaticamente (a API do Kaggle empacota arquivos grandes em `.zip` sem avisar — achado do Sprint 3).
- Dados ficam em `data/luna16/`, **fora do controle de versão** (`.gitignore`) — só os scripts que os geram são versionados, não os dados em si.

---

## 2. TRANSFORM (Transformação)

Cada estágio abaixo tem uma função dedicada em [`src/luna16/`](src/luna16/), documentada inline com o *porquê* de cada decisão.

### 2.1. Seleção (`selection.py`)

- Filtra pacientes por: máscara de referência presente e não vazia; espaçamento entre fatias ≤ 2,5mm.
- Resultado: 177/177 pacientes passam (LUNA16 já curou isso do LIDC-IDRI original).
- Saída: `data/luna16/selecao_subset0.csv`, `subset0_headers.csv`.

### 2.2. Split treino/validação/teste (`splits.py`)

- Split **por paciente** (nunca por fatia — evita vazamento), 60/20/20, seed fixa (42).
- Sprint 3: split inicial sobre 89 pacientes (`split_subset0.csv`, imutável).
- Sprint 4: estendido com os 88 pacientes do `subset1` (mesma seed/proporção), preservando as atribuições do Sprint 3 → `split_full.csv` (177 pacientes: 106 treino / 36 validação / 35 teste).

### 2.3. Pré-processamento de imagem (`preprocessing.py`)

Pipeline aplicado a cada volume de CT, nesta ordem:

1. **`clean_hu`**: remove padding fora do FOV circular (convertido para -1000 HU), recorta para `[-1000, 400]` HU.
2. **`denoise`**: filtro Gaussiano (σ=0,5 voxel) — usado só para a segmentação do pulmão, **não** para detecção de nódulo (suavizar piora o contraste de estruturas pequenas já afetadas por volume parcial — achado do Sprint 7).
3. **`resample_isotropic`**: reamostragem para espaçamento isotrópico de 1mm (linear para CT, nearest-neighbor para máscaras).

### 2.4. Segmentação do parênquima pulmonar (`baseline.py`, `region_growing.py`, `lung_air.py`)

- **Baseline**: threshold -600HU → remoção de fundo por fatia (perímetro inteiro, corrigido no Sprint 5) → maiores componentes 3D → preenchimento de buracos → abertura morfológica.
- **Region growing**: sementes automáticas (pico da transformada de distância) → crescimento por tolerância de intensidade (±200 HU), restrito à mesma região seguros do baseline.
- Saída: máscara booleana 3D do pulmão, usada como região de busca na etapa seguinte.

### 2.5. Detecção de candidatos a nódulo (`nodules.py`)

- Blob detection (Laplacian of Gaussian, `skimage.feature.blob_log`) restrito à região pulmonar, faixa de densidade -750 a +400 HU.
- Candidatos cacheados por paciente em `data/luna16/nodule_candidates_cache/<uid>.csv` (z, y, x, raio_mm) — evita reprocessar a etapa mais cara (~1-2min/paciente) a cada iteração do classificador.
- 45 pacientes com candidatos cacheados até o momento.

### 2.6. Extração de features + classificação (`nodule_features.py`)

- Para cada candidato: recorte cúbico (33×33×33 voxels) ao redor do centro → 11 features (estatísticas de HU, tamanho/forma do blob de tecido, magnitude do gradiente).
- Rótulo: correspondência espacial com `annotations.csv` (verdadeiro nódulo) ou `candidates.csv` (rótulo oficial do LUNA16, usado só na 1ª tentativa de treino, descartada por desalinhamento de distribuição).
- Classificador: Random Forest (`class_weight='balanced'`), treinado sobre os candidatos do conjunto de **treino**, threshold de operação escolhido no conjunto de **validação**, avaliado no conjunto de **teste** — sem vazamento entre conjuntos em nenhuma etapa.

### 2.7. Agregação de métricas (`metrics.py`, `evaluate.py`)

- Dice, IoU, sensibilidade, precisão (segmentação); acurácia, precisão, recall, F1, AUC-ROC, matriz de confusão (classificação de candidatos).
- Bootstrap não-paramétrico (500 reamostras) para IC95%, com seed fixa.

---

## 3. LOAD (Carga / Armazenamento dos resultados)

Nenhum banco de dados formal é usado — os artefatos intermediários e finais são persistidos como **arquivos CSV** em `data/luna16/` (fora do git) e os resultados consolidados (tabelas, gráficos, texto) ficam embutidos nos **notebooks executados** (versionados, mas ainda não commitados — ver nota abaixo).

### 3.1. Artefatos tabulares gerados (`data/luna16/*.csv`)

| Arquivo | Conteúdo | Gerado por |
|---|---|---|
| `selecao_subset0.csv`, `subset0_headers.csv` | Critérios de seleção + metadados de cabeçalho | Sprint 3 |
| `split_subset0.csv`, `split_full.csv` | Split treino/val/teste por paciente | Sprint 3 / 4 |
| `piloto_resultados_sprint3.csv` | Resultado do piloto (5 TCs) | Sprint 3 |
| `sprint4_baseline_test.csv`, `sprint4_region_growing_test.csv` | Dice/IoU/sensibilidade/precisão/tempo, 35 TCs de teste, os 2 métodos de segmentação | Sprint 4 |
| `tabela_resultados_finais.csv` | Tabela consolidada final (segmentação) | Sprint 6 |
| `sprint7_nodulos_resultados.csv` | Detecção de nódulos, 20 pacientes (FROC) | Sprint 7 |
| `own_candidate_features_{train,val,test}.csv` | Features + rótulos dos candidatos (treino do classificador) | Sprint 8b |
| `sprint8_resultados.csv`, `sprint8b_resultados.csv` | Antes/depois do filtro de falsos positivos | Sprint 8 / 8b |
| `nodule_candidates_cache/<uid>.csv` (45 arquivos) | Candidatos brutos por paciente (cache) | Sprint 7 em diante |

### 3.2. O que **não** é persistido (ainda)

- **O classificador treinado (Random Forest) não é salvo em disco** — é retreinado a cada execução de script/notebook a partir dos CSVs de features. Para produção ou reprodutibilidade sem retreino, seria necessário serializar com `joblib.dump`.
- **Nenhum dado bruto (imagens, máscaras) é versionado no Git** — só os scripts que os reproduzem (`scripts/download_luna16_subset.py`).

### 3.3. Estado do versionamento (importante)

Conforme instrução explícita da orientação do projeto nesta sessão: **nada deste pipeline foi commitado ou enviado ao GitHub/Trello** — todo o código (`src/luna16/`, `scripts/`), os notebooks e este relatório existem **apenas localmente**, aguardando revisão do grupo antes de qualquer commit.

---

## 4. Resumo visual do fluxo

```
Kaggle (avc0706/luna16)
   │  download_luna16_subset.py
   ▼
data/luna16/{subset0,subset1,seg-lungs-LUNA16,annotations.csv,candidates.csv}
   │  selection.py + splits.py
   ▼
split_full.csv (106 treino / 36 val / 35 teste)
   │  preprocessing.py (clean_hu → denoise → resample_isotropic)
   ▼
volume CT pré-processado (1mm isotrópico)
   ├─ baseline.py / region_growing.py ──► máscara do pulmão ──► sprint4_*.csv, tabela_resultados_finais.csv
   └─ nodules.py (blob_log, restrito ao pulmão) ──► nodule_candidates_cache/*.csv
         │  nodule_features.py (patch → 11 features)
         ▼
      own_candidate_features_{train,val,test}.csv
         │  RandomForestClassifier (treino/threshold/teste sem vazamento)
         ▼
      sprint8b_resultados.csv + métricas de classificação (acurácia/precisão/recall/F1/AUC/matriz de confusão)
```
