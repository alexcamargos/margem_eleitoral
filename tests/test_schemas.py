"""Testes unitários para validação de esquemas Pydantic."""

from datetime import date

import pytest
from pydantic import ValidationError

from src.transformations.schemas import (
    MetodologiaEnum,
    PesquisaEleitoralSchema,
    ResultadoOficialTSESchema,
)


def test_pesquisa_eleitoral_schema_valid() -> None:
    """Valida a instanciação correta de PesquisaEleitoralSchema com dados válidos."""
    pesquisa = PesquisaEleitoralSchema(
        id_registro_tse="BR-01234/2026",
        instituto_razao_social="Datafolha Instituto de Pesquisas Ltda",
        instituto_nome_fantasia="Datafolha",
        data_inicio_campo=date(2026, 9, 28),
        data_fim_campo=date(2026, 10, 1),
        data_divulgacao=date(2026, 10, 2),
        tamanho_amostra=2500,
        margem_erro_declarada=2.0,
        nivel_confianca=0.95,
        metodologia=MetodologiaEnum.PRESENCIAL_DOMICILIAR,
        deff_estimado=1.3,
        votos_totais={"Candidato A": 45.0, "Candidato B": 40.0, "Outros": 5.0},
        votos_validos={"Candidato A": 50.0, "Candidato B": 44.4, "Outros": 5.6},
        percentual_indecisos=4.0,
        percentual_brancos_nulos=6.0,
    )
    assert pesquisa.id_registro_tse == "BR-01234/2026"
    assert pesquisa.tamanho_amostra == 2500
    assert pesquisa.metodologia == MetodologiaEnum.PRESENCIAL_DOMICILIAR


def test_pesquisa_eleitoral_schema_invalid_tse_id() -> None:
    """Verifica se registro fora do padrão TSE é rejeitado."""
    with pytest.raises(ValidationError):
        PesquisaEleitoralSchema(
            id_registro_tse="INVALID-123",
            instituto_razao_social="Instituto X",
            instituto_nome_fantasia="Instituto X",
            data_inicio_campo=date(2026, 9, 28),
            data_fim_campo=date(2026, 10, 1),
            data_divulgacao=date(2026, 10, 2),
            tamanho_amostra=2000,
            margem_erro_declarada=2.0,
            metodologia=MetodologiaEnum.TELEFONICA_CATI,
            votos_totais={"A": 50.0},
            votos_validos={"A": 100.0},
            percentual_indecisos=0.0,
            percentual_brancos_nulos=0.0,
        )


def test_pesquisa_eleitoral_schema_invalid_dates() -> None:
    """Verifica se data final de campo anterior ao início de campo é rejeitada."""
    with pytest.raises(ValidationError, match="não pode ser anterior à data de início"):
        PesquisaEleitoralSchema(
            id_registro_tse="BR-01234/2026",
            instituto_razao_social="Instituto X",
            instituto_nome_fantasia="Instituto X",
            data_inicio_campo=date(2026, 10, 2),
            data_fim_campo=date(2026, 10, 1),
            data_divulgacao=date(2026, 10, 2),
            tamanho_amostra=2000,
            margem_erro_declarada=2.0,
            metodologia=MetodologiaEnum.ONLINE,
            votos_totais={"A": 50.0},
            votos_validos={"A": 100.0},
            percentual_indecisos=0.0,
            percentual_brancos_nulos=0.0,
        )


def test_resultado_oficial_tse_schema_valid() -> None:
    """Valida a instanciação de ResultadoOficialTSESchema com percentuais somando 100%."""
    resultado = ResultadoOficialTSESchema(
        cargo="PRESIDENTE",
        turno=1,
        ano=2026,
        total_votos_validos=118000000,
        total_brancos=2000000,
        total_nulos=3500000,
        total_abstencoes=31000000,
        resultado_nominal={"Candidato A": 48.4, "Candidato B": 43.2, "Candidato C": 8.4},
    )
    assert resultado.total_votos_validos == 118000000
    assert sum(resultado.resultado_nominal.values()) == 100.0


def test_resultado_oficial_tse_schema_invalid_sum() -> None:
    """Verifica se percentual divergente de 100% é rejeitado com ValidationError."""
    with pytest.raises(ValidationError, match="deve ser aproximadamente 100.0%"):
        ResultadoOficialTSESchema(
            cargo="PRESIDENTE",
            turno=1,
            ano=2026,
            total_votos_validos=1000000,
            total_brancos=10000,
            total_nulos=10000,
            total_abstencoes=50000,
            resultado_nominal={"Candidato A": 50.0, "Candidato B": 20.0},
        )
