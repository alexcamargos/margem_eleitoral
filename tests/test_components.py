"""Testes unitários para os componentes visuais Plotly."""

from datetime import date

from src.analytics.aggregator_model import compute_poll_aggregation_series
from src.presentation.components.bar_error_chart import create_weighted_error_bar_chart
from src.presentation.components.bias_chart import create_directional_bias_chart
from src.presentation.components.forest_plot import create_forest_plot
from src.presentation.components.simulator import create_sampling_simulator_figure
from src.presentation.components.small_multiples import create_small_multiples_grid
from src.presentation.components.trend_chart import create_trend_aggregator_chart
from src.transformations.schemas import PesquisaEleitoralSchema


def test_create_weighted_error_bar_chart() -> None:
    """Verifica a criação do gráfico de barras de erro ponderado."""
    evals = [
        {
            "instituto": "Datafolha",
            "campo_ate": "02/10",
            "erro_1_lugar": 2.1,
            "erro_2_lugar": 1.5,
            "erro_demais": 0.8,
            "erro_total_ponderado": 4.4,
            "faixa_acerto": "Erro Típico",
        },
        {
            "instituto": "DataTrends",
            "campo_ate": "30/09",
            "erro_1_lugar": 1.0,
            "erro_2_lugar": 1.2,
            "erro_demais": 0.5,
            "erro_total_ponderado": 2.7,
            "faixa_acerto": "Abaixo do Típico",
        },
    ]
    fig = create_weighted_error_bar_chart(evals)
    assert fig is not None
    assert len(fig.data) == 3  # 3 barras empilhadas

    # Teste com linha da Faixa do Acaso (P90)
    fig_p90 = create_weighted_error_bar_chart(evals, faixa_acaso_p90=4.5)
    assert fig_p90 is not None
    assert len(fig_p90.layout.shapes) > 0  # Linha vertical ou horizontal criada


def test_create_forest_plot() -> None:
    """Verifica a criação do Forest Plot com intervalos de confiança."""
    eve_evals = [
        {
            "instituto": "Quaest",
            "campo_ate": "02/10",
            "estimativa": 48.0,
            "ic_inf": 46.0,
            "ic_sup": 50.0,
            "margem_erro": 2.0,
        }
    ]
    fig = create_forest_plot(eve_evals, candidate_name="Lula", official_vote_percent=48.43)
    assert fig is not None
    assert len(fig.data) == 1


def test_create_small_multiples_grid() -> None:
    """Verifica a renderização do grid de Small Multiples com formato legado."""
    trajectories = {
        "Datafolha": [
            {"data": "15/09", "desvio_tse": -1.2, "diferenca_estimada": 8.0, "amostra": 2500},
            {"data": "02/10", "desvio_tse": 0.4, "diferenca_estimada": 6.5, "amostra": 3000},
        ],
        "Quaest": [
            {"data": "20/09", "desvio_tse": 1.1, "diferenca_estimada": 9.0, "amostra": 2000},
            {"data": "02/10", "desvio_tse": 0.5, "diferenca_estimada": 7.0, "amostra": 2500},
        ],
    }
    fig = create_small_multiples_grid(trajectories)
    assert fig is not None


def test_create_small_multiples_grid_structured() -> None:
    """Verifica a renderização do grid com estrutura analítica completa de inclinação."""
    structured_data = {
        "candidate_1": "Flávio Bolsonaro",
        "candidate_2": "Lula",
        "institutes": [
            {
                "instituto": "Quaest",
                "mean_tilt": -3.0,
                "ci_lower": -5.6,
                "ci_upper": -0.3,
                "includes_zero": False,
                "n_polls": 6,
                "points": [
                    {"data": date(2026, 8, 16), "margin": -1.0, "peer_mean": 2.0, "tilt": -3.0},
                    {"data": date(2026, 9, 15), "margin": 1.0, "peer_mean": 4.0, "tilt": -3.0},
                ],
            },
            {
                "instituto": "PoderData",
                "mean_tilt": 1.7,
                "ci_lower": -0.9,
                "ci_upper": 4.4,
                "includes_zero": True,
                "n_polls": 6,
                "points": [
                    {"data": date(2026, 8, 16), "margin": 3.0, "peer_mean": 1.3, "tilt": 1.7},
                    {"data": date(2026, 9, 15), "margin": 5.0, "peer_mean": 3.3, "tilt": 1.7},
                ],
            },
        ],
        "excluded_institutes": ["Alfa"],
        "total_comparable_polls": 12,
    }
    fig = create_small_multiples_grid(structured_data, "Flávio Bolsonaro", "Lula")
    assert fig is not None
    assert len(fig.data) >= 2


def test_create_trend_aggregator_chart(
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
) -> None:
    """Verifica a criação do gráfico de agregação contínua de tendências."""
    polls = sample_eve_polls_2026
    cands = ["Lula", "Flávio Bolsonaro"]
    df_agg = compute_poll_aggregation_series(
        polls=polls,
        candidates=cands,
        start_date=date(2026, 9, 28),
        end_date=date(2026, 10, 2),
    )
    fig = create_trend_aggregator_chart(df_agg, polls, candidates=cands)
    assert fig is not None


def test_create_directional_bias_chart() -> None:
    """Verifica a criação do gráfico divergente de viés direcional."""
    evals = [
        {"instituto": "Datafolha", "campo_ate": "02/10", "desvio": 1.5},
        {"instituto": "Futura", "campo_ate": "02/10", "desvio": -2.0},
    ]
    fig = create_directional_bias_chart(evals, candidate_name="Lula")
    assert fig is not None


def test_create_sampling_simulator_figure() -> None:
    """Verifica o simulador do Teorema Central do Limite."""
    fig = create_sampling_simulator_figure(p_true=50.0, sample_size=1000, num_simulations=100)
    assert fig is not None
