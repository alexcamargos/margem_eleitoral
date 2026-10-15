"""Testes unitários para o módulo de testes de hipótese e TSE."""

from datetime import date

import pytest

from src.analytics.hypothesis_tests import (
    decompose_total_survey_error,
    extract_pre_eve_estimates,
    run_coverage_binomial_test,
    run_paired_t_test,
    run_wilcoxon_test,
)
from src.transformations.schemas import MetodologiaEnum, PesquisaEleitoralSchema


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
    """Valida a decomposição do Total Survey Error (TSE) sem dados pré-véspera.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
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
    assert decomp["late_swing_variance"] is None
    assert decomp["structural_non_sampling_variance"] == decomp["non_sampling_error_variance"]
    assert decomp["theoretical_sampling_variance"] > 0
    assert decomp["mse"] >= decomp["empirical_variance"]


def test_decompose_total_survey_error_with_late_swing() -> None:
    """Valida a decomposição do Total Survey Error com isolamento de late swing.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    p_hats_eve = [47.0, 51.0, 48.0, 52.0]  # média = 49.5, var empírica ~ 5.67 > var teórica ~ 1.62
    p_true = 48.43
    ns = [2000, 2000, 2000, 2000]
    p_hats_pre = [48.0, 49.0, 48.5]  # média = 48.5 -> delta = 1.0 -> late swing = 1.0

    decomp = decompose_total_survey_error(
        p_hats_eve, p_true, ns, deff=1.3, pre_eve_p_hat_series=p_hats_pre
    )
    assert "late_swing_variance" in decomp
    assert "structural_non_sampling_variance" in decomp
    assert decomp["late_swing_variance"] is not None
    assert decomp["late_swing_variance"] > 0.0
    assert decomp["non_sampling_error_variance"] >= decomp["late_swing_variance"]
    assert (
        pytest.approx(
            decomp["non_sampling_error_variance"],
            abs=0.01,
        )
        == decomp["late_swing_variance"] + decomp["structural_non_sampling_variance"]
    )


def _make_dummy_poll(poll_id: str, end_date: date, p_cand: float) -> PesquisaEleitoralSchema:
    """Cria uma instância sintética de PesquisaEleitoralSchema para testes de data.

    Args:
        poll_id: Identificador único de registro no TSE.
        end_date: Data de encerramento do campo.
        p_cand: Percentual estimado para o candidato líder.

    Returns:
        PesquisaEleitoralSchema: Objeto validado com os campos mínimos.

    Raises:
        None.
    """
    return PesquisaEleitoralSchema(
        id_registro_tse=poll_id,
        instituto_razao_social="Instituto Teste Ltda",
        instituto_nome_fantasia="Instituto Teste",
        data_inicio_campo=end_date,
        data_fim_campo=end_date,
        data_divulgacao=end_date,
        tamanho_amostra=2000,
        margem_erro_declarada=2.0,
        nivel_confianca=0.95,
        metodologia=MetodologiaEnum.PRESENCIAL_DOMICILIAR,
        deff_estimado=1.3,
        votos_totais={"Candidato A": p_cand, "Outros": 100.0 - p_cand - 5.0},
        votos_validos={"Candidato A": p_cand, "Outros": 100.0 - p_cand},
        percentual_indecisos=2.0,
        percentual_brancos_nulos=3.0,
    )


def test_extract_pre_eve_estimates_standard_window() -> None:
    """Verifica que pesquisas dentro da janela padrão de 7 dias são capturadas.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    eve_polls = [_make_dummy_poll("BR-00001/2026", date(2026, 10, 2), 48.0)]
    pre_poll = _make_dummy_poll("BR-00002/2026", date(2026, 9, 28), 46.5)  # 4 dias antes
    all_polls = [pre_poll] + eve_polls

    estimates, window = extract_pre_eve_estimates(all_polls, eve_polls, candidate="Candidato A")
    assert estimates == [46.5]
    assert window == 7


def test_extract_pre_eve_estimates_extended_window() -> None:
    """Verifica a expansão dinâmica para até 14 dias quando a janela de 7 dias está vazia.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    eve_polls = [_make_dummy_poll("BR-00001/2026", date(2026, 10, 2), 48.0)]
    pre_poll = _make_dummy_poll("BR-00002/2026", date(2026, 9, 20), 45.0)  # 12 dias antes
    all_polls = [pre_poll] + eve_polls

    estimates, window = extract_pre_eve_estimates(all_polls, eve_polls, candidate="Candidato A")
    assert estimates == [45.0]
    assert window == 14


def test_extract_pre_eve_estimates_empty() -> None:
    """Verifica retorno vazio e None quando não há pesquisas na janela de até 14 dias.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    eve_polls = [_make_dummy_poll("BR-00001/2026", date(2026, 10, 2), 48.0)]
    old_poll = _make_dummy_poll("BR-00002/2026", date(2026, 9, 10), 42.0)  # 22 dias antes
    all_polls = [old_poll] + eve_polls

    estimates, window = extract_pre_eve_estimates(all_polls, eve_polls, candidate="Candidato A")
    assert estimates == []
    assert window is None


def test_extract_pre_eve_estimates_invalid_window_raises() -> None:
    """Verifica que parâmetros de janela temporal inválidos levantam ValueError.

    Args:
        None.

    Returns:
        None.

    Raises:
        ValueError: Esperado na validação de limites temporais.
    """
    eve_polls = [_make_dummy_poll("BR-00001/2026", date(2026, 10, 2), 48.0)]
    with pytest.raises(ValueError, match="Limiares de janela temporal inválidos."):
        extract_pre_eve_estimates(eve_polls, eve_polls, "Candidato A", standard_window_days=0)
    with pytest.raises(ValueError, match="Limiares de janela temporal inválidos."):
        extract_pre_eve_estimates(
            eve_polls, eve_polls, "Candidato A", standard_window_days=10, max_window_days=5
        )


def test_decompose_total_survey_error_empty_series_returns_none() -> None:
    """Verifica que passing lista vazia de pré-véspera resulta em late_swing_variance None.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    p_hats = [47.0, 48.0, 49.0]
    p_true = 48.43
    ns = [2000, 2000, 2000]

    decomp = decompose_total_survey_error(p_hats, p_true, ns, pre_eve_p_hat_series=[])
    assert decomp["late_swing_variance"] is None
    assert decomp["structural_non_sampling_variance"] == decomp["non_sampling_error_variance"]
