# Registros de decisão de arquitetura (ADRs)

Cada arquivo registra uma decisão técnica importante do projeto e o porquê dela, no modelo
Contexto / Decisão / Consequências.

| Nº | Decisão | Status | Data |
|---|---|---|---|
| [0001](0001-arquitetura-do-sistema.md) | Separar o sistema em pipeline de experimentos, API e tela | Aceito | 2026-10-05 |
| [0002](0002-linguagem-e-frameworks.md) | Usar Python no processamento e na API, e React + Vite na tela | Aceito | 2026-08-31 |
| [0003](0003-armazenamento-em-arquivos.md) | Guardar dados e resultados em arquivos, sem banco de dados | Aceito | 2026-08-31 |
| [0004](0004-execucao-e-hospedagem.md) | Executar localmente, treinar no Colab e demonstrar com a API em modo pré-calculado | Aceito | 2026-11-23 |

Para registrar uma decisão nova, crie o próximo número (`0005-...md`) no mesmo modelo. Uma
decisão substituída não é apagada: o status muda para "Substituído por 00XX".

Os requisitos do sistema estão em [`../requisitos.md`](../requisitos.md).
