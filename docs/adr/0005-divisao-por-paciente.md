# 0005 - Dividir os dados por paciente, em 70/15/15, com teste oficial de 107 exames

Status: Aceito
Data: 2026-09-14 (teste oficial de 107 exames definido em 2026-11-22)

## Contexto

Uma tomografia tem centenas de fatias, e fatias vizinhas são quase iguais. Se a divisão
entre treino e teste fosse feita por fatia, a U-Net veria no treino fatias praticamente
idênticas às do teste, e o Dice sairia inflado.

O grupo usava 60/20/20 até o Sprint 8. No feedback do Checkpoint 1, o professor exigiu a
proporção **70/15/15**. Depois, a base passou de 177 exames (subsets 0 e 1) para os 888 do
LUNA16, e era preciso garantir que o teste final não tivesse sido olhado durante o
desenvolvimento.

## Decisão

- Dividir **por paciente**, nunca por fatia, na proporção **70/15/15**, com **semente 42**
  (`src/luna16/splits.py`).
- Primeira fase: 177 exames, com o **Teste A** de 26 exames. Ficou como histórico.
- Fase final (`data/luna16/split_novo/split_novo.csv`): os 710 exames que não estavam na
  primeira fase foram divididos em **497 de treino, 106 de validação e 107 de teste**
  (`teste_interno`). O teste de 107 é o **teste oficial** do projeto. Nenhum desses 107
  estava entre os 177 da primeira fase.
- O teste não é usado para treinar nem para ajustar parâmetros.

## Consequências

**Melhora**
- Sem vazamento entre fatias do mesmo paciente.
- A proporção atende à exigência do professor.
- O teste oficial é formado por exames que ninguém usou para ajustar os métodos clássicos,
  o que responde à crítica de "conjunto de teste inspecionado".
- 107 exames dão intervalos de confiança mais estreitos que os 26 do Teste A.

**Piora**
- Os resultados da primeira fase (Teste A) e da fase final não são diretamente comparáveis.
  Os documentos precisam dizer sempre de qual conjunto é cada número
  (`docs/tabela_experimentos.md` faz isso).
- Mudar a divisão obrigou a reavaliar os três métodos e a refazer tabelas e slides.
- Algumas análises (nódulos apagados, ganho por quartil de dificuldade) ainda estão só no
  Teste A, porque precisam das tomografias do HD para serem refeitas.
