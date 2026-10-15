"""Modelo contínuo de agregação temporal e envelopes de credibilidade para pesquisas eleitorais.

Implementa a média ponderada dinâmica com decaimento exponencial (meia-vida de 14 dias),
ponderação por tamanho de amostra e qualidade metodológica, e cálculo de fitas de
incerteza estatística (80% e 95%).
"""

import math
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
