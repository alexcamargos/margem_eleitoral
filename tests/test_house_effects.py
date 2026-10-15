"""Testes unitários para o modelo de decomposição de House Effects."""

from src.analytics.house_effects import (
    compute_campaign_house_effects,
    fit_house_effects_model,
)
from src.ingestion.pesqele_collector import PesqEleCollector
from src.transformations.schemas import PesquisaEleitoralSchema


def test_fit_house_effects_model_eve_polls(
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
) -> None:
    """Verifica que o modelo lida de forma segura com amostras de véspera."""
    df = PesqEleCollector.polls_to_polars(sample_eve_polls_2026)

    res = fit_house_effects_model(df, target_candidate="Lula", p_true=45.16)

    assert "r_squared" in res
    assert "institute_effects" in res
    assert "methodology_effects" in res
    assert "p_val_institutes_anova" in res
    assert "p_val_methodology_anova" in res
    assert 0.0 <= res["r_squared"] <= 1.0


def test_fit_house_effects_model_multi_wave(
    sample_historical_campaign_polls_2026: list[PesquisaEleitoralSchema],
) -> None:
    """Verifica o modelo com múltiplas ondas históricas com graus de liberdade suficientes."""
    df = PesqEleCollector.polls_to_polars(sample_historical_campaign_polls_2026)

    res = fit_house_effects_model(df, target_candidate="Lula", p_true=45.16)

    assert res["r_squared"] >= 0.0
    assert len(res["institute_effects"]) > 0 or len(res["methodology_effects"]) > 0


def test_compute_campaign_house_effects_multi_wave(
    sample_historical_campaign_polls_2026: list[PesquisaEleitoralSchema],
) -> None:
    """Verifica o cálculo de inclinação longitudinal ao longo de ondas de campanha."""
    res = compute_campaign_house_effects(
        polls=sample_historical_campaign_polls_2026,
        candidate_1="Flávio Bolsonaro",
        candidate_2="Lula",
        window_days=7,
        min_peer_institutes=2,
        min_comparable_polls=2,
        confidence_level=0.80,
    )

    assert res["candidate_1"] == "Flávio Bolsonaro"
    assert res["candidate_2"] == "Lula"
    assert "institutes" in res
    assert "excluded_institutes" in res
    assert res["total_comparable_polls"] > 0

    institutes = res["institutes"]
    assert len(institutes) > 0

    # Verifica ordenação por mean_tilt crescente
    means = [inst["mean_tilt"] for inst in institutes]
    assert means == sorted(means)

    for inst in institutes:
        assert "instituto" in inst
        assert "mean_tilt" in inst
        assert "ci_lower" in inst
        assert "ci_upper" in inst
        assert inst["ci_lower"] <= inst["mean_tilt"] <= inst["ci_upper"]
        assert isinstance(inst["includes_zero"], bool)
        assert inst["n_polls"] >= 2
        assert len(inst["points"]) == inst["n_polls"]


def test_compute_campaign_house_effects_missing_candidate(
    sample_historical_campaign_polls_2026: list[PesquisaEleitoralSchema],
) -> None:
    """Verifica que ValueError é lançado caso os candidatos informados não existam."""
    import pytest

    with pytest.raises(ValueError, match="Nenhuma pesquisa encontrada"):
        compute_campaign_house_effects(
            polls=sample_historical_campaign_polls_2026,
            candidate_1="Candidato Inexistente A",
            candidate_2="Candidato Inexistente B",
        )
