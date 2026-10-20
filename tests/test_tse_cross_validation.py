"""Testes de validação cruzada das pesquisas eleitorais com o censo oficial do TSE (PesqEle).

Garante que 100% das pesquisas utilizadas nos datasets de 2022 e 2026 possuam registros
autênticos no repositório de dados abertos do TSE, sem qualquer dado fictício ou alucinado.
"""

from src.ingestion.data_loader import get_election_dataset, get_tse_registration_census
from src.ingestion.pesqele_collector import PesqEleCollector
from src.transformations.schemas import TierFonteEnum


def test_tse_cross_validation_2026_census() -> None:
    """Valida que todas as pesquisas de 2026 coincidem com os protocolos oficiais do TSE.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    collector = PesqEleCollector(year=2026)
    census_df = get_tse_registration_census(year=2026)
    audit = collector.cross_validate_with_tse_census(census_df=census_df)

    assert audit["total_avaliadas"] > 0
    assert audit["total_validadas"] == audit["total_avaliadas"]
    assert audit["total_divergentes"] == 0
    assert audit["taxa_conformidade"] == 1.0
    assert len(audit["detalhes_divergencias"]) == 0


def test_tse_cross_validation_2022_census() -> None:
    """Valida que todas as pesquisas de 2022 coincidem com os protocolos oficiais do TSE.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    collector = PesqEleCollector(year=2022)
    census_df = get_tse_registration_census(year=2022)
    audit = collector.cross_validate_with_tse_census(census_df=census_df)

    assert audit["total_avaliadas"] > 0
    assert audit["total_validadas"] == audit["total_avaliadas"]
    assert audit["total_divergentes"] == 0
    assert audit["taxa_conformidade"] == 1.0
    assert len(audit["detalhes_divergencias"]) == 0


def test_tier_source_hierarchy_and_urls_2026() -> None:
    """Valida a atribuição da hierarquia de fontes (Tier 1 a 4) e URLs das pesquisas de 2026.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    _, _, polls_26 = get_election_dataset(year=2026, turno=1, include_subnational=True)
    assert len(polls_26) > 0

    valid_tiers = {tier.value for tier in TierFonteEnum}

    for p in polls_26:
        assert p.tier_fonte in valid_tiers
        assert p.url_tse_pesqele.startswith("https://")
        assert "tse.jus.br" in p.url_tse_pesqele
        assert p.verificado_tse is True


def test_tier_source_hierarchy_and_urls_2022() -> None:
    """Valida a atribuição da hierarquia de fontes (Tier 1 a 4) e URLs das pesquisas de 2022.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    _, _, polls_22 = get_election_dataset(year=2022, turno=1, include_subnational=True)
    assert len(polls_22) > 0

    valid_tiers = {tier.value for tier in TierFonteEnum}

    for p in polls_22:
        assert p.tier_fonte in valid_tiers
        assert p.url_tse_pesqele.startswith("https://")
        assert "tse.jus.br" in p.url_tse_pesqele
        assert p.verificado_tse is True
