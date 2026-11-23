# Perguntas difíceis da banca: respostas para ensaiar

As quatro primeiras são as que o professor pediu na orientação final. As outras são as
que a banca provavelmente vai fazer a partir dos números. Cada resposta tem a frase curta,
para falar em voz alta, e os números que a sustentam. A fonte de cada número está em
[`tabela_experimentos.md`](tabela_experimentos.md).

---

## 1. Por que a rede e não o método simples?

**Frase curta:** na média os dois são bons, mas o método simples falha justamente onde
importa: nos exames difíceis e na borda do pulmão, onde ficam os nódulos colados na
parede.

- No teste oficial (107 exames), o Dice médio é 0,984 na U-Net e 0,949 no baseline. A U-Net
  ganha em **107 de 107** exames.
- O pior exame da U-Net tem Dice 0,955. O do baseline tem 0,381, e ele tem 3 exames abaixo
  da meta de 0,85. O region growing tem 6.
- No Teste A, o baseline apagou 13 de 43 nódulos, e a U-Net apagou 3 (pergunta 2).
- **O que a gente admite:** o ganho médio é pequeno (+0,035), e a rede exige treino, dados
  rotulados e mais computação. Se o objetivo fosse só o volume do pulmão, o baseline
  bastaria.

## 2. O que acontece com o nódulo apagado?

**Frase curta:** ele nunca chega ao detector. Se a máscara deixa o nódulo de fora, a etapa
seguinte nem procura ali.

- No Teste A (26 exames, 43 nódulos anotados), foi medido se cada nódulo continua dentro da
  máscara (pelo menos 50% da esfera anotada):
  - **baseline:** apaga 13, entre eles 8 dos 9 colados na pleura;
  - **U-Net:** apaga 3;
  - a U-Net mantém 11 nódulos que o baseline apaga, e o contrário acontece só 1 vez
    (McNemar, p = 0,006).
- **Por quê:** um nódulo colado na parede é tecido denso, acima de −600 HU. O limiar o
  classifica como "não pulmão", e o preenchimento de buracos não o recupera, porque ele não
  é um buraco fechado: está aberto para a parede.
- **Figura:** `docs/seminario/nodulo_apagado.png`.
- **O que a gente admite:** essa análise foi feita no Teste A, e não no teste oficial de 107
  exames.

## 3. De onde vem o gabarito, e por que ele também erra?

**Frase curta:** o gabarito do pulmão do LUNA16 foi gerado por um algoritmo automático, e
não desenhado por um radiologista. O Dice mede a concordância com outro algoritmo.

- Os nódulos (`annotations.csv`) foram anotados por radiologistas. A **máscara do pulmão**
  (`seg-lungs-LUNA16`) não foi.
- Nos 6 exames em que a U-Net mais discorda do gabarito, em 2 a máscara do LUNA16 marca gás
  do estômago ou do intestino, abaixo do diafragma, como pulmão. A U-Net está certa e
  perde Dice por isso (`docs/discordancia_unet/`).
- O gabarito também separa a traqueia (rótulo 5) do pulmão, e os métodos a incluem (pergunta
  9).
- **Consequência:** parte do "erro" que o Dice conta é erro da referência. Isso está escrito
  nas limitações do relatório.

## 4. Quantas vezes o teste foi aberto?

**Frase curta:** o teste antigo, de 26 exames, foi aberto várias vezes, e por isso virou
histórico. O teste oficial, de 107 exames, foi usado só para medir, uma vez, depois que os
métodos estavam fechados.

- **Teste A (26 exames):** foi olhado para diagnosticar erros. As duas correções de 26/10 (a
  semente do region growing e a limpeza da U-Net) e a inspeção visual de 12 exames usaram
  esse conjunto. Por isso ele não serve mais como teste independente.
- **Teste oficial (107 exames):** foi sorteado entre os 710 exames que ficaram fora da
  primeira fase, sem nenhum dos 177 antigos.
  - A U-Net nova foi avaliada nele em 09/11.
  - Os três métodos rodaram nele uma única vez, em 21/11, com o código já corrigido.
  - Nenhum parâmetro foi mudado depois disso. [CONFIRMAR: ninguém olhou imagens dos 107
    antes de 21/11]
- **O que a gente admite:** a redação formal das hipóteses (H0/H1) foi feita depois dos
  resultados do Teste A. O teste de 107 exames é o que confirma as hipóteses.

---

## 5. Por que o region growing, que é "mais inteligente", perdeu do limiar simples?

- A semente fica no ar do pulmão, abaixo de −750 HU. Com a banda de ±200 HU, o crescimento
  para por volta de −650 a −770 HU, um teto mais apertado que os −600 HU do baseline.
- Ele deixa de fora o pulmão mais denso: a sensibilidade é 0,901, contra 0,934 do baseline,
  e a precisão é maior (0,981 contra 0,968).
- Foi melhor que o baseline em só 15 de 107 exames. É um resultado negativo legítimo:
  adaptativo não quer dizer melhor.

## 6. Por que Dice e não acurácia?

A maior parte do volume da tomografia é fundo. Um método que não marcasse nada teria
acurácia alta. O Dice só olha a sobreposição entre a máscara prevista e a de referência,
então não é inflado pelo fundo.

## 7. A rede não é mais lenta?

- No Teste A, medido na mesma máquina, em CPU, a U-Net antiga levava 62 s por exame, contra
  16 s do baseline (cerca de 4 vezes mais).
- No teste oficial, os tempos foram 7,1 s (U-Net), 6,3 s (baseline) e 8,0 s (region
  growing), mas numa máquina que não ficou registrada e com outra rede.
- **Resposta honesta:** "com GPU a diferença some; em CPU a rede foi até quatro vezes mais
  lenta na nossa medição controlada. A medição do teste novo não é comparável, porque foi
  em outra máquina."

## 8. Por que 107 exames e não 99?

O sorteio deu 497/106/107. O filtro de espaçamento acima de 2,5 mm tiraria 8 exames do teste
e deixaria 99, mas a U-Net oficial foi treinada e avaliada sem esse filtro. Para os três
métodos ficarem na mesma régua, o teste oficial é o de 107 (`docs/base_oficial.md`).

## 9. E a traqueia?

- O gabarito exclui a traqueia (rótulo 5). Os métodos clássicos a incluem, porque ela
  também é ar.
- Nos 26 exames do Teste A, a máscara do baseline contém **88%** da traqueia, e a do region
  growing, **84%**. A **U-Net contém só 7%**: ela aprendeu com o gabarito a deixá-la de fora.
  É mais um ponto em que a rede acerta e o limiar não tem como acertar.
- O erro quase não aparece no Dice, porque a traqueia é pequena perto do pulmão.
- Está declarado como limitação dos métodos clássicos, com figura e medida:
  `docs/traqueia/traqueia_3_metodos.png` e `docs/traqueia/traqueia_por_exame.csv`.
- Para removê-la do baseline, seria preciso um crescimento de região a partir da traqueia,
  subtraído da máscara. Isso ficou como trabalho futuro.

## 10. Duas sementes bastam?

- As duas sementes dão 0,9841 e 0,9834 nos 99 exames em comum, uma variação de ±0,0004. Essa
  variação é menor que o intervalo de confiança de cada uma.
- O professor pediu "duas ou três". Com duas, dá para dizer que o resultado não é sorte de
  uma inicialização. Uma terceira deixaria a estimativa da variação mais firme.

## 11. Por que apareceram três Dice diferentes para a mesma rede (0,9781, 0,9818 e 0,9827)?

É a mesma rede antiga, de 124 exames, nos mesmos 26 exames, com três versões do
pós-processamento:
- **0,9781:** antes da correção da limpeza;
- **0,9827:** pós-processamento do Colab;
- **0,9818:** código corrigido, o mesmo dos outros métodos. **É o número que vale.**

Hoje o resultado oficial é outro, o da rede nova nos 107 exames: 0,9838. A tabela única
explica cada um.

## 12. A tela mostra os mesmos números do relatório?

Sim. Até 23/11 a API usava uma implementação própria, com resultados diferentes. Desde
então, ela usa o mesmo código dos experimentos, e um teste automático confere isso
(`pji/api/tests/test_metodos_iguais_ao_artigo.py`).

## 13. Isso pode ser usado num hospital?

Não. É um trabalho acadêmico, e não um dispositivo médico. Uso clínico exigiria registro na
ANVISA (RDC 657/2022), validação prospectiva em vários hospitais e monitoramento. O sistema
ajuda a localizar regiões para um especialista revisar. Ele não dá diagnóstico.
