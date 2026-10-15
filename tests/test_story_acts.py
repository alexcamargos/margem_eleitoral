"""Testes unitários para os módulos de Atos de Storytelling (Atos 1 a 5)."""

from pytest_mock import MockerFixture

from src.presentation.story_acts.act1_uncertainty import render_act1
from src.presentation.story_acts.act2_election_film import render_act2
from src.presentation.story_acts.act3_eve_clash import render_act3
from src.presentation.story_acts.act4_error_anatomy import render_act4
from src.presentation.story_acts.act5_scientific_verdict import render_act5
from src.transformations.schemas import PesquisaEleitoralSchema, ResultadoOficialTSESchema


def mock_columns(mocker: MockerFixture, arg: int | list) -> list:
    """Função utilitária para mockar st.columns recebendo int ou list de proporções."""
    count = arg if isinstance(arg, int) else len(arg)
    return [mocker.MagicMock() for _ in range(count)]


def test_render_act1(mocker: MockerFixture) -> None:
    """Valida a renderização do Ato 1 com mocks de Streamlit."""
    mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.slider", side_effect=[2000, 50.0, 1.35])
    mocker.patch("streamlit.select_slider", return_value=1000)
    mocker.patch("streamlit.plotly_chart")
    mocker.patch("streamlit.info")
    mocker.patch("streamlit.latex")
    mocker.patch("streamlit.columns", side_effect=lambda arg: mock_columns(mocker, arg))

    render_act1()


def test_render_act2(
    mocker: MockerFixture, sample_eve_polls_2026: list[PesquisaEleitoralSchema]
) -> None:
    """Valida a renderização do Ato 2 com Agregador Dinâmico."""
    polls = sample_eve_polls_2026
    mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.columns", side_effect=lambda arg: mock_columns(mocker, arg))
    mocker.patch(
        "streamlit.multiselect",
        side_effect=[["Lula", "Flávio Bolsonaro"], ["TELEFONICA_CATI", "PRESENCIAL_DOMICILIAR"]],
    )
    mocker.patch("streamlit.radio", return_value="Votos Válidos (Oficial)")
    mocker.patch("streamlit.plotly_chart")
    mocker.patch("streamlit.spinner")

    render_act2(polls)


def test_render_act3(
    mocker: MockerFixture,
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
    sample_tse_result_2026: ResultadoOficialTSESchema,
) -> None:
    """Valida a renderização do Ato 3 com Forest Plot e Cobertura."""
    eve_polls = sample_eve_polls_2026
    tse_result = sample_tse_result_2026

    mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.selectbox", return_value="Lula")
    mocker.patch("streamlit.columns", side_effect=lambda arg: mock_columns(mocker, arg))
    mocker.patch("streamlit.metric")
    mocker.patch("streamlit.plotly_chart")
    mocker.patch("streamlit.success")
    mocker.patch("streamlit.warning")

    render_act3(eve_polls, tse_result)


def test_render_act4(
    mocker: MockerFixture,
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
    sample_historical_campaign_polls_2026: list[PesquisaEleitoralSchema],
    sample_tse_result_2026: ResultadoOficialTSESchema,
) -> None:
    """Valida a renderização do Ato 4 com Barras Segmentadas, Faixa do Acaso e Abas."""
    eve_polls = sample_eve_polls_2026
    all_polls = sample_historical_campaign_polls_2026 + eve_polls
    tse_result = sample_tse_result_2026

    mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.columns", side_effect=lambda arg: mock_columns(mocker, arg))
    mocker.patch("streamlit.metric")
    mocker.patch("streamlit.tabs", return_value=[mocker.MagicMock(), mocker.MagicMock()])
    mocker.patch("streamlit.plotly_chart")
    mocker.patch("streamlit.dataframe")
    mocker.patch("streamlit.expander", return_value=mocker.MagicMock())

    render_act4(eve_polls, all_polls, tse_result)


def test_render_act5(
    mocker: MockerFixture,
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
    sample_historical_campaign_polls_2026: list[PesquisaEleitoralSchema],
    sample_tse_result_2026: ResultadoOficialTSESchema,
) -> None:
    """Valida a renderização do Ato 5 com Testes de Hipótese e TSE."""
    eve_polls = sample_eve_polls_2026
    all_polls = sample_historical_campaign_polls_2026 + eve_polls
    tse_result = sample_tse_result_2026

    mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.columns", side_effect=lambda arg: mock_columns(mocker, arg))
    mocker.patch("streamlit.write")
    mocker.patch("streamlit.metric")
    mocker.patch("streamlit.plotly_chart")

    # Renderiza sem all_polls
    render_act5(eve_polls, tse_result)

    # Renderiza com all_polls (ativa cálculo de late swing)
    render_act5(eve_polls, tse_result, all_polls=all_polls)
