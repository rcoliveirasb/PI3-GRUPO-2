"""Treina o U-Net 2D de contingencia (ver src/luna16/unet.py para o porque e
as limitacoes deliberadas de escopo -- CPU, sem GPU local disponivel).

Uso: python scripts/train_unet_baseline.py

Le data/luna16/split_full.csv (70/15/15, ja regenerado conforme o feedback do
professor), usa um subconjunto do split de TREINO (N_TRAIN_PATIENTS, nao todos
os 124 -- ver docstring de unet.py sobre o motivo: custo de tempo em CPU) para
montar um dataset de fatias axiais 2D, treina por poucas epocas e salva o
checkpoint em data/luna16/unet_baseline.pt.

Retomavel de forma simples: se o checkpoint ja existe, o script avisa e sai
sem re-treinar (apague o arquivo para re-treinar do zero).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd
import SimpleITK as sitk
import torch
from skimage.transform import resize
from torch.utils.data import DataLoader, TensorDataset

from luna16.io import load_ct, load_reference_mask
from luna16.preprocessing import clean_hu, denoise, resample_isotropic
from luna16.unet import SmallUNet2D, BCEDiceLoss, hu_to_input, INPUT_SIZE

SEED = 42
DATA_DIR = Path("data/luna16")
CHECKPOINT_PATH = DATA_DIR / "unet_baseline.pt"

# --- escopo deliberadamente limitado (ver src/luna16/unet.py) -------------
N_TRAIN_PATIENTS = 40      # de 124 disponiveis no split de treino
POS_SLICES_PER_PATIENT = 12   # fatias com pulmao na referencia
NEG_SLICES_PER_PATIENT = 4    # fatias de fundo (sem pulmao), p/ balancear
EPOCHS = 6
BATCH_SIZE = 16
LEARNING_RATE = 1e-3


def _to_sitk(array: np.ndarray, reference: sitk.Image, dtype: str) -> sitk.Image:
    img = sitk.GetImageFromArray(array.astype(dtype))
    img.CopyInformation(reference)
    return img


def load_preprocessed_volume(uid: str):
    """Mesma cadeia de pre-processamento usada na avaliacao dos outros
    metodos (pipeline.run_pipeline_for_uid) -- garante que o U-Net ve o
    mesmo tipo de entrada que baseline/region growing, para a comparacao de
    Dice/IoU ser justa."""
    ct = load_ct(uid, DATA_DIR)
    ref_mask = load_reference_mask(uid, DATA_DIR)
    ct_sitk = ct.to_sitk_image()

    cleaned = clean_hu(ct.array)
    denoised = denoise(cleaned, sigma=0.5)

    vol_sitk = _to_sitk(denoised, ct_sitk, "int16")
    vol_resampled = sitk.GetArrayFromImage(resample_isotropic(vol_sitk, (1.0, 1.0, 1.0), is_mask=False))

    ref_sitk = _to_sitk(ref_mask, ct_sitk, "uint8")
    ref_resampled = sitk.GetArrayFromImage(
        resample_isotropic(ref_sitk, (1.0, 1.0, 1.0), is_mask=True)
    ).astype(bool)

    return vol_resampled, ref_resampled


def slices_for_patient(uid: str, rng: np.random.Generator):
    """Extrai (imagem, mascara) 2D redimensionadas para INPUT_SIZE, algumas
    fatias com pulmao e algumas de fundo."""
    volume, ref = load_preprocessed_volume(uid)

    has_lung = ref.any(axis=(1, 2))
    pos_idx = np.where(has_lung)[0]
    neg_idx = np.where(~has_lung)[0]

    n_pos = min(POS_SLICES_PER_PATIENT, len(pos_idx))
    n_neg = min(NEG_SLICES_PER_PATIENT, len(neg_idx))
    chosen = list(rng.choice(pos_idx, size=n_pos, replace=False)) if n_pos else []
    chosen += list(rng.choice(neg_idx, size=n_neg, replace=False)) if n_neg else []

    images, masks = [], []
    for z in chosen:
        img = hu_to_input(volume[z]).astype(np.float32)
        img_r = resize(img, (INPUT_SIZE, INPUT_SIZE), order=1, anti_aliasing=True, preserve_range=True)
        mask_r = resize(
            ref[z].astype(np.float32), (INPUT_SIZE, INPUT_SIZE), order=0, anti_aliasing=False, preserve_range=True
        )
        images.append(img_r)
        masks.append((mask_r > 0.5).astype(np.float32))

    return images, masks


def build_dataset(train_uids: list[str]) -> TensorDataset:
    rng = np.random.default_rng(SEED)
    all_images, all_masks = [], []
    t0 = time.time()
    for i, uid in enumerate(train_uids, 1):
        imgs, masks = slices_for_patient(uid, rng)
        all_images.extend(imgs)
        all_masks.extend(masks)
        print(
            f"[dataset {i}/{len(train_uids)}] {uid[-10:]}  "
            f"+{len(imgs)} fatias (total {len(all_images)})  "
            f"{time.time() - t0:.0f}s decorridos",
            flush=True,
        )

    x = torch.tensor(np.stack(all_images)).unsqueeze(1)  # (N,1,H,W)
    y = torch.tensor(np.stack(all_masks)).unsqueeze(1)
    return TensorDataset(x, y)


def main():
    if CHECKPOINT_PATH.exists():
        print(f"{CHECKPOINT_PATH} ja existe -- apague para re-treinar do zero.", flush=True)
        return

    split = pd.read_csv(DATA_DIR / "split_full.csv")
    train_uids = split.loc[split["conjunto"] == "train", "uid"].tolist()

    rng = np.random.default_rng(SEED)
    rng.shuffle(train_uids)
    train_uids = train_uids[:N_TRAIN_PATIENTS]
    print(f"Treinando com {len(train_uids)} de {len(split[split.conjunto == 'train'])} pacientes de treino disponiveis (escopo limitado por tempo de CPU -- ver src/luna16/unet.py)", flush=True)

    print("\n=== Montando dataset de fatias 2D ===", flush=True)
    dataset = build_dataset(train_uids)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    print(f"\nDataset pronto: {len(dataset)} fatias", flush=True)

    model = SmallUNet2D(base_ch=16)
    loss_fn = BCEDiceLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

    print("\n=== Treinando ===", flush=True)
    model.train()
    for epoch in range(1, EPOCHS + 1):
        epoch_loss = 0.0
        for x, y in loader:
            optimizer.zero_grad()
            logits = model(x)
            loss = loss_fn(logits, y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * x.size(0)
        epoch_loss /= len(dataset)
        print(f"[epoca {epoch}/{EPOCHS}] loss (BCE+Dice) = {epoch_loss:.4f}", flush=True)

    torch.save(
        {"model_state": model.state_dict(), "base_ch": 16, "train_uids": train_uids},
        CHECKPOINT_PATH,
    )
    print(f"\nCheckpoint salvo em {CHECKPOINT_PATH}", flush=True)


if __name__ == "__main__":
    main()
