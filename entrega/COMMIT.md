# Como adicionar ao GitHub

Copie o notebook `eda_lidc_idri_hu_reprodutivel.ipynb` e o `README.md` para a pasta correspondente do repositório. Não versione as imagens DICOM nem arquivos grandes do dataset; mantenha apenas instruções para obtê-los.

```bash
git checkout -b docs/eda-hu-reprodutivel
git add eda_lidc_idri_hu_reprodutivel.ipynb README.md
git commit -m "docs: documenta EDA reprodutível de imagens CT"
git push -u origin docs/eda-hu-reprodutivel
```

Sugestão de descrição da pull request: “Organiza o EDA de uma série CT do LIDC-IDRI em notebook reproduzível, com seleção via API do TCIA, carregamento DICOM, análise de padding, histograma de HU e baseline de segmentação pulmonar.”
