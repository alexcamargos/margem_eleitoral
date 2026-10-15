"""Testes unitários para o módulo de métricas estatísticas e erro de pesquisas."""

import math

import pytest

from src.analytics.metrics import (
    calculate_bias_log_odds,
    calculate_confidence_interval,
    calculate_coverage_rate,
    calculate_mosteller_m3,
    calculate_mosteller_m5,
    calculate_variance_and_se,
    calculate_weighted_poll_error,
    simulate_stochastic_poll_thresholds,
)


def test_calculate_variance_and_se() -> None:
    """Verifica o cálculo da variância e desvio padrão com deff."""
    # p = 50%, n = 2000, deff = 1.0 -> SE = sqrt(0.5 * 0.5 / 2000) = sqrt(0.000125) = 0.01118 (1.118%)
    var, se = calculate_variance_and_se(50.0, 2000, deff=1.0)
    assert pytest.approx(se, rel=1e-3) == 1.118

    # Com deff = 1.44 -> SE deve aumentar por sqrt(1.44) = 1.2x -> 1.118 * 1.2 = 1.3416%
    _, se_deff = calculate_variance_and_se(50.0, 2000, deff=1.44)
    assert pytest.approx(se_deff, rel=1e-3) == 1.3416


def test_calculate_confidence_interval() -> None:
    """Verifica limites do intervalo de confiança de 95%."""
    lim_inf, lim_sup, me = calculate_confidence_interval(
        p_percent=50.0, n_sample=2000, deff=1.0, confidence_level=0.95
    )
    # Margem de erro esperada: 1.95996 * 1.118 = 2.19%
    assert pytest.approx(me, abs=0.05) == 2.19
    assert lim_inf < 50.0 < lim_sup
    assert pytest.approx(lim_sup - lim_inf, abs=0.1) == 2 * me


def test_mosteller_m3_and_m5() -> None:
    """Valida as métricas Mosteller 3 e Mosteller 5."""
    # Líder estimado: 48%, Oficial: 48.43% -> M3 = 0.43
    m3 = calculate_mosteller_m3(48.0, 48.43)
    assert m3 == 0.43

    # Estimado: Líder 48%, 2º 34% (margem = 14%)
    # Oficial: Líder 48.43%, 2º 43.20% (margem = 5.23%)
    # M5 = |14 - 5.23| = 8.77
    m5 = calculate_mosteller_m5(48.0, 34.0, 48.43, 43.20)
    assert m5 == 8.77

    with pytest.raises(ValueError, match="não podem ser negativos"):
        calculate_mosteller_m3(-1.0, 48.43)

    with pytest.raises(ValueError, match="não pode ser negativo"):
        calculate_mosteller_m5(48.0, -2.0, 48.43, 43.20)


def test_bias_log_odds() -> None:
    """Valida a métrica de viés log-odds A."""
    # Razão estimada igual à oficial -> A = ln(1) = 0.0
    a_zero = calculate_bias_log_odds(50.0, 50.0, 50.0, 50.0)
    assert a_zero == 0.0

    # Sobrestimação do candidato 1: estimado 60/40 = 1.5, oficial 50/50 = 1.0 -> ln(1.5) > 0
    a_pos = calculate_bias_log_odds(60.0, 40.0, 50.0, 50.0)
    assert a_pos > 0.0
    assert pytest.approx(a_pos, abs=1e-3) == round(math.log(1.5), 4)


def test_weighted_poll_error() -> None:
    """Valida a decomposição estrutural e classificação do erro ponderado multivariado."""
    votos_estimados = {"Lula": 48.0, "Bolsonaro": 42.0, "Ciro": 5.0, "Tebet": 5.0}
    resultado_oficial = {"Lula": 48.43, "Bolsonaro": 43.20, "Ciro": 3.04, "Tebet": 4.16}

    decomp = calculate_weighted_poll_error(votos_estimados, resultado_oficial)
    assert "erro_1_lugar" in decomp
    assert "erro_2_lugar" in decomp
    assert "erro_demais" in decomp
    assert "erro_total_ponderado" in decomp
    assert "disputa_decisiva" in decomp
    assert "eleitorado_fora_lugar" in decomp
    assert "penalidade_lado_errado" in decomp
    assert "peso_eleitorado_a" in decomp
    assert "faixa_acerto" in decomp
    assert decomp["faixa_acerto"] in ["Abaixo do Típico", "Erro Típico", "Acima do Típico"]

    # Como a pesquisa acertou o líder e não cruzou a linha de 50%, a penalidade deve ser nula
    assert decomp["penalidade_lado_errado"] == 0.0
    assert decomp["disputa_decisiva"] > 0.0
    assert decomp["eleitorado_fora_lugar"] > 0.0

    # Teste de inversão do líder (Bolsonaro à frente quando Lula venceu)
    votos_invertidos = {"Lula": 42.0, "Bolsonaro": 48.0, "Ciro": 5.0, "Tebet": 5.0}
    decomp_inv = calculate_weighted_poll_error(votos_invertidos, resultado_oficial)
    assert decomp_inv["penalidade_lado_errado"] > 0.0
    assert decomp_inv["erro_total_ponderado"] > decomp["erro_total_ponderado"]

    # Teste com limiares customizados derivados da simulação
    decomp_custom = calculate_weighted_poll_error(
        votos_estimados,
        resultado_oficial,
        thresholds={"p25": 10.0, "p75": 15.0},
    )
    assert decomp_custom["faixa_acerto"] == "Abaixo do Típico"

    with pytest.raises(ValueError, match="não pode ser vazio"):
        calculate_weighted_poll_error(votos_estimados, {})


def test_simulate_stochastic_poll_thresholds() -> None:
    """Valida a simulação de Monte Carlo para a Faixa do Acaso."""
    resultado_oficial = {"Lula": 48.43, "Bolsonaro": 43.20, "Ciro": 3.04, "Tebet": 4.16}

    res = simulate_stochastic_poll_thresholds(
        resultado_oficial=resultado_oficial,
        sample_size=2000,
        deff=1.35,
        n_simulations=1000,
        random_seed=42,
    )

    assert "p25" in res
    assert "median_a50" in res
    assert "p75" in res
    assert "faixa_acaso_p90" in res
    assert "effective_sample_size" in res
    assert "mean_ep" in res
    assert "std_ep" in res

    # Monotonicidade estocástica dos percentis
    assert res["p25"] <= res["median_a50"] <= res["p75"] <= res["faixa_acaso_p90"]

    # Amostra efetiva deve ser proporcional a n / deff (2000 / 1.35 = 1481)
    assert 1400 <= res["effective_sample_size"] <= 1500

    # Reprodutibilidade com a mesma semente
    res_repeat = simulate_stochastic_poll_thresholds(
        resultado_oficial=resultado_oficial,
        sample_size=2000,
        deff=1.35,
        n_simulations=1000,
        random_seed=42,
    )
    assert res["median_a50"] == res_repeat["median_a50"]
    assert res["faixa_acaso_p90"] == res_repeat["faixa_acaso_p90"]

    # Validação de erros
    with pytest.raises(ValueError, match="não pode ser vazio"):
        simulate_stochastic_poll_thresholds({}, sample_size=2000)

    with pytest.raises(ValueError, match="deve ser positivo"):
        simulate_stochastic_poll_thresholds(resultado_oficial, sample_size=0)

    with pytest.raises(ValueError, match="deff deve ser >= 1.0"):
        simulate_stochastic_poll_thresholds(resultado_oficial, sample_size=2000, deff=0.8)


def test_calculate_coverage_rate() -> None:
    """Valida cálculo de cobertura empírica."""
    intervals = [(45.0, 50.0), (40.0, 45.0), (48.0, 52.0), (30.0, 35.0)]
    true_vals = [48.0, 43.0, 49.0, 40.0]  # 3 primeiros acertam, 4º erra
    cov = calculate_coverage_rate(intervals, true_vals)
    assert cov == 75.0
