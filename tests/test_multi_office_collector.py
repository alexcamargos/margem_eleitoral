"""Testes unitários para o coletor multi-ano e multi-cargo de pesquisas eleitorais."""

from datetime import date
from pathlib import Path

from pytest_mock import MockerFixture

from src.ingestion.multi_office_collector import MultiOfficeCollector
from src.transformations.schemas import (
    AbrangenciaEnum,
    MetodologiaEnum,
    PesquisaEleitoralSchema,
    TierFonteEnum,
)


def test_multi_office_collector_init(tmp_path: Path) -> None:
    """Verifica a inicialização e criação de diretórios pelo MultiOfficeCollector.

    Args:
        tmp_path: Fixture nativa do pytest com diretório temporário.

    Returns:
        None.

    Raises:
        None.
    """
    raw_dir = tmp_path / "raw"
    proc_dir = tmp_path / "proc"
    collector = MultiOfficeCollector(raw_base_dir=raw_dir, processed_base_dir=proc_dir)

    assert collector.year == 2026
    assert collector.raw_base_dir == raw_dir
    assert collector.processed_dir == proc_dir
    assert raw_dir.exists()
    assert proc_dir.exists()


def test_determine_methodology() -> None:
    """Testa a classificação de metodologias e cálculo do fator de delineamento (deff).

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    collector = MultiOfficeCollector()

    m_pres, deff_pres = collector._determine_methodology("presencial", "Datafolha")
    assert m_pres == MetodologiaEnum.PRESENCIAL_DOMICILIAR
    assert deff_pres == 1.35

    m_ura, deff_ura = collector._determine_methodology("ura", "Veritá")
    assert m_ura == MetodologiaEnum.TELEFONICA_URA
    assert deff_ura == 1.30

    m_onl, deff_onl = collector._determine_methodology("web", "AtlasIntel")
    assert m_onl == MetodologiaEnum.ONLINE
    assert deff_onl == 1.35

    m_flux, deff_flux = collector._determine_methodology("fluxo", "Badra")
    assert m_flux == MetodologiaEnum.PRESENCIAL_FLUXO
    assert deff_flux == 1.30

    m_tel, deff_tel = collector._determine_methodology("telefone", "PoderData")
    assert m_tel == MetodologiaEnum.TELEFONICA_CATI
    assert deff_tel == 1.30


def test_calculate_margin_of_error() -> None:
    """Verifica o cálculo da margem de erro máxima teórica a 95% de confiança.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    collector = MultiOfficeCollector()
    assert collector._calculate_margin_of_error(0) == 2.0
    assert collector._calculate_margin_of_error(2000) == 2.2
    assert collector._calculate_margin_of_error(4000) == 1.5


def test_sanitize_dates() -> None:
    """Verifica a coerência cronológica entre datas de campo e publicação.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    collector = MultiOfficeCollector()

    # Caso normal
    d_i, d_f, d_d = collector._sanitize_dates("2026-10-01", "2026-10-03", "2026-10-03")
    assert d_i == date(2026, 10, 1)
    assert d_f == date(2026, 10, 3)
    assert d_d == date(2026, 10, 3)

    # Caso invertido: fim antes de início e divulgação antes de fim
    d_i2, d_f2, d_d2 = collector._sanitize_dates("2026-10-05", "2026-10-02", "2026-10-01")
    assert d_f2 >= d_i2
    assert d_d2 >= d_f2


def test_safe_float() -> None:
    """Testa a conversão resiliente de strings heterogêneas para float.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    collector = MultiOfficeCollector()
    assert collector._safe_float("45,5") == 45.5
    assert collector._safe_float("12.3") == 12.3
    assert collector._safe_float("NA", default=0.0) == 0.0
    assert collector._safe_float(None, default=5.0) == 5.0
    assert collector._safe_float("#NULO#", default=0.0) == 0.0
    assert collector._safe_float("invalid", default=0.0) == 0.0


def test_save_polls_to_csv_and_parquet(tmp_path: Path) -> None:
    """Verifica a serialização e idempotência dos datasets em CSV e Parquet.

    Args:
        tmp_path: Fixture de diretório temporário.

    Returns:
        None.

    Raises:
        None.
    """
    raw_dir = tmp_path / "raw"
    proc_dir = tmp_path / "proc"
    collector = MultiOfficeCollector(raw_base_dir=raw_dir, processed_base_dir=proc_dir)

    sample_poll = PesquisaEleitoralSchema(
        id_registro_tse="BR-01001/2026",
        instituto_razao_social="DATAFOLHA INSTITUTO DE PESQUISAS LTDA",
        instituto_nome_fantasia="Datafolha",
        data_inicio_campo=date(2026, 10, 1),
        data_fim_campo=date(2026, 10, 3),
        data_divulgacao=date(2026, 10, 3),
        tamanho_amostra=2500,
        margem_erro_declarada=2.0,
        nivel_confianca=0.95,
        metodologia=MetodologiaEnum.PRESENCIAL_DOMICILIAR,
        votos_totais={"Lula": 45.0, "Flávio Bolsonaro": 42.0},
        votos_validos={"Lula": 51.72, "Flávio Bolsonaro": 48.28},
        percentual_indecisos=8.0,
        percentual_brancos_nulos=5.0,
        turno=1,
        cargo="PRESIDENTE",
        ano=2026,
        abrangencia=AbrangenciaEnum.NACIONAL,
        uf="BR",
        regiao="BR",
        tier_fonte=TierFonteEnum.TIER_3_AGREGADOR_PUBLICO,
        verificado_tse=True,
    )

    csv_path, parquet_path = collector.save_polls_to_csv_and_parquet(
        polls=[sample_poll], year=2026, cargo="PRESIDENTE"
    )

    assert csv_path.exists()
    assert parquet_path.exists()
    assert "pesquisas_publicadas_2026.csv" in str(csv_path)
    assert "pesquisas_2026.parquet" in str(parquet_path)


def test_collect_presidente_2026_mocked(mocker: MockerFixture, tmp_path: Path) -> None:
    """Verifica a extração de pesquisas presidenciais de 2026 com payload mockado.

    Args:
        mocker: Fixture do pytest-mock.
        tmp_path: Fixture de diretório temporário.

    Returns:
        None.

    Raises:
        None.
    """
    mock_payload = {
        "presidente_t1": {
            "recent_polls": {
                "t1": [
                    {
                        "registro": "BR-01234/2026",
                        "instituto": "Quaest",
                        "dt_inicio": "2026-10-01",
                        "dt_fim": "2026-10-02",
                        "dt_divulgacao": "2026-10-03",
                        "n": 2000,
                        "scope": "BR",
                        "method": "Presencial",
                        "shares": {
                            "Lula": 44.0,
                            "Flávio Bolsonaro": 40.0,
                            "Indecisos": 6.0,
                        },
                        "url": "https://g1.globo.com/quaest",
                    }
                ],
                "t2": [],
            }
        }
    }

    collector = MultiOfficeCollector(
        raw_base_dir=tmp_path / "raw", processed_base_dir=tmp_path / "proc"
    )
    mocker.patch.object(collector, "fetch_plano_politico_json", return_value=mock_payload)

    polls = collector.collect_presidente_2026()
    assert len(polls) == 1
    p = polls[0]
    assert p.id_registro_tse == "BR-01234/2026"
    assert p.instituto_nome_fantasia == "Quaest"
    assert p.cargo == "PRESIDENTE"
    assert p.turno == 1
    assert p.tamanho_amostra == 2000
    assert "Lula" in p.votos_totais
    assert "Flávio Bolsonaro" in p.votos_totais


def test_collect_governadores_2026_mocked(mocker: MockerFixture, tmp_path: Path) -> None:
    """Verifica a extração de pesquisas para governadores com payload mockado.

    Args:
        mocker: Fixture do pytest-mock.
        tmp_path: Fixture de diretório temporário.

    Returns:
        None.

    Raises:
        None.
    """
    mock_payload = {
        "governador": {
            "states": {
                "SP": {
                    "recent_polls": {
                        "t1": [
                            {
                                "registro": "SP-05555/2026",
                                "instituto": "Datafolha",
                                "dt_inicio": "2026-09-28",
                                "dt_fim": "2026-09-30",
                                "dt_divulgacao": "2026-10-01",
                                "n": 1800,
                                "method": "Presencial",
                                "shares": {
                                    "Tarcísio de Freitas": 52.0,
                                    "Guilherme Boulos": 38.0,
                                    "Indecisos": 5.0,
                                },
                                "url": "https://folha.uol.com.br/datafolha-sp",
                            }
                        ],
                        "t2": [],
                    }
                }
            }
        }
    }

    collector = MultiOfficeCollector(
        raw_base_dir=tmp_path / "raw", processed_base_dir=tmp_path / "proc"
    )
    mocker.patch.object(collector, "fetch_plano_politico_json", return_value=mock_payload)

    polls = collector.collect_governadores_2026()
    assert len(polls) == 1
    p = polls[0]
    assert p.id_registro_tse == "SP-05555/2026"
    assert p.cargo == "GOVERNADOR"
    assert p.uf == "SP"
    assert p.regiao == "SE"
    assert "Tarcísio de Freitas" in p.votos_totais


def test_collect_senado_2026_mocked(mocker: MockerFixture, tmp_path: Path) -> None:
    """Verifica a extração de pesquisas para o Senado com payload mockado.

    Args:
        mocker: Fixture do pytest-mock.
        tmp_path: Fixture de diretório temporário.

    Returns:
        None.

    Raises:
        None.
    """
    mock_payload = {
        "senado": {
            "states": {
                "MG": {
                    "recent_polls": {
                        "t1": [
                            {
                                "registro": "MG-07777/2026",
                                "instituto": "Quaest",
                                "dt_inicio": "2026-09-29",
                                "dt_fim": "2026-10-01",
                                "dt_divulgacao": "2026-10-02",
                                "n": 1500,
                                "method": "Telefone",
                                "shares": {
                                    "Rodrigo Pacheco": 35.0,
                                    "Cleitinho": 32.0,
                                },
                                "indecisos": 15.0,
                                "url": "https://g1.globo.com/senado-mg",
                            }
                        ]
                    }
                }
            }
        }
    }

    collector = MultiOfficeCollector(
        raw_base_dir=tmp_path / "raw", processed_base_dir=tmp_path / "proc"
    )
    mocker.patch.object(collector, "fetch_plano_politico_json", return_value=mock_payload)

    polls = collector.collect_senado_2026()
    assert len(polls) == 1
    p = polls[0]
    assert p.id_registro_tse == "MG-07777/2026"
    assert p.cargo == "SENADOR"
    assert p.uf == "MG"
    assert p.regiao == "SE"
    assert p.percentual_indecisos == 15.0
