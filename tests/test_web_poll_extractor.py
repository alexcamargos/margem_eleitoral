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
        "primeiro_turno": {
            "pesquisas": [
                {
                    "data": "2026-07-06",
                    "instituto": "Ideia",
                    "lula": 40.4,
                    "flavio": 32.0,
                    "n": 1500,
                    "fracao_flavio": 0.4419889502762431,
                },
                {
                    "data": "2026-07-11",
                    "instituto": "Futura",
                    "lula": 40.1,
                    "flavio": 36.8,
                    "n": 2000,
                    "fracao_flavio": 0.4785435630689206,
                },
            ]
        },
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
    polls_2t = extractor.extract_and_transform(
        feed_data=mock_data, only_verified=True, only_eligible=True, include_first_round_history=False
    )

    # Das 3 pesquisas de 2T no mock, 1 é não-verificada e deve ser filtrada
    assert len(polls_2t) == 2
    for p in polls_2t:
        assert isinstance(p, PesquisaEleitoralSchema)
        assert p.id_registro_tse != "BR-99999/2026"
        assert p.turno == 2
        assert "Flávio Bolsonaro" in p.votos_validos
        assert "Lula" in p.votos_validos
        soma_validos = sum(p.votos_validos.values())
        assert 99.8 <= soma_validos <= 100.2

    # Quando incluído o histórico do 1º turno (2 de 1T + 2 de 2T = 4)
    polls_all = extractor.extract_and_transform(feed_data=mock_data, only_verified=True)
    assert len(polls_all) == 4


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
    assert res["total_avaliadas"] == 4
    # Todos os protocolos existem no censo real de 2026
    assert res["total_validadas"] == 4
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

    # 1ª execução: cria e insere 4 levantamentos (2 do 1T e 2 do 2T)
    count1 = extractor.update_published_polls_csv(polls=polls)
    assert count1 == 4
    csv_file = tmp_path / "pesquisas_publicadas_2026.csv"
    assert csv_file.exists()

    df_csv1 = pl.read_csv(csv_file)
    assert df_csv1.height == 4
    assert "voto_bruto_Flávio Bolsonaro" in df_csv1.columns
    assert "voto_bruto_Lula" in df_csv1.columns

    # 2ª execução com os mesmos dados: idempotência sem duplicação de protocolos
    count2 = extractor.update_published_polls_csv(polls=polls)
    assert count2 == 0
    df_csv2 = pl.read_csv(csv_file)
    assert df_csv2.height == 4


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


def test_web_poll_extractor_first_round_history() -> None:
    """Valida a extração e conversão de pesquisas históricas do 1º Turno desde julho.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    mock_data = _build_mock_feed_data()
    extractor = WebPollExtractor(year=2026)
    pt_polls = extractor.extract_and_transform_first_round(feed_data=mock_data)

    assert len(pt_polls) == 2
    for p in pt_polls:
        assert isinstance(p, PesquisaEleitoralSchema)
        assert p.turno == 1
        assert p.ano == 2026
        assert p.data_fim_campo.month == 7
        assert "Flávio Bolsonaro" in p.votos_validos
        assert "Lula" in p.votos_validos
        soma = sum(p.votos_validos.values())
        assert 99.8 <= soma <= 100.2
        assert p.id_registro_tse.startswith("BR-")

