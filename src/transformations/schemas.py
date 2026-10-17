"""Contratos e esquemas de dados com Pydantic para validação estrita.

Este módulo define as estruturas de dados tipadas e validadas para pesquisas eleitorais,
resultados oficiais do TSE e taxonomias de metodologia.
"""

from datetime import date
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, model_validator


class MetodologiaEnum(str, Enum):
    """Classificação metodológica das pesquisas eleitorais."""

    PRESENCIAL_DOMICILIAR = "PRESENCIAL_DOMICILIAR"
    PRESENCIAL_FLUXO = "PRESENCIAL_FLUXO"
    TELEFONICA_CATI = "TELEFONICA_CATI"
    TELEFONICA_URA = "TELEFONICA_URA"
    ONLINE = "ONLINE"


class AbrangenciaEnum(str, Enum):
    """Classificação de abrangência geográfica das pesquisas eleitorais."""

    NACIONAL = "NACIONAL"
    REGIONAL = "REGIONAL"
    ESTADUAL = "ESTADUAL"


class PesquisaEleitoralSchema(BaseModel):
    """Contrato de dados para um levantamento de pesquisa eleitoral registrado.

    Attributes:
        id_registro_tse: Identificador único de registro no TSE (ex.: 'BR-01234/2026').
        instituto_razao_social: Razão social registrada do instituto responsável.
        instituto_nome_fantasia: Nome de exibição ou marca do instituto.
        data_inicio_campo: Data inicial de coleta dos dados em campo.
        data_fim_campo: Data final de coleta dos dados em campo.
        data_divulgacao: Data de publicação dos resultados.
        tamanho_amostra: Número de eleitores entrevistados (deve ser > 0).
        margem_erro_declarada: Margem máxima de erro em pontos percentuais declarada.
        nivel_confianca: Nível de confiança nominal declarado (default: 0.95).
        metodologia: Categoria metodológica da pesquisa.
        deff_estimado: Fator de efeito de delineamento amostral (default: 1.3).
        votos_totais: Mapeamento de candidato para percentual bruto de intenção de voto.
        votos_validos: Mapeamento de candidato para percentual recalculado de votos válidos.
        percentual_indecisos: Percentual de indecisos / não sabe / não respondeu.
        percentual_brancos_nulos: Percentual de brancos e nulos somados.
        turno: Turno da eleição auditada (1 ou 2).
        cargo: Cargo eletivo em disputa (padrão: 'PRESIDENTE').
        ano: Ano do ciclo eleitoral (padrão: 2026).
        abrangencia: Escopo geográfico da coleta (NACIONAL, REGIONAL ou ESTADUAL).
        uf: Sigla da Unidade da Federação ou recorte territorial (padrão: 'BR').
        regiao: Sigla da macrorregião geográfica correspondente (padrão: 'BR').
    """

    id_registro_tse: str = Field(..., pattern=r"^[A-Z]{2}-\d{5}/\d{4}$")
    instituto_razao_social: str
    instituto_nome_fantasia: str
    data_inicio_campo: date
    data_fim_campo: date
    data_divulgacao: date
    tamanho_amostra: int = Field(..., gt=0)
    margem_erro_declarada: float = Field(..., gt=0.0, le=10.0)
    nivel_confianca: float = Field(default=0.95, gt=0.8, lt=1.0)
    metodologia: MetodologiaEnum
    deff_estimado: float = Field(default=1.3, ge=1.0, le=3.0)
    votos_totais: dict[str, float]
    votos_validos: dict[str, float]
    percentual_indecisos: float = Field(..., ge=0.0, le=100.0)
    percentual_brancos_nulos: float = Field(..., ge=0.0, le=100.0)
    turno: int = Field(default=1, ge=1, le=2)
    cargo: str = Field(default="PRESIDENTE")
    ano: int = Field(default=2026)
    abrangencia: AbrangenciaEnum = Field(default=AbrangenciaEnum.NACIONAL)
    uf: str = Field(default="BR", min_length=2, max_length=5)
    regiao: str = Field(default="BR", min_length=1, max_length=5)

    @model_validator(mode="after")
    def validate_chronology(self) -> Self:
        """Valida se a cronologia de campo e divulgação é coerente.

        Args:
            self: A própria instância do modelo validado.

        Returns:
            Self: Instância validada do modelo.

        Raises:
            ValueError: Se data_fim_campo for anterior a data_inicio_campo
                ou data_divulgacao for anterior a data_fim_campo.
        """
        if self.data_fim_campo < self.data_inicio_campo:
            raise ValueError(
                f"Data final de campo ({self.data_fim_campo}) não pode ser anterior "
                f"à data de início ({self.data_inicio_campo})."
            )
        if self.data_divulgacao < self.data_fim_campo:
            raise ValueError(
                f"Data de divulgação ({self.data_divulgacao}) não pode ser anterior "
                f"à data final de campo ({self.data_fim_campo})."
            )
        return self


class ResultadoOficialTSESchema(BaseModel):
    """Contrato de dados para o resultado oficial totalizado das urnas pelo TSE.

    Attributes:
        cargo: Cargo eletivo correspondente (default: 'PRESIDENTE').
        turno: Turno da eleição apurada (1 ou 2).
        ano: Ano do ciclo eleitoral (default: 2026).
        total_votos_validos: Total absoluto de votos válidos nominais e de legenda.
        total_brancos: Total absoluto de votos em branco.
        total_nulos: Total absoluto de votos nulos.
        total_abstencoes: Total absoluto de eleitores ausentes.
        resultado_nominal: Mapeamento de candidato para percentual oficial de votos válidos.
    """

    cargo: str = "PRESIDENTE"
    turno: int = Field(..., ge=1, le=2)
    ano: int = 2026
    total_votos_validos: int = Field(..., ge=0)
    total_brancos: int = Field(..., ge=0)
    total_nulos: int = Field(..., ge=0)
    total_abstencoes: int = Field(..., ge=0)
    resultado_nominal: dict[str, float]

    @model_validator(mode="after")
    def validate_percentages(self) -> Self:
        """Valida se a soma dos percentuais oficiais de votos válidos converge para 100%.

        Args:
            self: A própria instância do modelo validado.

        Returns:
            Self: Instância validada do modelo.

        Raises:
            ValueError: Se a soma dos percentuais nominais divergir de 100%.
        """
        soma = sum(self.resultado_nominal.values())
        if not (99.8 <= soma <= 100.2):
            raise ValueError(
                f"A soma dos percentuais nominais deve ser aproximadamente 100.0%, "
                f"mas resultou em {soma:.2f}%."
            )
        return self
