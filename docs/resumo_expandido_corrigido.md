# Segmentação automática do parênquima pulmonar em TCs do LUNA16: comparação entre métodos clássicos e U-Net

**Modalidade:** Resumo Expandido

Érica Souza dos Santos; Amabilly Riva Dutra; Roger Caldeira de Oliveira; Herbe Fragoso; Rafael Cassiano Manchini; Ruan Matheus de Souza

---

## 1 INTRODUÇÃO

A segmentação do parênquima pulmonar em tomografias computadorizadas (TCs) é uma etapa relevante para a identificação de alterações e nódulos, pois delimita a região de interesse e reduz a interferência de estruturas externas. A literatura aborda técnicas como limiarização, crescimento de regiões e operações morfológicas [2], além de redes neurais convolucionais como a U-Net [3]. A escolha do tema baseia-se na necessidade de obter uma segmentação prévia confiável dos exames. Nesse contexto, investiga-se, no conjunto LUNA16, o quanto métodos clássicos baseados na intensidade dos voxels, de menor complexidade computacional e mais fáceis de interpretar, delimitam adequadamente os pulmões em comparação a uma U-Net 2D treinada, mesmo com variações anatômicas e de aquisição. A hipótese é que o parênquima, por ser aerado, ocupa a faixa de baixa densidade da escala Hounsfield (HU) e, por isso, pode ser separado dos demais tecidos por limiarização, atingindo boa concordância com as máscaras de referência.

O objetivo é desenvolver e comparar três métodos automáticos de segmentação pulmonar: (i) limiarização a −600 HU com morfologia matemática (baseline), (ii) crescimento de regiões (*region growing*) com sementes automáticas e (iii) U-Net 2D. A qualidade é medida pelo Dice e pelo IoU entre a máscara predita e a máscara de referência, com intervalos de confiança de 95% por *bootstrap*. Diferentemente da acurácia, essas métricas não são inflacionadas pela grande quantidade de voxels externos aos pulmões, o que permite uma análise adequada da região segmentada. A meta estabelecida é Dice médio ≥ 0,85.

## 2 REFERENCIAL TEÓRICO

O número de casos de câncer de pulmão diagnosticados tardiamente é alarmante, o que torna cada vez mais necessária a detecção automática de nódulos pulmonares em TCs, área ligada à *Computer-Aided Diagnosis* (CAD). Nesse contexto, a segmentação do parênquima pulmonar é a base para a detecção de nódulos, pois determina a região de busca e reduz a interferência de estruturas não relevantes, como costelas, mediastino e vasos maiores. Datasets como o LUNA16 fornecem uma estrutura de avaliação objetiva para algoritmos de detecção automática de nódulos [4]. O conjunto reúne 888 exames de TC da base LIDC-IDRI, anotados por quatro radiologistas experientes em um processo de duas fases [1], e disponibiliza máscaras de referência do parênquima pulmonar.

Abordagens clássicas combinam limiarização por unidades Hounsfield (HU) com morfologia matemática, pois dificilmente se obtêm bons resultados apenas com limiarização. Koyuncu propôs um *framework* em cascata para segmentação do parênquima em TCs axiais, combinando análise de histograma, operações morfológicas, *mean shift* e crescimento de região [2]. Como alternativa supervisionada, a U-Net [3] é uma rede convolucional do tipo codificador-decodificador com conexões de atalho, amplamente usada em segmentação biomédica.

## 3 METODOLOGIA

Trata-se de uma pesquisa aplicada, de natureza quantitativa, que compara três métodos automáticos de segmentação do parênquima pulmonar em TCs.

**Base de dados:** foi utilizado o LUNA16 (espessura de corte ≤ 3 mm, curadoria dos organizadores). Nesta etapa foram usados 177 exames (subsets 0 e 1), aplicando-se ainda os critérios do grupo: máscara de referência presente e não vazia e espaçamento entre fatias ≤ 2,5 mm; nenhum exame foi excluído. Os exames foram divididos por paciente, com semente fixa (42), em treino (70%, 124 exames), validação (15%, 27) e teste (15%, 26), para evitar vazamento de dados entre os conjuntos.

**Pré-processamento:** as imagens foram carregadas com SimpleITK, preservando os metadados de espaçamento. Em seguida, valores de preenchimento (≤ −2047 HU) foram convertidos em ar (−1000 HU), a escala HU foi limitada a [−1000, 400], aplicou-se filtro gaussiano 3D (σ = 0,5 voxel) e os volumes foram reamostrados para espaçamento isotrópico de 1 mm.

**Métodos de segmentação:**
- *Baseline:* limiar HU < −600, remoção do ar de fundo fatia a fatia, retenção dos dois maiores componentes conexos 3D (os dois pulmões), preenchimento de buracos e abertura morfológica (erosão seguida de dilatação) com elemento esférico de raio 1 voxel.
- *Region growing:* sementes automáticas (limiar auxiliar de −320 HU para localizar candidatos e ponto mais interior de cada componente pela transformada de distância) e crescimento por tolerância de intensidade de ±200 HU, com domínio restrito para impedir o vazamento pela traqueia, seguido de preenchimento de buracos.
- *U-Net 2D:* rede compacta com fatias axiais redimensionadas para 128×128, treinada com função de perda BCE + Dice (otimizador Adam, taxa de aprendizado 1e-3), 25 épocas, usando os 124 exames de treino.

**Avaliação:** o Dice, 2|A ∩ B| / (|A| + |B|), e o IoU, |A ∩ B| / |A ∪ B|, são calculados entre a máscara predita (A) e a máscara de referência do LUNA16 (B), nos 26 exames de teste, com IC95% por *bootstrap* (≥ 500 reamostras).

## 4 RESULTADOS E DISCUSSÃO

Nos 26 exames de teste, o baseline obteve Dice médio de 0,956 (IC95% [0,941; 0,967]) e IoU médio de 0,917 (IC95% [0,893; 0,936]). O *region growing* obteve Dice médio de 0,907 (IC95% [0,838; 0,954]) e IoU médio de 0,855 (IC95% [0,776; 0,913]), e a U-Net, Dice médio de 0,983 e IoU médio de 0,966 [ATUALIZAR: incluir IC95% e confirmar com o `sprint_unet_test.csv`]. Todos os métodos ficaram, em média, acima da meta de 0,85.

Um exame ficou abaixo da meta no baseline (Dice 0,847), e o *region growing* teve três exames abaixo da meta, incluindo um com Dice 0,23 em que o crescimento cobriu apenas parte do pulmão (sensibilidade 0,13), em linha com o esperado para abordagens baseadas em intensidade, que sofrem em regiões de borda irregular e de densidades similares. O desempenho elevado do baseline, que não aprende nada dos dados, indica que segmentar o pulmão é um problema de alto contraste em HU, e não que a U-Net esteja superajustada; ainda assim, ela superou os dois métodos clássicos.

[FIGURA 1: refazer a figura com o limiar real de −600 HU — a versão atual mostra −1000 a −500 HU — e legendas: fatia original, limiar, máscara final após a limpeza.]

Como limitações, a avaliação usa 177 dos 888 exames do LUNA16, o conjunto de teste é pequeno (n = 26) e as máscaras de referência do LUNA16 foram geradas por algoritmo automático, e não por segmentação manual; concordar com elas não equivale a concordar com a anatomia real.

## 5 CONSIDERAÇÕES FINAIS

Este trabalho comparou três métodos de segmentação do parênquima pulmonar em TCs do LUNA16: limiarização com morfologia, *region growing* e U-Net 2D. O baseline clássico atingiu Dice de 0,956, o *region growing*, de 0,907, e a U-Net, de 0,983, todos acima da meta de Dice ≥ 0,85 em média, o que indica que métodos de baixa complexidade computacional já produzem segmentações consistentes, e que a U-Net oferece ganho adicional.

Como trabalhos futuros, pretende-se ampliar a avaliação para os 888 exames do LUNA16, reduzir as falhas do *region growing* e integrar os três modelos em uma API com interface web de demonstração, permitindo sua utilização nas etapas posteriores de detecção de nódulos pulmonares.

## REFERÊNCIAS

[1] ARMATO III, S. G. et al. The Lung Image Database Consortium (LIDC) and Image Database Resource Initiative (IDRI): a completed reference database of lung nodules on CT scans. *Medical Physics*, v. 38, n. 2, p. 915–931, 2011. DOI: 10.1118/1.3528204.

[2] KOYUNCU, H. Lupsix: a cascade framework for lung parenchyma segmentation in axial CT images. *International Journal of Intelligent Systems and Applications in Engineering*, v. 6, n. 4, p. 322–328, 2018. DOI: 10.18201/ijisae.2018448460.

[3] RONNEBERGER, O.; FISCHER, P.; BROX, T. U-Net: convolutional networks for biomedical image segmentation. In: *Medical Image Computing and Computer-Assisted Intervention – MICCAI 2015*. Cham: Springer, 2015. p. 234–241. DOI: 10.1007/978-3-319-24574-4_28.

[4] SETIO, A. A. A. et al. Validation, comparison, and combination of algorithms for automatic detection of pulmonary nodules in computed tomography images: the LUNA16 challenge. *Medical Image Analysis*, v. 42, p. 1–13, 2017. DOI: 10.1016/j.media.2017.06.015.
