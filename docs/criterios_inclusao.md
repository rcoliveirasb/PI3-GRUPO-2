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

Na fase 1 (177 exames), nenhum exame foi excluído por esses critérios. Na fase 2, o
critério 2 excluiu 32 exames, e mais 1 saiu por geometria divergente entre a imagem e a
máscara (ver [`base_oficial.md`](base_oficial.md)).

## 3. Exames usados

A contagem completa está em [`base_oficial.md`](base_oficial.md), seção 3. Em resumo:

- **Fase 1 (histórico):** 177 exames (`subset0` + `subset1`).
- **Fase 2 (oficial desde a Sprint 4):** os 888 exames do LUNA16, da cópia integral no HD
  externo do Roger. Os 177 da fase 1 ficaram em quarentena e 1 exame foi removido por
  geometria divergente, sobrando 710 inéditos. Depois do filtro de espaçamento sobram 678.

## 4. Split treino/validação/teste

**Proporção oficial: 70/15/15, por paciente, seed fixa (42).**

- Cada `SeriesInstanceUID` do LUNA16 corresponde a um único paciente (verificado contra
  `PatientID` do LIDC-IDRI quando disponível). Logo, dividir por UID é dividir por paciente,
  e o mesmo paciente nunca aparece em dois conjuntos.
- Implementado em `src/luna16/splits.py` (`patient_split`, `train_frac=0.7,
  val_frac=0.15`), com checagem de vazamento em `assert_no_leakage`.
- **Fase 1:** 124 / 27 / 26 (`data/luna16/split_full.csv`, regenerado em 2026-09-14).
- **Fase 2:** sorteio 497 / 106 / 107 sobre os 710 exames inéditos; depois do filtro de
  espaçamento, ficam 479 / 100 / 99 (678 exames).
- **Histórico:** entre as Sprints 3 e 8 o grupo usou 60/20/20 (35 exames de teste). Os
  resultados desse período estão em `data/luna16/archive_split_v1_60_20_20/`.

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
