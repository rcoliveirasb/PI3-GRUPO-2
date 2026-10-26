# Sprint 5 — material de estudo

Escrito para o Ruan, para estudar depois e conseguir explicar sem consultar nada.
Não é documento de entrega: é explicação, do começo, incluindo as partes que normalmente
ficam implícitas.

---

## Parte 0 — O vocabulário mínimo

Se você não tiver segurança nestes cinco conceitos, o resto não gruda. Eles aparecem
o tempo todo.

### Unidade Hounsfield (HU)

Tomografia não mede "brilho", mede **o quanto cada ponto absorve raio X**, numa escala
calibrada em dois pontos fixos: **água = 0 HU** e **ar = −1000 HU**. Os valores são
absolutos — −850 HU significa a mesma coisa em qualquer tomógrafo do mundo.

Para o nosso problema, a escala relevante:

| Tecido | HU aproximado |
|---|---|
| Ar (fora do corpo, traqueia) | −1000 |
| **Pulmão aerado normal** | **−900 a −700** |
| Pulmão mais denso | −700 a −400 |
| Gordura | −100 |
| Água / líquido | 0 |
| Tecido mole, músculo, sangue | +20 a +70 |
| Osso | +400 a +1000 |

**Por que o pulmão é tão negativo?** Porque ele é quase todo ar. O parênquima é uma
espuma de alvéolos — tecido fininho envolvendo bolsas de ar. A média entre o ar
(−1000) e o tecido (+50) dá algo em torno de −850.

**É daqui que sai tudo.** O limiar de −600 HU do baseline existe porque está no meio do
caminho entre o pulmão (−850) e o tecido mole (+50). Mas só funciona **se o pulmão
estiver aerado**. É exatamente essa condição que quebra nos casos difíceis.

### Voxel, spacing e reamostragem isotrópica

**Pixel** é um quadradinho 2D; **voxel** é um bloquinho 3D. Uma TC é uma pilha de fatias,
então cada voxel tem três medidas:

- `spacing_xy` — o tamanho do voxel dentro da fatia (tipicamente 0,6 a 0,8 mm)
- `spacing_z` — a distância entre fatias (varia muito: de 0,6 a 2,5 mm no nosso dataset)

O problema: um voxel de 0,7 × 0,7 × 2,5 mm é um **tijolo achatado**, não um cubo. Se você
aplicar uma operação morfológica de "raio 1 voxel", ela significa 0,7 mm numa direção e
2,5 mm na outra — ou seja, a mesma linha de código faz coisas diferentes em cada eixo.

**Reamostragem isotrópica** resolve: reconstrói o volume com voxels cúbicos de 1 × 1 × 1 mm.
Aí "raio 1" quer dizer 1 mm em qualquer direção. É por isso que o pipeline faz
`resample_isotropic` antes de segmentar, e é por isso que as métricas são calculadas
nesse espaço, não no original.

> **Para explicar:** "A gente reamostra para voxel cúbico porque senão as operações
> morfológicas teriam significado físico diferente em cada eixo, e o resultado dependeria
> do protocolo do tomógrafo em vez de depender da anatomia."

### Volume parcial

Um voxel é uma caixinha. Se metade dela cai no pulmão (−850) e metade no diafragma (+50),
o tomógrafo não registra as duas coisas — ele registra **uma média**: −400.

Esse valor não corresponde a tecido nenhum. É artefato de resolução. E ele cria uma
**faixa de transição** em volta de toda fronteira do pulmão.

Quanto mais grossa a fatia, mais larga essa faixa. **Com 2,5 mm de espessura, a borda do
pulmão vira um degrau largo em vez de uma linha.** Guarde isso: é a causa raiz de metade
dos problemas que a gente viu.

### Componentes conexos

Pegue todos os voxels marcados como "pulmão" e pergunte: quais estão grudados uns nos
outros? Cada grupo grudado é um **componente conexo**.

Anatomicamente, o esperado é **1 ou 2** (os dois pulmões, às vezes unidos pela carina).
Se a contagem dá 149, ou 2.655, isso significa que a máscara virou confete — e é um
sinal de defeito que o Dice **não mostra**, porque os fragmentos podem ser minúsculos em
volume.

### Transformada de distância

Para cada voxel de uma região, calcula **a que distância ele está da borda mais próxima**.
Voxel encostado na borda → valor baixo. Voxel no meio → valor alto.

Serve para achar "o ponto mais interior" de uma região: é só pegar a posição do **maior
valor**. Em código, `np.argmax` — que devolve a *posição* do máximo, não o valor.

É assim que o region growing escolhe onde começar. E é aí que mora o bug desta sprint.

---

## Parte 1 — O problema e os três métodos

### O que estamos resolvendo

Dada uma tomografia de tórax, produzir uma máscara 3D marcando **quais voxels são
parênquima pulmonar**. Isso é pré-requisito de quase tudo em análise pulmonar: se você
vai procurar nódulos, precisa primeiro saber onde é pulmão.

O gabarito é o `seg-lungs-LUNA16`, com os rótulos:

| Rótulo | O que é |
|---|---|
| 0 | fundo |
| 3 | pulmão direito |
| 4 | pulmão esquerdo |
| **5** | **traqueia / vias aéreas centrais** |

**Nós usamos 3 + 4 e excluímos o 5 de propósito.** Traqueia é via aérea, não parênquima.
Essa decisão está em `src/luna16/io.py` e vai reaparecer de forma importante mais adiante.

### Método 1 — Baseline (limiar + morfologia)

A ideia em uma frase: **ar é escuro, então marque o que é escuro.** Mas só isso não
funciona, e os quatro passos existem para consertar os problemas que aparecem:

1. **Limiar:** marca tudo abaixo de −600 HU.
   *Problema:* pega o ar de fora do corpo também, e o ar do intestino.
2. **Remove o fundo, fatia a fatia:** descarta qualquer região que toque a borda da
   imagem. Isso elimina o ar externo.
   *Por que fatia a fatia e não em 3D?* Porque em 3D a traqueia conecta o pulmão ao ar
   externo (pela boca), e o pulmão seria descartado junto com o fundo. Em 2D, numa fatia
   axial, o pulmão nunca encosta na borda lateral da imagem — sempre há margem de tecido.
3. **Mantém os 2 maiores componentes:** os dois pulmões.
4. **Preenche buracos e faz abertura morfológica:** os vasos dentro do pulmão são tecido
   (não ar), então viram buracos na máscara — mas o gabarito os inclui, porque estão
   dentro do pulmão. Preencher resolve.

**A limitação fundamental:** o passo 1 decide tudo, e ele só olha **intensidade**. Se o
parênquima estiver mais denso que −600 HU, ele é descartado — e nenhum dos passos
seguintes recupera, porque eles só limpam o que o limiar já marcou.

### Método 2 — Region growing

A ideia: em vez de um limiar global fixo, **comece de um ponto dentro do pulmão e vá
crescendo** para os vizinhos que tenham intensidade parecida.

- Acha um ponto inicial (**semente**) dentro de cada pulmão.
- Cresce incluindo vizinhos dentro de uma **banda de ±200 HU em torno do valor da
  semente**.

**O ponto crucial, e que quase todo mundo erra ao explicar:** a banda é centrada no
**valor da semente**, não num valor fixo. Se a semente vale −850, a banda é
[−1050, −650] e cobre pulmão aerado. Se a semente vale −602, a banda é [−802, −402] e
**não cobre** pulmão aerado (−850 fica de fora!).

Ou seja: **o método inteiro depende de onde a semente cai.** Essa é a fragilidade dele, e
foi o que a gente provou nesta sprint.

A semente é escolhida automaticamente (não há clique de usuário): pega o componente de ar,
calcula a transformada de distância e escolhe o ponto mais interior via `argmax`.

### Método 3 — U-Net 2D

Rede neural convolucional, treinada com exemplos: dada uma fatia, produza a máscara.

Arquitetura em U: o **encoder** vai comprimindo a imagem (ganha contexto, perde detalhe),
o **decoder** vai reconstruindo, e as **skip connections** ligam cada nível do encoder ao
nível correspondente do decoder — é isso que permite ter contexto *e* borda precisa ao
mesmo tempo.

Nossa configuração: entrada 128×128, `base_ch=32`, loss BCE+Dice, 1,9 M de parâmetros.

**A diferença conceitual que importa:** o baseline e o region growing decidem por
**intensidade**. A U-Net decide por **aparência e forma** — ela aprendeu como pulmão se
parece, onde ele fica, que formato tem. Por isso ela consegue marcar parênquima denso que
o limiar descartaria.

**Mas ela não tem nenhuma regra anatômica embutida.** O baseline tem "descarte o que toca
a borda da imagem" escrito no código. A U-Net não tem nada disso — só o que aprendeu dos
exemplos. Essa assimetria é a chave do segundo bug desta sprint.

---

## Parte 2 — As métricas, e o que elas escondem

### Dice e IoU

**Dice** = 2 × (interseção) / (soma dos dois volumes). Vai de 0 a 1.

**IoU** (Jaccard) = interseção / união. Sempre menor que o Dice, pune erro de forma com
mais severidade.

### Sensibilidade e precisão — e por que importam mais que o Dice

- **Sensibilidade** = do pulmão que existe, quanto eu marquei? *(mede omissão)*
- **Precisão** = do que eu marquei, quanto é pulmão de verdade? *(mede excesso)*

**O Dice mistura os dois num número só, e com isso apaga a direção do erro.** Dois
métodos com Dice 0,95 podem ser completamente diferentes: um marca pulmão demais, o outro
de menos. Para uso clínico isso é decisivo — não é a mesma coisa.

> **Para explicar:** "O Dice diz *quanto* você errou. Sensibilidade e precisão dizem
> *para que lado*. E quase sempre é o lado que importa."

### Os quatro pontos cegos que a gente documentou

Isto é o coração da análise e o que rende no artigo:

**1. O Dice não tem direção.** Nos 12 exames que inspecionei, a predição **sempre**
subestimou o volume — em média 5%, até 22%. Nunca superestimou. Se alguém usar essas
máscaras para medir volume pulmonar, o erro é sistemático e sempre para baixo. **O Dice
não mostra isso**, porque pune igual os dois lados.

**2. A média por paciente esconde as fatias ruins.** Dice médio de 0,96 por paciente, mas
**799 de 3.635 fatias (22%) têm Dice abaixo de 0,8**, e 11 dos 12 exames têm pelo menos
uma fatia com Dice **exatamente zero**. As fatias ruins se concentram nas bases, onde o
pulmão é uma lâmina fina.

**3. Erros pequenos em volume podem ser graves em anatomia.** A traqueia estava dentro da
predição em **12 de 12 exames** (418 mL dos 470 rotulados). O gabarito a exclui de
propósito. É um viés sistemático, 100% dos casos, e **invisível no Dice** porque a traqueia
é pequena perto do pulmão.

**4. A média entre pacientes esconde a cauda.** É o achado principal: comparar os métodos
pelo Dice médio (0,956 contra 0,978) sugere ganho modesto. Mas o ganho está concentrado
nos casos difíceis.

---

## Parte 3 — O achado principal (Sprint 4)

### O número

| Grupo | Ganho médio da U-Net |
|---|---|
| 3 piores exames do baseline | **+0,0941** |
| Outros 23 | **+0,0133** |
| | **razão 7,1×** |

E por quartil de dificuldade: **+0,0536 → +0,0187 → +0,0155 → +0,0011**. Queda monotônica,
correlação de **−0,92** entre o Dice do baseline e o ganho.

**Por que a correlação importa mais que a razão:** a razão entre o primeiro e o último
quartil daria "48×", mas com denominador de 0,0011 esse número é instável — qualquer
ruidinho o move muito. A correlação de −0,92 sobre os 26 pontos é robusta e diz a mesma
coisa. **Se alguém questionar o 7×, é para a correlação que você aponta.**

### O mecanismo, que é o que o professor pediu

Nos casos difíceis, o parênquima está **mais denso que −600 HU**. Pode ser por várias
razões (e aqui a gente **não diagnostica** — só descreve o que a imagem mostra): a região
aparece mais acinzentada em vez de preta.

O limiar descarta tudo isso em bloco. A U-Net recupera porque decide por forma, não por
intensidade.

E o erro dos métodos clássicos é **de omissão**: no pior caso, baseline deixou de marcar
**354 mL** de pulmão com apenas **24 mL** de falso positivo. Eles não erram o que marcam —
**deixam de marcar**.

> **A frase que resume tudo:** "A média esconde o argumento. A U-Net não melhora tudo um
> pouco — ela conserta os casos ruins. O Dice mínimo sobe de 0,847 para 0,928 e os exames
> abaixo de 0,85 caem de um para nenhum."

---

## Parte 4 — As duas correções desta sprint

### Correção 1 — A semente do region growing

**O sintoma:** no exame `…079549658100`, o region growing deu Dice **0,226**. No mesmo
exame, baseline dá 0,980 e U-Net 0,988. **O exame é fácil** — não é caso difícil, é falha
do método.

**O que a imagem mostrava:** a predição não cobria o ar do pulmão. Ela desenhava uma
**árvore ramificada** acompanhando os vasos e a borda da pleura, fragmentada em
**2.655 componentes conexos** (contra 5 do baseline).

**A verificação numérica** (isto é o que transforma suspeita em achado):

```
exame que colapsa:   semente HU = -602  ->  banda [-802, -402]   NÃO cobre -850
exame de controle:   semente HU = -912  ->  banda [-1112, -712]  cobre
                     semente HU = -967  ->  banda [-1167, -767]  cobre
```

**A cadeia causal completa, que é como você deve explicar:**

1. O componente candidato é achado com limiar **permissivo** de −320 HU (não −600).
2. Sendo permissivo, ele inclui a **franja de volume parcial** junto com o ar de verdade.
3. O `argmax` da transformada de distância escolhe o ponto **geometricamente** mais
   central — ele **não olha o HU**.
4. Nesse exame, o ponto mais central calhou de cair na franja: **−602 HU**.
5. A banda de ±200 virou [−802, −402], que **não alcança** o parênquima aerado de −850.
6. O crescimento ficou preso na franja ao redor dos vasos → árvore ramificada,
   2.655 fragmentos, Dice 0,226.

**A correção:** antes do `argmax`, zerar a distância nos voxels que não são ar de verdade.
O ponto continua sendo o mais interior — mas só entre os voxels abaixo de −750 HU.

```python
aerado = volume_hu[slices] < -750
if (aerado & local_mask).any():
    local_distance = np.where(aerado, local_distance, 0)
```

Três linhas. Com salvaguarda: se nenhum voxel passar no corte, mantém o comportamento
antigo em vez de falhar.

**Resultado: Dice 0,2263 → 0,9779.**

**Por que −750 e não outro valor?** Precisa ser baixo o bastante para excluir a franja
(que estava em −602) e alto o bastante para não excluir pulmão aerado legítimo (−900 a
−700). −750 fica confortavelmente entre os dois.

### Correção 2 — Componentes fora do tórax na U-Net

**O sintoma:** no exame `…696274044574`, a U-Net deu Dice **0,928** contra 0,973 do
baseline. **É o único dos 26 em que ela perde feio.**

**O que a imagem mostrava:** manchas vermelhas grandes na **borda inferior da imagem,
fora do corpo do paciente** — o ar do colchão e da mesa do tomógrafo, marcado como
pulmão. **672,5 mL**, dez vezes o falso positivo do baseline no mesmo exame.

**Por que acontece:** a U-Net decide por aparência local, e naquela região o colchão
parece pulmão — escuro, cercado de material mais claro. Ela nunca aprendeu "isto está
fora do corpo", porque **ninguém ensinou e ela não tem como inferir só da aparência**.

**E por que o baseline não cai nessa:** porque tem a regra `remove_background_per_slice`
escrita no código, descartando o que toca a borda da imagem. É uma **restrição anatômica
explícita**, que a U-Net simplesmente não tinha.

> **Essa é a lição conceitual mais interessante da sprint:** métodos clássicos carregam
> conhecimento anatômico embutido à mão; redes neurais carregam só o que extraíram dos
> dados. Quando o conhecimento é espacial e não aparece na aparência local, a rede não
> aprende — e o jeito de consertar não é treinar mais, é **devolver a restrição**.

**A correção:** aplicar à saída da U-Net a mesma `keep_largest_components` que os outros
dois métodos já usavam. Reaproveitamento, não código novo.

**Resultado: Dice 0,9281 → 0,9679. Falso positivo 672,5 → 239,4 mL.**

**O detalhe que valida a correção:** a **sensibilidade não mudou** (0,9829 nos dois). A
limpeza tirou 433 mL de falso positivo sem descartar **um voxel sequer** de pulmão
verdadeiro. Se a sensibilidade tivesse caído, seria sinal de que a regra estava comendo
pulmão junto — e aí seria uma correção ruim.

> **Guarde esse raciocínio.** Quando você aplica um filtro que remove coisas, sempre
> verifique a sensibilidade. Se ela cai, o filtro está removendo demais. É a checagem que
> separa uma correção de um band-aid.

### O que as correções deram nos 26 exames

Medido com `scripts/medir_correcoes.py`, rodando as duas versões **no mesmo volume e no
mesmo pré-processamento** — assim a diferença é atribuível só à correção, não a ruído.

| | Region growing | U-Net |
|---|---|---|
| Dice médio | 0,9065 → **0,9355** | 0,9781 → **0,9804** |
| Dice mínimo | 0,2263 → **0,5941** | 0,9281 → **0,9628** |
| Melhoraram | 2 | 7 |
| Pioraram | **0** | 1 (−0,0003) |
| Ficaram iguais | 24 | 18 |
| Falso positivo médio | 71,2 → 70,4 mL | 88,1 → **66,8 mL** |
| Sensibilidade média | 0,8666 → **0,8986** | 0,9742 → **0,9742** |

**O que ler nesses números — e é aqui que está a parte interessante:**

**1. As correções são cirúrgicas.** 24 dos 26 exames ficaram **idênticos** no region
growing. Isso é o comportamento certo de uma correção de bug: ela conserta o defeito sem
perturbar o que já funcionava. Se metade dos exames tivesse mudado, seria sinal de que eu
mexi no comportamento geral do método, não num caso patológico.

**2. A U-Net removeu 553 mL de falso positivo nos 26 exames com sensibilidade média
idêntica** (0,9742 nos dois, até a quarta casa). Isso é a prova de que o filtro só tirou
o que não era pulmão. Se tivesse comido pulmão junto, a sensibilidade teria caído.

**3. O ganho médio parece pequeno, e isso é esperado.** +0,0022 na U-Net soa irrelevante —
mas o **mínimo** subiu de 0,9281 para 0,9628. É exatamente o mesmo padrão do achado
principal da Sprint 4: a média esconde, a cauda é onde está o efeito. Aqui a gente caiu na
mesma armadilha que documentou, só que do lado de quem corrige.

**4. O que a correção NÃO resolveu, e é importante dizer.** O region growing continua com
dois exames abaixo de 0,85:

| Exame | Dice | Sensibilidade |
|---|---|---|
| `…658609808059` | 0,7790 | 0,6469 |
| `…021509831276` | 0,5941 | 0,4276 |

Sensibilidade de 0,43 e 0,65 significa que o método **está perdendo pulmão**, não
marcando coisa errada. **Isso é outra falha, não a da semente** — é o mesmo problema do
baseline (parênquima denso e volume parcial em fatia de 2,5 mm). A correção da semente
consertou o que ela podia consertar; esses dois casos têm causa diferente.

> **Lição para o seu raciocínio:** quando uma correção não resolve tudo, verifique se o
> que sobrou é *a mesma falha residual* ou *uma falha diferente*. Aqui a sensibilidade
> baixa diz que é outra coisa — e saber disso evita você ficar ajustando o parâmetro
> errado tentando consertar algo que ele não alcança.

---

## Parte 5 — Como explicar em 2 minutos

Se te derem pouco tempo, é esta a sequência:

1. **O problema:** segmentar pulmão em TC. Três métodos: limiar, region growing, U-Net.
2. **O que parecia:** na média, a U-Net ganha 2 pontos de Dice. Modesto.
3. **O que a gente olhou:** abrimos as imagens dos piores casos, em vez de só comparar
   médias.
4. **O que achamos:** o ganho da U-Net é **7× maior nos casos difíceis**, com correlação
   de −0,92 entre dificuldade e ganho. Ela não melhora tudo um pouco — conserta a cauda
   ruim.
5. **Por quê:** onde o parênquima está denso demais para o limiar de −600 HU, os métodos
   clássicos **deixam de marcar** (354 mL num exame). A U-Net decide por forma, não por
   intensidade.
6. **A honestidade:** a U-Net também erra — marcou 672 mL de ar da mesa do tomógrafo.
   E a gente corrigiu.
7. **O que consertamos:** dois bugs diagnosticados pela imagem e verificados no número —
   a semente do region growing (0,226 → 0,978) e o pós-processamento da U-Net
   (0,928 → 0,968).

---

## Parte 6 — Perguntas difíceis, com resposta

**"Isso não é só overfitting da U-Net?"**
Não. Os 26 exames são de teste e **nenhum** estava no treino — isso é verificado no
notebook contra os `train_uids` guardados no próprio checkpoint, não contra o split.

**"O 7× não é artefato de pegar só 3 exames?"**
Por isso a gente reporta também a correlação de −0,92 sobre os 26 e a queda monotônica
nos quatro quartis. Três métricas independentes apontando o mesmo.

**"Vocês consertaram o region growing só para ele ficar bonito?"**
Ao contrário: o conserto **melhora o concorrente**, não o nosso método. Diagnosticamos a
causa (semente em −602 HU), verificamos numericamente contra um exame de controle e
corrigimos. Isso fortalece a comparação, porque agora ela é justa.

**"Por que a U-Net é 2D e não 3D?"**
Restrição de recurso — 2D treina em minutos, 3D exigiria muito mais. É limitação
reconhecida, não escolha ótima. Uma U-Net 3D provavelmente resolveria sozinha o problema
do ar da mesa, porque teria contexto volumétrico.

**"Por que não usar sensibilidade e precisão em vez de Dice?"**
A gente usa os dois — e defende que o Dice sozinho é insuficiente, justamente por não ter
direção. Os quatro pontos cegos da Parte 2 são o argumento.

**"O que vocês fariam com mais tempo?"**
Remover a traqueia explicitamente da predição (viés presente em 100% dos casos), reportar
o viés de volume junto do Dice, e avaliar Dice por fatia em vez de só por paciente.

---

## Parte 7 — Onde está cada coisa

| Arquivo | O que tem |
|---|---|
| `analise_piores_casos_grp2.ipynb` | análise dos 6 exames, 3 fatias × 5 painéis |
| `docs/piores_casos/` | as figuras e as métricas |
| `entrega/inspecao_visual/` | os 12 exames aleatórios (não commitado) |
| `src/luna16/region_growing.py` | a correção da semente, em `_find_seed_points` |
| `src/luna16/unet.py` | a correção do pós-processamento, em `segment_with_unet` |
| `scripts/medir_correcoes.py` | a medição antes/depois nos 26 exames |

**Para rodar qualquer coisa:** sempre a partir da raiz do repositório, com caminho
relativo (`data/luna16`). Caminho absoluto quebra a leitura do SimpleITK nessa pasta.

**As duas correções são reversíveis por parâmetro**, o que serve para auditoria:

```python
segment_region_growing(vol, seed_max_hu=-1e9)        # comportamento antigo
segment_with_unet(vol, modelo, limpar_fora_do_torax=False)  # comportamento antigo
```
