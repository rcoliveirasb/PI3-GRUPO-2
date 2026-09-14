"""
Baixa um subset do LUNA16 (89 pacientes cada, .mhd/.raw), as mascaras de
referencia (seg-lungs-LUNA16) correspondentes e os CSVs de anotacoes,
a partir do mirror publico avc0706/luna16 no Kaggle.

Uso: python scripts/download_luna16_subset.py [N]
     N = indice do subset (0-4 disponiveis nesse mirror). Default: 0.
Requer: token de API do Kaggle em ~/.kaggle/access_token (ou kaggle.json),
        e a lista de arquivos do subset em data/luna16/_lists/ (gerada uma
        vez via API do Kaggle -- ver histórico do projeto/scripts/README).
"""
import sys
import time
import zipfile
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi

DATASET = "avc0706/luna16"
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "luna16"
MASKS_DIR = DATA_DIR / "seg-lungs-LUNA16"
LISTS_DIR = DATA_DIR / "_lists"


def _unzip_if_needed(dest_dir: Path, expected_name: str):
    """A API do Kaggle empacota arquivos individuais grandes num .zip
    (ex: foo.raw -> foo.raw.zip). Descompacta e remove o .zip."""
    zip_path = dest_dir / (expected_name + ".zip")
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest_dir)
        zip_path.unlink()


def download_list(api: KaggleApi, list_path: Path, dest_dir: Path, label: str):
    dest_dir.mkdir(parents=True, exist_ok=True)
    names = [l.strip() for l in list_path.read_text().splitlines() if l.strip()]
    total = len(names)
    for i, name in enumerate(names, 1):
        t0 = time.time()
        basename = Path(name).name
        try:
            api.dataset_download_file(DATASET, name, path=str(dest_dir), force=False, quiet=True)
            _unzip_if_needed(dest_dir, basename)
        except Exception as e:
            print(f"[{label} {i}/{total}] FALHOU {name}: {e}", flush=True)
            continue
        dt = time.time() - t0
        print(f"[{label} {i}/{total}] ok ({dt:.1f}s) {basename}", flush=True)


def main():
    subset_n = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    subset_name = f"subset{subset_n}"

    api = KaggleApi()
    api.authenticate()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("== CSVs ==", flush=True)
    for fname in ["annotations.csv", "candidates.csv"]:
        api.dataset_download_file(DATASET, fname, path=str(DATA_DIR), force=False, quiet=True)
        print(f"ok {fname}", flush=True)

    print(f"== {subset_name} (.mhd/.raw) ==", flush=True)
    download_list(api, LISTS_DIR / f"{subset_name}_files.txt", DATA_DIR / subset_name, subset_name)

    print("== seg-lungs-LUNA16 (mascaras de referencia) ==", flush=True)
    download_list(api, LISTS_DIR / f"mask_files_{subset_name}.txt", MASKS_DIR, "masks")

    print("CONCLUIDO", flush=True)


if __name__ == "__main__":
    main()
