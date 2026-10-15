"""Fixtures compartilhadas para a suíte de testes unitários do margem_eleitoral.

Fornece dados canônicos em memória para validação dos módulos analíticos,
componentes visuais e Atos de storytelling sem dependência de chamadas externas de rede.
"""

from datetime import date, timedelta

import pytest

from src.transformations.schemas import (
    MetodologiaEnum,
    PesquisaEleitoralSchema,
    ResultadoOficialTSESchema,
)
from src.transformations.valid_votes import calculate_valid_votes


@pytest.fixture
def sample_tse_result_2026() -> ResultadoOficialTSESchema:
    """Fixture que fornece a apuração oficial do TSE no 1º Turno de 2026.

    Returns:
        ResultadoOficialTSESchema: Objeto tipado com a totalização oficial.
    """
    return ResultadoOficialTSESchema(
        cargo="PRESIDENTE",
        turno=1,
        ano=2026,
        total_votos_validos=119300788,
        total_brancos=2300798,
        total_nulos=3674249,
        total_abstencoes=33469244,
        resultado_nominal={
            "Flávio Bolsonaro": 47.03,
            "Lula": 45.16,
            "Augusto Cury": 2.89,
            "Renan Santos": 2.24,
            "Ronaldo Caiado": 2.18,
            "Romeu Zema": 0.27,
            "Outros": 0.23,
        },
    )


@pytest.fixture
def sample_eve_polls_2026() -> list[PesquisaEleitoralSchema]:
    """Fixture que fornece pesquisas de véspera calibradas para o 1º Turno de 2026.

    Returns:
        list[PesquisaEleitoralSchema]: Lista de pesquisas no critério de véspera (<= 72h).
    """
    institutes = [
        ("Datafolha", MetodologiaEnum.PRESENCIAL_DOMICILIAR, 1.40, 12800, 43.0, 44.0),
        ("Quaest", MetodologiaEnum.PRESENCIAL_DOMICILIAR, 1.35, 4000, 43.5, 43.0),
        ("AtlasIntel", MetodologiaEnum.ONLINE, 1.40, 4500, 45.5, 43.5),
        ("Paraná Pesquisas", MetodologiaEnum.PRESENCIAL_DOMICILIAR, 1.35, 2020, 44.5, 40.5),
        ("PoderData", MetodologiaEnum.TELEFONICA_URA, 1.30, 3000, 44.0, 41.5),
        ("Real Time Big Data", MetodologiaEnum.TELEFONICA_CATI, 1.30, 3000, 44.5, 42.0),
        ("Futura", MetodologiaEnum.TELEFONICA_CATI, 1.25, 2000, 44.5, 39.0),
        ("DataTrends", MetodologiaEnum.TELEFONICA_CATI, 1.30, 2000, 44.0, 41.0),
        ("Gerp", MetodologiaEnum.TELEFONICA_CATI, 1.30, 2095, 43.0, 39.5),
        ("Vox Brasil", MetodologiaEnum.TELEFONICA_CATI, 1.30, 2000, 45.0, 40.0),
        ("MDA", MetodologiaEnum.PRESENCIAL_DOMICILIAR, 1.35, 2002, 44.0, 41.5),
        ("Delta", MetodologiaEnum.PRESENCIAL_DOMICILIAR, 1.35, 2000, 43.5, 41.0),
        ("França", MetodologiaEnum.TELEFONICA_CATI, 1.30, 1500, 44.0, 40.0),
        ("Nexus", MetodologiaEnum.TELEFONICA_CATI, 1.30, 2000, 44.0, 41.5),
        ("Polaris", MetodologiaEnum.ONLINE, 1.35, 2000, 44.5, 42.0),
    ]

    polls: list[PesquisaEleitoralSchema] = []
    for idx, (inst, method, deff, n, fb_raw, lula_raw) in enumerate(institutes, start=1):
        totais = {
            "Flávio Bolsonaro": fb_raw,
            "Lula": lula_raw,
            "Augusto Cury": 2.8,
            "Renan Santos": 2.2,
            "Ronaldo Caiado": 2.0,
            "Romeu Zema": 0.5,
            "Outros": 0.5,
        }
        bn = 4.0
        ind = 3.0
        validos = calculate_valid_votes(totais, bn, ind)

        schema = PesquisaEleitoralSchema(
            id_registro_tse=f"BR-{1000 + idx:05d}/2026",
            instituto_razao_social=f"{inst.upper()} PESQUISAS LTDA",
            instituto_nome_fantasia=inst,
            data_inicio_campo=date(2026, 9, 29),
            data_fim_campo=date(2026, 10, 2),
            data_divulgacao=date(2026, 10, 3),
            tamanho_amostra=n,
            margem_erro_declarada=2.2,
            nivel_confianca=0.95,
            metodologia=method,
            deff_estimado=deff,
            votos_totais=totais,
            votos_validos=validos,
            percentual_indecisos=ind,
            percentual_brancos_nulos=bn,
            turno=1,
            cargo="PRESIDENTE",
            ano=2026,
        )
        polls.append(schema)

    return polls


@pytest.fixture
def sample_historical_campaign_polls_2026() -> list[PesquisaEleitoralSchema]:
    """Fixture que fornece levantamentos longitudinais ao longo da campanha de 2026.

    Returns:
        list[PesquisaEleitoralSchema]: Lista de pesquisas distribuídas entre julho e setembro.
    """
    institutes = [
        ("Datafolha", MetodologiaEnum.PRESENCIAL_DOMICILIAR, 1.35, 2800),
        ("Quaest", MetodologiaEnum.PRESENCIAL_DOMICILIAR, 1.35, 2200),
        ("AtlasIntel", MetodologiaEnum.ONLINE, 1.40, 3200),
        ("Paraná Pesquisas", MetodologiaEnum.PRESENCIAL_DOMICILIAR, 1.35, 2020),
        ("PoderData", MetodologiaEnum.TELEFONICA_URA, 1.30, 2500),
        ("Real Time Big Data", MetodologiaEnum.TELEFONICA_CATI, 1.30, 2200),
        ("Futura", MetodologiaEnum.TELEFONICA_CATI, 1.25, 2000),
    ]

    polls: list[PesquisaEleitoralSchema] = []
    base_date = date(2026, 7, 15)

    for inst_idx, (inst, method, deff, n) in enumerate(institutes):
        for wave in range(4):
            f_start = base_date + timedelta(days=wave * 18 + inst_idx)
            f_end = f_start + timedelta(days=2)
            pub = f_end + timedelta(days=1)

            fb_base = 38.0 + (wave * 2.0)
            lula_base = 43.5 + (wave * 0.3)

            totais = {
                "Flávio Bolsonaro": round(fb_base, 1),
                "Lula": round(lula_base, 1),
                "Augusto Cury": 3.0,
                "Renan Santos": 2.5,
                "Ronaldo Caiado": 2.5,
                "Romeu Zema": 0.8,
                "Outros": 0.7,
            }
            bn = 4.0
            ind = 3.5
            validos = calculate_valid_votes(totais, bn, ind)

            schema = PesquisaEleitoralSchema(
                id_registro_tse=f"BR-{2000 + inst_idx * 10 + wave:05d}/2026",
                instituto_razao_social=f"{inst.upper()} PESQUISAS LTDA",
                instituto_nome_fantasia=inst,
                data_inicio_campo=f_start,
                data_fim_campo=f_end,
                data_divulgacao=pub,
                tamanho_amostra=n,
                margem_erro_declarada=2.2,
                nivel_confianca=0.95,
                metodologia=method,
                deff_estimado=deff,
                votos_totais=totais,
                votos_validos=validos,
                percentual_indecisos=ind,
                percentual_brancos_nulos=bn,
                turno=1,
                cargo="PRESIDENTE",
                ano=2026,
            )
            polls.append(schema)

    return polls
