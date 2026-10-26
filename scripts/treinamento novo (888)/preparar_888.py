
from pathlib import Path
import SimpleITK as sitk
import numpy as np
import csv

uid = (
    "1.3.6.1.4.1.14519.5.2.1.6279.6001."
    "103115201714075993579787468219"
)

pasta = Path(
    r"D:\DATASET_LUNA16\mascaras\seg-lungs-LUNA16\seg-lungs-LUNA16"
)
arquivo = pasta / f"{uid}.mhd"

mascara = sitk.ReadImage(str(arquivo))
volume = sitk.GetArrayFromImage(mascara)

# Formato do volume: Z, Y, X
pixels_por_corte = np.count_nonzero(volume, axis=(1, 2))
cortes_validos = np.where(pixels_por_corte > 0)[0]

if len(cortes_validos) == 0:
    print("A máscara não contém pixels positivos.")
else:
    primeiro = int(cortes_validos[0])
    ultimo = int(cortes_validos[-1])
    origem_z = mascara.GetOrigin()[2]
    espacamento_z = mascara.GetSpacing()[2]

    print("UID:", uid)
    print("Primeiro corte com máscara:", primeiro)
    print("Último corte com máscara:", ultimo)
    print("Z inicial aproximado:", origem_z + primeiro * espacamento_z, "mm")
    print("Z final aproximado:", origem_z + ultimo * espacamento_z, "mm")
    print("Cortes com máscara:", len(cortes_validos))
    print("Cortes vazios no início:", primeiro)
    print("Cortes vazios no final:", volume.shape[0] - 1 - ultimo)

    for indice in range(max(0, primeiro - 3), min(volume.shape[0], primeiro + 5)):
        print(
            f"Corte {indice}: "
            f"{pixels_por_corte[indice]} pixels positivos"
        )
