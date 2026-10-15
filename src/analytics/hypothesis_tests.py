"""Testes de hipótese e diagnóstico inferencial do Total Survey Error (TSE).

Implementa testes estatísticos formais (t-Student, Wilcoxon e Binomial de cobertura)
para confrontar a hipótese de ruído estocástico contra viés sistemático nas pesquisas de véspera.
"""

from typing import Sequence

import numpy as np
from scipy import stats


def run_paired_t_test(residuals: Sequence[float]) -> dict[str, float | bool]:
    """Executa o teste t de Student para média dos resíduos igual a zero.

    H0: mu_residuo = 0 (as divergências têm média nula, consistentes com ruído estocástico).
    H1: mu_residuo != 0 (evidência de viés sistemático direcional).

    Args:
        residuals: Sequência de resíduos (p_hat - P_real) em pontos percentuais.

    Returns:
        dict[str, float | bool]: Dicionário com:
            - t_statistic: Valor da estatística t.
            - p_value: Valor-p bilateral do teste.
            - mean_residual: Média amostral dos resíduos.
            - reject_h0: Booleano indicando rejeição de H0 ao nível alfa de 5%.

    Raises:
        ValueError: Se a sequência tiver menos de 2 elementos.
    """
    if len(residuals) < 2:
        raise ValueError(f"O teste t requer ao menos 2 observações. Recebido: {len(residuals)}")

    arr = np.array(residuals, dtype=float)
    t_stat, p_val = stats.ttest_1samp(arr, popmean=0.0)
    mean_val = float(np.mean(arr))

    return {
        "t_statistic": round(float(t_stat), 4),
        "p_value": round(float(p_val), 4),
        "mean_residual": round(mean_val, 4),
        "reject_h0": bool(p_val < 0.05),
    }


def run_wilcoxon_test(residuals: Sequence[float]) -> dict[str, float | bool]:
    """Executa o teste de postos sinalizados de Wilcoxon para mediana dos resíduos nula.

    Alternativa não-paramétrica robusta a assimetrias e caudas pesadas.
    H0: Mediana dos resíduos = 0.
    H1: Mediana dos resíduos != 0.

    Args:
        residuals: Sequência de resíduos (p_hat - P_real).

    Returns:
        dict[str, float | bool]: Dicionário com:
            - statistic: Valor da estatística de Wilcoxon W.
            - p_value: Valor-p bilateral.
            - median_residual: Mediana amostral dos resíduos.
            - reject_h0: Booleano indicando rejeição de H0 (alfa = 0.05).

    Raises:
        ValueError: Se a sequência tiver menos de 5 elementos.
    """
    if len(residuals) < 5:
        raise ValueError(
            f"O teste de Wilcoxon requer ao menos 5 observações. Recebido: {len(residuals)}"
        )

    arr = np.array(residuals, dtype=float)
    # Filtra zeros exatos para evitar advertências no Wilcoxon
    diffs = arr[arr != 0.0]
    if len(diffs) == 0:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "median_residual": 0.0,
            "reject_h0": False,
        }

    stat, p_val = stats.wilcoxon(diffs, alternative="two-sided")
    med_val = float(np.median(arr))

    return {
        "statistic": round(float(stat), 4),
        "p_value": round(float(p_val), 4),
        "median_residual": round(med_val, 4),
        "reject_h0": bool(p_val < 0.05),
    }


def run_coverage_binomial_test(
    n_covered: int,
    n_total: int,
    nominal_rate: float = 0.95,
) -> dict[str, float | bool]:
    """Testa se a taxa de cobertura observada difere significativamente da nominal (95%).

    H0: Taxa de cobertura = 0.95 (a calibração dos intervalos teóricos é perfeita).
    H1: Taxa de cobertura < 0.95 (subcobertura estatística sistemática).

    Args:
        n_covered: Número de intervalos de confiança que contiveram o resultado da urna.
        n_total: Total de pesquisas de véspera avaliadas.
        nominal_rate: Taxa teórica esperada (default: 0.95).

    Returns:
        dict[str, float | bool]: Dicionário com:
            - observed_rate: Taxa percentual observada de acertos.
            - p_value: Valor-p do teste binomial exato (unilateral à esquerda).
            - reject_h0: Booleano indicando rejeição de H0 ao nível alfa de 5%.

    Raises:
        ValueError: Se n_total <= 0 ou n_covered fora do intervalo [0, n_total].
    """
    if n_total <= 0:
        raise ValueError(f"Total de pesquisas deve ser positivo. Recebido: {n_total}")
    if not (0 <= n_covered <= n_total):
        raise ValueError(f"Intervalos cobertos ({n_covered}) deve estar entre 0 e {n_total}.")

    # Teste binomial unilateral (alternative='less'): testando se a cobertura empírica é inferior
    res = stats.binomtest(k=n_covered, n=n_total, p=nominal_rate, alternative="less")
    observed_pct = round((n_covered / n_total) * 100.0, 2)

    return {
        "observed_rate": observed_pct,
        "p_value": round(float(res.pvalue), 4),
        "reject_h0": bool(res.pvalue < 0.05),
    }


def decompose_total_survey_error(
    p_hat_series: Sequence[float],
    p_true: float,
    sample_sizes: Sequence[int],
    deff: float = 1.3,
    pre_eve_p_hat_series: Sequence[float] | None = None,
) -> dict[str, float]:
    """Decompõe o Total Survey Error (TSE) em variância amostral, viés, late swing e resíduo estrutural.

    MSE = Bias^2 + Var_Total

    Permite quantificar o efeito do voto útil e movimentação de última hora (late swing)
    ao contrastar as estimativas de véspera com a série de pesquisas pré-véspera (T-7 a T-3).

    Args:
        p_hat_series: Sequência de estimativas dos institutos de véspera para o candidato líder.
        p_true: Percentual oficial apurado pelo TSE para o candidato líder.
        sample_sizes: Tamanhos amostrais de cada instituto correspondente.
        deff: Efeito de delineamento médio aplicado (default: 1.3).
        pre_eve_p_hat_series: Sequência opcional de estimativas pré-véspera (T-7 a T-3)
            para isolar a movimentação tardia do eleitorado.

    Returns:
        dict[str, float]: Dicionário com:
            - bias: Viés médio (mean(p_hat) - p_true).
            - mse: Erro quadrático médio total.
            - theoretical_sampling_variance: Variância estocástica esperada pelo tamanho amostral.
            - empirical_variance: Variância observada entre os institutos de véspera.
            - non_sampling_error_variance: Componente não-amostral total (excesso de dispersão).
            - late_swing_variance: Variância atribuível à movimentação tardia (T-7 a T-3 vs véspera).
            - structural_non_sampling_variance: Erro estrutural não-amostral residual (abstenção/coleta).

    Raises:
        ValueError: Se as listas forem vazias ou de comprimentos desiguais.
    """
    if len(p_hat_series) != len(sample_sizes) or not p_hat_series:
        raise ValueError("Tamanhos incompatíveis ou sequência vazia de estimativas.")

    p_arr = np.array(p_hat_series, dtype=float)
    n_arr = np.array(sample_sizes, dtype=float)

    # 1. Bias médio em pontos percentuais
    bias = float(np.mean(p_arr - p_true))

    # 2. Variância amostral estocástica teórica média
    # Var(p) = deff * [P*(100 - P) / n]
    var_teorica = float(np.mean(deff * (p_true * (100.0 - p_true)) / n_arr))

    # 3. Variância empírica observada entre as pesquisas de véspera
    var_empirica = float(np.var(p_arr, ddof=1)) if len(p_arr) > 1 else 0.0

    # 4. Componente não-amostral (excesso de dispersão não explicado por erro de amostragem)
    excesso_dispersao = max(0.0, var_empirica - var_teorica)

    # 5. Estimativa de Late Swing (movimentação de última hora entre pré-véspera e véspera)
    if pre_eve_p_hat_series and len(pre_eve_p_hat_series) > 0:
        mean_eve = float(np.mean(p_arr))
        mean_pre = float(np.mean(pre_eve_p_hat_series))
        delta_late = abs(mean_eve - mean_pre)
        late_swing_var = float(delta_late**2)
        structural_var = max(0.0, excesso_dispersao - min(excesso_dispersao, late_swing_var))
    else:
        late_swing_var = 0.0
        structural_var = excesso_dispersao

    # 6. MSE Total
    mse = (bias**2) + var_empirica

    return {
        "bias": round(bias, 2),
        "mse": round(mse, 2),
        "theoretical_sampling_variance": round(var_teorica, 2),
        "empirical_variance": round(var_empirica, 2),
        "non_sampling_error_variance": round(excesso_dispersao, 2),
        "late_swing_variance": round(late_swing_var, 2),
        "structural_non_sampling_variance": round(structural_var, 2),
    }
