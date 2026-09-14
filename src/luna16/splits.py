"""Split treino/validacao/teste por paciente (regra obrigatoria, secao 3.1).

No LUNA16, cada SeriesInstanceUID (o `uid` usado no resto do codigo) e uma
tomografia de um paciente, e nao ha duas series do mesmo paciente dentro do
subset0 -- entao splitar por `uid` e equivalente a splitar por paciente.
Isso e verificado no notebook antes do split (checando duplicatas no
PatientID que vem do `annotations.csv`/metadados do LIDC-IDRI, quando
disponivel) para nao assumir isso as cegas.
"""
from dataclasses import dataclass

import numpy as np


@dataclass
class Split:
    train: list
    val: list
    test: list

    def as_dict(self) -> dict:
        return {"train": self.train, "val": self.val, "test": self.test}


def patient_split(uids: list[str], seed: int, train_frac: float = 0.7, val_frac: float = 0.15) -> Split:
    """Embaralha os uids com uma seed fixa e corta em train/val/test.

    test_frac = 1 - train_frac - val_frac (0.15 por padrao -- 70/15/15).
    Ate o Sprint 8 o projeto usava 60/20/20 sobre um subconjunto do LUNA16
    (subset0+subset1, 177 pacientes); com o dataset completo (888 pacientes,
    via HD externo) passamos para 70/15/15, mais comum quando ha volume de
    dado suficiente para um treino maior sem sacrificar o tamanho estatistico
    de validacao/teste.
    Embaralhar (em vez de pegar sequencial) evita vies de ordem no manifest
    do LUNA16 (ex: uids agrupados por alguma caracteristica de aquisicao).
    """
    assert 0 < train_frac < 1 and 0 < val_frac < 1 and train_frac + val_frac < 1

    rng = np.random.default_rng(seed)
    shuffled = list(uids)
    rng.shuffle(shuffled)

    n = len(shuffled)
    n_train = int(round(n * train_frac))
    n_val = int(round(n * val_frac))

    train = shuffled[:n_train]
    val = shuffled[n_train : n_train + n_val]
    test = shuffled[n_train + n_val :]
    return Split(train=train, val=val, test=test)


def assert_no_leakage(split: Split):
    """Garante que nenhum uid aparece em mais de um subconjunto -- a checagem
    minima da regra 'nunca misturar paciente entre treino e teste'."""
    train_s, val_s, test_s = set(split.train), set(split.val), set(split.test)
    assert train_s.isdisjoint(val_s), "vazamento: uid em train e val"
    assert train_s.isdisjoint(test_s), "vazamento: uid em train e test"
    assert val_s.isdisjoint(test_s), "vazamento: uid em val e test"
