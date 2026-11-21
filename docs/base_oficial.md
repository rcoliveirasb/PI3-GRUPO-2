# Base oficial do projeto

Documento único sobre a base de dados, pedido na orientação 6 do feedback da Sprint 4. Aqui
ficam três coisas: quais exames compõem a base, como foram divididos e de onde vem o
gabarito. Os números de resultado ficam em [`tabela_experimentos.md`](tabela_experimentos.md).
Os parâmetros do pré-processamento e dos métodos estão em
[`criterios_inclusao.md`](criterios_inclusao.md), seção 5.

## 1. Fonte

- **Base:** LUNA16, derivado do LIDC-IDRI. São 888 tomografias de tórax distribuídas em 10
  subsets (`subset0` a `subset9`). Os organizadores do LUNA16 já excluíram os exames com
  corte mais grosso que 3 mm.
- **Download:** o LUNA16 é a base. O Kaggle (mirror `avc0706/luna16`) foi só o lugar de onde
  os subsets 0 e 1 foram baixados, com `scripts/download_luna16_subset.py`. A cópia
  completa dos 888 exames está no HD externo do Roger.
- **O LIDC-IDRI via TCIA** (manifest `.tcia`, notebook da Sprint 2) foi usado só na análise
  exploratória do histograma de HU. Não faz parte da base, porque não tem máscara de
  referência.

## 2. Gabarito

| O quê | Arquivo | Quem produziu |
|---|---|---|
| Máscara do pulmão | `seg-lungs-LUNA16/<uid>.mhd` | **Algoritmo automático** dos organizadores do LUNA16, **não um radiologista** |
| Nódulos | `annotations.csv` (centro e diâmetro) | Radiologistas do LIDC-IDRI; o LUNA16 mantém os nódulos ≥ 3 mm aceitos por pelo menos 3 de 4 leitores |

- **Rótulos da máscara:** 3 e 4 são os pulmões, e o gabarito do projeto é a união dos dois. O
  rótulo 5 é a traqueia e fica de fora, porque não é parênquima.
- **Consequência:** o Dice mede a **concordância com outro algoritmo**, não o acerto
  anatômico. Quando um método discorda do gabarito, nem sempre é o método que está errado
  (ver pendências, no fim).

## 3. Os exames, em duas fases

### Fase 1 (histórico): 177 exames

- **Exames:** subset0 (89) + subset1 (88) = **177**. Nenhum foi excluído pelos critérios de
  seleção.
- **Divisão:** 70/15/15 por paciente, semente 42: **124 treino / 27 validação / 26 teste**.
  O arquivo é `data/luna16/split_full.csv`.
- **Uso:** os 26 exames de teste formam o **Teste A**. Nele foram comparados os 3 métodos
  (baseline, region growing e a U-Net treinada com 124 exames).
- **Antes disso:** entre as Sprints 3 e 8 o grupo usou 60/20/20, com 35 exames de teste.
  Esses resultados estão arquivados em `data/luna16/archive_split_v1_60_20_20/` e não valem
  mais.

### Fase 2 (oficial a partir da Sprint 4): 888 exames

| Etapa | Exames |
|---|---|
| LUNA16 completo, convertido para MetaImage | 888 |
| − exames da fase 1, em quarentena (nunca entram no treino novo) | −177 |
| − exame com geometria divergente entre imagem e máscara | −1 |
| **Exames inéditos** | **710** |
| Sorteio por paciente, 70/15/15, semente 42 | 497 treino / 106 validação / 107 teste |
| − espaçamento entre cortes acima de 2,5 mm, em cada conjunto | −18 / −6 / −8 (−32) |
| **Exames usados** | **479 treino / 100 validação / 99 teste (678)** |

- **De onde vem o 479:** o sorteio 70/15/15 foi feito sobre os **710** exames inéditos
  (70% de 710 ≈ 497, como o professor calculou). Depois disso, o filtro de espaçamento
  removeu 18 exames do treino, 6 da validação e 8 do teste. Fonte: relatório de migração
  do Roger, apresentado na Sprint 4.
- **Teste B:** os 99 exames de teste. A partir da orientação 1 do feedback, **é o conjunto
  oficial de comparação dos três métodos.** Os 26 exames do Teste A viram histórico.

## 4. Glossário das contagens

| Número | O que é |
|---|---|
| 888 | LUNA16 completo |
| 177 | Fase 1: subset0 + subset1 |
| 178 | Quarentena da fase 2: os 177 da fase 1 + 1 exame com geometria divergente |
| 710 | Exames inéditos para a fase 2 |
| 32 | Excluídos na fase 2 por espaçamento acima de 2,5 mm |
| 497 / 106 / 107 | Sorteio da fase 2 sobre os 710, antes do filtro de espaçamento |
| 678 | Utilizáveis na fase 2, depois do filtro |
| 479 / 100 / 99 | Treino / validação / teste da fase 2, depois do filtro (Teste B = 99) |
| 124 / 27 / 26 | Treino / validação / teste da fase 1 (Teste A = 26) |
| 35 | Teste do split antigo 60/20/20, histórico (é o número que aparece na pré-banca) |
| 20 | Exames usados na avaliação de detecção de nódulos (extensão fora do escopo formal) |

## 5. Pendências deste documento

- **Arquivos da fase 2 no repositório** (Roger): o `split_novo.csv` já está no GitHub, em
  `pji/modelos/unet_seed123/`, junto com os pesos e a avaliação da rede final. Ainda faltam
  a lista dos 32 exames excluídos e o identificador do exame com geometria divergente.
- **107 ou 99 exames de teste? (17/11)** O `split_novo.csv` e a rede final (semente 123) **não**
  aplicam o filtro de espaçamento: a rede foi treinada com 497 exames e avaliada nos 107 de
  `teste_interno`. Por isso o teste oficial dos três métodos passa a ser o de **107**. Os
  números 479/100/99 da seção 3 descrevem o treino mostrado na Sprint 4. Roger confirma, e
  depois esta seção 3 é reescrita. Ver [`tabela_experimentos.md`](tabela_experimentos.md).
- **Parâmetros escolhidos só com a validação** (pré-banca, orientação 6): documentar em quais
  exames foram definidos o limiar de −600 HU, o raio morfológico e a tolerância do region
  growing, e garantir que nenhum deles foi ajustado olhando o teste.
- **Discordância entre método e gabarito** (Sprint 4): olhar os exames de maior discordância
  e ver se o erro está no método ou na máscara do LUNA16.
