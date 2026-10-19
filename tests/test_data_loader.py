"""Testes unitários para o carregador de dados com cache (data_loader)."""

from datetime import date

from src.ingestion.data_loader import (
    get_election_dataset,
    get_election_date,
    load_election_settings,
)
from src.transformations.schemas import PesquisaEleitoralSchema, ResultadoOficialTSESchema


def test_load_election_settings() -> None:
    """Verifica se as configurações eleitorais são carregadas corretamente de settings.yaml."""
    settings = load_election_settings()
    assert "elections" in settings
    assert 2026 in settings["elections"]
    assert 2022 in settings["elections"]


def test_get_election_date() -> None:
    """Verifica a obtenção das datas dos pleitos do 1º e 2º turnos."""
    d_2026_t1 = get_election_date(2026, 1)
    assert d_2026_t1 == date(2026, 10, 4)

    d_2026_t2 = get_election_date(2026, 2)
    assert d_2026_t2 == date(2026, 10, 25)

    d_2022_t1 = get_election_date(2022, 1)
    assert d_2022_t1 == date(2022, 10, 2)

    d_2022_t2 = get_election_date(2022, 2)
    assert d_2022_t2 == date(2022, 10, 30)


def test_get_election_dataset_2026() -> None:
    """Valida o carregamento do dataset de 2026 segregando véspera e série completa."""
    tse_result, eve_polls, all_polls = get_election_dataset(year=2026, turno=1, cutoff_days=3)

    assert isinstance(tse_result, ResultadoOficialTSESchema)
    assert tse_result.ano == 2026
    assert len(eve_polls) > 0
    assert len(all_polls) >= len(eve_polls)

    # Todas as pesquisas de véspera devem ter fim de campo <= 3 dias antes da eleição (04/10/2026)
    elec_date = date(2026, 10, 4)
    for p in eve_polls:
        assert isinstance(p, PesquisaEleitoralSchema)
        assert (elec_date - p.data_fim_campo).days <= 3


def test_get_election_dataset_2022() -> None:
    """Valida o carregamento do dataset de 2022 segregando véspera e série completa."""
    tse_result, eve_polls, all_polls = get_election_dataset(year=2022, turno=1, cutoff_days=3)

    assert isinstance(tse_result, ResultadoOficialTSESchema)
    assert tse_result.ano == 2022
    assert len(eve_polls) > 0
    assert len(all_polls) >= len(eve_polls)

    elec_date = date(2022, 10, 2)
    for p in eve_polls:
        assert (elec_date - p.data_fim_campo).days <= 3


def test_get_election_dataset_2026_turno_2() -> None:
    """Valida o carregamento do dataset do 2º Turno de 2026 em modo pré-eleição.

    Em 19/10/2026, a apuração do 2º Turno (25/10/2026) ainda não ocorreu, portanto
    `tse_result` é None e não existem pesquisas na janela de véspera (<= 72h).

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    tse_result, eve_polls, all_polls = get_election_dataset(year=2026, turno=2, cutoff_days=3)

    assert tse_result is None or not getattr(tse_result, "apuracao_concluida", True)
    assert len(eve_polls) == 0
    assert len(all_polls) >= 15

    for p in all_polls:
        assert isinstance(p, PesquisaEleitoralSchema)
        assert p.turno == 2
        assert p.data_fim_campo <= date(2026, 10, 19)


def test_get_second_round_sync_summary() -> None:
    """Verifica a geração do sumário estruturado de sincronização do 2º Turno.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    from src.ingestion.data_loader import get_second_round_sync_summary

    summary = get_second_round_sync_summary(year=2026)
    assert summary["is_synced"] is True
    assert summary["total_polls"] >= 15
    assert summary["eve_polls_count"] == 0
    assert len(summary["institutes"]) >= 5
    assert summary["latest_field_date"] is not None
