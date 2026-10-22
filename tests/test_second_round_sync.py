"""Testes unitários para o serviço de sincronização automática de pesquisas do 2º Turno junto ao TSE."""

import httpx
from pytest_mock import MockerFixture

from src.ingestion.pesqele_collector import PesqEleCollector
from src.transformations.schemas import PesquisaEleitoralSchema


def test_sync_official_second_round_polls_structure() -> None:
    """Valida a estrutura e conformidade dos dados de 2º Turno sincronizados do TSE.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    collector = PesqEleCollector(year=2026)
    polls = collector.sync_official_second_round_polls(force_download=False)

    assert len(polls) >= 5
    for p in polls:
        assert isinstance(p, PesquisaEleitoralSchema)
        assert p.turno == 2
        assert p.ano == 2026
        assert p.cargo == "PRESIDENTE"
        assert "Flávio Bolsonaro" in p.votos_validos
        assert "Lula" in p.votos_validos
        assert p.tamanho_amostra >= 500
        assert p.margem_erro_declarada > 0.0
        assert p.deff_estimado >= 1.2

        # Valida invariante de votos válidos somando 100%
        soma_validos = sum(p.votos_validos.values())
        assert 99.8 <= soma_validos <= 100.2


def test_sync_second_round_polls_invalid_year() -> None:
    """Verifica se anos incompatíveis levantam ValueError na sincronização do 2º Turno.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    collector = PesqEleCollector(year=2022)
    try:
        collector.sync_official_second_round_polls()
        assert False, "Deveria ter levantado ValueError para ano diferente de 2026."
    except ValueError as e:
        assert "2026" in str(e)


def test_sync_second_round_polls_network_fallback(mocker: MockerFixture) -> None:
    """Valida a resiliência a falhas de rede com fallback local caso o CDN do TSE falhe.

    Args:
        mocker: Fixture do pytest-mock para interceptação de chamadas externas.

    Returns:
        None.

    Raises:
        None.
    """
    mocker.patch(
        "src.ingestion.pesqele_collector.PesqEleCollector.download_official_tse_pesqele_data",
        side_effect=httpx.ConnectError(
            "Simulação de indisponibilidade no CDN de Dados Abertos do TSE"
        ),
    )

    collector = PesqEleCollector(year=2026)
    polls = collector.sync_official_second_round_polls(force_download=True)

    assert len(polls) >= 5
    assert all(p.turno == 2 for p in polls)


def test_sync_second_round_polls_persistence() -> None:
    """Valida a persistência em disco do arquivo Parquet e leitura do dataset completo.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    from pathlib import Path

    import polars as pl

    repo_root = Path(__file__).resolve().parent.parent
    parquet_path = repo_root / "data" / "processed" / "pesquisas_2026.parquet"

    collector = PesqEleCollector(year=2026)
    collector.sync_official_second_round_polls(force_download=False)

    assert parquet_path.exists()
    df = pl.read_parquet(parquet_path)
    assert "turno" in df.columns
    assert df.filter(pl.col("turno") == 2).height >= 5
