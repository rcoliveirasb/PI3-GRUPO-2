# 0003 - Guardar dados e resultados em arquivos, sem banco de dados

Status: Aceito
Data: 2026-08-31

## Contexto

Há dois tipos de dado no projeto, muito diferentes entre si:

- **Volumes de TC e máscaras**: o LUNA16 tem 888 exames, cerca de 12 GB por subset (mais de
  100 GB no total). São arquivos binários grandes, lidos inteiros e nunca alterados.
- **Resultados**: uma linha por exame e por método (Dice, IoU, sensibilidade, precisão,
  tempo), mais as tabelas finais e as evidências do KDD. São poucos megabytes.

O professor e qualquer pessoa de fora precisam conferir os números sem montar
infraestrutura. Não há usuários cadastrados, nem escrita concorrente, nem consultas que
cruzem tabelas grandes.

## Decisão

Não usar banco de dados.

- Os **volumes** ficam no formato original do LUNA16 (`.mhd`/`.raw`), **fora do Git**
  (`.gitignore`). Quem precisa deles baixa pelo Kaggle (`scripts/download_luna16_subset.py`)
  ou usa a cópia do grupo no Google Drive. A base completa fica num HD externo do Roger.
- Os **resultados** ficam em **CSV versionado no Git**, em `data/luna16/`: um arquivo por
  método e por conjunto de teste, uma linha por exame. As evidências do KDD ficam em
  `data/luna16/kdd/` (CSV e JSON).
- A **API** lê os exames do disco e, no modo `precalculado`, lê PNGs e um JSON já gerados em
  `pji/api/resultados_precalculados/`.
- Os **pesos da U-Net oficial** (`.pt`, poucos MB) ficam no Git, em `pji/modelos/`.

## Consequências

**Melhora**
- Qualquer pessoa confere a tabela oficial só com `git clone` e um comando, sem servidor e
  sem as tomografias.
- Cada mudança de resultado aparece no histórico do Git, com o commit que a gerou.
  `docs/tabela_experimentos.md` cita o commit de cada número.
- CSV abre em qualquer ferramenta (pandas, planilha, editor de texto).

**Piora**
- Não há consulta nem índice: para cruzar dados, é preciso carregar os CSVs no pandas.
- Os volumes dependem de fontes externas (Kaggle, Drive, HD). Se uma delas sair do ar,
  refazer do zero fica mais difícil.
- Não serve para uso com vários usuários gravando ao mesmo tempo. Se o sistema virar um
  serviço com cadastro de exames, um banco de dados terá de ser reavaliado.
