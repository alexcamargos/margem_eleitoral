"""Testes unitários para o módulo de testes de hipótese e TSE."""

import pytest

from src.analytics.hypothesis_tests import (
    decompose_total_survey_error,
    run_coverage_binomial_test,
    run_paired_t_test,
    run_wilcoxon_test,
)


def test_run_paired_t_test_centered() -> None:
    """Verifica que resíduos simétricos centrados em zero não rejeitam H0."""
    residuos = [-1.0, 1.0, -0.5, 0.5, 0.0, -0.2, 0.2]
    resultado = run_paired_t_test(residuos)
    assert not resultado["reject_h0"]
    assert pytest.approx(resultado["mean_residual"], abs=0.01) == 0.0
    assert resultado["p_value"] > 0.05


def test_run_paired_t_test_biased() -> None:
    """Verifica que resíduos com viés forte rejeitam H0."""
    residuos = [3.0, 4.0, 3.5, 4.2, 3.8, 4.5, 5.0]
    resultado = run_paired_t_test(residuos)
    assert resultado["reject_h0"]
    assert resultado["p_value"] < 0.001
    assert resultado["mean_residual"] > 3.0


def test_run_wilcoxon_test() -> None:
    """Verifica a aplicação do teste não-paramétrico de Wilcoxon."""
    residuos = [2.5, 3.0, 4.0, 2.8, 3.2, 4.1]
    res = run_wilcoxon_test(residuos)
    assert "statistic" in res
    assert "p_value" in res
    assert res["reject_h0"]


def test_run_coverage_binomial_test() -> None:
    """Verifica o teste binomial exato de cobertura contra a meta teórica de 95%."""
    # 19 acertos em 20 pesquisas (95%) -> não deve rejeitar H0
    res_high = run_coverage_binomial_test(n_covered=19, n_total=20, nominal_rate=0.95)
    assert not res_high["reject_h0"]
    assert res_high["observed_rate"] == 95.0

    # 10 acertos em 20 pesquisas (50%) -> deve rejeitar H0 (p-valor muito baixo)
    res_low = run_coverage_binomial_test(n_covered=10, n_total=20, nominal_rate=0.95)
    assert res_low["reject_h0"]
    assert res_low["p_value"] < 0.01


def test_decompose_total_survey_error() -> None:
    """Valida a decomposição do Total Survey Error (TSE)."""
    p_hats = [47.0, 48.0, 49.0, 48.5, 47.5]
    p_true = 48.43
    ns = [2000, 2500, 3000, 2000, 3500]

    decomp = decompose_total_survey_error(p_hats, p_true, ns, deff=1.3)
    assert "bias" in decomp
    assert "mse" in decomp
    assert "theoretical_sampling_variance" in decomp
    assert "empirical_variance" in decomp
    assert "non_sampling_error_variance" in decomp
    assert "late_swing_variance" in decomp
    assert "structural_non_sampling_variance" in decomp
    assert decomp["theoretical_sampling_variance"] > 0
    assert decomp["mse"] >= decomp["empirical_variance"]


def test_decompose_total_survey_error_with_late_swing() -> None:
    """Valida a decomposição do Total Survey Error com isolamento de late swing."""
    p_hats_eve = [47.0, 51.0, 48.0, 52.0]  # média = 49.5, var empírica ~ 5.67 > var teórica ~ 1.62
    p_true = 48.43
    ns = [2000, 2000, 2000, 2000]
    p_hats_pre = [48.0, 49.0, 48.5]  # média = 48.5 -> delta = 1.0 -> late swing = 1.0

    decomp = decompose_total_survey_error(
        p_hats_eve, p_true, ns, deff=1.3, pre_eve_p_hat_series=p_hats_pre
    )
    assert "late_swing_variance" in decomp
    assert "structural_non_sampling_variance" in decomp
    assert decomp["late_swing_variance"] > 0.0
    assert decomp["non_sampling_error_variance"] >= decomp["late_swing_variance"]
    assert (
        pytest.approx(
            decomp["non_sampling_error_variance"],
            abs=0.01,
        )
        == decomp["late_swing_variance"] + decomp["structural_non_sampling_variance"]
    )
