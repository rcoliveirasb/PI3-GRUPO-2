
from pathlib import Path

import SimpleITK as sitk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap


# Caminhos do exame divergente
uid = (
    "1.3.6.1.4.1.14519.5.2.1.6279.6001."
    "103115201714075993579787468219"
)

pasta_ct = Path(r"D:\DATASET_LUNA16\ct_preparados\subset0")
pasta_mascaras = Path(
    r"D:\DATASET_LUNA16\mascaras\seg-lungs-LUNA16\seg-lungs-LUNA16"
)

arquivo_ct = pasta_ct / f"{uid}.mhd"
arquivo_mascara = pasta_mascaras / f"{uid}.mhd"

arquivo_saida = Path(
    r"D:\DATASET_LUNA16\ct_preparados\visualizacao_divergente.png"
)


# 1. Verificar se os arquivos existem
if not arquivo_ct.exists():
    raise FileNotFoundError(f"CT não encontrado: {arquivo_ct}")

if not arquivo_mascara.exists():
    raise FileNotFoundError(
        f"Máscara não encontrada: {arquivo_mascara}"
    )


# 2. Carregar os volumes
ct = sitk.ReadImage(str(arquivo_ct))
mascara = sitk.ReadImage(str(arquivo_mascara))

print("Geometria do CT:")
print("Tamanho:", ct.GetSize())
print("Espaçamento:", ct.GetSpacing())
print("Origem:", ct.GetOrigin())

print("\nGeometria da máscara:")
print("Tamanho:", mascara.GetSize())
print("Espaçamento:", mascara.GetSpacing())
print("Origem:", mascara.GetOrigin())


# 3. Reamostrar a máscara na grade do CT.
# Isso é feito somente para visualização.
# Nenhum arquivo original é modificado.
mascara_alinhada = sitk.Resample(
    mascara,
    ct,
    sitk.Transform(),
    sitk.sitkNearestNeighbor,
    0,
    mascara.GetPixelID()
)

ct_array = sitk.GetArrayFromImage(ct)
mascara_array = sitk.GetArrayFromImage(mascara_alinhada)

# Os arrays têm formato [Z, Y, X].
origem_z = ct.GetOrigin()[2]
espacamento_z = ct.GetSpacing()[2]
quantidade_cortes = ct_array.shape[0]

inicio_ct = origem_z
fim_ct = origem_z + (quantidade_cortes - 1) * espacamento_z

inicio_mascara = mascara.GetOrigin()[2]
fim_mascara = (
    inicio_mascara
    + (mascara.GetSize()[2] - 1) * mascara.GetSpacing()[2]
)

print("\nIntervalo aproximado em Z:")
print(f"CT:      {inicio_ct:.2f} até {fim_ct:.2f} mm")
print(f"Máscara: {inicio_mascara:.2f} até {fim_mascara:.2f} mm")


# 4. Escolher posições físicas para visualizar.
# Incluímos cortes antes do início da máscara e cortes com sobreposição.
posicoes_z = [
    inicio_ct + 5,
    inicio_mascara - 5,
    inicio_mascara + 2,
    inicio_mascara + (fim_mascara - inicio_mascara) * 0.25,
    inicio_mascara + (fim_mascara - inicio_mascara) * 0.50,
    inicio_mascara + (fim_mascara - inicio_mascara) * 0.75,
    fim_mascara - 2,
]

# Converter posições físicas para índices de cortes do CT.
indices = []

for z in posicoes_z:
    indice = round((z - origem_z) / espacamento_z)
    indice = max(0, min(indice, quantidade_cortes - 1))

    if indice not in indices:
        indices.append(indice)


# 5. Preparar as cores dos rótulos da máscara.
# Rótulos 3, 4 e 5 recebem cores distintas.
cores = ListedColormap([
    "red",
    "lime",
    "cyan",
])

# 6. Criar a figura
fig, eixos = plt.subplots(2, 4, figsize=(18, 10))
eixos = eixos.flatten()

for posicao, ax in enumerate(eixos):
    if posicao >= len(indices):
        ax.axis("off")
        continue

    indice_z = indices[posicao]
    z_fisico = origem_z + indice_z * espacamento_z

    corte_ct = ct_array[indice_z]
    corte_mascara = mascara_array[indice_z]

    # Exibir a tomografia com uma janela de intensidade pulmonar.
    ax.imshow(
        corte_ct,
        cmap="gray",
        vmin=-1000,
        vmax=400
    )

    # Sobrepor apenas os pixels pertencentes à máscara.
    mascara_visivel = np.ma.masked_where(
        corte_mascara == 0,
        corte_mascara
    )

    ax.imshow(
        mascara_visivel,
        cmap=cores,
        vmin=3,
        vmax=5,
        alpha=0.40,
        interpolation="nearest"
    )

    quantidade_marcada = int(np.count_nonzero(corte_mascara))

    ax.set_title(
        f"Corte {indice_z}\n"
        f"Z = {z_fisico:.2f} mm\n"
        f"Pixels da máscara: {quantidade_marcada}"
    )

    ax.axis("off")

fig.suptitle(
    "LUNA16 — Verificação visual do alinhamento CT e máscara",
    fontsize=15
)

plt.tight_layout()
fig.savefig(arquivo_saida, dpi=150, bbox_inches="tight")
plt.close(fig)

print(f"\nImagem salva em:\n{arquivo_saida}")
print("Os arquivos originais não foram alterados.")
