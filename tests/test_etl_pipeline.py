"""Testes unitários para o pipeline de ETL e coletores do TSE e PesqEle."""

from src.ingestion.pesqele_collector import PesqEleCollector
from src.ingestion.pipeline import run_etl_for_year
from src.ingestion.tse_results import TSEResultsExtractor
from src.transformations.schemas import PesquisaEleitoralSchema, ResultadoOficialTSESchema


def test_tse_results_extractor_2026() -> None:
    """Valida a extração dos resultados oficiais do TSE para o 1º turno de 2026."""
    extractor = TSEResultsExtractor(year=2026, turno=1)
    result = extractor.extract_and_transform()

    assert isinstance(result, ResultadoOficialTSESchema)
    assert result.ano == 2026
    assert result.turno == 1
    assert "Flávio Bolsonaro" in result.resultado_nominal
    assert "Lula" in result.resultado_nominal
    assert "Augusto Cury" in result.resultado_nominal
    assert "Renan Santos" in result.resultado_nominal
    assert "Ronaldo Caiado" in result.resultado_nominal
    assert "Romeu Zema" in result.resultado_nominal
    assert result.resultado_nominal["Flávio Bolsonaro"] == 47.03
    assert result.resultado_nominal["Lula"] == 45.16
    assert result.total_votos_validos == 119300788
    assert result.total_brancos == 2300798
    assert result.total_nulos == 3674249
    assert result.total_abstencoes == 33469244
    assert sum(result.resultado_nominal.values()) == 100.0


def test_tse_results_extractor_2026_t2() -> None:
    """Valida a extração dos resultados oficiais do TSE para o 2º turno de 2026.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    extractor = TSEResultsExtractor(year=2026, turno=2)
    result = extractor.extract_and_transform()

    assert isinstance(result, ResultadoOficialTSESchema)
    assert result.ano == 2026
    assert result.turno == 2
    assert result.apuracao_concluida is True
    assert "Flávio Bolsonaro" in result.resultado_nominal
    assert "Lula" in result.resultado_nominal
    assert result.resultado_nominal["Lula"] == 51.79
    assert result.resultado_nominal["Flávio Bolsonaro"] == 48.21
    assert result.total_votos_validos == 124082273
    assert result.total_brancos == 1430496
    assert result.total_nulos == 2723305
    assert result.total_abstencoes == 30509005
    assert sum(result.resultado_nominal.values()) == 100.0


def test_tse_results_extractor_2022() -> None:
    """Valida a extração dos resultados oficiais do TSE para o 1º e 2º turnos de 2022."""
    ext_t1 = TSEResultsExtractor(year=2022, turno=1)
    r1 = ext_t1.extract_and_transform()
    assert r1.ano == 2022
    assert "Bolsonaro" in r1.resultado_nominal
    assert "Simone Tebet" in r1.resultado_nominal
    assert "Ciro Gomes" in r1.resultado_nominal

    ext_t2 = TSEResultsExtractor(year=2022, turno=2)
    r2 = ext_t2.extract_and_transform()
    assert r2.ano == 2022
    assert r2.turno == 2
    assert sum(r2.resultado_nominal.values()) == 100.0


def test_pesqele_collector_2026() -> None:
    """Valida o coletor de pesquisas do PesqEle para o pleito de 2026."""
    collector = PesqEleCollector(year=2026)
    polls = collector.extract_and_transform()

    assert len(polls) >= 15
    for p in polls:
        assert isinstance(p, PesquisaEleitoralSchema)
        assert p.ano == 2026
        assert "Lula" in p.votos_validos
        assert "Flávio Bolsonaro" in p.votos_validos

    df = collector.polls_to_polars(polls)
    assert df.height == len(polls)
    assert "id_registro_tse" in df.columns
    assert "validos_Flávio Bolsonaro" in df.columns


def test_pesqele_collector_2022() -> None:
    """Valida o coletor de pesquisas do PesqEle para o pleito de 2022."""
    collector = PesqEleCollector(year=2022)
    polls = collector.extract_and_transform()

    assert len(polls) >= 15
    for p in polls:
        assert isinstance(p, PesquisaEleitoralSchema)
        assert p.ano == 2022
        assert "Bolsonaro" in p.votos_validos

    df = collector.polls_to_polars(polls)
    assert df.height == len(polls)
    assert "validos_Bolsonaro" in df.columns


def test_run_etl_pipeline_both_years() -> None:
    """Valida a execução ponta a ponta do orquestrador de ETL para 2026 e 2022."""
    tse_2026, polls_2026 = run_etl_for_year(year=2026, turno=1)
    assert tse_2026.ano == 2026
    assert len(polls_2026) > 0

    tse_2022, polls_2022 = run_etl_for_year(year=2022, turno=1)
    assert tse_2022.ano == 2022
    assert len(polls_2022) > 0


def test_pesqele_tse_registration_census_2026() -> None:
    """Valida o processamento do censo de pesquisas registradas no TSE."""
    collector = PesqEleCollector(year=2026)
    census_df = collector.get_tse_registration_census()

    assert census_df.height >= 1000
    assert "instituto_consistente" in census_df.columns
    assert "total_registros_instituto" in census_df.columns
    assert "id_registro_tse" in census_df.columns
    assert census_df.filter(census_df["instituto_consistente"]).height > 0
