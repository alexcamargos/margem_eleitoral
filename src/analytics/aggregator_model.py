"""Modelo contínuo de agregação temporal e envelopes de credibilidade para pesquisas eleitorais.

Implementa a média ponderada dinâmica com decaimento exponencial (meia-vida de 14 dias),
ponderação por tamanho de amostra e qualidade metodológica, e cálculo de fitas de
incerteza estatística (80% e 95%).
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Sequence

import numpy as np
import polars as pl

from src.transformations.schemas import MetodologiaEnum, PesquisaEleitoralSchema


def calculate_temporal_weight(
    poll_date: date,
    reference_date: date,
    half_life_days: float = 14.0,
) -> float:
    """Calcula o peso exponencial temporal de uma pesquisa em relação a uma data de referência.

    w_tempo(t) = exp( - (ln(2) / meia_vida) * (t_ref - t_poll) )
    Se a pesquisa for futura em relação à data de referência (dias < 0), o peso é 0.0.

    Args:
        poll_date: Data de término de campo da pesquisa.
        reference_date: Data de referência para cálculo do agregador.
        half_life_days: Número de dias para o peso decair à metade (default: 14.0).

    Returns:
        float: Fator de decaimento temporal no intervalo [0.0, 1.0].

    Raises:
        ValueError: Se half_life_days for menor ou igual a zero.
    """
    if half_life_days <= 0.0:
        raise ValueError("A meia-vida em dias deve ser estritamente positiva.")

    days_diff = (reference_date - poll_date).days
    if days_diff < 0:
        return 0.0

    decay_constant = math.log(2.0) / half_life_days
    return float(math.exp(-decay_constant * days_diff))


def get_methodology_quality_weight(metodologia: MetodologiaEnum | str) -> float:
    """Retorna o peso empírico de calibração qualitativa por tipo de metodologia.

    Args:
        metodologia: Metodologia da pesquisa (MetodologiaEnum ou string).

    Returns:
        float: Fator multiplicativo de qualidade.

    Raises:
        None.
    """
    val = metodologia.value if isinstance(metodologia, MetodologiaEnum) else str(metodologia)
    weights = {
        "PRESENCIAL_DOMICILIAR": 1.10,
        "ONLINE": 1.05,
        "TELEFONICA_CATI": 1.00,
        "PRESENCIAL_FLUXO": 0.90,
        "TELEFONICA_URA": 0.85,
    }
    return weights.get(val, 1.0)


def calculate_poll_weight(
    poll: PesquisaEleitoralSchema,
    reference_date: date,
    half_life_days: float = 14.0,
) -> float:
    """Calcula o peso total da pesquisa Wi = w_tempo * w_qualidade * sqrt(n).

    Args:
        poll: Instância de PesquisaEleitoralSchema.
        reference_date: Data para o cálculo do peso temporal.
        half_life_days: Meia-vida em dias do decaimento temporal.

    Returns:
        float: Peso escalar não-negativo.

    Raises:
        None.
    """
    w_time = calculate_temporal_weight(poll.data_fim_campo, reference_date, half_life_days)
    if w_time <= 0.0:
        return 0.0

    w_qual = get_methodology_quality_weight(poll.metodologia)
    w_sample = math.sqrt(poll.tamanho_amostra)

    return float(w_time * w_qual * w_sample)


def compute_poll_aggregation_series(
    polls: Sequence[PesquisaEleitoralSchema],
    candidates: Sequence[str],
    start_date: date | None = None,
    end_date: date | None = None,
    half_life_days: float = 14.0,
    deff: float = 1.3,
    use_valid_votes: bool = True,
) -> pl.DataFrame:
    """Gera a série temporal diária agregada com média ponderada e bandas de incerteza.

    Para cada data t no intervalo, calcula a estimativa latente do eleitorado
    e os intervalos de credibilidade de 80% e 95%.

    Args:
        polls: Lista de pesquisas registradas.
        candidates: Nomes dos candidatos a incluir no agregador.
        start_date: Data de início da série (se None, usa a menor data de campo).
        end_date: Data final da série (se None, usa a maior data de campo).
        half_life_days: Meia-vida em dias para decaimento exponencial (default: 14.0).
        deff: Efeito de delineamento aplicado na variância residual (default: 1.3).
        use_valid_votes: Se True usa votos_validos; se False usa votos_totais (default: True).

    Returns:
        pl.DataFrame: DataFrame com colunas:
            ['data', 'candidato', 'media_ponderada', 'ic_80_inf', 'ic_80_sup',
             'ic_95_inf', 'ic_95_sup', 'peso_total_amostras']

    Raises:
        None.
    """
    if not polls:
        return pl.DataFrame()

    min_date = min(p.data_fim_campo for p in polls) if start_date is None else start_date
    max_date = max(p.data_fim_campo for p in polls) if end_date is None else end_date

    z_80 = 1.28155
    z_95 = 1.95996

    rows: list[dict[str, Any]] = []
    current_date = min_date

    while current_date <= max_date:
        # Pesquisas disponíveis até a data corrente
        available_polls = [p for p in polls if p.data_fim_campo <= current_date]

        if available_polls:
            weights = np.array(
                [calculate_poll_weight(p, current_date, half_life_days) for p in available_polls]
            )
            total_weight = float(np.sum(weights))

            if total_weight > 0.0:
                normalized_weights = weights / total_weight

                for cand in candidates:
                    estimates = np.array(
                        [
                            (p.votos_validos if use_valid_votes else p.votos_totais).get(cand, 0.0)
                            for p in available_polls
                        ]
                    )
                    media_pond = float(np.sum(normalized_weights * estimates))

                    # Variância ponderada observada entre as pesquisas
                    var_between = float(
                        np.sum(normalized_weights * ((estimates - media_pond) ** 2))
                    )

                    # Amostra efetiva acumulada
                    n_eff = total_weight**2 / float(np.sum(weights**2))
                    var_sampling = deff * (media_pond * (100.0 - media_pond)) / max(100.0, n_eff)

                    se_total = math.sqrt(max(0.25, var_between + var_sampling))

                    rows.append(
                        {
                            "data": current_date,
                            "candidato": cand,
                            "media_ponderada": round(media_pond, 2),
                            "ic_80_inf": max(0.0, round(media_pond - z_80 * se_total, 2)),
                            "ic_80_sup": min(100.0, round(media_pond + z_80 * se_total, 2)),
                            "ic_95_inf": max(0.0, round(media_pond - z_95 * se_total, 2)),
                            "ic_95_sup": min(100.0, round(media_pond + z_95 * se_total, 2)),
                            "peso_total": round(total_weight, 2),
                        }
                    )

        current_date += timedelta(days=1)

    return pl.DataFrame(rows)


@dataclass(frozen=True)
class CandidatePhaseEstimate:
    """Estimativa agregada de um candidato em uma fase eleitoral específica.

    Args:
        candidato: Nome do candidato avaliado.
        media_ponderada: Percentual ponderado representativo no fechamento da fase.
        ic_95_inf: Limite inferior do envelope de credibilidade de 95%.
        ic_95_sup: Limite superior do envelope de credibilidade de 95%.
        media_periodo: Média simples da série diária agregada no período da fase.
        delta_anterior: Variação em pontos percentuais em relação à fase anterior.

    Returns:
        None.

    Raises:
        None.
    """

    candidato: str
    media_ponderada: float
    ic_95_inf: float
    ic_95_sup: float
    media_periodo: float
    delta_anterior: float | None = None


@dataclass(frozen=True)
class PhaseAggregationSummary:
    """Sumário analítico e amostral de uma fase eleitoral.

    Args:
        nome_fase: Nome de exibição da fase (ex.: 'Ciclo Completo (Jul-Out)', '1ª Semana').
        rotulo_curto: Rótulo conciso para eixos e badges (ex.: 'Ciclo Completo', '1ª Semana').
        icone: Emoji ou ícone representativo da fase.
        descricao_periodo: Texto descritivo do intervalo de datas.
        data_inicio: Data inicial da fase.
        data_fim: Data final da fase.
        dias_duracao: Quantidade de dias cobertos pela fase.
        total_pesquisas: Quantidade total de pesquisas nesta fase.
        pesquisas_por_dia: Densidade média de pesquisas por dia.
        percentual_total_pesquisas: Percentual das pesquisas da base nesta fase.
        estimativas: Dicionário mapeando nome do candidato a CandidatePhaseEstimate.
        lider: Nome do candidato com maior estimativa nesta fase.
        vice: Nome do candidato em segundo lugar.
        margem_lider_vice: Diferença em pontos percentuais entre líder e vice.

    Returns:
        None.

    Raises:
        None.
    """

    nome_fase: str
    rotulo_curto: str
    icone: str
    descricao_periodo: str
    data_inicio: date
    data_fim: date
    dias_duracao: int
    total_pesquisas: int
    pesquisas_por_dia: float
    percentual_total_pesquisas: float
    estimativas: dict[str, CandidatePhaseEstimate]
    lider: str | None = None
    vice: str | None = None
    margem_lider_vice: float | None = None


def compute_phase_aggregation_metrics(
    polls: Sequence[PesquisaEleitoralSchema],
    candidates: Sequence[str],
    ano_pleito: int = 2026,
    turno: int = 1,
    election_date: date | None = None,
    use_valid_votes: bool = True,
    half_life_days: float = 14.0,
    deff: float = 1.3,
) -> list[PhaseAggregationSummary]:
    """Calcula o sumário amostral e as estimativas agregadas nas 3 fases do processo eleitoral.

    No 1º Turno, estrutura os 3 horizontes consolidados da eleição:
    1. Ciclo Completo (Jul-Out): Visão macro longitudinal desde a pré-campanha.
    2. Campanha Oficial (Ago-Out): A partir do início legal da campanha (16/Ago).
    3. Reta Final (14 dias): Período crítico de cristalização do voto.

    No 2º Turno, adapta a análise para a divisão semanal em 3 fases:
    1. 1ª Semana (Arranjos & Alianças): Rearticulação política pós-1º turno.
    2. 2ª Semana (Horário Eleitoral & Debates): Propaganda televisiva e confrontos diretos.
    3. 3ª Semana (Reta Final): Mobilização decisiva e véspera das urnas.

    Args:
        polls: Lista das pesquisas eleitorais registradas.
        candidates: Candidatos selecionados para acompanhamento.
        ano_pleito: Ano do pleito eleitoral (default: 2026).
        turno: Turno da eleição (1 ou 2, default: 1).
        election_date: Data oficial do pleito (opcional, calculada se None).
        use_valid_votes: Se True utiliza votos válidos; se False votos totais (default: True).
        half_life_days: Meia-vida em dias para decaimento exponencial temporal (default: 14.0).
        deff: Efeito de delineamento aplicado na variância residual (default: 1.3).

    Returns:
        list[PhaseAggregationSummary]: Lista com 3 sumários analíticos correspondentes às fases.

    Raises:
        None.
    """
    if not polls:
        hoje = date(ano_pleito, 10, 1)
        fases_vazias = (
            [
                ("Ciclo Completo (Jul-Out)", "Ciclo Completo", ""),
                ("Campanha Oficial (Ago-Out)", "Campanha Oficial", ""),
                ("Reta Final (14 dias)", "Reta Final", ""),
            ]
            if turno == 1
            else [
                ("1ª Semana (Arranjos & Alianças)", "1ª Semana", ""),
                ("2ª Semana (Horário Eleitoral & Debates)", "2ª Semana", ""),
                ("3ª Semana (Reta Final)", "3ª Semana", ""),
            ]
        )
        return [
            PhaseAggregationSummary(
                nome_fase=nome,
                rotulo_curto=rotulo,
                icone=ico,
                descricao_periodo="Sem dados",
                data_inicio=hoje,
                data_fim=hoje,
                dias_duracao=1,
                total_pesquisas=0,
                pesquisas_por_dia=0.0,
                percentual_total_pesquisas=0.0,
                estimativas={},
                lider=None,
                vice=None,
                margem_lider_vice=None,
            )
            for nome, rotulo, ico in fases_vazias
        ]

    min_date = min(p.data_fim_campo for p in polls)
    max_date = max(p.data_fim_campo for p in polls)
    total_polls_base = len(polls)

    phases_definition: list[tuple[str, str, str, date, date, list[PesquisaEleitoralSchema]]] = []

    if turno == 1:
        corte_campanha = date(ano_pleito, 8, 16)
        corte_reta_final = max_date - timedelta(days=14)

        p_ciclo = list(polls)
        p_campanha = [p for p in polls if p.data_fim_campo >= corte_campanha]
        p_reta_final = [p for p in polls if p.data_fim_campo >= corte_reta_final]

        d_ini_campanha = corte_campanha if min_date < corte_campanha else min_date
        d_ini_reta_final = corte_reta_final if corte_reta_final > min_date else min_date

        phases_definition = [
            (
                "Ciclo Completo (Jul-Out)",
                "Ciclo Completo",
                "",
                min_date,
                max_date,
                p_ciclo,
            ),
            (
                "Campanha Oficial (Ago-Out)",
                "Campanha Oficial",
                "",
                d_ini_campanha,
                max_date,
                p_campanha,
            ),
            (
                "Reta Final (14 dias)",
                "Reta Final",
                "",
                d_ini_reta_final,
                max_date,
                p_reta_final,
            ),
        ]
    else:
        # 2º Turno: Divisão célere de 3 semanas (3 fases)
        if ano_pleito == 2026:
            t1_date = date(2026, 10, 4)
            t2_date = election_date or date(2026, 10, 25)
        elif ano_pleito == 2022:
            t1_date = date(2022, 10, 2)
            t2_date = election_date or date(2022, 10, 30)
        else:
            t1_date = min_date - timedelta(days=1)
            t2_date = election_date or max_date

        w1_start = t1_date + timedelta(days=1)
        w1_end = w1_start + timedelta(days=6)
        w2_start = w1_end + timedelta(days=1)
        w2_end = w2_start + timedelta(days=6)
        w3_start = w2_end + timedelta(days=1)
        w3_end = max(t2_date, max_date)

        p_w1 = [p for p in polls if w1_start <= p.data_fim_campo <= w1_end]
        p_w2 = [p for p in polls if w2_start <= p.data_fim_campo <= w2_end]
        p_w3 = [p for p in polls if w3_start <= p.data_fim_campo <= w3_end]

        phases_definition = [
            (
                "1ª Semana (Arranjos & Alianças)",
                "1ª Semana",
                "",
                w1_start,
                w1_end,
                p_w1,
            ),
            (
                "2ª Semana (Horário Eleitoral & Debates)",
                "2ª Semana",
                "",
                w2_start,
                w2_end,
                p_w2,
            ),
            (
                "3ª Semana (Reta Final)",
                "3ª Semana",
                "",
                w3_start,
                w3_end,
                p_w3,
            ),
        ]

    summaries: list[PhaseAggregationSummary] = []
    prev_estimates: dict[str, CandidatePhaseEstimate] = {}

    for nome_fase, rotulo_curto, icone, dt_ini, dt_fim, phase_polls in phases_definition:
        dias_duracao = max(1, (dt_fim - dt_ini).days + 1)
        n_pesquisas = len(phase_polls)
        pesq_dia = round(n_pesquisas / dias_duracao, 2)
        pct_base = (
            round((n_pesquisas / total_polls_base) * 100.0, 1) if total_polls_base > 0 else 0.0
        )
        desc_periodo = f"{dt_ini.strftime('%d/%m')} a {dt_fim.strftime('%d/%m')}"

        estimates: dict[str, CandidatePhaseEstimate] = {}

        if n_pesquisas > 0 and candidates:
            df_phase = compute_poll_aggregation_series(
                polls=phase_polls,
                candidates=candidates,
                half_life_days=half_life_days,
                deff=deff,
                use_valid_votes=use_valid_votes,
            )

            if df_phase.height > 0:
                for cand in candidates:
                    sub = df_phase.filter(pl.col("candidato") == cand)
                    if sub.height > 0:
                        last_row = sub.sort("data", descending=True)[0]
                        media_pond = float(last_row["media_ponderada"][0])
                        ic_inf = float(last_row["ic_95_inf"][0])
                        ic_sup = float(last_row["ic_95_sup"][0])
                        media_periodo = round(float(sub["media_ponderada"].mean()), 2)

                        delta: float | None = None
                        if cand in prev_estimates:
                            delta = round(media_pond - prev_estimates[cand].media_ponderada, 2)

                        estimates[cand] = CandidatePhaseEstimate(
                            candidato=cand,
                            media_ponderada=media_pond,
                            ic_95_inf=ic_inf,
                            ic_95_sup=ic_sup,
                            media_periodo=media_periodo,
                            delta_anterior=delta,
                        )

        # Determina líder e vice na fase
        sorted_cands = sorted(
            estimates.keys(), key=lambda c: estimates[c].media_ponderada, reverse=True
        )
        lider = sorted_cands[0] if sorted_cands else None
        vice = sorted_cands[1] if len(sorted_cands) > 1 else None
        margem: float | None = None
        if lider and vice:
            margem = round(estimates[lider].media_ponderada - estimates[vice].media_ponderada, 2)

        summary = PhaseAggregationSummary(
            nome_fase=nome_fase,
            rotulo_curto=rotulo_curto,
            icone=icone,
            descricao_periodo=desc_periodo,
            data_inicio=dt_ini,
            data_fim=dt_fim,
            dias_duracao=dias_duracao,
            total_pesquisas=n_pesquisas,
            pesquisas_por_dia=pesq_dia,
            percentual_total_pesquisas=pct_base,
            estimativas=estimates,
            lider=lider,
            vice=vice,
            margem_lider_vice=margem,
        )
        summaries.append(summary)

        # Atualiza estimativas anteriores para delta apenas se esta fase possui dados válidos
        if estimates:
            prev_estimates = estimates

    return summaries
