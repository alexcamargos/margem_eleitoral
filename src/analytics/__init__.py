"""Módulo de análise estatística, agregação, modelos preditivos e testes de hipótese."""

from src.analytics.hypothesis_tests import (
    decompose_total_survey_error,
    extract_pre_eve_estimates,
    run_coverage_binomial_test,
    run_paired_t_test,
    run_wilcoxon_test,
)
from src.analytics.predictive_model import (
    CandidatePrediction,
    ElectionForecastResult,
    InstituteT1Calibration,
    PredictiveModelConfig,
    RegionalForecastSlice,
    compute_first_round_institute_calibration,
    compute_regional_electoral_breakdown,
    evaluate_promotion_gates,
    predict_election_outcome,
    run_point_in_time_backtest,
)

__all__ = [
    "CandidatePrediction",
    "ElectionForecastResult",
    "InstituteT1Calibration",
    "PredictiveModelConfig",
    "RegionalForecastSlice",
    "compute_first_round_institute_calibration",
    "compute_regional_electoral_breakdown",
    "decompose_total_survey_error",
    "evaluate_promotion_gates",
    "extract_pre_eve_estimates",
    "predict_election_outcome",
    "run_coverage_binomial_test",
    "run_paired_t_test",
    "run_point_in_time_backtest",
    "run_wilcoxon_test",
]
