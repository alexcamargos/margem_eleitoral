"""Testes unitários para o módulo de conversão de votos válidos."""

import pytest

from src.transformations.valid_votes import (
    InvalidVoteCalculationError,
    calculate_valid_votes,
)


def test_calculate_valid_votes_basic() -> None:
    """Verifica a conversão padrão e o fechamento em 100% dos votos válidos."""
    # Candidato A: 45%, Candidato B: 35%, Brancos/Nulos: 10%, Indecisos: 10%
    # Válidos esperados: A = 45 / 0.8 = 56.25, B = 35 / 0.8 = 43.75
    votos_totais = {"Lula": 45.0, "Bolsonaro": 35.0}
    validos = calculate_valid_votes(
        votos_totais=votos_totais,
        percentual_brancos_nulos=10.0,
        percentual_indecisos=10.0,
    )

    assert validos["Lula"] == 56.25
    assert validos["Bolsonaro"] == 43.75
    assert round(sum(validos.values()), 2) == 100.0


def test_calculate_valid_votes_preserves_ratio() -> None:
    """Garante que a razão relativa entre os candidatos é estritamente preservada."""
    votos_totais = {"Candidato A": 40.0, "Candidato B": 20.0, "Candidato C": 10.0}
    validos = calculate_valid_votes(
        votos_totais=votos_totais,
        percentual_brancos_nulos=15.0,
        percentual_indecisos=15.0,
    )

    # Razão A/B nos totais: 40/20 = 2.0
    razao_bruta = votos_totais["Candidato A"] / votos_totais["Candidato B"]
    razao_valida = validos["Candidato A"] / validos["Candidato B"]
    assert pytest.approx(razao_bruta, rel=1e-3) == razao_valida
    assert pytest.approx(sum(validos.values()), abs=0.05) == 100.0


def test_calculate_valid_votes_invalid_sum_non_valid() -> None:
    """Garante lançamento de erro quando a soma de brancos/nulos/indecisos for >= 100%."""
    with pytest.raises(InvalidVoteCalculationError, match="deve ser estritamente menor que 100%"):
        calculate_valid_votes(
            votos_totais={"A": 10.0},
            percentual_brancos_nulos=50.0,
            percentual_indecisos=50.0,
        )


def test_calculate_valid_votes_negative_values() -> None:
    """Garante rejeição de valores negativos em qualquer percentual."""
    with pytest.raises(InvalidVoteCalculationError, match="não podem ser negativos"):
        calculate_valid_votes(
            votos_totais={"A": 50.0},
            percentual_brancos_nulos=-2.0,
            percentual_indecisos=5.0,
        )

    with pytest.raises(InvalidVoteCalculationError, match="não pode ser negativo"):
        calculate_valid_votes(
            votos_totais={"A": -10.0, "B": 50.0},
            percentual_brancos_nulos=5.0,
            percentual_indecisos=5.0,
        )


def test_calculate_valid_votes_empty_or_zero() -> None:
    """Garante rejeição de dicionário vazio ou votos brutos com soma zero."""
    with pytest.raises(InvalidVoteCalculationError, match="não pode ser vazio"):
        calculate_valid_votes(
            votos_totais={},
            percentual_brancos_nulos=5.0,
            percentual_indecisos=5.0,
        )

    with pytest.raises(InvalidVoteCalculationError, match="estritamente positiva"):
        calculate_valid_votes(
            votos_totais={"A": 0.0, "B": 0.0},
            percentual_brancos_nulos=50.0,
            percentual_indecisos=30.0,
        )
