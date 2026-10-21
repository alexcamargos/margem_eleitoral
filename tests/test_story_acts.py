"""Testes unitários para os módulos de Atos de Storytelling (Atos 1 a 5)."""

from datetime import timedelta

from pytest_mock import MockerFixture

from src.presentation.story_acts.act1_uncertainty import render_act1
from src.presentation.story_acts.act2_election_film import render_act2
from src.presentation.story_acts.act3_rejection import render_act3
from src.presentation.story_acts.act4_eve_clash import render_act4
from src.presentation.story_acts.act5_error_anatomy import render_act5
from src.presentation.story_acts.act6_scientific_verdict import render_act6
from src.transformations.schemas import (
    MetodologiaEnum,
    PesquisaEleitoralSchema,
    ResultadoOficialTSESchema,
)


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
    mocker.patch(
        "streamlit.radio",
        side_effect=["Ciclo Completo (Jul-Out)", "Votos Válidos (Oficial)"],
    )
    mocker.patch("streamlit.plotly_chart")
    mocker.patch("streamlit.spinner")

    render_act2(polls)


def test_render_act3(mocker: MockerFixture) -> None:
    """Valida a renderização do Ato 3 com Termômetro da Rejeição e Dumbbell Plot."""
    mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.columns", side_effect=lambda arg: mock_columns(mocker, arg))
    mocker.patch("streamlit.plotly_chart")
    mocker.patch("streamlit.expander", return_value=mocker.MagicMock())
    mocker.patch("streamlit.warning")

    # Ciclo 2026
    render_act3(year=2026, turno=1)
    # Ciclo 2022
    render_act3(year=2022, turno=1)
    # Ano inexistente (deve acionar st.warning com segurança)
    render_act3(year=1994, turno=1)


def test_render_act4(
    mocker: MockerFixture,
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
    sample_tse_result_2026: ResultadoOficialTSESchema,
) -> None:
    """Valida a renderização do Ato 4 com Forest Plot e Cobertura."""
    eve_polls = sample_eve_polls_2026
    tse_result = sample_tse_result_2026

    mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.selectbox", return_value="Lula")
    mocker.patch("streamlit.columns", side_effect=lambda arg: mock_columns(mocker, arg))
    mocker.patch("streamlit.metric")
    mocker.patch("streamlit.plotly_chart")
    mocker.patch("streamlit.success")
    mocker.patch("streamlit.warning")

    render_act4(eve_polls, tse_result)


def test_render_act5(
    mocker: MockerFixture,
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
    sample_historical_campaign_polls_2026: list[PesquisaEleitoralSchema],
    sample_tse_result_2026: ResultadoOficialTSESchema,
) -> None:
    """Valida a renderização do Ato 5 com Barras Segmentadas, Faixa do Acaso e Abas."""
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

    render_act5(eve_polls, all_polls, tse_result)


def test_render_act6(
    mocker: MockerFixture,
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
    sample_historical_campaign_polls_2026: list[PesquisaEleitoralSchema],
    sample_tse_result_2026: ResultadoOficialTSESchema,
) -> None:
    """Valida a renderização do Ato 6 com Testes de Hipótese e TSE.

    Args:
        mocker: Fixture de mock do pytest-mock.
        sample_eve_polls_2026: Fixture com pesquisas de véspera.
        sample_historical_campaign_polls_2026: Fixture com histórico de campanha (>14 dias).
        sample_tse_result_2026: Fixture com resultado oficial apurado.

    Returns:
        None.

    Raises:
        None.
    """
    eve_polls = sample_eve_polls_2026
    all_polls = sample_historical_campaign_polls_2026 + eve_polls
    tse_result = sample_tse_result_2026

    mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.columns", side_effect=lambda arg: mock_columns(mocker, arg))
    mocker.patch("streamlit.write")
    mock_metric = mocker.patch("streamlit.metric")
    mocker.patch("streamlit.plotly_chart")

    # Renderiza sem all_polls
    render_act6(eve_polls, tse_result)
    calls_sem_all = [
        call for call in mock_metric.call_args_list if call[0][0] == "Late Swing Estimado"
    ]
    assert len(calls_sem_all) == 1
    assert calls_sem_all[0][0][1] == "N/D"

    mock_metric.reset_mock()

    # Renderiza com all_polls onde todas são > 14 dias (deve continuar N/D)
    render_act6(eve_polls, tse_result, all_polls=all_polls)
    calls_com_all = [
        call for call in mock_metric.call_args_list if call[0][0] == "Late Swing Estimado"
    ]
    assert len(calls_com_all) == 1
    assert calls_com_all[0][0][1] == "N/D"


def test_render_act6_with_pre_eve_polls(
    mocker: MockerFixture,
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
    sample_tse_result_2026: ResultadoOficialTSESchema,
) -> None:
    """Valida a renderização do Ato 6 com cálculo de late swing ativo via pré-véspera.

    Args:
        mocker: Fixture de mock do pytest-mock.
        sample_eve_polls_2026: Fixture com pesquisas de véspera.
        sample_tse_result_2026: Fixture com resultado oficial do TSE.

    Returns:
        None.

    Raises:
        None.
    """
    eve_polls = sample_eve_polls_2026
    c1 = sorted(
        sample_tse_result_2026.resultado_nominal.keys(),
        key=lambda c: sample_tse_result_2026.resultado_nominal[c],
        reverse=True,
    )[0]

    # Cria pesquisa de pré-véspera a 10 dias da véspera (janela expandida)
    min_date = min(p.data_fim_campo for p in eve_polls)
    pre_poll = PesquisaEleitoralSchema(
        id_registro_tse="BR-09999/2026",
        instituto_razao_social="Instituto Teste Ltda",
        instituto_nome_fantasia="Instituto Teste",
        data_inicio_campo=min_date - timedelta(days=12),
        data_fim_campo=min_date - timedelta(days=10),
        data_divulgacao=min_date - timedelta(days=9),
        tamanho_amostra=2000,
        margem_erro_declarada=2.0,
        nivel_confianca=0.95,
        metodologia=MetodologiaEnum.PRESENCIAL_DOMICILIAR,
        deff_estimado=1.3,
        votos_totais={c1: 45.0, "Outros": 50.0},
        votos_validos={c1: 47.4, "Outros": 52.6},
        percentual_indecisos=2.0,
        percentual_brancos_nulos=3.0,
    )
    all_polls = [pre_poll] + eve_polls

    mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.columns", side_effect=lambda arg: mock_columns(mocker, arg))
    mocker.patch("streamlit.write")
    mock_metric = mocker.patch("streamlit.metric")
    mocker.patch("streamlit.plotly_chart")

    render_act6(eve_polls, sample_tse_result_2026, all_polls=all_polls)

    calls = [call for call in mock_metric.call_args_list if call[0][0] == "Late Swing Estimado"]
    assert len(calls) == 1
    assert calls[0][0][1] != "N/D"
    assert "janela de 14 dias" in calls[0][1]["help"]


def test_render_act7(
    mocker: MockerFixture,
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
    sample_historical_campaign_polls_2026: list[PesquisaEleitoralSchema],
    sample_tse_result_2026: ResultadoOficialTSESchema,
) -> None:
    """Valida a renderização completa do Ato 7 no 1º Turno e no 2º Turno calibrado.

    Args:
        mocker: Fixture de mock do pytest-mock.
        sample_eve_polls_2026: Fixture com pesquisas de véspera.
        sample_historical_campaign_polls_2026: Fixture com histórico de campanha.
        sample_tse_result_2026: Fixture com resultado oficial do TSE.

    Returns:
        None.

    Raises:
        None.
    """
    from datetime import date

    from src.presentation.story_acts.act7_predictive_forecast import render_act7

    all_polls = sample_historical_campaign_polls_2026 + sample_eve_polls_2026

    mock_md = mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.columns", side_effect=lambda arg: mock_columns(mocker, arg))
    mocker.patch("streamlit.slider", return_value=1)
    mocker.patch("streamlit.checkbox", side_effect=[False, True, True, True])
    mock_plotly = mocker.patch("streamlit.plotly_chart")
    mock_df = mocker.patch("streamlit.dataframe")
    mocker.patch("streamlit.caption")
    mocker.patch("streamlit.success")
    mocker.patch("streamlit.warning")
    mocker.patch("streamlit.expander", return_value=mocker.MagicMock())

    # 1º Turno (com resultado oficial do TSE para backtest)
    render_act7(
        polls=all_polls,
        tse_result=sample_tse_result_2026,
        election_date=date(2026, 10, 4),
    )

    assert mock_md.call_count >= 6
    assert mock_plotly.call_count == 3
    assert mock_df.call_count >= 3

    # 2º Turno (com calibração empírica do 1º turno)
    polls_t2 = [p.model_copy(update={"turno": 2}) for p in all_polls]
    tse_t2 = sample_tse_result_2026.model_copy(
        update={
            "turno": 2,
            "resultado_nominal": {"Flávio Bolsonaro": 0.0, "Lula": 0.0},
        }
    )
    render_act7(
        polls=polls_t2,
        tse_result=tse_t2,
        election_date=date(2026, 10, 25),
        t1_polls=all_polls,
        t1_tse_result=sample_tse_result_2026,
        t1_election_date=date(2026, 10, 4),
    )

    assert mock_plotly.call_count >= 5


def test_render_act7_empty_polls(
    mocker: MockerFixture,
    sample_tse_result_2026: ResultadoOficialTSESchema,
) -> None:
    """Valida a renderização segura do Ato 7 quando a lista de pesquisas é vazia.

    Args:
        mocker: Fixture de mock do pytest-mock.
        sample_tse_result_2026: Fixture com resultado oficial do TSE.

    Returns:
        None.

    Raises:
        None.
    """
    from datetime import date

    from src.presentation.story_acts.act7_predictive_forecast import render_act7

    mocker.patch("streamlit.markdown")
    mock_info = mocker.patch("streamlit.info")

    render_act7(
        polls=[],
        tse_result=sample_tse_result_2026,
        election_date=date(2026, 10, 25),
    )

    assert mock_info.called
