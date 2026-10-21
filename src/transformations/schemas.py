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


class TierFonteEnum(str, Enum):
    """Classificação hierárquica da fonte de dados da pesquisa eleitoral.

    Define os níveis de autoridade e confiabilidade da informação coletada:
    - TIER_1_OFICIAL_TSE: Metadados e relatórios do Portal de Dados Abertos ou PesqEle do TSE.
    - TIER_1_RELATORIO_INSTITUTO: Relatório técnico oficial em PDF emitido diretamente pelo instituto.
    - TIER_2_CONTRATANTE_ORIGINAL: Matéria jornalística do veículo contratante formal da pesquisa.
    - TIER_3_AGREGADOR_PUBLICO: Base aberta consolidada (ex.: Repositório Poder360, FGV CEPESP).
    - TIER_4_IMPRENSA_SECUNDARIA: Repercussão geral (utilizado apenas para alerta/descoberta).
    """

    TIER_1_OFICIAL_TSE = "TIER_1_OFICIAL_TSE"
    TIER_1_RELATORIO_INSTITUTO = "TIER_1_RELATORIO_INSTITUTO"
    TIER_2_CONTRATANTE_ORIGINAL = "TIER_2_CONTRATANTE_ORIGINAL"
    TIER_3_AGREGADOR_PUBLICO = "TIER_3_AGREGADOR_PUBLICO"
    TIER_4_IMPRENSA_SECUNDARIA = "TIER_4_IMPRENSA_SECUNDARIA"


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
        rejeicao: Mapeamento opcional de candidato para percentual de rejeição ("não votaria de jeito nenhum").
        turno: Turno da eleição auditada (1 ou 2).
        cargo: Cargo eletivo em disputa (padrão: 'PRESIDENTE').
        ano: Ano do ciclo eleitoral (padrão: 2026).
        abrangencia: Escopo geográfico da coleta (NACIONAL, REGIONAL ou ESTADUAL).
        uf: Sigla da Unidade da Federação ou recorte territorial (padrão: 'BR').
        regiao: Sigla da macrorregião geográfica correspondente (padrão: 'BR').
        tier_fonte: Nível hierárquico de autoridade da fonte primária do resultado.
        url_fonte_publicacao: Link público para a publicação oficial na imprensa ou relatório.
        url_tse_pesqele: Link direto da consulta pública do registro no portal PesqEle do TSE.
        verificado_tse: Indicador booleano de confirmação cruzada com o censo oficial do TSE.
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
    rejeicao: dict[str, float] | None = Field(
        default=None,
        description="Mapeamento de candidato para percentual de rejeição declarada",
    )
    turno: int = Field(default=1, ge=1, le=2)
    cargo: str = Field(default="PRESIDENTE")
    ano: int = Field(default=2026)
    abrangencia: AbrangenciaEnum = Field(default=AbrangenciaEnum.NACIONAL)
    uf: str = Field(default="BR", min_length=2, max_length=5)
    regiao: str = Field(default="BR", min_length=1, max_length=5)
    tier_fonte: TierFonteEnum = Field(
        default=TierFonteEnum.TIER_2_CONTRATANTE_ORIGINAL,
        description="Nível hierárquico da autoridade da fonte",
    )
    url_fonte_publicacao: str | None = Field(
        default=None,
        description="Link da matéria de divulgação original ou relatório técnico",
    )
    url_tse_pesqele: str | None = Field(
        default=None,
        description="Link da consulta pública de registro no TSE",
    )
    verificado_tse: bool = Field(
        default=True,
        description="Flag indicando conformidade cadastral estrita com o TSE",
    )

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
    apuracao_concluida: bool = True

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
        if not self.apuracao_concluida:
            return self
        soma = sum(self.resultado_nominal.values())
        if not (99.8 <= soma <= 100.2):
            raise ValueError(
                f"A soma dos percentuais nominais deve ser aproximadamente 100.0%, "
                f"mas resultou em {soma:.2f}%."
            )
        return self


class RejeicaoPesquisaSchema(BaseModel):
    """Contrato de dados para levantamentos de rejeição de candidatos.

    Attributes:
        instituto: Nome de exibição ou marca do instituto.
        data_inicio_campo: Data inicial de coleta em campo.
        data_fim_campo: Data final de coleta em campo.
        data_divulgacao: Data de publicação dos dados.
        rejeicao_nominal: Mapeamento de candidato para percentual de rejeição declarada.
        turno: Turno eleitoral analisado (1 ou 2).
        ano: Ano do ciclo eleitoral (padrão: 2026).
        tamanho_amostra: Número de eleitores entrevistados.
        margem_erro: Margem de erro declarada em pontos percentuais.
        observacao: Ressalva ou anotação metodológica específica.
        onda_anterior: Flag indicando se utilizou onda anterior por ausência de rejeição na véspera.
    """

    instituto: str
    data_inicio_campo: date
    data_fim_campo: date
    data_divulgacao: date
    rejeicao_nominal: dict[str, float]
    turno: int = Field(default=1, ge=1, le=2)
    ano: int = Field(default=2026)
    tamanho_amostra: int | None = Field(default=None, gt=0)
    margem_erro: float | None = Field(default=None, gt=0.0)
    observacao: str | None = None
    onda_anterior: bool = False

