"""Métricas padronizadas de erro e inferência amostral para pesquisas eleitorais.

Implementa as métricas internacionais da WAPOR/AAPOR (Mosteller M3, M5, Log-Odds A),
cálculo de intervalos de confiança com efeito de delineamento (deff),
classificação de faixas de erro da referência visual e taxa de cobertura empírica.
"""

import math
from typing import Any, Sequence

import numpy as np
from scipy import stats


def calculate_variance_and_se(
    p_percent: float,
    n_sample: int,
    deff: float = 1.3,
) -> tuple[float, float]:
    """Calcula a variância e o erro padrão (SE) de uma proporção ajustados pelo deff.

    Aplica a formulação:
    Var(p) = deff * [p * (1 - p) / n]
    SE = sqrt(Var(p))

    Args:
        p_percent: Percentual estimado de votos (escala de 0.0 a 100.0).
        n_sample: Tamanho da amostra de entrevistados (deve ser > 0).
        deff: Fator de correção de efeito de delineamento (padrão: 1.3).

    Returns:
        tuple[float, float]: Tupla contendo (variância, erro padrão), ambos expressos
            em pontos percentuais (escala 0-100).

    Raises:
        ValueError: Se n_sample <= 0, se deff < 1.0 ou se p_percent estiver fora de [0, 100].
    """
    if n_sample <= 0:
        raise ValueError(f"Tamanho da amostra deve ser positivo. Recebido: {n_sample}")
    if deff < 1.0:
        raise ValueError(f"Fator deff deve ser >= 1.0. Recebido: {deff}")
    if not (0.0 <= p_percent <= 100.0):
        raise ValueError(f"Percentual deve estar entre 0 e 100. Recebido: {p_percent}")

    # Converte para proporção unitária [0, 1] para cálculo numérico estável
    p = p_percent / 100.0
    var_prop = deff * (p * (1.0 - p)) / n_sample
    se_prop = math.sqrt(max(0.0, var_prop))

    # Retorna na escala percentual (pontos percentuais)
    return var_prop * 10000.0, se_prop * 100.0


def calculate_confidence_interval(
    p_percent: float,
    n_sample: int,
    deff: float = 1.3,
    confidence_level: float = 0.95,
) -> tuple[float, float, float]:
    """Calcula a margem de erro e o intervalo de confiança bilateral de uma estimativa.

    Args:
        p_percent: Estimativa pontual do candidato (0 a 100%).
        n_sample: Tamanho da amostra de eleitores.
        deff: Fator de efeito de delineamento (default: 1.3).
        confidence_level: Nível de confiança nominal (default: 0.95).

    Returns:
        tuple[float, float, float]: Tupla contendo:
            - limite_inferior: Limite inferior do IC (truncado em 0.0%).
            - limite_superior: Limite superior do IC (truncado em 100.0%).
            - margem_erro: Margem de erro em pontos percentuais.

    Raises:
        ValueError: Se confidence_level não estiver estritamente entre 0 e 1.
    """
    if not (0.0 < confidence_level < 1.0):
        raise ValueError(f"Nível de confiança deve estar entre 0 e 1. Recebido: {confidence_level}")

    _, se = calculate_variance_and_se(p_percent, n_sample, deff)
    z_critical = float(stats.norm.ppf(1.0 - (1.0 - confidence_level) / 2.0))
    margem_erro = z_critical * se

    lim_inf = max(0.0, round(p_percent - margem_erro, 2))
    lim_sup = min(100.0, round(p_percent + margem_erro, 2))

    return lim_inf, lim_sup, round(margem_erro, 2)


def calculate_mosteller_m3(p_hat_leader: float, p_true_leader: float) -> float:
    """Calcula a métrica Mosteller 3 (M3): erro absoluto do candidato líder.

    M3 = |p_hat_lider - P_lider|

    Args:
        p_hat_leader: Percentual estimado de votos válidos para o líder.
        p_true_leader: Percentual oficial apurado pelo TSE para o líder.

    Returns:
        float: Desvio absoluto em pontos percentuais.

    Raises:
        ValueError: Se qualquer valor for negativo.
    """
    if p_hat_leader < 0.0 or p_true_leader < 0.0:
        raise ValueError("Valores percentuais não podem ser negativos.")
    return round(abs(p_hat_leader - p_true_leader), 2)


def calculate_mosteller_m5(
    p_hat_1: float,
    p_hat_2: float,
    p_true_1: float,
    p_true_2: float,
) -> float:
    """Calcula a métrica Mosteller 5 (M5): erro na diferença entre 1º e 2º colocados.

    M5 = |(p_hat_1 - p_hat_2) - (P_1 - P_2)|

    Args:
        p_hat_1: Percentual estimado de válidos para o 1º colocado.
        p_hat_2: Percentual estimado de válidos para o 2º colocado.
        p_true_1: Percentual apurado pelo TSE para o 1º colocado.
        p_true_2: Percentual apurado pelo TSE para o 2º colocado.

    Returns:
        float: Desvio absoluto da margem em pontos percentuais.

    Raises:
        ValueError: Se qualquer percentual for negativo.
    """
    for val, name in [
        (p_hat_1, "p_hat_1"),
        (p_hat_2, "p_hat_2"),
        (p_true_1, "p_true_1"),
        (p_true_2, "p_true_2"),
    ]:
        if val < 0.0:
            raise ValueError(f"Percentual '{name}' não pode ser negativo.")

    margem_estimada = p_hat_1 - p_hat_2
    margem_oficial = p_true_1 - p_true_2
    return round(abs(margem_estimada - margem_oficial), 2)


def calculate_bias_log_odds(
    p_hat_1: float,
    p_hat_2: float,
    p_true_1: float,
    p_true_2: float,
) -> float:
    """Calcula o Log-Odds Ratio de Viés (Métrica A da AAPOR/WAPOR).

    A = ln( (p_hat_1 / p_hat_2) / (P_1 / P_2) )

    Um valor positivo indica sobrestimação relativa do candidato 1;
    um valor negativo indica sobrestimação relativa do candidato 2.

    Args:
        p_hat_1: Estimativa de votos válidos do candidato 1 (> 0).
        p_hat_2: Estimativa de votos válidos do candidato 2 (> 0).
        p_true_1: Votos válidos oficiais do candidato 1 (> 0).
        p_true_2: Votos válidos oficiais do candidato 2 (> 0).

    Returns:
        float: Coeficiente Log-Odds de viés direcional.

    Raises:
        ValueError: Se qualquer percentual for menor ou igual a zero.
    """
    for val, name in [
        (p_hat_1, "p_hat_1"),
        (p_hat_2, "p_hat_2"),
        (p_true_1, "p_true_1"),
        (p_true_2, "p_true_2"),
    ]:
        if val <= 0.0:
            raise ValueError(f"Percentual '{name}' deve ser estritamente positivo para log-odds.")

    odds_estimadas = p_hat_1 / p_hat_2
    odds_oficiais = p_true_1 / p_true_2
    return round(math.log(odds_estimadas / odds_oficiais), 4)


def calculate_weighted_poll_error(
    votos_validos_estimados: dict[str, float],
    resultado_oficial: dict[str, float],
    ranking_candidatos: list[str] | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Calcula a decomposição do erro ponderado multivariado e politicamente sensível.

    Implementa a formulação estrutural do Erro Ponderado (EP):
    EP = (1 - a) * D + a * F + 0.5 * X

    Onde:
    - D (Disputa Decisiva): Erro nas margens (1º vs 2º e 2º vs 3º), ponderadas continuamente
      pela competitividade real da corrida através de decaimento exponencial:
      w_{1->2} = exp( - (R1 - R2) / 15 )
      w_{2->3} = g * exp( - (R2 - R3) / 15 ), com g atenuado se R1 >= 50%.
    - F (Eleitorado Fora do Lugar): Distância de Variação Total (L1 / Índice de Duncan),
      representando a porcentagem exata de eleitores que precisariam trocar de candidato
      para a pesquisa espelhar a urna:
      F = 0.5 * ( sum(|P_c - R_c|) + |(100 - sum P_c) - (100 - sum R_c)| )
      com peso a = 0.50 + 0.25 * exp( - |R1 - 50| / 5 ).
    - X (Penalização de Linhas Decisórias): Penalidade por inversão de fronteiras eleitorais
      (quem lidera, quem vai ao 2º turno, maioria absoluta de 50%), atenuada continuamente
      pela distância do resultado oficial à linha: (1 - exp(-delta)).

    Args:
        votos_validos_estimados: Estimativas de votos válidos do instituto.
        resultado_oficial: Percentuais oficiais apurados pelo TSE.
        ranking_candidatos: Ordem de relevância dos candidatos (default: ordenados pelo TSE).
        thresholds: Dicionário opcional contendo limiares de calibração ('p25', 'p75')
            derivados da simulação estocástica de Monte Carlo.

    Returns:
        dict[str, Any]: Dicionário contendo:
            - 'erro_total_ponderado': Erro Ponderado total (EP).
            - 'disputa_decisiva': Componente D (erro nas margens críticas).
            - 'eleitorado_fora_lugar': Componente F (Distância de Variação Total L1).
            - 'penalidade_lado_errado': Componente X (penalidade suave de fronteiras).
            - 'peso_eleitorado_a': Peso 'a' aplicado ao eleitorado fora do lugar.
            - 'erro_1_lugar': Desvio absoluto pontual no 1º colocado (|p_hat_1 - P_1|).
            - 'erro_2_lugar': Desvio absoluto pontual no 2º colocado (|p_hat_2 - P_2|).
            - 'erro_demais': Média dos desvios absolutos das demais colocações.
            - 'faixa_acerto': Classificação categórica ("Abaixo do Típico", "Erro Típico", "Acima do Típico").

    Raises:
        ValueError: Se resultado_oficial for vazio.
    """
    if not resultado_oficial:
        raise ValueError("O resultado oficial do TSE não pode ser vazio.")

    if ranking_candidatos is None:
        ranking_candidatos = sorted(
            resultado_oficial.keys(), key=lambda c: resultado_oficial[c], reverse=True
        )

    cand_1 = ranking_candidatos[0]
    cand_2 = ranking_candidatos[1] if len(ranking_candidatos) > 1 else cand_1
    cand_3 = ranking_candidatos[2] if len(ranking_candidatos) > 2 else None

    p1 = float(votos_validos_estimados.get(cand_1, 0.0))
    r1 = float(resultado_oficial.get(cand_1, 0.0))
    p2 = float(votos_validos_estimados.get(cand_2, 0.0))
    r2 = float(resultado_oficial.get(cand_2, 0.0))

    # 1. Disputa Decisiva (D)
    e1_2 = (p1 - p2) - (r1 - r2)
    w1_2 = math.exp(-max(0.0, r1 - r2) / 15.0)

    if cand_3 is not None:
        p3 = float(votos_validos_estimados.get(cand_3, 0.0))
        r3 = float(resultado_oficial.get(cand_3, 0.0))
        e2_3 = (p2 - p3) - (r2 - r3)
        g = 1.0 if r1 < 50.0 else math.exp(-(r1 - 50.0) / 2.5)
        w2_3 = g * math.exp(-max(0.0, r2 - r3) / 15.0)
        d_val = (w1_2 * abs(e1_2) + w2_3 * abs(e2_3)) / max(1e-6, w1_2 + w2_3)
    else:
        g = 1.0
        d_val = abs(e1_2)

    # 2. Eleitorado Fora do Lugar (F - Total Variation Distance L1)
    all_candidates = set(resultado_oficial.keys()).union(votos_validos_estimados.keys())
    sum_p = sum(votos_validos_estimados.get(c, 0.0) for c in all_candidates)
    sum_r = sum(resultado_oficial.get(c, 0.0) for c in all_candidates)

    l1_sum = sum(
        abs(votos_validos_estimados.get(c, 0.0) - resultado_oficial.get(c, 0.0))
        for c in all_candidates
    )
    unlisted_diff = abs((100.0 - sum_p) - (100.0 - sum_r))
    f_val = 0.5 * (l1_sum + unlisted_diff)

    # Peso do eleitorado fora do lugar (a)
    a_weight = 0.50 + 0.25 * math.exp(-abs(r1 - 50.0) / 5.0)

    # 3. Penalidade de Linhas Decisórias (Lado Errado - X)
    x_val = 0.0

    # Linha 1: Quem lidera
    other_estimates = [votos_validos_estimados.get(c, 0.0) for c in all_candidates if c != cand_1]
    max_other_p = max(other_estimates, default=0.0)
    d_lead = 0.5 * max(0.0, max_other_p - p1)
    delta_lead = 0.5 * max(0.0, r1 - r2)
    x_val += d_lead * (1.0 - math.exp(-delta_lead))

    # Linha 2: Vaga no segundo turno (se aplicável)
    if cand_3 is not None:
        other_non_top2 = [
            votos_validos_estimados.get(c, 0.0) for c in all_candidates if c not in (cand_1, cand_2)
        ]
        max_non_top2_p = max(other_non_top2, default=0.0)
        d_round2 = 0.5 * g * max(0.0, max_non_top2_p - min(p1, p2))
        r3_val = float(resultado_oficial.get(cand_3, 0.0))
        delta_round2 = 0.5 * max(0.0, r2 - r3_val)
        x_val += d_round2 * (1.0 - math.exp(-delta_round2))

    # Linha 3: Maioria de 50% (Vitória em 1º Turno)
    if r1 >= 50.0:
        d_50 = max(0.0, 50.0 - p1, max_other_p - 50.0)
    else:
        all_max_p = max((votos_validos_estimados.get(c, 0.0) for c in all_candidates), default=0.0)
        d_50 = max(0.0, all_max_p - 50.0)
    delta_50 = abs(r1 - 50.0)
    x_val += d_50 * (1.0 - math.exp(-delta_50))

    # Erro Ponderado Final (EP)
    erro_total_ponderado = (1.0 - a_weight) * d_val + a_weight * f_val + 0.5 * x_val

    # Desvios pontuais individuais para manter retrocompatibilidade com UI e tabelas
    erro_1 = abs(p1 - r1)
    erro_2 = abs(p2 - r2)
    demais_erros = [
        abs(votos_validos_estimados.get(c, 0.0) - resultado_oficial.get(c, 0.0))
        for c in ranking_candidatos[2:]
    ]
    erro_demais = float(np.mean(demais_erros)) if demais_erros else 0.0

    # Classificação categórica por limiares (dinâmicos via simulação ou estáticos de fallback)
    lim_inf = thresholds.get("p25", 3.5) if thresholds else 3.5
    lim_sup = thresholds.get("p75", 6.5) if thresholds else 6.5

    if erro_total_ponderado <= lim_inf:
        faixa = "Abaixo do Típico"
    elif erro_total_ponderado <= lim_sup:
        faixa = "Erro Típico"
    else:
        faixa = "Acima do Típico"

    return {
        "erro_total_ponderado": round(erro_total_ponderado, 2),
        "disputa_decisiva": round(d_val, 2),
        "eleitorado_fora_lugar": round(f_val, 2),
        "penalidade_lado_errado": round(x_val, 2),
        "peso_eleitorado_a": round(a_weight, 3),
        "erro_1_lugar": round(erro_1, 2),
        "erro_2_lugar": round(erro_2, 2),
        "erro_demais": round(erro_demais, 2),
        "faixa_acerto": faixa,
    }


def simulate_stochastic_poll_thresholds(
    resultado_oficial: dict[str, float],
    sample_size: int = 2000,
    deff: float = 1.3,
    n_simulations: int = 10000,
    random_seed: int | None = 42,
) -> dict[str, float]:
    """Simula a distribuição nula do erro ponderado sob a hipótese estocástica de puro acaso (H0).

    Gera N sorteios multinomiais baseados no resultado oficial da eleição com tamanho
    amostral efetivo n_ef = n / deff, calculando o Erro Ponderado (EP) em cada amostra
    para derivar a Faixa do Acaso (P90) e os percentis de corte (P25 e P75) específicos
    para a dispersão daquela corrida eleitoral.

    Args:
        resultado_oficial: Percentuais oficiais de votos válidos do TSE.
        sample_size: Tamanho amostral representativo da disputa (default: 2000).
        deff: Fator de efeito de delineamento (default: 1.3).
        n_simulations: Quantidade de amostras aleatórias simuladas (default: 10000).
        random_seed: Semente pseudo-aleatória para reproducibilidade (default: 42).

    Returns:
        dict[str, float]: Dicionário com:
            - 'p25': 25º percentil do erro estocástico (limiar de 'Abaixo do Típico').
            - 'median_a50': Mediana do erro puro ao acaso (A50).
            - 'p75': 75º percentil do erro estocástico (limiar de 'Acima do Típico').
            - 'faixa_acaso_p90': 90º percentil (limite superior da Faixa do Acaso).
            - 'effective_sample_size': Tamanho efetivo n_ef considerado.
            - 'mean_ep': Média do erro ponderado sob H0.
            - 'std_ep': Desvio padrão do erro ponderado sob H0.

    Raises:
        ValueError: Se resultado_oficial for vazio, sample_size <= 0 ou deff < 1.0.
    """
    if not resultado_oficial:
        raise ValueError("O resultado oficial não pode ser vazio para simulação.")
    if sample_size <= 0:
        raise ValueError(f"Tamanho da amostra deve ser positivo. Recebido: {sample_size}")
    if deff < 1.0:
        raise ValueError(f"Fator deff deve ser >= 1.0. Recebido: {deff}")

    # Ordena candidatos pelo percentual oficial
    candidatos = sorted(resultado_oficial.keys(), key=lambda c: resultado_oficial[c], reverse=True)
    props = np.array([resultado_oficial[c] for c in candidatos], dtype=float)
    total_prop = np.sum(props)
    if total_prop <= 0.0:
        raise ValueError("A soma dos votos válidos oficiais deve ser positiva.")
    props_norm = props / total_prop

    # Tamanho efetivo da amostra ajustado pelo deff
    n_ef = max(100, int(round(sample_size / deff)))

    rng = np.random.default_rng(random_seed)
    counts = rng.multinomial(n_ef, props_norm, size=n_simulations)
    sim_pcts = (counts / n_ef) * 100.0

    # Constantes oficiais
    r1 = props_norm[0] * 100.0
    r2 = props_norm[1] * 100.0 if len(props_norm) > 1 else r1
    has_third = len(props_norm) > 2
    r3 = props_norm[2] * 100.0 if has_third else 0.0

    # Vetores simulados para o líder e vice
    p1_vec = sim_pcts[:, 0]
    p2_vec = sim_pcts[:, 1] if len(props_norm) > 1 else p1_vec

    # 1. Disputa Decisiva simulada
    e1_2_vec = (p1_vec - p2_vec) - (r1 - r2)
    w1_2 = math.exp(-max(0.0, r1 - r2) / 15.0)

    if has_third:
        p3_vec = sim_pcts[:, 2]
        e2_3_vec = (p2_vec - p3_vec) - (r2 - r3)
        g = 1.0 if r1 < 50.0 else math.exp(-(r1 - 50.0) / 2.5)
        w2_3 = g * math.exp(-max(0.0, r2 - r3) / 15.0)
        d_vec = (w1_2 * np.abs(e1_2_vec) + w2_3 * np.abs(e2_3_vec)) / max(1e-6, w1_2 + w2_3)
    else:
        g = 1.0
        d_vec = np.abs(e1_2_vec)

    # 2. Eleitorado Fora do Lugar simulado (F)
    diffs = np.abs(sim_pcts - (props_norm * 100.0))
    f_vec = 0.5 * np.sum(diffs, axis=1)

    a_weight = 0.50 + 0.25 * math.exp(-abs(r1 - 50.0) / 5.0)

    # 3. Linhas Decisórias simuladas (X)
    x_vec = np.zeros(n_simulations, dtype=float)

    # Liderança
    if len(props_norm) > 1:
        max_other_p = np.max(sim_pcts[:, 1:], axis=1)
        d_lead = 0.5 * np.maximum(0.0, max_other_p - p1_vec)
        delta_lead = 0.5 * max(0.0, r1 - r2)
        x_vec += d_lead * (1.0 - math.exp(-delta_lead))

    # Segundo Turno
    if has_third:
        if len(props_norm) > 2:
            max_non_top2 = np.max(sim_pcts[:, 2:], axis=1)
            min_top2 = np.minimum(p1_vec, p2_vec)
            d_round2 = 0.5 * g * np.maximum(0.0, max_non_top2 - min_top2)
            delta_round2 = 0.5 * max(0.0, r2 - r3)
            x_vec += d_round2 * (1.0 - math.exp(-delta_round2))

    # Maioria de 50%
    if r1 >= 50.0:
        max_oth = np.max(sim_pcts[:, 1:], axis=1) if len(props_norm) > 1 else np.zeros_like(p1_vec)
        d_50 = np.maximum(0.0, np.maximum(50.0 - p1_vec, max_oth - 50.0))
    else:
        max_all = np.max(sim_pcts, axis=1)
        d_50 = np.maximum(0.0, max_all - 50.0)
    delta_50 = abs(r1 - 50.0)
    x_vec += d_50 * (1.0 - math.exp(-delta_50))

    # EP Simulado
    ep_sims = (1.0 - a_weight) * d_vec + a_weight * f_vec + 0.5 * x_vec

    p25, p50, p75, p90 = np.percentile(ep_sims, [25.0, 50.0, 75.0, 90.0])

    return {
        "p25": round(float(p25), 2),
        "median_a50": round(float(p50), 2),
        "p75": round(float(p75), 2),
        "faixa_acaso_p90": round(float(p90), 2),
        "effective_sample_size": float(n_ef),
        "mean_ep": round(float(np.mean(ep_sims)), 2),
        "std_ep": round(float(np.std(ep_sims)), 2),
    }


def calculate_coverage_rate(
    intervals: Sequence[tuple[float, float]],
    true_values: Sequence[float],
) -> float:
    """Calcula a taxa de cobertura empírica dos intervalos de confiança.

    Verifica quantos intervalos de confiança [lim_inf, lim_sup] contêm o valor
    oficial apurado correspondente.

    Coverage Rate = (Nº de intervalos que contêm o valor real / Total de intervalos) * 100

    Args:
        intervals: Sequência de tuplas (limite_inferior, limite_superior).
        true_values: Sequência de valores verdadeiros oficiais apurados correspondentes.

    Returns:
        float: Taxa percentual de cobertura empírica (0.0 a 100.0%).

    Raises:
        ValueError: Se as sequências tiverem tamanhos distintos ou forem vazias.
    """
    if len(intervals) != len(true_values):
        raise ValueError(
            f"Tamanho incompatível: {len(intervals)} intervalos vs {len(true_values)} valores."
        )
    if not intervals:
        raise ValueError("A lista de intervalos não pode ser vazia.")

    acertos = sum(1 for (inf, sup), val in zip(intervals, true_values) if inf <= val <= sup)
    return round((acertos / len(intervals)) * 100.0, 2)
