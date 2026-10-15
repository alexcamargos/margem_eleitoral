"""Testes unitários para o TaxonomyNormalizer."""

import pytest

from src.transformations.normalizer import TaxonomyNormalizer
from src.transformations.schemas import MetodologiaEnum


@pytest.fixture
def normalizer() -> TaxonomyNormalizer:
    """Fixture que instancia o TaxonomyNormalizer padrão.

    Returns:
        TaxonomyNormalizer: Instância inicializada com arquivo taxonomy_mapping.yaml.
    """
    return TaxonomyNormalizer()


def test_normalize_institute_exact_and_partial(normalizer: TaxonomyNormalizer) -> None:
    """Verifica a normalização de institutos tanto por exatidão quanto por busca parcial."""
    assert normalizer.normalize_institute("DATAFOLHA") == "Datafolha"
    assert normalizer.normalize_institute("DATAFOLHA INSTITUTO DE PESQUISAS LTDA") == "Datafolha"
    assert normalizer.normalize_institute("ATLAS INTEL") == "AtlasIntel"
    assert normalizer.normalize_institute("QUAEST PESQUISAS") == "Quaest"
    assert normalizer.normalize_institute("Instituto Desconhecido") == "Instituto Desconhecido"


def test_normalize_methodology(normalizer: TaxonomyNormalizer) -> None:
    """Verifica a normalização correta de strings de metodologia para MetodologiaEnum."""
    assert (
        normalizer.normalize_methodology("PRESENCIAL DOMICILIAR")
        == MetodologiaEnum.PRESENCIAL_DOMICILIAR
    )
    assert normalizer.normalize_methodology("TELEFONICA CATI") == MetodologiaEnum.TELEFONICA_CATI
    assert normalizer.normalize_methodology("ROBÔ URA") == MetodologiaEnum.TELEFONICA_URA
    assert normalizer.normalize_methodology("PAINEL ONLINE") == MetodologiaEnum.ONLINE


def test_normalize_methodology_invalid(normalizer: TaxonomyNormalizer) -> None:
    """Verifica se metodologia totalmente irreconhecível lança ValueError."""
    with pytest.raises(ValueError, match="Metodologia desconhecida"):
        normalizer.normalize_methodology("METODOLOGIA_ESOTERICA_INEXISTENTE")
