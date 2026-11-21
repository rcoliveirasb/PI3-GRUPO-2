# Relatorio do pipeline KDD (gerado automaticamente)

Gerado por `scripts/pipeline_kdd.py` em 2026-11-16 15:20. Nao editar a mao:
rode o script de novo. A explicacao de cada etapa esta em `docs/kdd.md` e a das
hipoteses em `docs/hipotese.md`.

## 1. Selecao
- Exames encontrados: 178; incluidos: 177
- Espacamento entre fatias: 0.50 a 2.50 mm (criterio: <= 2,5 mm)
- Split por paciente: treino 124, validacao 27, teste 26 (disjunto: sim)

## 2. Pre-processamento (exame ...658609808059)
- HU bruto: [-3024, 2211] -> limpo: [-1000, 400]
- Voxels de padding fora do campo de visao: 21.28%
- Filtro Gaussiano (sigma 0,5): desvio do ruido removido = 68.27 HU

## 3. Transformacao
- Espacamento original (x, y, z): [0.549, 0.549, 1.25] mm -> 1 mm isotropico
- Volume (z, y, x): [161, 512, 512] -> [201, 281, 281]
- Entrada da U-Net: [128, 128], valores em [-1.0, 0.966]

Figura: `etapa2_3_preprocessamento_transformacao.png`

## 4. Mineracao de dados
- Tres metodos avaliados nos mesmos 26 exames de teste.
- Reprodutibilidade: 3 reexecucoes em 1 exame(s);
  todas reproduzem o Dice salvo (tolerancia 0.0001): True

## 5. Interpretacao / avaliacao

| Metodo | Dice [IC95%] | IoU [IC95%] | Tempo/TC (s) |
|---|---|---|---|
| Baseline (threshold -600HU + morfologia) | 0.9555 [0.9416, 0.9663] | 0.9165 [0.8928, 0.9350] | 15.9511 [13.8279, 18.3373] |
| Region growing | 0.9354 [0.9006, 0.9582] | 0.8867 [0.8378, 0.9201] | 19.3794 [16.8966, 22.1994] |
| U-Net 2D | 0.9818 [0.9790, 0.9843] | 0.9644 [0.9590, 0.9691] | 62.1329 [57.4690, 66.9763] |

### Teste das hipoteses (Wilcoxon unilateral pareado, Holm, alfa = 0,05)

| Hipotese | H1 | Efeito [IC95%] | p (Holm) | Conclusao |
|---|---|---|---|---|
| H1 (Baseline) | Dice medio do Baseline > 0.85 | 0.9555 [0.9416; 0.9663] | 5.96e-08 | H0 rejeitada: evidencia a favor de H1 |
| H1 (Region growing) | Dice medio do Region growing > 0.85 | 0.9354 [0.9006; 0.9582] | 1.88e-05 | H0 rejeitada: evidencia a favor de H1 |
| H1 (U-Net 2D) | Dice medio do U-Net 2D > 0.75 | 0.9818 [0.9790; 0.9843] | 4.47e-08 | H0 rejeitada: evidencia a favor de H1 |
| H2 | Dice do Region growing > Dice do Baseline | -0.0200 [-0.0434; -0.0064] | 1.00e+00 | H0 nao rejeitada: o efeito observado e o oposto do previsto (IC95% inteiro abaixo de 0) |
| H3a | Dice do U-Net 2D > Dice do Baseline | 0.0263 [0.0176; 0.0378] | 2.98e-08 | H0 rejeitada: evidencia a favor de H1 |
| H3b | Dice do U-Net 2D > Dice do Region growing | 0.0464 [0.0254; 0.0790] | 2.98e-08 | H0 rejeitada: evidencia a favor de H1 |
