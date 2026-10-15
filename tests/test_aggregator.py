"""Testes unitários para o modelo de agregação dinâmica e bandas de incerteza."""

from datetime import date, timedelta

import pytest

from src.analytics.aggregator_model import (
    calculate_poll_weight,
    calculate_temporal_weight,
    compute_poll_aggregation_series,
)
from src.transformations.schemas import PesquisaEleitoralSchema


def test_calculate_temporal_weight() -> None:
    """Verifica o decaimento exponencial temporal com meia-vida de 14 dias."""
    ref_date = date(2026, 10, 4)

    # No mesmo dia: peso deve ser exatamente 1.0
    w_same = calculate_temporal_weight(ref_date, ref_date, half_life_days=14.0)
    assert w_same == 1.0

    # 14 dias antes: peso deve ser exatamente 0.5
    w_14d = calculate_temporal_weight(ref_date - timedelta(days=14), ref_date, half_life_days=14.0)
    assert pytest.approx(w_14d, rel=1e-3) == 0.5

    # 28 dias antes (2 meias-vidas): peso deve ser 0.25
    w_28d = calculate_temporal_weight(ref_date - timedelta(days=28), ref_date, half_life_days=14.0)
    assert pytest.approx(w_28d, rel=1e-3) == 0.25

    # Data futura em relação à referência: peso zero
    w_fut = calculate_temporal_weight(ref_date + timedelta(days=2), ref_date, half_life_days=14.0)
    assert w_fut == 0.0


def test_calculate_poll_weight(sample_eve_polls_2026: list[PesquisaEleitoralSchema]) -> None:
    """Verifica que o peso total cresce com a raiz da amostra e proximidade temporal."""
    polls = sample_eve_polls_2026
    ref_date = date(2026, 10, 4)

    p1 = polls[0]
    weight = calculate_poll_weight(p1, ref_date)
    assert weight > 0.0


def test_compute_poll_aggregation_series(
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
) -> None:
    """Verifica a geração da série contínua agregada e consistência dos intervalos."""
    polls = sample_eve_polls_2026
    candidates = ["Lula", "Flávio Bolsonaro"]

    df_agg = compute_poll_aggregation_series(
        polls=polls,
        candidates=candidates,
        start_date=date(2026, 9, 28),
        end_date=date(2026, 10, 2),
    )

    assert df_agg.height > 0
    assert "data" in df_agg.columns
    assert "media_ponderada" in df_agg.columns
    assert "ic_80_inf" in df_agg.columns
    assert "ic_95_inf" in df_agg.columns

    # Testa consistência lógica dos envelopes
    for row in df_agg.iter_rows(named=True):
        med = row["media_ponderada"]
        ic80_inf = row["ic_80_inf"]
        ic80_sup = row["ic_80_sup"]
        ic95_inf = row["ic_95_inf"]
        ic95_sup = row["ic_95_sup"]

        assert ic95_inf <= ic80_inf <= med <= ic80_sup <= ic95_sup
