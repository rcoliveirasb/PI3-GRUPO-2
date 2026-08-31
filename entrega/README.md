# EDA de imagens CT em Hounsfield Units

Este diretório contém o notebook reproduzível do EDA do Projeto Integrador sobre uma série de tomografia computadorizada do dataset LIDC-IDRI/TCIA. A análise é objetiva: seleciona uma série CT, carrega o volume DICOM, verifica a distribuição de HU, trata o padding e testa um threshold inicial para a região pulmonar.

## Como executar

Baixe o manifest `TCIA_LIDC-IDRI_20200921.tcia` na fonte oficial do TCIA e coloque-o em `data/TCIA_LIDC-IDRI_20200921.tcia`. Em seguida, abra `eda_lidc_idri_hu_reprodutivel.ipynb` no Google Colab ou em um ambiente Jupyter e execute as células em ordem. O notebook baixa uma única série CT pela API do TCIA e reutiliza a pasta `data/serie_ct` se ela já existir.

O acesso à API exige internet e o download pode levar alguns minutos. O notebook não inclui imagens médicas no repositório, evitando versionar arquivos grandes.

## Estrutura sugerida

```text
.
├── data/
│   ├── TCIA_LIDC-IDRI_20200921.tcia
│   └── serie_ct/
└── eda_lidc_idri_hu_reprodutivel.ipynb
```

## Resultado esperado

Na execução original, foram observados 1.308 UIDs no manifest, uma série com 133 fatias de 512×512 pixels e aproximadamente 21% de padding em `-2048 HU`. Esses números podem variar se outra versão do manifest ou outra série for utilizada.
