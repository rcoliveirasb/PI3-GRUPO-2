# Definição do Problema — Grupo 02

> Versão corrigida conforme o feedback do professor no fechamento do Checkpoint 1
> (Sprint 1): a versão anterior deste documento (mantida até então só no Drive do
> grupo) usava métricas de **classificação** (Kappa, acurácia), que pertencem a outra
> seção do documento geral da disciplina — não ao escopo deste grupo. Esta versão
> substitui aquela e passa a ser a referência oficial, versionada no repositório.

## Gap identificado

Existe variabilidade entre equipamentos de tomografia e um abismo entre o desempenho
de algoritmos de segmentação pulmonar em laboratório e em produção clínica real. Antes
de qualquer análise automatizada de nódulos pulmonares, o parênquima precisa ser
isolado de forma confiável das estruturas adjacentes (coração, costelas, mediastino) —
esse isolamento é o problema deste grupo.

## Pergunta SMART (corrigida)

> **Alcançar Dice Coefficient de pelo menos 0,85 na segmentação do parênquima pulmonar
> no conjunto de teste do LUNA16, comparando um baseline por limiarização de Hounsfield
> Units (HU) com operações morfológicas contra um método por region growing, até a data
> de entrega do projeto.**

- **Specific**: segmentar o parênquima pulmonar em TC de tórax, comparando dois métodos
  específicos (baseline HU+morfologia vs. region growing).
- **Measurable**: Dice Coefficient (meta ≥ 0,85) e IoU (meta ≥ 0,75), ambos com
  intervalo de confiança de 95% por bootstrap (≥ 500 reamostragens).
- **Achievable**: métodos clássicos de visão computacional, sem depender de
  treinamento de rede neural do zero; validados na literatura para este problema.
- **Relevant**: segmentação do parênquima é pré-requisito necessário para qualquer
  detecção/classificação de nódulos pulmonares — o objetivo clínico que dá sentido ao
  projeto.
- **Time-bound**: avaliado no conjunto de teste do LUNA16 (split por paciente, nunca
  por fatia — ver [`docs/criterios_inclusao.md`](docs/criterios_inclusao.md)), dentro do
  cronograma de sprints da disciplina.

## Métricas (corrigidas)

| Métrica | Papel | Meta | Por que (e por que não Kappa/acurácia) |
|---|---|---|---|
| **Dice Coefficient** | Primária | ≥ 0,85 | Métrica padrão de sobreposição para segmentação; Kappa/acurácia são métricas de **classificação binária**, não se aplicam a comparar duas máscaras |
| **IoU (Jaccard)** | Primária | ≥ 0,75 | Mesma família de métricas de sobreposição, mais rigorosa que Dice para o mesmo par de máscaras |
| Sensibilidade por pixel | Secundária | — | Mede quanto do pulmão real foi capturado (custo de falso negativo é alto no domínio clínico) |
| Precisão por pixel | Secundária | — | Mede quanto do que foi predito como pulmão realmente é pulmão |
| Tempo por TC | Secundária | — | Custo computacional, para a discussão desempenho × custo |

Todas as médias são reportadas com **intervalo de confiança de 95% por bootstrap**
(mínimo 500 reamostragens, o grupo usa 1000), nunca como número único — ver
justificativa em [`RELATORIO_FINAL_RASCUNHO.md`](RELATORIO_FINAL_RASCUNHO.md).

**Por que acurácia enganaria aqui**: o parênquima pulmonar ocupa uma fração pequena do
volume total de uma TC (~10-15%). Um classificador trivial que responde "nada é
pulmão" para todo voxel acertaria a maioria dos voxels e teria Dice = 0 — por isso
acurácia não é usada como métrica de avaliação da segmentação neste projeto.

## Escopo (duas fases encadeadas)

1. **Segmentação do parênquima pulmonar** (foco deste checkpoint): baseline
   (threshold −600HU + morfologia) vs. region growing, avaliados por Dice/IoU.
2. **Detecção de nódulos pulmonares** (extensão incorporada depois do Sprint 6, usando
   o pulmão já segmentado): candidatos via blob detection, avaliados no padrão FROC do
   próprio desafio LUNA16, com um classificador de redução de falsos positivos.
   Ver `PROJETO.md` para o histórico dessa extensão e se ela precisa de validação
   explícita do professor quanto ao escopo formal da entrega.

## Dataset

[LUNA16](https://luna16.grand-challenge.org/): 888 exames de TC de tórax, derivados do
LIDC-IDRI (1.018 exames originais, filtrados para espessura de corte ≤ 3mm e nódulos
anotados ≥ 3mm). Ver [`docs/criterios_inclusao.md`](docs/criterios_inclusao.md) para o
detalhamento formal dos critérios de inclusão e do split treino/validação/teste
(70/15/15 por paciente).
