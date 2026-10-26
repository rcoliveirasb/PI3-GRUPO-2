# Inspeção visual de 12 exames do conjunto de teste

Sprint 5 (análise de falhas) — Grupo 02, segmentação do parênquima pulmonar.

## O que foi feito

Sorteamos **12 dos 26 pacientes** do conjunto de teste (split 70/15/15, seed 42) e, para
cada um, plotamos **3 fatias** — início, meio e fim do pulmão — com quatro painéis lado a
lado: **TC original**, **máscara predita**, **máscara de referência** (`seg-lungs-LUNA16`,
rótulos 3+4) e uma **sobreposição** com falso positivo em vermelho, falso negativo em azul
e acerto em verde.

O pedido original eram três painéis. A sobreposição foi acrescentada porque é justamente
ela que responde à pergunta "o Dice esconde alguma coisa?": um erro localizado só aparece
quando você vê *onde* ele está, não quanto ele pesa na média.

As fatias saem dos **percentis 10/50/90** da extensão do pulmão na referência, não da
primeira e da última fatia com pulmão — nos extremos exatos o ápice e a base têm poucas
dezenas de voxels e não dá para julgar nada visualmente.

| Arquivo | Conteúdo |
|---|---|
| `caso_01..12_<uid>.png` | as 12 figuras (3 fatias × 4 painéis) |
| `diagnosticos_inspecao_visual.csv` | métricas + diagnósticos por caso |
| `analise_falhas_quantitativa.csv` | traqueia incluída e FP abaixo do diafragma, em mL |
| `scripts/inspecao_visual_teste.py` | gera as figuras |
| `scripts/analise_falhas_inspecao.py` | quantifica os dois padrões de erro |

**Reprodutibilidade:** o pipeline é o mesmo do Sprint 4 (`clean_hu` → `denoise` →
`resample_isotropic` 1 mm → `segment_baseline`), chamado dos módulos de `src/luna16/`. As
métricas recalculadas batem dígito a dígito com `sprint4_baseline_test.csv` — por exemplo,
o `…741695800950` dá Dice 0,9816, sensibilidade 0,9735 e precisão 0,9898 nos dois.

> As máscaras avaliadas são do **baseline** (limiar −600 HU + morfologia), não da U-Net.
> A inspeção foi feita em 15/09; desde então a U-Net foi treinada e seus resultados
> entraram no repositório (`data/luna16/sprint_unet_test.csv`). Ver a seção
> "Confronto com a U-Net" no fim deste documento — as imagens e os diagnósticos abaixo
> continuam válidos, porque o baseline e o split não mudaram.

## Panorama dos 12

| # | Paciente | Dice | Sens. | Prec. | Comp. | Fatias Dice<0,8 | Pior fatia |
|---|---|---|---|---|---|---|---|
| 1 | …098781143514 | 0,9601 | 0,9306 | 0,9915 | 2 | 93/332 | 0,000 |
| 2 | …741695800950 | 0,9816 | 0,9735 | 0,9898 | 3 | 60/326 | 0,000 |
| 3 | …340281098509 | 0,9676 | 0,9492 | 0,9868 | 2 | 95/313 | 0,000 |
| 4 | …280013275227 | 0,9674 | 0,9477 | 0,9878 | 15 | 37/263 | 0,000 |
| 5 | …079549658100 | 0,9795 | 0,9655 | 0,9939 | 5 | 46/331 | 0,000 |
| 6 | …547290922949 | 0,9688 | 0,9552 | 0,9828 | **149** | 61/332 | 0,000 |
| 7 | …512130599234 | 0,9637 | 0,9468 | 0,9813 | 3 | 43/279 | 0,000 |
| 8 | …929031534291 | 0,9727 | 0,9577 | 0,9881 | 5 | 70/332 | 0,000 |
| 9 | …124419915089 | 0,9767 | 0,9646 | 0,9890 | 2 | 24/310 | 0,047 |
| 10 | …604069960014 | 0,9518 | 0,9248 | 0,9804 | 5 | 73/266 | 0,000 |
| 11 | …021509831276 | **0,8600** | **0,7649** | 0,9820 | 35 | 102/215 | 0,000 |
| 12 | …860209787179 | 0,9657 | 0,9594 | 0,9720 | 2 | 95/336 | 0,000 |

O sorteio pegou 4 dos 5 exames já marcados para a demo (`1-sucesso`, `2-tipico`,
`3-falha-region-growing`, `5-baixa-resolucao`). O `4-pior-caso` não caiu na amostra.

---

## Comentário por caso

**1 — `…098781143514` (Dice 0,9601).** Anatomicamente correto no meio do pulmão: a fatia
p50 tem Dice 0,9816 e o contorno acompanha bem a pleura. O problema está na base: na fatia
p10 a predição está **completamente vazia** enquanto a referência ainda marca uma lâmina de
pulmão — Dice 0,0000 naquela fatia. É o caso com maior precisão dos 12 (0,9915) e uma das
menores sensibilidades (0,9306): o baseline é conservador e prefere não marcar a duvidar.
93 das 332 fatias ficam abaixo de Dice 0,8.

**2 — `…741695800950` (Dice 0,9816).** O melhor Dice dos 26 e, no geral, a segmentação mais
limpa da amostra — o parênquima no p50 é praticamente perfeito. Mesmo assim, a fatia p90
mostra um **blob vermelho central nítido: a traqueia**, que a referência exclui de propósito
e a predição inclui. Há também pontos vermelhos junto aos hilos (brônquios principais).
Nenhum desses erros aparece no Dice de 0,98.

**3 — `…340281098509` (Dice 0,9676).** O achado aqui é a **espessura do contorno na base**: na
fatia p10 a referência marca uma faixa nitidamente mais larga que a predição, e a
sobreposição fica com uma borda azul contínua ao longo de toda a interface pulmão-diafragma
(Dice da fatia 0,8059). O limiar de −600 HU corta a franja de volume parcial que a
referência inclui. Anatomicamente a forma está certa; o que difere é onde cada método
coloca a fronteira.

**4 — `…280013275227` (Dice 0,9674).** Anatomia atípica: a fatia p90 mostra um tórax bem
assimétrico, com um pulmão só visível no corte, e no p50 o pulmão esquerdo aparece
comprimido em formato de crescente contra um mediastino alargado. A predição acompanha bem
essa anatomia incomum — é um bom sinal de robustez. Os **15 componentes conexos**, porém,
indicam fragmentos soltos, e a traqueia aparece de novo como blob vermelho isolado no p90.

**5 — `…079549658100` (Dice 0,9795).** Segundo melhor da amostra e a maior precisão dos 12
(0,9939). É o exame que serve de `3-falha-region-growing` — vale registrar que **o problema
daquele caso é do region growing, não do baseline**: aqui o baseline vai muito bem. O
defeito visível é sistemático e discreto: **árvores azuis nos hilos**, onde os vasos
pulmonares ficam de fora da predição, e a traqueia em vermelho no p90.

**6 — `…547290922949` (Dice 0,9688).** O caso dos **149 componentes conexos**. A causa está
visível nas três fatias: **listras vermelhas finas na borda inferior da imagem, fora do
corpo do paciente** — bolsões de ar do colchão/mesa do tomógrafo entrando na máscara. Em
volume isso é quase nada (por isso a precisão continua 0,9828), mas é um defeito
qualitativo real: a máscara de pulmão contém estruturas que não são do paciente. Tem também
perda azul significativa nas bases posteriores no p10.

**7 — `…512130599234` (Dice 0,9637).** O exame `2-tipico`. Na fatia p10 há um **falso
positivo grande e compacto no quadrante superior esquerdo do abdome: a bolha gástrica**. A
TC mostra dois bolsões de ar ali; a predição engoliu um deles e deixou o outro. Marcar ar
gástrico como parênquima pulmonar é um erro anatômico claro, e o Dice de 0,96 não dá
nenhuma pista dele.

**8 — `…929031534291` (Dice 0,9727).** Bom desempenho geral. Repete os dois padrões da
amostra em escala menor: um ponto vermelho de ar abdominal no p10 e a traqueia no p90, além
das reentrâncias azuis nos hilos no p50. A base do pulmão no p10 mostra a mesma borda azul
de volume parcial do caso 3.

**9 — `…124419915089` (Dice 0,9767).** É o único caso em que **nenhuma fatia zera** (pior
fatia 0,047) e o que tem menos fatias ruins (24 de 310) — a segmentação é consistente ao
longo de todo o eixo z. Duas coisas aparecem: uma **listra vermelha fora do corpo, na mesa
do tomógrafo**, na fatia p10; e, no p50, o desenho azul da **árvore vascular hilar** — a
referência preenche os vasos, a predição os escava.

**10 — `…604069960014` (Dice 0,9518).** Segundo pior da amostra. A sub-segmentação nas bases
é a mais visível depois do caso 11: no p10 a sobreposição é quase toda azul (Dice da fatia
0,8310), com a predição marcando lâminas finas e descontínuas onde a referência marca
crescentes completos. Fatias de 2,5 mm — consistente com a correlação negativa entre
espaçamento e Dice já observada no Sprint 5.

**11 — `…021509831276` (Dice 0,8600).** O pior da amostra e a falha mais instrutiva. No p50
a predição fica **corroída em padrão rendilhado** na metade inferior dos dois pulmões: onde
o parênquima é mais denso (região dependente, com o paciente em decúbito dorsal), o tecido
passa de −600 HU e o limiar simplesmente o descarta. São grandes regiões azuis contíguas de
pulmão anatomicamente real que ficaram de fora — o maior blob de falso negativo tem
**310 mL**. No p10 a predição está vazia com referência não-vazia (Dice 0,0029). Sensibilidade
despenca para 0,7649 enquanto a precisão fica em 0,9820: **o método não erra o que marca,
ele deixa de marcar**. Fatias de 2,5 mm agravam o quadro.

**12 — `…860209787179` (Dice 0,9657).** O falso positivo mais grave da amostra em volume.
Na fatia p10 há um **blob vermelho grande e redondo no estômago** — 91,4 mL de ar gástrico
classificado como pulmão, o maior componente de FP dos 12. Também é o caso com a menor
precisão da amostra (0,9720), e ainda assim o Dice fica em 0,9657. Um Dice de 0,97
convivendo com quase 100 mL de estômago dentro da máscara é a melhor ilustração do limite
da métrica.

---

## Os padrões que atravessam a amostra

### 1. A traqueia entra na máscara em 12 de 12 casos

A convenção do projeto (documentada em `src/luna16/io.py`) é que a referência de
parênquima são os rótulos 3 e 4, **excluindo o rótulo 5 (traqueia/vias aéreas centrais)**.
A predição não faz essa distinção: a traqueia é ar, e depois do preenchimento 2D ela fica
contígua aos pulmões.

Quantificando: **418 mL dos 470 mL rotulados como traqueia nos 12 exames estão dentro da
predição** — entre 82,9% e 94,6% por caso, sem uma única exceção. É um viés sistemático,
não ruído, e é totalmente invisível no Dice porque a traqueia é pequena perto do pulmão.

### 2. O volume predito é sempre menor que o de referência

Nos 12 casos, sem exceção, a predição subestima o volume: em média **5,0%**, indo de 1,3% a
22,1%. Isso importa porque o **Dice não tem direção** — ele penaliza igualmente marcar a
mais e marcar a menos. Se alguém usar essas máscaras para estimar volume pulmonar, o erro
não é aleatório, é **sempre para baixo**. Um viés desses precisa ser reportado como viés, e
nenhuma das quatro métricas do projeto o expõe.

### 3. Um Dice global alto convive com fatias catastróficas

Somando os 12 exames, **799 de 3.635 fatias (22%) têm Dice abaixo de 0,8**, e **11 dos 12
casos têm pelo menos uma fatia com Dice exatamente 0**. A média por paciente é 0,96. As
fatias ruins se concentram nas bases pulmonares, onde o pulmão é uma lâmina fina e o limiar
frequentemente não marca nada. Quem olha só a média por paciente não vê isso.

### 4. Vasos hilares: a referência preenche, a predição escava

Aparece no p50 de quase todos os casos, como reentrâncias azuis em forma de árvore nos
hilos. O mecanismo está em `fill_holes_per_slice` ([lung_air.py](../../src/luna16/lung_air.py)):
ela usa `binary_fill_holes`, que só preenche regiões **totalmente cercadas**. Vasos no meio
do parênquima viram buracos fechados e são preenchidos corretamente; mas no hilo os vasos
se conectam ao mediastino, formando um entalhe aberto na borda — e entalhe aberto não é
buraco. A referência os inclui; a predição não.

### 5. Ar que não é do paciente

Dois sabores. **Fora do corpo:** listras de ar do colchão/mesa do tomógrafo (casos 6 e 9) —
volume desprezível, mas são os 149 componentes do caso 6. **Abaixo do diafragma:** bolha
gástrica e alças intestinais (casos 12, 7 e 8).

Uma ressalva sobre o número: o teste geométrico de `analise_falhas_inspecao.py` conta só os
blobs cujo centroide fica **abaixo da fatia mais inferior em que a referência ainda tem
pulmão**, e por isso acusa 4 de 12. Ele **subestima**. Como o diafragma é uma cúpula, a
bolha gástrica costuma estar no mesmo nível axial das bases pulmonares posteriores — o caso
7 tem um FP gástrico bem visível na imagem e marca 0,0 mL nesse teste. Tome os 4/12 como
piso, não como contagem.

---

## O que isso sugere para as próximas sprints

Nenhum desses achados é bug de implementação — são limites do método de limiar global.
Quatro coisas que valem discussão:

1. **Separar a traqueia.** Remover as vias aéreas centrais da predição (crescimento de
   região a partir da traqueia, subtraído do resultado) resolve um viés que existe em 100%
   dos casos e que a U-Net, treinada contra a mesma referência, deve aprender a evitar
   sozinha — o que vale como hipótese testável na comparação.
2. **Recortar ao tórax.** Descartar componentes abaixo da base pulmonar elimina o ar
   gástrico sem tocar no parênquima.
3. **Reportar o viés de volume junto do Dice.** Uma tabela de Bland-Altman ou o erro
   percentual de volume com sinal mostra o que o Dice apaga.
4. **Olhar Dice por fatia, não só por paciente.** O percentil 5 do Dice por fatia separa
   métodos que a média por paciente empata.

O caso 11 merece destaque no relatório final: ele mostra que o limiar de −600 HU falha
exatamente onde há **achado clínico** (parênquima denso), que é onde a segmentação mais
precisaria funcionar. É um argumento concreto a favor da U-Net, e não depende de nenhum
número — está visível na imagem.

---

## Confronto com a U-Net (atualização de 05/10)

A U-Net foi treinada depois desta inspeção. Comparando o Dice dos **mesmos 12 exames**:

| # | Paciente | Baseline | U-Net | Ganho |
|---|---|---|---|---|
| 1 | …098781143514 | 0,9601 | 0,9677 | +0,0076 |
| 2 | …741695800950 | 0,9816 | 0,9900 | +0,0084 |
| 3 | …340281098509 | 0,9676 | 0,9844 | +0,0168 |
| 4 | …280013275227 | 0,9674 | 0,9673 | −0,0001 |
| 5 | …079549658100 | 0,9795 | 0,9884 | +0,0089 |
| 6 | …547290922949 | 0,9688 | 0,9872 | +0,0185 |
| 7 | …512130599234 | 0,9637 | 0,9830 | +0,0193 |
| 8 | …929031534291 | 0,9727 | 0,9873 | +0,0146 |
| 9 | …124419915089 | 0,9767 | 0,9880 | +0,0113 |
| 10 | …604069960014 | 0,9518 | 0,9687 | +0,0169 |
| 11 | …021509831276 | 0,8600 | **0,9628** | **+0,1028** |
| 12 | …860209787179 | 0,9657 | 0,9870 | +0,0213 |

Ganho médio nos 12: **+0,0205**.

**A previsão da inspeção se confirmou.** O caso 11 — apontado acima como a falha mais
instrutiva, onde o limiar de −600 HU descarta parênquima denso — é de longe o que mais
ganhou: **+0,1028**, cinco vezes o ganho médio. O argumento a favor da U-Net que estava
visível na imagem apareceu depois no número.

No conjunto completo (`tabela_resultados_finais.csv`), o efeito aparece menos no Dice médio
(0,9555 → 0,9781) do que onde esta inspeção disse que apareceria: o **Dice mínimo** sobe de
0,8468 para 0,9281 e os **exames abaixo de 0,85 caem de 1 para 0**. A U-Net não melhora
tudo um pouco — ela conserta os casos ruins, que é exatamente o que as imagens previam.

O caso 4 é a única exceção (−0,0001, empate técnico). Vale notar que era justamente o de
anatomia mais atípica da amostra, com tórax assimétrico — plausível que seja um padrão
sub-representado no treino, e é o candidato óbvio para olhar se alguém for investigar os
limites da U-Net.

**O que esta inspeção levanta e os números da U-Net ainda não respondem:** se a U-Net
também inclui a traqueia, se ela também subestima volume de forma sistemática, e se ela
também marca ar gástrico. Ela foi treinada contra a mesma referência, que exclui a
traqueia, então em tese deveria aprender a excluí-la — mas isso é hipótese, não resultado.
Rodar `scripts/inspecao_visual_teste.py` com a predição da U-Net no lugar do baseline
responderia às três de uma vez, reaproveitando todo o código.

---

## Correção de 26/10 — a hipótese do caso 4 estava errada

Na Sprint 5 o pós-processamento da U-Net foi corrigido (descartar componentes fora do
tórax, ver `src/luna16/unet.py`). Isso **invalida a explicação que dei acima para o caso 4**,
e vale registrar porque é um exemplo de hipótese plausível que o dado derrubou.

Eu havia atribuído a perda da U-Net naquele exame a "anatomia atípica, padrão
sub-representado no treino". **Não era isso.** Com a correção, o caso 4 vai de 0,9673 para
**0,9818**, e o falso positivo dele cai de **133,1 para 47,3 mL** — ou seja, a perda vinha
do mesmo bug espacial do caso 5, com a rede marcando ar fora do corpo. Nada a ver com a
anatomia do paciente.

Três dos doze exames mudaram com a correção:

| Exame | U-Net antes | U-Net depois |
|---|---|---|
| `…280013275227` (caso 4) | 0,9673 | **0,9818** |
| `…604069960014` (caso 10) | 0,9687 | 0,9711 |
| `…929031534291` (caso 8) | 0,9873 | 0,9875 |

Os outros nove não mudaram, e **nenhuma métrica do baseline mudou** — as 12 figuras e
todos os diagnósticos deste relatório continuam válidos, porque são do baseline, que não
foi tocado.

A pergunta que ficou em aberto acima também tem resposta agora: a U-Net **aprendeu sim a
excluir a traqueia** (15,7% incluída, contra 84,6% do baseline), conforme medido na
análise dos piores casos.

> **A lição:** "anatomia atípica" é uma explicação confortável, porque é difícil de testar
> e soa razoável. A explicação verdadeira era mecânica e verificável. Quando uma hipótese
> não leva a um teste, desconfie dela.
