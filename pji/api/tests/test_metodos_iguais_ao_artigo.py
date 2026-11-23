"""Os metodos da API tem de ser os mesmos dos experimentos do artigo.

pji/src/luna16/{baseline,region_growing,lung_air}.py sao copias de src/luna16/
na raiz do repositorio. Se alguem mudar um lado e esquecer o outro, a tela
passa a mostrar numeros diferentes do relatorio. Este teste pega isso.
Fora do repositorio completo (so a pasta pji/), ele e pulado.
"""
from pathlib import Path

import pytest

PJI = Path(__file__).resolve().parents[2]
ORIGINAL = PJI.parent / "src" / "luna16"
COPIA = PJI / "src" / "luna16"
ARQUIVOS = ["baseline.py", "region_growing.py", "lung_air.py"]


@pytest.mark.parametrize("arquivo", ARQUIVOS)
def test_copia_identica_ao_codigo_do_artigo(arquivo):
    if not (ORIGINAL / arquivo).exists():
        pytest.skip("src/luna16 da raiz nao encontrado (pasta pji isolada)")
    original = (ORIGINAL / arquivo).read_bytes().replace(b"\r\n", b"\n")
    copia = (COPIA / arquivo).read_bytes().replace(b"\r\n", b"\n")
    assert copia == original, f"pji/src/luna16/{arquivo} difere de src/luna16/{arquivo}: copie de novo"


def test_inferir_usa_os_metodos_do_artigo():
    from src.luna16 import inference
    from src.luna16.baseline import segment_baseline
    from src.luna16.region_growing import segment_region_growing

    assert inference.segment_baseline is segment_baseline
    assert inference.segment_region_growing is segment_region_growing
