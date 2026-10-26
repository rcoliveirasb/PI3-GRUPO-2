
import argparse
import csv
import shutil
import tempfile
from pathlib import Path

import numpy as np
import SimpleITK as sitk

RAIZ = Path(r"D:\DATASET_LUNA16")
PASTA_DICOM = RAIZ / "lidc_idri"
PASTA_MASCARAS = (
    RAIZ / "mascaras" / "seg-lungs-LUNA16" / "seg-lungs-LUNA16"
)
SAIDA = RAIZ / "ct_preparados"
METADADOS = RAIZ / "metadata" / "metadata.csv"
LOG = SAIDA / "conversao_888.csv"

TOL_ESP = 1e-3
TOL_ORIG = 1e-3
TOL_DIR = 1e-5


def geometria_igual(ct, mascara):
    return (
        ct.GetSize() == mascara.GetSize()
        and np.allclose(
            ct.GetSpacing(), mascara.GetSpacing(), atol=TOL_ESP, rtol=0
        )
        and np.allclose(
            ct.GetOrigin(), mascara.GetOrigin(), atol=TOL_ORIG, rtol=0
        )
        and np.allclose(
            ct.GetDirection(), mascara.GetDirection(), atol=TOL_DIR, rtol=0
        )
    )


def registrar(linha):
    existe = LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linha.keys()))
        if not existe:
            escritor.writeheader()
        escritor.writerow(linha)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limite", type=int, default=3,
        help="Quantidade de exames a processar; use 3 para o teste inicial."
    )
    args = parser.parse_args()

    if not METADADOS.exists() or not PASTA_MASCARAS.exists():
        raise SystemExit("ERRO: confira os caminhos da base LUNA16.")

    SAIDA.mkdir(parents=True, exist_ok=True)

    with METADADOS.open(encoding="utf-8-sig", newline="") as f:
        registros = list(csv.DictReader(f))

    por_uid = {r["SeriesInstanceUID"]: r for r in registros}
    mascaras = sorted(PASTA_MASCARAS.glob("*.mhd"))

    print(f"Máscaras encontradas: {len(mascaras)}")
    print(f"Registros de metadados: {len(por_uid)}")

    # Retoma os exames já processados com sucesso.
    concluidos = set()
    if LOG.exists():
        with LOG.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("status") in {
                    "OK_GEOMETRIA", "GEOMETRIA_DIVERGENTE"
                }:
                    concluidos.add(r["uid"])

    pendentes = [m for m in mascaras if m.stem not in concluidos]
    if args.limite < 1:
        raise SystemExit("--limite deve ser maior que zero.")

    lote = pendentes[:args.limite]
    print(f"Exames já concluídos: {len(concluidos)}")
    print(f"Exames neste lote: {len(lote)}")

    for pos, mascara_path in enumerate(lote, 1):
        uid = mascara_path.stem
        print(f"\n[{pos}/{len(lote)}] {uid}")

        linha = {
            "uid": uid,
            "status": "",
            "n_dicom": 0,
            "ct_path": "",
            "mask_path": str(mascara_path),
            "geometria_igual": "",
            "detalhe": "",
        }

        try:
            registro = por_uid.get(uid)
            if registro is None:
                raise ValueError("UID ausente nos metadados.")

            # Caminho da série, confirmado no exame de teste.
            estudo = registro["StudyInstanceUID"][-5:]
            serie = uid[-5:]
            pasta = (
                PASTA_DICOM / registro["PatientID"] / estudo / serie
            )

            if not pasta.is_dir():
                raise FileNotFoundError(f"Pasta DICOM não encontrada: {pasta}")

            ids = sitk.ImageSeriesReader.GetGDCMSeriesIDs(str(pasta))
            if not ids or uid not in ids:
                raise ValueError("Série DICOM correspondente não encontrada.")

            arquivos = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(
                str(pasta), uid
            )
            if not arquivos:
                raise ValueError("Nenhum arquivo DICOM na série.")

            linha["n_dicom"] = len(arquivos)

            # Lê a máscara para comparar a geometria.
            mascara = sitk.ReadImage(str(mascara_path))

            # Se o CT já existe, não o sobrescreve.
            existentes = list(SAIDA.glob(f"subset*/*{uid}.mhd"))
            existentes = [p for p in existentes if p.stem == uid]

            if existentes:
                destino = existentes[0]
                raw = destino.with_suffix(".raw")
                if not raw.exists():
                    raise FileExistsError(
                        f"CT parcial encontrado; verificar manualmente: {destino}"
                    )
                ct = sitk.ReadImage(str(destino))
                igual = geometria_igual(ct, mascara)
                linha["ct_path"] = str(destino)
                linha["geometria_igual"] = igual
                linha["status"] = (
                    "OK_GEOMETRIA" if igual else "GEOMETRIA_DIVERGENTE"
                )
                linha["detalhe"] = "CT existente; não foi sobrescrito."
                registrar(linha)
                concluidos.add(uid)
                print(linha["status"])
                continue

            leitor = sitk.ImageSeriesReader()
            leitor.SetFileNames(arquivos)
            ct = leitor.Execute()

            igual = geometria_igual(ct, mascara)
            linha["geometria_igual"] = igual

            # Distribui os exames em dez pastas.
            indice_global = mascaras.index(mascara_path)
            subset = min(indice_global // 89, 9)
            pasta_saida = SAIDA / f"subset{subset}"
            pasta_saida.mkdir(parents=True, exist_ok=True)
            destino = pasta_saida / f"{uid}.mhd"

            # Grava primeiro em uma pasta temporária.
            with tempfile.TemporaryDirectory(dir=str(SAIDA)) as temp:
                temporario = Path(temp) / f"{uid}.mhd"
                sitk.WriteImage(ct, str(temporario), useCompression=False)

                # Confirma que o CT gravado pode ser reaberto.
                verificado = sitk.ReadImage(str(temporario))
                if verificado.GetSize() != ct.GetSize():
                    raise IOError("Dimensões divergentes após salvar o CT.")

                shutil.move(
                    str(temporario.with_suffix(".raw")),
                    str(destino.with_suffix(".raw"))
                )
                shutil.move(str(temporario), str(destino))

            linha["ct_path"] = str(destino)
            linha["status"] = (
                "OK_GEOMETRIA" if igual else "GEOMETRIA_DIVERGENTE"
            )
            linha["detalhe"] = (
                "CT convertido."
                if igual
                else "CT salvo; geometria da máscara precisa ser revisada."
            )

        except Exception as erro:
            linha["status"] = "ERRO"
            linha["detalhe"] = f"{type(erro).__name__}: {erro}"

        registrar(linha)
        print(f"Status: {linha['status']}")
        if linha["detalhe"]:
            print(linha["detalhe"])

    print(f"\nLog atualizado: {LOG}")
    print("Revise os resultados antes de aumentar o lote.")


if __name__ == "__main__":
    main()
