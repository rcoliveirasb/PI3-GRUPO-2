# Critérios de Inclusão e Split — LUNA16

> Documento pedido explicitamente no feedback do professor (Checkpoint 1 / Sprint 1,
> "Orientações para o Próximo Ciclo", item 1: *"Documentar o critério de inclusão dos
> exames... registrar isso formalmente em `docs/criterios_inclusao.md` com a proporção
> treino/validação/teste"*). Complementa, sem duplicar, a documentação técnica mais
> detalhada em [`RELATORIO_ETL.md`](../RELATORIO_ETL.md).

## 1. De onde vêm os 888 exames do LUNA16

O LIDC-IDRI original tem 1.018 exames de TC de tórax de baixa dose. O LUNA16 aplica,
sobre esse conjunto, dois critérios de exclusão (curadoria feita pelos organizadores do
desafio, não pelo grupo):

- espessura de corte (slice thickness) **> 3mm** → excluído;
- nódulos anotados **< 3mm** → excluídos da lista de anotações (não do exame em si).

Isso reduz o conjunto para os **888 exames** que compõem o LUNA16 propriamente dito,
distribuídos em 10 subsets (`subset0`–`subset9`) de ~89 pacientes cada, cada um com sua
máscara de referência do parênquima em `seg-lungs-LUNA16`.

## 2. Critério de inclusão adicional aplicado pelo grupo

Além da curadoria já embutida no LUNA16, o pipeline do grupo (`src/luna16/selection.py`)
verifica, para cada exame antes de processá-lo:

| # | Critério | Por quê |
|---|---|---|
| 1 | Máscara de referência presente | Sem ela não é possível calcular Dice/IoU |
| 2 | Espaçamento entre fatias (`spacing_z`) ≤ 2,5mm | Critério de qualidade do grupo, mais restritivo que o corte de 3mm do próprio LUNA16 — verificação, não redundância, já que o LUNA16 curado quase sempre já satisfaz isso |
| 3 | Máscara de referência não vazia | Máscara com zero voxels indicaria arquivo corrompido/ausente de fato, não um paciente sem pulmão |

Nenhum exame do subconjunto processado até agora (ver seção 3) foi excluído por esses
critérios — a curadoria do próprio LUNA16 já é suficiente na prática.

## 3. Estado real de download (importante — gap entre o alvo e o que está processado)

- **Meta formal**: os 888 exames do LUNA16 completo. Uma cópia integral (~133GB) foi
  baixada por Roger para um HD externo no início do projeto.
- **O que está de fato integrado ao pipeline reprodutível do grupo até 2026-09-14**:
  apenas **177 pacientes** (`subset0` + `subset1`, baixados via mirror do Kaggle
  `avc0706/luna16`, arquivo a arquivo, por `scripts/download_luna16_subset.py`) — os
  outros 8 subsets (≈711 pacientes) ainda não foram baixados/processados por esse
  pipeline.
- **Por quê a diferença**: baixar e processar os 888 exames completos tem custo de
  armazenamento (~120GB) e tempo de execução (o pipeline de avaliação já leva
  15–20 min para 35 pacientes) que não coube no tempo disponível até este checkpoint.
- **Decisão pendente**: se o grupo deve migrar para o conjunto completo (via o HD
  externo do Roger) antes da próxima entrega, ou manter o escopo em 177 pacientes com
  essa limitação documentada explicitamente no relatório final. Ver `PROJETO.md`.

## 4. Split treino/validação/teste

**Proporção oficial: 70/15/15, por paciente, seed fixa (42).**

- Cada `SeriesInstanceUID` do LUNA16 corresponde a um único paciente (verificado contra
  `PatientID` do LIDC-IDRI quando disponível) — logo splitar por UID é splitar por
  paciente, atendendo à regra de não misturar o mesmo paciente entre conjuntos.
- Implementado em `src/luna16/splits.py` (`patient_split`, `train_frac=0.7,
  val_frac=0.15`), com checagem de vazamento em `assert_no_leakage`.
- **Nota de reconciliação**: entre os Sprints 3 e 8, o grupo usou 60/20/20 sobre os 177
  pacientes então disponíveis (arquivo `data/luna16/split_full.csv`, gerado em
  2026-09-01) — proporção diferente da exigida pelo professor. A função de split já foi
  atualizada para 70/15/15 em 2026-09-02, mas o artefato `split_full.csv` **ainda não foi
  regenerado** com a nova proporção, e os resultados publicados até agora
  (`sprint4_*_test.csv`, `tabela_resultados_finais.csv`, etc.) ainda refletem o split
  antigo (60/20/20). Isso precisa ser corrigido antes da próxima entrega — ver
  `PROJETO.md`, seção "Próximos passos".

## 5. Parâmetros do pipeline (documentação exigida pelo feedback)

Ver também os docstrings de cada função (código é a fonte de verdade; resumo aqui):

**Pré-processamento** (`src/luna16/preprocessing.py`):
- Remoção de padding: valores ≤ −2047 HU → convertidos para −1000 HU (ar).
- Clip para a faixa `[-1000, 400]` HU.
- Denoise (só para segmentação do pulmão, não para detecção de nódulo): filtro
  Gaussiano 3D, σ = 0,5 voxel.
- Reamostragem para espaçamento isotrópico de 1mm (linear para CT, nearest-neighbor
  para máscaras).

**Baseline — threshold + morfologia** (`src/luna16/baseline.py`):
- Limiar: `HU < -600` → candidato a ar/pulmão.
- Remoção do ar de fundo fatia a fatia (`lung_air.py`).
- Mantém os 2 maiores componentes conectados 3D (os dois pulmões).
- Preenchimento de buracos fatia a fatia (recupera vasos/nódulos internos).
- Abertura morfológica (erosão seguida de dilatação) com elemento estruturante esférico
  de raio 1 voxel (`skimage.morphology.ball(1)`).

**Nota sobre nomenclatura**: o feedback do professor sugere o caminho
`src/preprocessing/segmentar_parenquima.py`. O grupo optou por manter a estrutura já
existente e mais completa em `src/luna16/` (usada por 6 notebooks e 6 scripts) em vez
de renomear um pacote funcional — a funcionalidade equivalente está em
`src/luna16/baseline.py` (threshold + morfologia) e `src/luna16/region_growing.py`.

**Region growing** (`src/luna16/region_growing.py`):
- Sementes automáticas: threshold auxiliar −320 HU (só para localizar candidatos, nunca
  para decidir a fronteira final) → maiores componentes → semente = pico da transformada
  de distância de cada componente (ponto mais interior).
- Crescimento por tolerância de intensidade: banda de ±200 HU ao redor do valor da
  semente (`skimage.segmentation.flood`, `tolerance=200`).
- Domínio seguro: fora da região candidata a pulmão, o HU é substituído por 400 (bem
  fora de qualquer tolerância plausível) para impedir o crescimento de vazar pela
  traqueia até o ar externo ao corpo.
- Preenchimento de buracos fatia a fatia ao final, igual ao baseline.
