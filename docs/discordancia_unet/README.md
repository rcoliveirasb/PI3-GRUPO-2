# Onde a U-Net discorda do gabarito: quem errou?

Pedido do feedback da Sprint 4: *"quando a rede discorda do gabarito, nem sempre ela está
errada. Olhem alguns casos de maior discordância e vejam se o erro está na rede ou no
gabarito."*

- **Imagens:** os 6 exames de teste (Teste A, U-Net de 124 exames) com o maior volume de
  discordância. Foram geradas por `scripts/gerar_discordancia_unet.py`.
- **Cada imagem:** duas fatias. Em cima, a fatia com mais área marcada só pela U-Net
  (**azul**); embaixo, a fatia com mais área marcada só pela referência (**laranja**).
- **Planilha para o grupo:** `discordancia.csv`, com as colunas `veredito` e `comentario` em
  branco. Valores de `veredito`: `rede`, `gabarito`, `ambos` ou `indefinido`.

## Primeira leitura (a confirmar pelo grupo)

A tabela descreve só o que aparece nas imagens, sem diagnóstico.

| # | Exame | Dice | O que a imagem mostra | Leitura provável |
|---|---|---|---|---|
| 1 | …696274044574 | 0,9281 | Em cima: grandes áreas azuis **fora do corpo**, no ar entre as costas e a mesa do tomógrafo (672 mL). Embaixo: só uma borda fina junto ao diafragma. | **Rede.** É o defeito já conhecido (orientação 2) |
| 2 | …360275453085 | 0,9769 | Em cima: azul **fora do corpo**, junto à mesa, e nos **brônquios principais**. Embaixo: laranja em bolhas de ar **abaixo do diafragma**, na frente do abdome. | **Ambos.** A rede marca ar externo e brônquios; o gabarito marca gás do abdome como pulmão |
| 3 | …098781143514 | 0,9677 | Em cima: azul em volta de uma **região densa arredondada** dentro do pulmão direito, que a referência deixa de fora. Embaixo: laranja em ar **abaixo do diafragma**, na região do estômago. | **Gabarito** na fatia de baixo. Na de cima, depende da definição: lesão dentro do pulmão conta como parênquima? |
| 4 | …635595118048 | 0,9858 | Em cima: diferenças pequenas no hilo. Embaixo: laranja em anel em volta de uma **região densa** no pulmão esquerdo, que a referência inclui e a U-Net exclui, e uma borda fina junto ao coração. | **Rede**, se a região densa for parênquima |
| 5 | …091404659845 | 0,9828 | Borda fina junto ao diafragma (azul em cima, laranja embaixo). Embaixo: laranja numa **região densa arredondada** que a U-Net deixa de fora; o exame tem nódulos anotados de 14,8 e 10,9 mm perto da borda. | **Rede** na região densa (coerente com a análise de nódulos); a borda é indefinida |
| 6 | …779172047718 | 0,9808 | **Região densa** no pulmão direito, junto ao coração: a U-Net inclui parte dela numa fatia e a referência inclui parte na outra. Borda fina em volta. | **Indefinido.** As duas máscaras são inconsistentes na mesma região |

## Padrões

1. **O gabarito também erra.** Em 2 dos 6 exames, a máscara do LUNA16 marca **gás do
   estômago ou do intestino, abaixo do diafragma,** como pulmão. Nesses pontos a U-Net está
   certa e é penalizada no Dice.
2. **O erro típico da rede é ar fora do tórax** (exames 1, 2 e 5), além dos brônquios
   principais. É o que o pós-processamento da orientação 2 deve remover.
3. **Regiões densas são o caso ambíguo.** A U-Net às vezes inclui e às vezes exclui; a
   referência também. Para a detecção de nódulos, o desejável é **incluir**: uma lesão fora
   da máscara nunca chega ao detector. Vale o grupo fixar essa definição por escrito.
4. **Bordas finas** de 1 a 2 voxels junto ao diafragma e ao coração são efeito de volume
   parcial e não têm certo nem errado claro.

**Consequência para o artigo:** parte do que o Dice conta como erro da U-Net é erro do
gabarito, e o Dice da rede pode estar levemente subestimado. Não dá para corrigir o número
sem uma referência melhor, mas dá para declarar isso como limitação, com estes exemplos.
