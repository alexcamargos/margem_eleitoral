"""Módulo de análise estatística, agregação e testes de hipótese."""

from src.analytics.hypothesis_tests import (
    decompose_total_survey_error,
    extract_pre_eve_estimates,
    run_coverage_binomial_test,
    run_paired_t_test,
    run_wilcoxon_test,
)

__all__ = [
    "decompose_total_survey_error",
    "extract_pre_eve_estimates",
    "run_coverage_binomial_test",
    "run_paired_t_test",
    "run_wilcoxon_test",
]
