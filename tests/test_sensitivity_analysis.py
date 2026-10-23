"""Testes unitários e de invariantes para o módulo de Análise de Sensibilidade e Robustez (Ato 7).

Valida:
1. Extração correta das 13 variantes metodológicas (P e S0 a S11) a partir do feed de 2026.
2. Invariantes matemáticos do simplex de votos válidos e probabilidades de vitória.
3. Consistência e estabilidade do motor de contingência (fallback determinístico).
4. Geração do relatório consolidado e métricas de dispersão [min, max].
5. Renderização íntegra da visualização Plotly (Forest/Dot Plot).
"""

from pathlib import Path

import pytest

from src.analytics.sensitivity_analysis import (
    CANONICAL_SENSITIVITY_RULES,
    compute_fallback_sensitivity_variants,
    get_sensitivity_report,
    parse_sensitivity_variants_from_feed,
    synthesize_sensitivity_report,
)
from src.presentation.components.sensitivity_table_card import create_sensitivity_forest_plot


def test_canonical_rules_definition() -> None:
    """Valida se todas as 13 regras canônicas estão devidamente tipadas e descritas.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    expected_codes = [
        "P",
        "S0",
        "S1",
        "S2",
        "S3",
        "S4",
        "S5",
        "S6",
        "S7",
        "S8",
        "S9",
        "S10",
        "S11",
    ]
    assert list(CANONICAL_SENSITIVITY_RULES.keys()) == expected_codes
    for code, info in CANONICAL_SENSITIVITY_RULES.items():
        assert "variante" in info and len(info["variante"]) > 0
        assert "regra" in info and len(info["regra"]) > 0


def test_parse_sensitivity_variants_from_feed_invariants() -> None:
    """Verifica os invariantes matemáticos das 13 variantes extraídas do feed de 2026.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    repo_root = Path(__file__).resolve().parent.parent
    feed_path = repo_root / "data" / "raw" / "2026" / "feed_pesquisas_publicadas_2026.json"

    report = get_sensitivity_report(feed_path=feed_path)
    assert len(report.variantes) == 13

    codigos = [v.codigo for v in report.variantes]
    assert codigos[0] == "P"
    assert codigos[1:] == [f"S{i}" for i in range(12)]

    for v in report.variantes:
        # Soma de votos válidos no simplex de 100%
        soma_validos = v.p_validos_a + v.p_validos_b
        assert pytest.approx(soma_validos, abs=1e-4) == 1.0

        # Margem coerente com a diferença
        diff = v.p_validos_a - v.p_validos_b
        assert pytest.approx(v.margem, abs=1e-4) == diff

        # Probabilidades somam 1.0 e estão no intervalo unitário
        soma_probs = v.prob_a + v.prob_b
        assert pytest.approx(soma_probs, abs=1e-4) == 1.0
        assert 0.0 <= v.prob_a <= 1.0
        assert 0.0 <= v.prob_b <= 1.0

        # Todas as variantes apontam o favorito esperado (Flávio)
        assert v.favorito in ("Flávio", "Flávio Bolsonaro")
        assert not v.inverte


def test_synthesize_sensitivity_report_metrics() -> None:
    """Valida as métricas agregadas de consenso e dispersão no relatório de sensibilidade.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    variants = compute_fallback_sensitivity_variants([])
    report = synthesize_sensitivity_report(variants, candidate_a="Lula", candidate_b="Flávio")

    assert report.concordancia_favorito_pct == 100.0
    assert report.favorito_consenso == "Flávio"
    assert report.min_p_validos_a >= 47.0
    assert report.max_p_validos_a <= 49.5
    assert report.min_prob_a >= 8.5
    assert report.max_prob_a <= 36.0
    assert "todas as 13 de 13 variações" in report.resumo_veredito


def test_synthesize_sensitivity_report_empty_raises() -> None:
    """Garante que `synthesize_sensitivity_report` levanta ValueError se a lista for vazia.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    with pytest.raises(ValueError, match="não pode ser vazia"):
        synthesize_sensitivity_report([])


def test_fallback_sensitivity_variants_values() -> None:
    """Verifica que o fallback determinístico preserva os números canônicos da especificação.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    variants = compute_fallback_sensitivity_variants([])
    var_dict = {v.codigo: v for v in variants}

    # P: 48,1% Lula | -3,9 p.p. | 16,7% chance
    p_var = var_dict["P"]
    assert pytest.approx(round(p_var.p_validos_a * 100.0, 1), abs=0.1) == 48.1
    assert pytest.approx(round(p_var.margem * 100.0, 1), abs=0.1) == -3.9
    assert pytest.approx(round(p_var.prob_a * 100.0, 1), abs=0.1) == 16.7

    # S0: 49,0% Lula | -2,0 p.p. | 30,3% chance
    s0_var = var_dict["S0"]
    assert pytest.approx(round(s0_var.p_validos_a * 100.0, 1), abs=0.1) == 49.0
    assert pytest.approx(round(s0_var.margem * 100.0, 1), abs=0.1) == -2.0
    assert pytest.approx(round(s0_var.prob_a * 100.0, 1), abs=0.1) == 30.3

    # S7: 47,1% Lula | -5,8 p.p. | 8,9% chance
    s7_var = var_dict["S7"]
    assert pytest.approx(round(s7_var.p_validos_a * 100.0, 1), abs=0.1) == 47.1
    assert pytest.approx(round(s7_var.prob_a * 100.0, 1), abs=0.1) == 8.9

    # S8: 49,3% Lula | -1,5 p.p. | 35,0% chance
    s8_var = var_dict["S8"]
    assert pytest.approx(round(s8_var.p_validos_a * 100.0, 1), abs=0.1) == 49.3
    assert pytest.approx(round(s8_var.prob_a * 100.0, 1), abs=0.1) == 35.0


def test_create_sensitivity_forest_plot() -> None:
    """Verifica a geração do gráfico Plotly para as variantes e casos vazios.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    variants = compute_fallback_sensitivity_variants([])
    fig = create_sensitivity_forest_plot(variants, candidate_a="Lula", candidate_b="Flávio")

    assert fig is not None
    assert len(fig.data) == 1
    assert len(fig.data[0].x) == 13

    # Caso de borda vazio
    fig_empty = create_sensitivity_forest_plot([])
    assert fig_empty is not None
    assert len(fig_empty.data) == 0


def test_parse_sensitivity_variants_empty_feed() -> None:
    """Verifica que `parse_sensitivity_variants_from_feed` retorna lista vazia para feed nulo.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    res = parse_sensitivity_variants_from_feed({})
    assert res == []
