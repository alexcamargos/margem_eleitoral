"""Testes unitários para o componente visual da decomposição de projeção (A CONTA)."""

from datetime import date

import pytest

from src.analytics.predictive_model import (
    CandidatePrediction,
    ElectionForecastResult,
    RegionalForecastSlice,
)
from src.presentation.components.waterfall_projection_card import (
    _resolve_decomposition_metrics,
    create_waterfall_projection_chart,
)
from src.transformations.schemas import (
    AbrangenciaEnum,
    MetodologiaEnum,
    PesquisaEleitoralSchema,
    ResultadoOficialTSESchema,
)


@pytest.fixture
def mock_forecast() -> ElectionForecastResult:
    """Fixture com um objeto ElectionForecastResult sintético para testes."""
    cands = [
        CandidatePrediction(
            candidato="Lula",
            voto_esperado=48.4,
            ic_95_inferior=43.7,
            ic_95_superior=53.0,
            probabilidade_vitoria=20.5,
            probabilidade_vitoria_1_turno=0.0,
            tendencia_diaria_pp=-0.01,
        ),
        CandidatePrediction(
            candidato="Flávio Bolsonaro",
            voto_esperado=51.6,
            ic_95_inferior=47.0,
            ic_95_superior=56.3,
            probabilidade_vitoria=79.5,
            probabilidade_vitoria_1_turno=0.0,
            tendencia_diaria_pp=0.01,
        ),
    ]
    reg_slices = [
        RegionalForecastSlice(
            regiao="SE",
            nome_regiao="Sudeste",
            peso_eleitorado=0.426,
            votos_projetados={"Lula": 46.0, "Flávio Bolsonaro": 54.0},
            n_pesquisas=12,
            margem_lider=-8.0,
        )
    ]
    return ElectionForecastResult(
        ano=2026,
        turno=2,
        cutoff_date=date(2026, 10, 22),
        election_date=date(2026, 10, 25),
        dias_ate_eleicao=3,
        n_pesquisas_utilizadas=30,
        n_pesquisas_nacionais=20,
        n_pesquisas_estaduais=10,
        n_pesquisas_regionais=0,
        n_institutos=12,
        calibrado_pos_t1=True,
        candidatos=cands,
        vencedor_previsto="Flávio Bolsonaro",
        margem_esperada=-3.2,
        ic_95_margem=(-8.0, 1.6),
        probabilidade_segundo_turno=0.0,
        distribuicao_simulada={"Lula": [48.4] * 50, "Flávio Bolsonaro": [51.6] * 50},
        pesos_institutos={"Datafolha": 15.0},
        agregacao_regional=reg_slices,
    )


@pytest.fixture
def mock_t1_tse() -> ResultadoOficialTSESchema:
    """Fixture com resultado oficial do 1º Turno."""
    return ResultadoOficialTSESchema(
        ano=2026,
        turno=1,
        cargo="Presidente da República",
        resultado_nominal={"Lula": 48.99, "Flávio Bolsonaro": 51.01},
        total_votos_validos=110000000,
        total_brancos=2000000,
        total_nulos=3000000,
        total_abstencoes=20000000,
        apuracao_concluida=True,
    )


def test_resolve_decomposition_metrics_lula(
    mock_forecast: ElectionForecastResult,
    mock_t1_tse: ResultadoOficialTSESchema,
) -> None:
    """Testa os cálculos de decomposição da projeção para Lula."""
    metrics = _resolve_decomposition_metrics(
        candidate="Lula",
        forecast=mock_forecast,
        t1_tse_result=mock_t1_tse,
        polls=[],
    )

    assert metrics["pesquisa_bruta"] == 49.0
    assert metrics["vies"] == -0.9
    assert metrics["rejeicao"] == 0.2
    assert metrics["corrigida"] == 48.3 or metrics["corrigida"] == 48.4
    assert metrics["peso_1t"] == 0.0
    assert metrics["peso_corrigida"] == 1.0
    assert metrics["projecao"] == metrics["corrigida"]


def test_resolve_decomposition_metrics_flavio(
    mock_forecast: ElectionForecastResult,
    mock_t1_tse: ResultadoOficialTSESchema,
) -> None:
    """Testa os cálculos de decomposição da projeção para Flávio Bolsonaro."""
    metrics = _resolve_decomposition_metrics(
        candidate="Flávio Bolsonaro",
        forecast=mock_forecast,
        t1_tse_result=mock_t1_tse,
        polls=[],
    )

    assert metrics["pesquisa_bruta"] == 51.0
    assert metrics["vies"] == 0.9
    assert metrics["rejeicao"] == -0.2
    assert metrics["corrigida"] == 51.7 or metrics["corrigida"] == 51.6
    assert metrics["peso_1t"] == 0.0
    assert metrics["peso_corrigida"] == 1.0
    assert metrics["projecao"] == metrics["corrigida"]


def test_create_waterfall_projection_chart(
    mock_forecast: ElectionForecastResult,
    mock_t1_tse: ResultadoOficialTSESchema,
) -> None:
    """Valida que o gráfico Plotly é construído com todas as barras esperadas."""
    metrics = _resolve_decomposition_metrics(
        candidate="Lula",
        forecast=mock_forecast,
        t1_tse_result=mock_t1_tse,
        polls=[],
    )

    fig = create_waterfall_projection_chart("Lula", metrics)
    assert fig is not None
    assert len(fig.data) == 1
    trace = fig.data[0]
    assert list(trace.x) == ["Pesquisa", "Viés", "Rejeição", "Corrigida", "1º turno", "Projeção"]
