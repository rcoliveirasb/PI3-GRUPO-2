# Referências do projeto

Pedido da pré-banca (critério "fundamentação científica", nota 6,3; orientação 7: *"cada
decisão importante deve apontar para o trabalho que a sustenta"*). Cada referência vem com a
frase do nosso trabalho que ela sustenta.

**Antes de pôr no artigo:** abra cada PDF e confira volume, páginas e DOI. A coluna
"Conferência" diz o que já foi checado:
- ✔ título, revista e ano conferidos em fonte online;
- **conferir**: referência conhecida, ainda não checada nesta lista.

## 1. Base de dados e gabarito

| Referência | Frase que sustenta | Conferência |
|---|---|---|
| Setio AAA, Traverso A, de Bel T, et al. *Validation, comparison, and combination of algorithms for automatic detection of pulmonary nodules in computed tomography images: The LUNA16 challenge.* Medical Image Analysis, v. 42, 2017. arXiv:1612.08012. | "Usamos o LUNA16, com 888 TCs derivadas do LIDC-IDRI, base padrão para avaliar detecção de nódulos." | ✔ (páginas 1–13: conferir) |
| Armato SG III, McLennan G, Bidaut L, et al. *The Lung Image Database Consortium (LIDC) and Image Database Resource Initiative (IDRI): a completed reference database of lung nodules on CT scans.* Medical Physics, 38(2):915–931, 2011. doi:10.1118/1.3528204. | "Os nódulos de referência foram anotados por radiologistas do LIDC-IDRI." | conferir |
| van Rikxoort EM, de Hoop B, Viergever MA, Prokop M, van Ginneken B. *Automatic lung segmentation from thoracic computed tomography scans using a hybrid approach with error detection.* Medical Physics, 36(7):2934–2947, 2009. | "A máscara de referência do LUNA16 foi gerada por algoritmo automático, não por radiologista." | ✔ o artigo existe; **falta confirmar** na página de dados do LUNA16 que as máscaras `seg-lungs-LUNA16` vêm dele. Até lá, cite só a página do LUNA16 |

## 2. Métodos de segmentação

| Referência | Frase que sustenta | Conferência |
|---|---|---|
| Hu S, Hoffman EA, Reinhardt JM. *Automatic lung segmentation for accurate quantitation of volumetric X-ray CT images.* IEEE Transactions on Medical Imaging, 20(6):490–498, 2001. | "O baseline segue a abordagem clássica de limiar de intensidade seguido de operações morfológicas." | conferir |
| Adams R, Bischof L. *Seeded region growing.* IEEE Transactions on Pattern Analysis and Machine Intelligence, 16(6):641–647, 1994. | "O segundo método é crescimento de região a partir de sementes." | conferir |
| Ronneberger O, Fischer P, Brox T. *U-Net: Convolutional Networks for Biomedical Image Segmentation.* MICCAI 2015, LNCS 9351, p. 234–241. arXiv:1505.04597. | "O terceiro método é uma U-Net 2D, arquitetura de referência para segmentação de imagens médicas." | conferir |
| Milletari F, Navab N, Ahmadi SA. *V-Net: Fully Convolutional Neural Networks for Volumetric Medical Image Segmentation.* 3DV 2016. | "A função de perda combina entropia cruzada com Dice, que lida melhor com o desbalanço entre fundo e pulmão." | conferir |
| Hofmanninger J, Prayer F, Pan J, Röhrich S, Prosch H, Langs G. *Automatic lung segmentation in routine imaging is primarily a data diversity problem, not a methodology problem.* European Radiology Experimental, 4:50, 2020. doi:10.1186/s41747-020-00173-2. | (a) "Trabalhos recentes relatam Dice de 0,97 a 0,98 para U-Net em segmentação de pulmão, faixa em que estão nossos resultados." (b) "A diversidade dos dados de treino pesa mais que a arquitetura, o que é coerente com a melhora do pior exame ao treinar com 479 exames em vez de 124." | ✔ (relata Dice 0,97–0,98 para U-Net) |

## 3. Segmentação e nódulos colados na parede

| Referência | Frase que sustenta | Conferência |
|---|---|---|
| Armato SG III, Sensakovic WF. *Automated lung segmentation for thoracic CT: impact on computer-aided diagnosis.* Academic Radiology, 11(9):1011–1021, 2004. | "Já se sabe que a segmentação por limiar pode deixar de fora nódulos colados na parede (justapleurais), o que prejudica a detecção." | **conferir**: a busca não trouxe o texto do artigo. Não citar números dele sem ler o PDF |

## 4. Métrica e estatística

| Referência | Frase que sustenta | Conferência |
|---|---|---|
| Dice LR. *Measures of the amount of ecologic association between species.* Ecology, 26(3):297–302, 1945. | "O coeficiente de Dice mede a sobreposição entre duas máscaras." | conferir |
| Taha AA, Hanbury A. *Metrics for evaluating 3D medical image segmentation: analysis, selection, and tool.* BMC Medical Imaging, 15:29, 2015. | "Usamos Dice e IoU, métricas padrão para segmentação 3D; acurácia seria enganosa pelo desbalanço entre fundo e pulmão." | conferir |
| Efron B, Tibshirani RJ. *An Introduction to the Bootstrap.* Chapman & Hall, 1993. | "O intervalo de confiança de 95% foi estimado por bootstrap com 10.000 reamostras." | conferir |
| Wilcoxon F. *Individual comparisons by ranking methods.* Biometrics Bulletin, 1(6):80–83, 1945. | "A comparação entre métodos usou o teste de Wilcoxon pareado, que não assume normalidade." | conferir |
| Holm S. *A simple sequentially rejective multiple test procedure.* Scandinavian Journal of Statistics, 6(2):65–70, 1979. | "Os p-valores foram corrigidos por Holm, porque fizemos mais de uma comparação." | conferir |
| McNemar Q. *Note on the sampling error of the difference between correlated proportions or percentages.* Psychometrika, 12(2):153–157, 1947. | "A preservação de nódulos entre métodos foi comparada com o teste exato de McNemar, para dados pareados." | conferir |

## Como usar no artigo

- **Introdução:** Setio 2017 (o problema e a base), Armato & Sensakovic 2004 (por que segmentar
  bem importa para a detecção).
- **Métodos:** Hu 2001, Adams 1994, Ronneberger 2015 e Milletari 2016 (os três métodos e a
  perda); Dice 1945, Taha 2015, Efron 1993, Wilcoxon 1945, Holm 1979 e McNemar 1947 (métricas e
  estatística).
- **Discussão:** Hofmanninger 2020 (comparação com a literatura e o papel da diversidade dos
  dados), Armato & Sensakovic 2004 (nódulos de borda).
- **Limitações:** a página do LUNA16 e van Rikxoort 2009 (gabarito gerado por algoritmo),
  junto com os exemplos de `docs/discordancia_unet/`.
