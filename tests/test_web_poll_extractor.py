"""Testes unitários e de integração para o WebPollExtractor."""

from datetime import date
from pathlib import Path
from typing import Any

import httpx
import polars as pl
from pytest_mock import MockerFixture

from src.ingestion.web_poll_extractor import WebPollExtractor
from src.transformations.schemas import AbrangenciaEnum, MetodologiaEnum, PesquisaEleitoralSchema


def _build_mock_feed_data() -> dict[str, Any]:
    """Cria uma fixture em memória simulando um payload de feed de pesquisas abertas.

    Args:
        None.

    Returns:
        dict[str, Any]: Dicionário representativo com casos verificados e não verificados.

    Raises:
        None.
    """
    return {
        "versao_schema": 1,
        "data_referencia": "2026-10-20",
        "candidatos": {
            "a": {"id": "lula", "nome_urna": "Lula"},
            "b": {"id": "flavio", "nome_urna": "Flávio Bolsonaro"},
        },
        "pesquisas": [
            {
                "poll_id": "mock_poll_1",
                "instituto": "PoderData",
                "registro_tse": "BR-08134/2026",
                "data_campo_inicio": "2026-10-05",
                "data_campo_fim": "2026-10-07",
                "data_divulgacao": "2026-10-08",
                "modo": "telefone",
                "amostra_n": 3000,
                "margem_erro_pp": 1.8,
                "nivel_confianca": 95.0,
                "base_percentual": "votos_validos",
                "pct_a": 47.0,
                "pct_b": 53.0,
                "pct_branco_nulo": None,
                "pct_indeciso": None,
                "p_validos_a": 0.47,
                "urls": "https://www.poder360.com.br/pesquisa1",
                "verificado": True,
                "elegivel": True,
            },
            {
                "poll_id": "mock_poll_2",
                "instituto": "Datafolha",
                "registro_tse": "BR-02949/2026",
                "data_campo_inicio": "2026-10-06",
                "data_campo_fim": "2026-10-08",
                "data_divulgacao": "2026-10-08",
                "modo": "presencial",
                "amostra_n": 2800,
                "margem_erro_pp": 2.0,
                "nivel_confianca": 95.0,
                "base_percentual": "votos_totais",
                "pct_a": 45.0,
                "pct_b": 49.0,
                "pct_branco_nulo": 5.0,
                "pct_indeciso": 1.0,
                "p_validos_a": 0.4787,
                "urls": "https://g1.globo.com/pesquisa2",
                "verificado": True,
                "elegivel": True,
            },
            {
                "poll_id": "mock_unverified_poll",
                "instituto": "Instituto Fake",
                "registro_tse": "BR-99999/2026",
                "data_campo_inicio": "2026-10-10",
                "data_campo_fim": "2026-10-12",
                "data_divulgacao": "2026-10-13",
                "modo": "online",
                "amostra_n": 1000,
                "margem_erro_pp": 3.0,
                "nivel_confianca": 95.0,
                "base_percentual": "votos_totais",
                "pct_a": 50.0,
                "pct_b": 50.0,
                "pct_branco_nulo": 0.0,
                "pct_indeciso": 0.0,
                "p_validos_a": 0.50,
                "urls": "https://fake.com/pesquisa",
                "verificado": False,
                "elegivel": False,
            },
        ],
    }


def test_web_poll_extractor_fetch_feed_payload_mocked(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Verifica a requisição HTTP mockada e escrita de snapshot local em disco.

    Args:
        mocker: Fixture do pytest-mock para interceptação de chamadas de rede.
        tmp_path: Diretório temporário fornecido pelo pytest.

    Returns:
        None.

    Raises:
        None.
    """
    mock_data = _build_mock_feed_data()
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_data
    mock_response.raise_for_status.return_value = None

    mocker.patch("httpx.Client.get", return_value=mock_response)

    extractor = WebPollExtractor(year=2026, raw_base_dir=tmp_path)
    payload = extractor.fetch_feed_payload(url="https://mock-feed.org/api/polls.json")

    assert payload["versao_schema"] == 1
    assert len(payload["pesquisas"]) == 3
    snapshot = tmp_path / "feed_pesquisas_publicadas_2026.json"
    assert snapshot.exists()


def test_web_poll_extractor_filters_unverified() -> None:
    """Valida o descarte rigoroso de levantamentos com verificado=False ou elegivel=False.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    mock_data = _build_mock_feed_data()
    extractor = WebPollExtractor(year=2026)
    polls = extractor.extract_and_transform(feed_data=mock_data, only_verified=True, only_eligible=True)

    # Das 3 pesquisas no mock, 1 é não-verificada e deve ser filtrada
    assert len(polls) == 2
    for p in polls:
        assert isinstance(p, PesquisaEleitoralSchema)
        assert p.id_registro_tse != "BR-99999/2026"
        assert p.turno == 2
        assert "Flávio Bolsonaro" in p.votos_validos
        assert "Lula" in p.votos_validos
        soma_validos = sum(p.votos_validos.values())
        assert 99.8 <= soma_validos <= 100.2


def test_web_poll_extractor_cross_validation_with_census() -> None:
    """Verifica a auditoria cruzada contra o censo oficial de registros do TSE.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    mock_data = _build_mock_feed_data()
    extractor = WebPollExtractor(year=2026)
    polls = extractor.extract_and_transform(feed_data=mock_data, only_verified=True)

    res = extractor.cross_validate_with_tse_census(polls=polls)
    assert res["total_avaliadas"] == 2
    # Ambos os protocolos existem no censo real de 2026
    assert res["total_validadas"] == 2
    assert res["total_divergentes"] == 0
    assert res["taxa_conformidade"] == 1.0


def test_web_poll_extractor_update_published_polls_csv(tmp_path: Path) -> None:
    """Valida a atualização atômica e idempotente do CSV oficial de pesquisas.

    Args:
        tmp_path: Diretório temporário fornecido pelo pytest.

    Returns:
        None.

    Raises:
        None.
    """
    mock_data = _build_mock_feed_data()
    extractor = WebPollExtractor(year=2026, raw_base_dir=tmp_path)
    polls = extractor.extract_and_transform(feed_data=mock_data, only_verified=True)

    # 1ª execução: cria e insere
    count1 = extractor.update_published_polls_csv(polls=polls)
    assert count1 == 2
    csv_file = tmp_path / "pesquisas_publicadas_2026.csv"
    assert csv_file.exists()

    df_csv1 = pl.read_csv(csv_file)
    assert df_csv1.height == 2
    assert "voto_bruto_Flávio Bolsonaro" in df_csv1.columns
    assert "voto_bruto_Lula" in df_csv1.columns

    # 2ª execução com os mesmos dados: idempotência sem duplicação de protocolos
    count2 = extractor.update_published_polls_csv(polls=polls)
    assert count2 == 0
    df_csv2 = pl.read_csv(csv_file)
    assert df_csv2.height == 2


def test_web_poll_extractor_network_error_without_cache(mocker: MockerFixture, tmp_path: Path) -> None:
    """Garante que exceções adequadas são propagadas em falhas de rede sem cache local.

    Args:
        mocker: Fixture do pytest-mock.
        tmp_path: Diretório temporário fornecido pelo pytest.

    Returns:
        None.

    Raises:
        None.
    """
    mocker.patch(
        "httpx.Client.get",
        side_effect=httpx.ConnectError("Erro simulado de conexão"),
    )
    extractor = WebPollExtractor(year=2026, raw_base_dir=tmp_path)
    try:
        extractor.fetch_feed_payload(url="https://inexistente-feed.gov/api.json")
        assert False, "Deveria ter levantado httpx.ConnectError"
    except httpx.ConnectError:
        pass
