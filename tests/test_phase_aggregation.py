"""Testes unitários para o cálculo de métricas das 3 fases eleitorais.

Valida a segmentação temporal, contagem de pesquisas, cálculo de densidade e
estimativas agregadas dinâmicas para o 1º e 2º Turnos.
"""

from datetime import date, timedelta

from src.analytics.aggregator_model import (
    CandidatePhaseEstimate,
    PhaseAggregationSummary,
    compute_phase_aggregation_metrics,
)
from src.transformations.schemas import MetodologiaEnum, PesquisaEleitoralSchema


def test_compute_phase_aggregation_metrics_empty() -> None:
    """Verifica o retorno estruturado quando a lista de pesquisas está vazia.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    summaries_t1 = compute_phase_aggregation_metrics(
        polls=[],
        candidates=["Lula", "Flávio Bolsonaro"],
        ano_pleito=2026,
        turno=1,
    )
    assert len(summaries_t1) == 3
    assert summaries_t1[0].nome_fase == "Ciclo Completo (Jul-Out)"
    assert summaries_t1[0].total_pesquisas == 0
    assert summaries_t1[0].estimativas == {}

    summaries_t2 = compute_phase_aggregation_metrics(
        polls=[],
        candidates=["Lula", "Flávio Bolsonaro"],
        ano_pleito=2026,
        turno=2,
    )
    assert len(summaries_t2) == 3
    assert summaries_t2[0].nome_fase == "1ª Semana (Arranjos & Alianças)"
    assert summaries_t2[0].total_pesquisas == 0


def test_compute_phase_aggregation_metrics_t1(
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
) -> None:
    """Verifica a agregação de fases no 1º Turno com pesquisas sintéticas calibradas.

    Args:
        sample_eve_polls_2026: Fixture de pesquisas de véspera de 2026.

    Returns:
        None.

    Raises:
        None.
    """
    # Cria pesquisas distribuídas entre Julho, Agosto e Setembro/Outubro
    jul_poll = PesquisaEleitoralSchema(
        id_registro_tse="BR-00010/2026",
        instituto_razao_social="Inst A",
        instituto_nome_fantasia="Inst A",
        data_inicio_campo=date(2026, 7, 10),
        data_fim_campo=date(2026, 7, 15),
        data_divulgacao=date(2026, 7, 16),
        tamanho_amostra=2000,
        margem_erro_declarada=2.2,
        nivel_confianca=0.95,
        metodologia=MetodologiaEnum.PRESENCIAL_DOMICILIAR,
        deff_estimado=1.3,
        votos_totais={"Lula": 45.0, "Flávio Bolsonaro": 35.0},
        votos_validos={"Lula": 52.0, "Flávio Bolsonaro": 40.0},
        percentual_indecisos=10.0,
        percentual_brancos_nulos=10.0,
        turno=1,
        ano=2026,
    )
    ago_poll = PesquisaEleitoralSchema(
        id_registro_tse="BR-00020/2026",
        instituto_razao_social="Inst B",
        instituto_nome_fantasia="Inst B",
        data_inicio_campo=date(2026, 8, 20),
        data_fim_campo=date(2026, 8, 25),
        data_divulgacao=date(2026, 8, 26),
        tamanho_amostra=2500,
        margem_erro_declarada=2.0,
        nivel_confianca=0.95,
        metodologia=MetodologiaEnum.PRESENCIAL_DOMICILIAR,
        deff_estimado=1.3,
        votos_totais={"Lula": 44.0, "Flávio Bolsonaro": 38.0},
        votos_validos={"Lula": 49.0, "Flávio Bolsonaro": 43.0},
        percentual_indecisos=8.0,
        percentual_brancos_nulos=10.0,
        turno=1,
        ano=2026,
    )

    all_polls = [jul_poll, ago_poll, *sample_eve_polls_2026]
    candidates = ["Lula", "Flávio Bolsonaro"]

    summaries = compute_phase_aggregation_metrics(
        polls=all_polls,
        candidates=candidates,
        ano_pleito=2026,
        turno=1,
    )

    assert len(summaries) == 3

    # Fase 1: Ciclo Completo
    fase1 = summaries[0]
    assert fase1.nome_fase == "Ciclo Completo (Jul-Out)"
    assert fase1.total_pesquisas == len(all_polls)
    assert fase1.percentual_total_pesquisas == 100.0
    assert "Lula" in fase1.estimativas
    assert "Flávio Bolsonaro" in fase1.estimativas
    assert fase1.lider is not None
    assert fase1.margem_lider_vice is not None

    # Fase 2: Campanha Oficial (>= 16/Ago)
    fase2 = summaries[1]
    assert fase2.nome_fase == "Campanha Oficial (Ago-Out)"
    # Exclui a pesquisa de julho
    assert fase2.total_pesquisas == len(all_polls) - 1
    assert fase2.estimativas["Lula"].delta_anterior is not None

    # Fase 3: Reta Final (<= 14 dias da data máxima)
    fase3 = summaries[2]
    assert fase3.nome_fase == "Reta Final (14 dias)"
    assert fase3.total_pesquisas == len(sample_eve_polls_2026)
    assert fase3.pesquisas_por_dia >= 0.0


def test_compute_phase_aggregation_metrics_t2() -> None:
    """Verifica a adaptação do cálculo para a divisão de 3 semanas no 2º Turno.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    # 2º Turno de 2026: T1 em 04/10/2026, T2 em 25/10/2026
    # Semana 1: 05/10 a 11/10
    # Semana 2: 12/10 a 18/10
    # Semana 3: 19/10 a 25/10
    poll_w1 = PesquisaEleitoralSchema(
        id_registro_tse="BR-00101/2026",
        instituto_razao_social="Inst W1",
        instituto_nome_fantasia="Inst W1",
        data_inicio_campo=date(2026, 10, 6),
        data_fim_campo=date(2026, 10, 8),
        data_divulgacao=date(2026, 10, 9),
        tamanho_amostra=2000,
        margem_erro_declarada=2.2,
        nivel_confianca=0.95,
        metodologia=MetodologiaEnum.PRESENCIAL_DOMICILIAR,
        deff_estimado=1.3,
        votos_totais={"Lula": 48.0, "Flávio Bolsonaro": 44.0},
        votos_validos={"Lula": 52.0, "Flávio Bolsonaro": 48.0},
        percentual_indecisos=4.0,
        percentual_brancos_nulos=4.0,
        turno=2,
        ano=2026,
    )
    poll_w2 = PesquisaEleitoralSchema(
        id_registro_tse="BR-00102/2026",
        instituto_razao_social="Inst W2",
        instituto_nome_fantasia="Inst W2",
        data_inicio_campo=date(2026, 10, 13),
        data_fim_campo=date(2026, 10, 15),
        data_divulgacao=date(2026, 10, 16),
        tamanho_amostra=2500,
        margem_erro_declarada=2.0,
        nivel_confianca=0.95,
        metodologia=MetodologiaEnum.PRESENCIAL_DOMICILIAR,
        deff_estimado=1.3,
        votos_totais={"Lula": 47.0, "Flávio Bolsonaro": 45.0},
        votos_validos={"Lula": 51.0, "Flávio Bolsonaro": 49.0},
        percentual_indecisos=4.0,
        percentual_brancos_nulos=4.0,
        turno=2,
        ano=2026,
    )
    poll_w3 = PesquisaEleitoralSchema(
        id_registro_tse="BR-00103/2026",
        instituto_razao_social="Inst W3",
        instituto_nome_fantasia="Inst W3",
        data_inicio_campo=date(2026, 10, 20),
        data_fim_campo=date(2026, 10, 22),
        data_divulgacao=date(2026, 10, 23),
        tamanho_amostra=3000,
        margem_erro_declarada=1.8,
        nivel_confianca=0.95,
        metodologia=MetodologiaEnum.PRESENCIAL_DOMICILIAR,
        deff_estimado=1.3,
        votos_totais={"Lula": 46.5, "Flávio Bolsonaro": 46.5},
        votos_validos={"Lula": 50.0, "Flávio Bolsonaro": 50.0},
        percentual_indecisos=3.5,
        percentual_brancos_nulos=3.5,
        turno=2,
        ano=2026,
    )

    all_polls_t2 = [poll_w1, poll_w2, poll_w3]
    summaries = compute_phase_aggregation_metrics(
        polls=all_polls_t2,
        candidates=["Lula", "Flávio Bolsonaro"],
        ano_pleito=2026,
        turno=2,
    )

    assert len(summaries) == 3
    assert summaries[0].nome_fase == "1ª Semana (Arranjos & Alianças)"
    assert summaries[0].total_pesquisas == 1
    assert summaries[1].nome_fase == "2ª Semana (Horário Eleitoral & Debates)"
    assert summaries[1].total_pesquisas == 1
    assert summaries[2].nome_fase == "3ª Semana (Reta Final)"
    assert summaries[2].total_pesquisas == 1

    # Verifica se os deltas foram calculados
    assert summaries[1].estimativas["Lula"].delta_anterior is not None
    assert summaries[2].estimativas["Lula"].delta_anterior is not None


def test_compute_phase_aggregation_metrics_real_dataset() -> None:
    """Valida o cálculo com dados reais carregados de 2026 e 2022.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    from src.ingestion.data_loader import get_election_dataset

    # 2026 T1
    _, _, polls_2026 = get_election_dataset(2026, 1)
    summaries_26 = compute_phase_aggregation_metrics(
        polls=polls_2026,
        candidates=["Lula", "Flávio Bolsonaro"],
        ano_pleito=2026,
        turno=1,
    )
    assert len(summaries_26) == 3
    assert summaries_26[0].total_pesquisas == len(polls_2026)
    assert summaries_26[2].total_pesquisas <= summaries_26[1].total_pesquisas
    assert "Lula" in summaries_26[2].estimativas

    # 2022 T1
    _, _, polls_2022 = get_election_dataset(2022, 1)
    summaries_22 = compute_phase_aggregation_metrics(
        polls=polls_2022,
        candidates=["Lula", "Bolsonaro"],
        ano_pleito=2022,
        turno=1,
    )
    assert len(summaries_22) == 3
    assert summaries_22[0].total_pesquisas == len(polls_2022)
    assert "Bolsonaro" in summaries_22[2].estimativas

