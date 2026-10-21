"""Testes unitários para o motor de análise de rejeição e componente Dumbbell Plot."""

import pytest

from src.analytics.rejection_analysis import (
    calculate_electoral_ceiling,
    calculate_rejection_averages,
    classify_institute_rejection,
    compute_rejection_scoreboard,
    structure_rejection_metrics,
)
from src.ingestion.data_loader import get_rejection_dataset
from src.presentation.components.dumbbell_chart import create_rejection_dumbbell_chart


def test_calculate_rejection_averages_success() -> None:
    """Verifica o cálculo correto das médias de rejeição."""
    polls = [
        {"rejeicao": {"Lula": 48.0, "Flávio Bolsonaro": 51.0}},
        {"rejeicao": {"Lula": 50.0, "Flávio Bolsonaro": 45.0}},
    ]
    averages = calculate_rejection_averages(polls=polls, candidates=["Lula", "Flávio Bolsonaro", "Candidato Ausente"])
    assert averages["Lula"] == 49.0
    assert averages["Flávio Bolsonaro"] == 48.0
    assert averages["Candidato Ausente"] == 0.0


def test_calculate_rejection_averages_empty_raises() -> None:
    """Verifica lançamento de exceção quando lista de pesquisas ou candidatos for vazia."""
    with pytest.raises(ValueError, match="não pode estar vazia"):
        calculate_rejection_averages(polls=[], candidates=["Lula"])

    with pytest.raises(ValueError, match="não pode estar vazia"):
        calculate_rejection_averages(polls=[{"rejeicao": {}}], candidates=[])


def test_classify_institute_rejection() -> None:
    """Verifica as três condições de classificação: empate, candidato 1 menos e candidato 2 menos."""
    # Empate técnico (|diff| <= 1.0)
    verdict, diff = classify_institute_rejection(
        {"Lula": 49.0, "Flávio Bolsonaro": 49.5},
        candidate_1="Lula",
        candidate_2="Flávio Bolsonaro",
        tie_threshold=1.0,
    )
    assert verdict == "empate"
    assert diff == 0.5

    # Lula menos rejeitado (|diff| > 1.0)
    verdict, diff = classify_institute_rejection(
        {"Lula": 46.0, "Flávio Bolsonaro": 50.0},
        candidate_1="Lula",
        candidate_2="Flávio Bolsonaro",
        tie_threshold=1.0,
    )
    assert verdict == "Lula menos"
    assert diff == 4.0

    # Flávio menos rejeitado (|diff| > 1.0)
    verdict, diff = classify_institute_rejection(
        {"Lula": 52.0, "Flávio Bolsonaro": 46.0},
        candidate_1="Lula",
        candidate_2="Flávio Bolsonaro",
        tie_threshold=1.0,
    )
    assert verdict == "Flávio Bolsonaro menos"
    assert diff == 6.0


def test_classify_institute_rejection_invalid_raises() -> None:
    """Verifica validações de parâmetros inválidos na classificação."""
    with pytest.raises(ValueError, match="não pode ser negativo"):
        classify_institute_rejection(
            {"Lula": 49.0, "Flávio": 49.0}, "Lula", "Flávio", tie_threshold=-0.5
        )

    with pytest.raises(KeyError, match="devem estar presentes"):
        classify_institute_rejection({"Lula": 49.0}, "Lula", "Flávio")


def test_compute_rejection_scoreboard_2026() -> None:
    """Valida o placar consolidado de 2026 refletindo a captura de referência (4 Lula, 6 Flávio, 3 empate)."""
    dataset_2026 = get_rejection_dataset(year=2026)
    polls = dataset_2026["primeiro_turno"]["pesquisas_instituto"]

    scoreboard = compute_rejection_scoreboard(
        polls=polls,
        candidate_1="Lula",
        candidate_2="Flávio Bolsonaro",
        tie_threshold=1.0,
    )

    assert scoreboard["candidato_1_menos"] == 4
    assert scoreboard["candidato_2_menos"] == 6
    assert scoreboard["empate"] == 3


def test_compute_rejection_scoreboard_without_explicit_verdict() -> None:
    """Valida o cálculo do placar quando as pesquisas não trazem a chave 'veredito' declarada."""
    polls = [
        {"rejeicao": {"Lula": 45.0, "Flávio Bolsonaro": 50.0}},  # Lula menos
        {"rejeicao": {"Lula": 50.0, "Flávio Bolsonaro": 45.0}},  # Flávio menos
        {"rejeicao": {"Lula": 49.0, "Flávio Bolsonaro": 49.5}},  # empate
    ]
    scoreboard = compute_rejection_scoreboard(
        polls=polls,
        candidate_1="Lula",
        candidate_2="Flávio Bolsonaro",
        tie_threshold=1.0,
    )
    assert scoreboard["candidato_1_menos"] == 1
    assert scoreboard["candidato_2_menos"] == 1
    assert scoreboard["empate"] == 1


def test_compute_rejection_scoreboard_empty_raises() -> None:
    """Verifica exceção ao passar lista vazia para o placar."""
    with pytest.raises(ValueError, match="não pode estar vazia"):
        compute_rejection_scoreboard([], "Lula", "Flávio")


def test_calculate_electoral_ceiling() -> None:
    """Verifica o cálculo e os limites do teto eleitoral teórico."""
    assert calculate_electoral_ceiling(49.3) == 50.7
    assert calculate_electoral_ceiling(41.6) == 58.4

    with pytest.raises(ValueError, match="entre 0.0 e 100.0"):
        calculate_electoral_ceiling(-5.0)

    with pytest.raises(ValueError, match="entre 0.0 e 100.0"):
        calculate_electoral_ceiling(105.0)


def test_structure_rejection_metrics() -> None:
    """Valida a estruturação completa das métricas para os anos de 2026 e 2022."""
    for ano in [2026, 2022]:
        dataset = get_rejection_dataset(ano)
        metrics = structure_rejection_metrics(dataset)

        assert metrics["ano"] == ano
        assert len(metrics["candidatos"]) == 2
        assert metrics["total_institutos"] > 0
        assert sum(metrics["placar"].values()) == metrics["total_institutos"]
        assert len(metrics["tetos_eleitorais"]) == 2


def test_structure_rejection_metrics_invalid_dataset_raises() -> None:
    """Verifica exceção para datasets sem candidatos ou primeiro_turno."""
    with pytest.raises(KeyError, match="Dataset de rejeição inválido"):
        structure_rejection_metrics({"invalido": True})


def test_get_rejection_dataset_not_found() -> None:
    """Verifica que anos não mapeados lançam FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="não encontrado"):
        get_rejection_dataset(1990)


def test_create_rejection_dumbbell_chart() -> None:
    """Verifica a geração correta do Dumbbell Plot com linhas, pontos e anotações."""
    dataset = get_rejection_dataset(2026)
    polls = dataset["primeiro_turno"]["pesquisas_instituto"]

    fig = create_rejection_dumbbell_chart(
        polls=polls,
        candidate_1="Lula",
        candidate_2="Flávio Bolsonaro",
        display_names=dataset["candidatos_nomes_exibicao"],
        candidate_colors=dataset["cores_candidatos"],
    )

    # 3 traços: linhas de conexão, pontos C1, pontos C2
    assert len(fig.data) == 3
    # Anotações laterais: 1 para cada instituto (13)
    assert len(fig.layout.annotations) == len(polls)


def test_create_rejection_dumbbell_chart_empty_raises() -> None:
    """Verifica erro ao tentar gerar o gráfico de halteres com pesquisas vazias."""
    with pytest.raises(ValueError, match="não pode estar vazia"):
        create_rejection_dumbbell_chart([])
