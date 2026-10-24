"""Modelo Preditivo e Nowcasting Eleitoral (Estado-Espaço Hierárquico Calibrado).

Implementa o modelo preditivo oficial do projeto Margem Eleitoral:
- Agregação multi-escopo geográfica (Nacional, Estadual e Regional) com pós-estratificação
  pelo Colégio Eleitoral do TSE (5 macrorregiões: SE, NE, S, N, CO).
- Correção bayesiana de Efeitos de Casa (House Effects) intra-campanha e calibração empírica
  pós-1º Turno (ponderação exponencial pelo Erro Ponderado EP_T1 e de-biasing direcional).
- Extrapolação controlada de momentum (tendência linear local ponderada WLS).
- Simulação de Monte Carlo com caudas pesadas (Student-t, nu=5) para estimar probabilidades
  de vitória P(Vitória), intervalos de credibilidade de 95% e validação temporal retroativa
  (Point-in-Time Backtesting sem vazamento de dados futuros).
"""

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import polars as pl
import yaml

from src.analytics.metrics import calculate_mosteller_m5, calculate_weighted_poll_error
from src.transformations.schemas import (
    AbrangenciaEnum,
    PesquisaEleitoralSchema,
    ResultadoOficialTSESchema,
)

DEFAULT_MACRO_REGION_WEIGHTS: dict[str, float] = {
    "SE": 0.426,
    "NE": 0.271,
    "S": 0.147,
    "N": 0.086,
    "CO": 0.070,
}

REGION_NAMES: dict[str, str] = {
    "SE": "Sudeste",
    "NE": "Nordeste",
    "S": "Sul",
    "N": "Norte",
    "CO": "Centro-Oeste",
    "BR": "Colégio Eleitoral Nacional",
}

DEFAULT_SCOPE_WEIGHTS: dict[str, float] = {
    "NACIONAL": 1.00,
    "ESTADUAL": 0.75,
    "REGIONAL": 0.45,
}

DEFAULT_REGIONAL_DIFFERENTIALS: dict[int, dict[str, dict[str, float]]] = {
    2026: {
        "SE": {"Flávio Bolsonaro": 4.29, "Lula": -4.29},
        "NE": {"Flávio Bolsonaro": -17.0, "Lula": 17.0},
        "S": {"Flávio Bolsonaro": 12.5, "Lula": -12.5},
        "N": {"Flávio Bolsonaro": 2.0, "Lula": -2.0},
        "CO": {"Flávio Bolsonaro": 11.0, "Lula": -11.0},
    },
    2022: {
        "SE": {"Bolsonaro": 5.39, "Lula": -5.39},
        "NE": {"Bolsonaro": -19.5, "Lula": 19.5},
        "S": {"Bolsonaro": 13.8, "Lula": -13.8},
        "N": {"Bolsonaro": 1.8, "Lula": -1.8},
        "CO": {"Bolsonaro": 11.5, "Lula": -11.5},
    },
}


def balance_regional_differentials(
    differentials: dict[int, dict[str, dict[str, float]]],
    macro_weights: dict[str, float],
) -> dict[int, dict[str, dict[str, float]]]:
    """Garante a condição de soma-zero estrita dos diferenciais regionais no Colégio Eleitoral.

    Para cada ano e cada candidato, assegura que a soma ponderada dos diferenciais
    estruturais regionais pelas frações do eleitorado seja estritamente nula
    (sum_r w_r * D_{r, c} == 0.0). Caso exista deriva residual, redistribui subtraindo
    o drift ponderado de cada região.

    Args:
        differentials: Dicionário mapeando ano -> região -> candidato -> diferencial (em pp).
        macro_weights: Dicionário de pesos eleitorais oficiais por macrorregião (SE, NE, S, N, CO).

    Returns:
        dict[int, dict[str, dict[str, float]]]: Dicionário de diferenciais rebalanceados com soma-zero estrita.

    Raises:
        None.
    """
    sum_w = sum(macro_weights.values())
    if sum_w <= 0.0:
        return differentials

    norm_w = {r: w / sum_w for r, w in macro_weights.items()}
    balanced: dict[int, dict[str, dict[str, float]]] = {}

    for year, reg_dict in differentials.items():
        balanced[year] = {}
        candidates: set[str] = set()
        for cand_map in reg_dict.values():
            candidates.update(cand_map.keys())

        drift_cand: dict[str, float] = {}
        for c in candidates:
            drift = sum(
                norm_w.get(reg, 0.0) * float(reg_dict.get(reg, {}).get(c, 0.0))
                for reg in norm_w
            )
            drift_cand[c] = drift

        for reg in norm_w:
            balanced[year][reg] = {}
            for c in candidates:
                orig_d = float(reg_dict.get(reg, {}).get(c, 0.0))
                d_corr = orig_d - drift_cand[c]
                balanced[year][reg][c] = round(d_corr, 4)

    return balanced


@dataclass(frozen=True)
class PredictiveModelConfig:
    """Parâmetros de configuração do modelo preditivo Estado-Espaço Hierárquico Calibrado.

    Args:
        tau_days: Meia-vida exponencial (em dias) para decaimento temporal das pesquisas.
        momentum_window_days: Janela temporal (em dias) para regressão local WLS de tendência.
        audit_lambda: Coeficiente de penalização exponencial do Erro Ponderado do 1º Turno.
        shrinkage_alpha: Fator de encolhimento bayesiano para correção de viés direcional.
        unobserved_error_sigma: Erro sistêmico irredutível base da urna (em pontos percentuais).
        student_t_df: Graus de liberdade da distribuição t de Student para Monte Carlo.
        n_simulations: Número de sorteios estocásticos na simulação de Monte Carlo.
        random_seed: Semente pseudo-aleatória para reprodutibilidade científica.
        scope_weights: Multiplicadores de abrangência geográfica (NACIONAL, ESTADUAL, REGIONAL).
        macro_region_weights: Pesos do Colégio Eleitoral do TSE por macrorregião.
        regional_differentials: Diferenciais estruturais regionais por ciclo eleitoral.
        promotion_gates: Limiares formais de aprovação (Quality Gates MLE) no backtest.

    Returns:
        None.

    Raises:
        None.
    """

    tau_days: float = 7.0
    momentum_window_days: int = 14
    audit_lambda: float = 0.25
    shrinkage_alpha: float = 0.65
    unobserved_error_sigma: float = 1.60
    student_t_df: int = 5
    n_simulations: int = 10000
    random_seed: int = 42
    scope_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_SCOPE_WEIGHTS))
    macro_region_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_MACRO_REGION_WEIGHTS)
    )
    regional_differentials: dict[int, dict[str, dict[str, float]]] = field(
        default_factory=lambda: dict(DEFAULT_REGIONAL_DIFFERENTIALS)
    )
    promotion_gates: dict[str, float] = field(
        default_factory=lambda: {
            "brier_score_max": 0.20,
            "log_loss_max": 0.58,
            "ci_95_coverage_min": 0.80,
            "ep_reduction_vs_naive_min_pct": 10.0,
            "eve_winner_accuracy_min": 1.0,
        }
    )

    def __post_init__(self) -> None:
        """Garante a condição de soma-zero estrita dos diferenciais regionais no Colégio Eleitoral.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        balanced = balance_regional_differentials(
            self.regional_differentials, self.macro_region_weights
        )
        object.__setattr__(self, "regional_differentials", balanced)

    @classmethod
    def load_from_settings(cls, settings_path: str | Path | None = None) -> "PredictiveModelConfig":
        """Carrega os hiperparâmetros do modelo a partir do arquivo YAML de configuração.

        Args:
            settings_path: Caminho opcional para `config/settings.yaml`.

        Returns:
            PredictiveModelConfig: Instância imutável configurada com os parâmetros do projeto.

        Raises:
            None.
        """
        if settings_path is None:
            repo_root = Path(__file__).resolve().parent.parent.parent
            settings_path = repo_root / "config" / "settings.yaml"
        else:
            settings_path = Path(settings_path)

        if not settings_path.exists():
            return cls()

        try:
            with open(settings_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError):
            return cls()

        pm = data.get("predictive_model", {})
        ec = data.get("electoral_college", {})

        raw_macro = ec.get("macro_regions", DEFAULT_MACRO_REGION_WEIGHTS)
        macro_weights: dict[str, float] = {}
        for reg_k, reg_v in raw_macro.items():
            if isinstance(reg_v, dict):
                macro_weights[str(reg_k)] = float(reg_v.get("weight", 0.0))
            else:
                macro_weights[str(reg_k)] = float(reg_v)
        if not macro_weights:
            macro_weights = dict(DEFAULT_MACRO_REGION_WEIGHTS)

        raw_diffs = ec.get("regional_differentials", {})
        parsed_diffs: dict[int, dict[str, dict[str, float]]] = {}
        if any(str(k) in ("2022", "2026") for k in raw_diffs):
            for k, v in raw_diffs.items():
                try:
                    parsed_diffs[int(k)] = v
                except (ValueError, TypeError):
                    continue
        elif raw_diffs:
            # Formato indexado diretamente por macrorregião (SE, NE, S, N, CO)
            reg_map: dict[str, dict[str, float]] = {}
            for reg_k, cand_dict in raw_diffs.items():
                if isinstance(cand_dict, dict):
                    reg_map[str(reg_k)] = {str(ck): float(cv) for ck, cv in cand_dict.items()}
            parsed_diffs = {2022: reg_map, 2026: reg_map}

        if not parsed_diffs:
            parsed_diffs = dict(DEFAULT_REGIONAL_DIFFERENTIALS)

        parsed_diffs = balance_regional_differentials(parsed_diffs, macro_weights)

        raw_gates = pm.get("promotion_gates", {})
        normalized_gates = {
            "brier_score_max": float(
                raw_gates.get("brier_score_max", raw_gates.get("max_brier_score", 0.20))
            ),
            "log_loss_max": float(raw_gates.get("log_loss_max", 0.58)),
            "ci_95_coverage_min": float(
                raw_gates.get(
                    "ci_95_coverage_min",
                    float(raw_gates.get("min_coverage_95", 80.0)) / 100.0
                    if float(raw_gates.get("min_coverage_95", 0.80)) > 1.0
                    else raw_gates.get("min_coverage_95", 0.80),
                )
            ),
            "ep_reduction_vs_naive_min_pct": float(
                raw_gates.get("ep_reduction_vs_naive_min_pct", 10.0)
            ),
            "eve_winner_accuracy_min": float(raw_gates.get("eve_winner_accuracy_min", 1.0)),
        }

        return cls(
            tau_days=float(pm.get("tau_days", pm.get("half_life_days", 7.0))),
            momentum_window_days=int(
                pm.get("momentum_window_days", pm.get("trend_window_days", 14))
            ),
            audit_lambda=float(pm.get("audit_lambda", pm.get("t1_calibration_lambda", 0.25))),
            shrinkage_alpha=float(pm.get("shrinkage_alpha", pm.get("t1_bias_shrinkage", 0.65))),
            unobserved_error_sigma=float(
                pm.get("unobserved_error_sigma", pm.get("structural_tse_sigma", 1.60))
            ),
            student_t_df=int(pm.get("student_t_df", 5)),
            n_simulations=int(pm.get("n_simulations", 10000)),
            random_seed=int(pm.get("random_seed", 42)),
            scope_weights=dict(pm.get("scope_weights", DEFAULT_SCOPE_WEIGHTS)),
            macro_region_weights=macro_weights,
            regional_differentials=parsed_diffs,
            promotion_gates=normalized_gates,
        )


@dataclass(frozen=True)
class InstituteT1Calibration:
    """Credencial de calibração empírica de um instituto auditado contra a urna do 1º Turno.

    Args:
        instituto: Nome canônico do instituto de pesquisa.
        erro_ponderado_t1: Erro Ponderado (EP) apurado no 1º Turno contra o resultado oficial TSE.
        vies_direcional_t1: Viés direcional observado por candidato (p_hat - P_real) em pp.
        peso_auditoria: Multiplicador de precisão w_audit = exp(-lambda * EP_T1).
        n_pesquisas_t1: Total de levantamentos publicados pelo instituto no 1º Turno.

    Returns:
        None.

    Raises:
        None.
    """

    instituto: str
    erro_ponderado_t1: float
    vies_direcional_t1: dict[str, float]
    peso_auditoria: float
    n_pesquisas_t1: int


@dataclass(frozen=True)
class RegionalForecastSlice:
    """Fatia de projeção regional ponderada pelo Colégio Eleitoral do TSE.

    Args:
        regiao: Sigla da macrorregião ('SE', 'NE', 'S', 'N', 'CO' ou 'BR').
        nome_regiao: Nome por extenso da macrorregião.
        peso_eleitorado: Proporção do eleitorado nacional (0.0 a 1.0).
        n_pesquisas: Quantidade de levantamentos estaduais/regionais na macrorregião.
        votos_projetados: Votos válidos projetados por candidato na macrorregião (%).
        margem_lider: Diferença projetada entre os dois principais candidatos na região (pp).

    Returns:
        None.

    Raises:
        None.
    """

    regiao: str
    nome_regiao: str
    peso_eleitorado: float
    n_pesquisas: int
    votos_projetados: dict[str, float]
    margem_lider: float


@dataclass(frozen=True)
class CandidatePrediction:
    """Previsão probabilística de desempenho eleitoral para um candidato.

    Args:
        candidato: Nome do candidato.
        voto_esperado: Estimativa pontual esperada de votos válidos (%).
        ic_95_inferior: Limite inferior do intervalo de credibilidade de 95% (%).
        ic_95_superior: Limite superior do intervalo de credibilidade de 95% (%).
        probabilidade_vitoria: Probabilidade de terminar em 1º lugar (0.0 a 100.0%).
        probabilidade_vitoria_1_turno: Probabilidade de superar 50% dos votos válidos (0.0 a 100.0%).
        tendencia_diaria_pp: Taxa de variação diária recente (pp/dia).

    Returns:
        None.

    Raises:
        None.
    """

    candidato: str
    voto_esperado: float
    ic_95_inferior: float
    ic_95_superior: float
    probabilidade_vitoria: float
    probabilidade_vitoria_1_turno: float
    tendencia_diaria_pp: float


@dataclass(frozen=True)
class ElectionForecastResult:
    """Resultado consolidado da previsão e simulação estocástica da eleição.

    Args:
        ano: Ano do pleito eleitoral.
        turno: Turno eleitoral (1 ou 2).
        cutoff_date: Data de corte point-in-time utilizada na previsão.
        election_date: Data oficial de realização do pleito.
        dias_ate_eleicao: Dias restantes entre `cutoff_date` e `election_date`.
        n_pesquisas_utilizadas: Total de pesquisas até `cutoff_date` incorporadas no modelo.
        n_pesquisas_nacionais: Quantidade de pesquisas nacionais utilizadas.
        n_pesquisas_estaduais: Quantidade de pesquisas estaduais utilizadas.
        n_pesquisas_regionais: Quantidade de pesquisas regionais utilizadas.
        n_institutos: Quantidade de institutos distintos contribuindo para a previsão.
        calibrado_pos_t1: Indica se houve calibração empírica pós-1º Turno ativa.
        candidatos: Lista de previsões individuais ordenada pelo voto esperado decrescente.
        vencedor_previsto: Candidato com maior probabilidade de vitória.
        margem_esperada: Diferença esperada entre 1º e 2º colocados (pp).
        ic_95_margem: Intervalo de credibilidade de 95% para a margem entre 1º e 2º (pp).
        probabilidade_segundo_turno: Probabilidade de nenhum candidato atingir >50% no 1º Turno (%).
        distribuicao_simulada: Amostras simuladas de votos válidos por candidato.
        pesos_institutos: Participação percentual de cada instituto no estado latente final.
        agregacao_regional: Decomposição regional pós-estratificada pelo Colégio Eleitoral TSE.

    Returns:
        None.

    Raises:
        None.
    """

    ano: int
    turno: int
    cutoff_date: date
    election_date: date
    dias_ate_eleicao: int
    n_pesquisas_utilizadas: int
    n_pesquisas_nacionais: int
    n_pesquisas_estaduais: int
    n_pesquisas_regionais: int
    n_institutos: int
    calibrado_pos_t1: bool
    candidatos: list[CandidatePrediction]
    vencedor_previsto: str
    margem_esperada: float
    ic_95_margem: tuple[float, float]
    probabilidade_segundo_turno: float
    distribuicao_simulada: dict[str, list[float]]
    pesos_institutos: dict[str, float]
    agregacao_regional: list[RegionalForecastSlice]


def _get_regional_differential(
    year: int,
    regiao: str,
    candidate: str,
    config: PredictiveModelConfig,
) -> float:
    """Retorna o diferencial estrutural regional (em pp) de um candidato em relação à média nacional.

    Args:
        year: Ano eleitoral (2022 ou 2026).
        regiao: Sigla da macrorregião ('SE', 'NE', 'S', 'N', 'CO' ou 'BR').
        candidate: Nome do candidato.
        config: Configuração do modelo preditivo.

    Returns:
        float: Diferencial regional em pontos percentuais (0.0 para escopo 'BR').

    Raises:
        None.
    """
    if regiao == "BR" or not regiao:
        return 0.0
    year_diffs = config.regional_differentials.get(year, {})
    reg_diffs = year_diffs.get(regiao, {})
    return float(reg_diffs.get(candidate, 0.0))


def _project_poll_to_national_space(
    poll: PesquisaEleitoralSchema,
    candidates: Sequence[str],
    config: PredictiveModelConfig,
) -> dict[str, float]:
    """Projeta os votos válidos de uma pesquisa (nacional, estadual ou regional) no espaço nacional.

    Para pesquisas nacionais, mantém os percentuais originais. Para pesquisas estaduais ou
    regionais, subtrai o diferencial estrutural da macrorregião correspondente e renormaliza
    no simplex de votos válidos (soma = 100%).

    Args:
        poll: Levantamento eleitoral validado.
        candidates: Lista de candidatos avaliados.
        config: Configuração do modelo preditivo.

    Returns:
        dict[str, float]: Votos válidos projetados no espaço latente nacional (soma 100%).

    Raises:
        None.
    """
    if poll.abrangencia == AbrangenciaEnum.NACIONAL or poll.regiao == "BR":
        raw_vals = {c: float(poll.votos_validos.get(c, 0.0)) for c in candidates}
    else:
        raw_vals = {}
        for c in candidates:
            v_local = float(poll.votos_validos.get(c, 0.0))
            diff_reg = _get_regional_differential(poll.ano, poll.regiao, c, config)
            raw_vals[c] = max(0.1, v_local - diff_reg)

    total = sum(raw_vals.values())
    if total <= 0.0:
        return {c: 100.0 / max(1, len(candidates)) for c in candidates}
    return {c: (val / total) * 100.0 for c, val in raw_vals.items()}


def compute_first_round_institute_calibration(
    t1_polls: Sequence[PesquisaEleitoralSchema],
    t1_official_result: ResultadoOficialTSESchema,
    election_date_t1: date,
    audit_lambda: float = 0.25,
    cutoff_days: int = 7,
    config: PredictiveModelConfig | None = None,
) -> dict[str, InstituteT1Calibration]:
    """Audita o desempenho real de cada instituto no 1º Turno para calibrar o 2º Turno.

    Compara o último levantamento de cada instituto antes da eleição do 1º Turno contra
    a apuração oficial do TSE, extraindo o Erro Ponderado (EP_T1), o vetor de viés
    direcional por candidato e o peso de credibilidade exponencial.

    Args:
        t1_polls: Sequência de pesquisas do 1º Turno.
        t1_official_result: Resultado oficial consolidado do TSE para o 1º Turno.
        election_date_t1: Data oficial do 1º Turno.
        audit_lambda: Taxa de decaimento exponencial da penalização por erro (default: 0.25).
        cutoff_days: Janela preferencial de véspera em dias antes do 1º Turno (default: 7).
        config: Configuração opcional do modelo preditivo.

    Returns:
        dict[str, InstituteT1Calibration]: Mapa de instituto para suas credenciais de calibração.

    Raises:
        ValueError: Se `t1_polls` estiver vazio ou `audit_lambda` for negativo.
    """
    if not t1_polls:
        raise ValueError("A lista de pesquisas do 1º Turno não pode ser vazia para calibração.")
    if audit_lambda < 0.0:
        raise ValueError(
            f"O parâmetro audit_lambda deve ser não-negativo. Recebido: {audit_lambda}"
        )

    cfg = config or PredictiveModelConfig.load_from_settings()
    oficial_dict = t1_official_result.resultado_nominal
    candidates = list(oficial_dict.keys())

    # Agrupa pesquisas elegíveis (data_fim_campo <= election_date_t1) por instituto
    polls_by_inst: dict[str, list[PesquisaEleitoralSchema]] = {}
    for p in t1_polls:
        if p.data_fim_campo <= election_date_t1:
            polls_by_inst.setdefault(p.instituto_nome_fantasia, []).append(p)

    calibrations: dict[str, InstituteT1Calibration] = {}
    for inst, inst_polls in polls_by_inst.items():
        # Prioriza pesquisas nacionais na avaliação do erro nacional do 1º Turno
        nat_polls = [p for p in inst_polls if p.abrangencia == AbrangenciaEnum.NACIONAL]
        pool = nat_polls if nat_polls else inst_polls

        # Seleciona pesquisas na janela final (cutoff_days) ou a mais recente disponível
        recent_pool = [
            p for p in pool if 0 <= (election_date_t1 - p.data_fim_campo).days <= cutoff_days
        ]
        target_pool = recent_pool if recent_pool else pool
        latest_poll = max(target_pool, key=lambda x: (x.data_fim_campo, x.tamanho_amostra))

        projected_votes = _project_poll_to_national_space(latest_poll, candidates, cfg)
        ep_metrics = calculate_weighted_poll_error(
            votos_validos_estimados=projected_votes,
            resultado_oficial=oficial_dict,
        )
        ep_val = float(ep_metrics["erro_total_ponderado"])
        peso_audit = math.exp(-audit_lambda * ep_val)

        vies_cand = {
            c: round(float(projected_votes.get(c, 0.0)) - float(oficial_dict.get(c, 0.0)), 3)
            for c in candidates
        }

        calibrations[inst] = InstituteT1Calibration(
            instituto=inst,
            erro_ponderado_t1=round(ep_val, 2),
            vies_direcional_t1=vies_cand,
            peso_auditoria=round(peso_audit, 4),
            n_pesquisas_t1=len(inst_polls),
        )

    return calibrations


def compute_regional_electoral_breakdown(
    polls: Sequence[PesquisaEleitoralSchema],
    cutoff_date: date,
    candidates: Sequence[str],
    national_baseline: dict[str, float],
    config: PredictiveModelConfig,
    calibration_t1: dict[str, InstituteT1Calibration] | None = None,
) -> list[RegionalForecastSlice]:
    """Calcula a projeção regional por macrorregião e a síntese pós-estratificada do Colégio Eleitoral.

    Combina pesquisas estaduais e regionais de cada macrorregião (SE, NE, S, N, CO) com a
    âncora nacional ajustada pelos diferenciais regionais via encolhimento bayesiano, e
    aplica os pesos oficiais de eleitorado do TSE para obter o agregado nacional pós-estratificado.

    Args:
        polls: Pesquisas elegíveis até `cutoff_date`.
        cutoff_date: Data limite da previsão.
        candidates: Candidatos avaliados no pleito.
        national_baseline: Estimativa latente nacional base por candidato.
        config: Configuração do modelo preditivo.
        calibration_t1: Credenciais opcionais de calibração pós-1º Turno.

    Returns:
        list[RegionalForecastSlice]: Lista contendo as 5 macrorregiões e a síntese 'BR'.

    Raises:
        None.
    """
    if not polls or not candidates:
        return []

    year = polls[0].ano
    top_2 = sorted(candidates, key=lambda c: national_baseline.get(c, 0.0), reverse=True)[:2]
    c1 = top_2[0]
    c2 = top_2[1] if len(top_2) > 1 else c1

    slices: list[RegionalForecastSlice] = []
    synthesized_national: dict[str, float] = {c: 0.0 for c in candidates}

    for reg_code, reg_weight in config.macro_region_weights.items():
        reg_polls = [
            p
            for p in polls
            if p.abrangencia in (AbrangenciaEnum.ESTADUAL, AbrangenciaEnum.REGIONAL)
            and p.regiao == reg_code
        ]

        # Prior regional construído a partir do baseline nacional + diferencial estrutural da região
        prior_regional: dict[str, float] = {}
        for c in candidates:
            diff_reg = _get_regional_differential(year, reg_code, c, config)
            prior_regional[c] = max(0.1, national_baseline.get(c, 0.0) + diff_reg)
        sum_prior = sum(prior_regional.values())
        prior_regional = {c: (v / sum_prior) * 100.0 for c, v in prior_regional.items()}

        if reg_polls:
            local_weighted_sum = {c: 0.0 for c in candidates}
            total_w = 0.0
            for p in reg_polls:
                days_ago = max(0, (cutoff_date - p.data_fim_campo).days)
                w_time = math.exp(-days_ago / (config.tau_days * 1.5))
                n_eff = p.tamanho_amostra / max(1.0, p.deff_estimado)
                w_scope = config.scope_weights.get(p.abrangencia.value, 0.75)
                w_audit = (
                    calibration_t1[p.instituto_nome_fantasia].peso_auditoria
                    if calibration_t1 and p.instituto_nome_fantasia in calibration_t1
                    else 1.0
                )
                w = n_eff * w_time * w_scope * w_audit
                total_w += w
                for c in candidates:
                    # Aplica correção de viés do instituto se calibrado no T1
                    raw_c = float(p.votos_validos.get(c, 0.0))
                    if calibration_t1 and p.instituto_nome_fantasia in calibration_t1:
                        bias_t1 = calibration_t1[p.instituto_nome_fantasia].vies_direcional_t1.get(
                            c, 0.0
                        )
                        raw_c = max(0.1, raw_c - 0.50 * config.shrinkage_alpha * bias_t1)
                    local_weighted_sum[c] += w * raw_c

            local_avg = {c: local_weighted_sum[c] / max(1e-9, total_w) for c in candidates}
            sum_local = sum(local_avg.values())
            local_avg = {c: (v / max(1e-9, sum_local)) * 100.0 for c, v in local_avg.items()}

            # Peso empírico da evidência local vs prior regional (conjugação Normal-Normal)
            credibility_local = min(0.80, len(reg_polls) / (len(reg_polls) + 1.5))
            reg_proj = {
                c: credibility_local * local_avg[c] + (1.0 - credibility_local) * prior_regional[c]
                for c in candidates
            }
        else:
            reg_proj = dict(prior_regional)

        sum_reg = sum(reg_proj.values())
        reg_proj = {c: round((v / max(1e-9, sum_reg)) * 100.0, 2) for c, v in reg_proj.items()}

        for c in candidates:
            synthesized_national[c] += reg_weight * reg_proj[c]

        margem_reg = round(reg_proj.get(c1, 0.0) - reg_proj.get(c2, 0.0), 2)
        slices.append(
            RegionalForecastSlice(
                regiao=reg_code,
                nome_regiao=REGION_NAMES.get(reg_code, reg_code),
                peso_eleitorado=reg_weight,
                n_pesquisas=len(reg_polls),
                votos_projetados=reg_proj,
                margem_lider=margem_reg,
            )
        )

    sum_nat = sum(synthesized_national.values())
    synthesized_national = {
        c: round((v / max(1e-9, sum_nat)) * 100.0, 2) for c, v in synthesized_national.items()
    }
    total_subnational = sum(s.n_pesquisas for s in slices)
    slices.append(
        RegionalForecastSlice(
            regiao="BR",
            nome_regiao=REGION_NAMES["BR"],
            peso_eleitorado=1.0,
            n_pesquisas=total_subnational,
            votos_projetados=synthesized_national,
            margem_lider=round(
                synthesized_national.get(c1, 0.0) - synthesized_national.get(c2, 0.0), 2
            ),
        )
    )
    return slices


def predict_election_outcome(
    polls: Sequence[PesquisaEleitoralSchema],
    election_date: date,
    cutoff_date: date | None = None,
    turno: int = 1,
    calibration_t1: dict[str, InstituteT1Calibration] | None = None,
    config: PredictiveModelConfig | None = None,
) -> ElectionForecastResult:
    """Executa o Modelo Estado-Espaço Hierárquico Calibrado para prever o resultado eleitoral.

    Integra pesquisas Nacionais, Estaduais e Regionais estritamente até `cutoff_date`
    (sem vazamento de dados futuros), aplica ponderação de precisão amostral efetiva (n/deff),
    decaimento temporal exponencial, correção de House Effects intra-campanha, calibração
    pós-1º Turno, pós-estratificação pelo Colégio Eleitoral do TSE, extrapolação controlada
    de momentum (WLS) e simulação de Monte Carlo Student-t (N=10.000).

    Args:
        polls: Sequência de pesquisas eleitorais do turno avaliado.
        election_date: Data oficial de votação do pleito.
        cutoff_date: Data limite para corte point-in-time (default: `election_date`).
        turno: Turno eleitoral (1 ou 2).
        calibration_t1: Dicionário opcional com a calibração empírica pós-1º Turno por instituto.
        config: Parâmetros de configuração do modelo (default: carregados de `settings.yaml`).

    Returns:
        ElectionForecastResult: Objeto completo contendo probabilidades de vitória, votos
            esperados, intervalos de credibilidade de 95% e decomposição regional.

    Raises:
        ValueError: Se nenhuma pesquisa for encontrada até `cutoff_date`.
    """
    cfg = config or PredictiveModelConfig.load_from_settings()
    effective_cutoff = cutoff_date if cutoff_date is not None else election_date
    if effective_cutoff > election_date:
        effective_cutoff = election_date

    eligible_polls = [p for p in polls if p.data_fim_campo <= effective_cutoff]
    if not eligible_polls:
        raise ValueError(
            f"Nenhuma pesquisa disponível com data_fim_campo <= {effective_cutoff.isoformat()}."
        )

    year = eligible_polls[0].ano
    dias_ate_eleicao = max(0, (election_date - effective_cutoff).days)

    # Identifica todos os candidatos presentes nas pesquisas elegíveis
    candidate_set: set[str] = set()
    for p in eligible_polls:
        candidate_set.update(p.votos_validos.keys())
    candidates = sorted(candidate_set)

    # 1. Projeta todas as pesquisas elegíveis no espaço latente nacional e calcula pesos compostos
    projected_list: list[dict[str, float]] = []
    weights: list[float] = []
    days_ago_list: list[int] = []
    institutes_list: list[str] = []

    for p in eligible_polls:
        proj = _project_poll_to_national_space(p, candidates, cfg)
        projected_list.append(proj)

        d_ago = max(0, (effective_cutoff - p.data_fim_campo).days)
        days_ago_list.append(d_ago)

        w_time = math.exp(-d_ago / cfg.tau_days)
        n_eff = p.tamanho_amostra / max(1.0, p.deff_estimado)
        w_scope = cfg.scope_weights.get(p.abrangencia.value, 1.0)
        w_audit = (
            calibration_t1[p.instituto_nome_fantasia].peso_auditoria
            if calibration_t1 and p.instituto_nome_fantasia in calibration_t1
            else 1.0
        )

        # Pesquisas presenciais domiciliares possuem menor erro de cobertura estrutural
        method_val = p.metodologia.value if hasattr(p.metodologia, "value") else str(p.metodologia)
        w_method = 1.15 if "PRESENCIAL_DOMICILIAR" in method_val else 1.0

        w_total = n_eff * w_time * w_scope * w_audit * w_method
        weights.append(w_total)
        institutes_list.append(p.instituto_nome_fantasia)

    w_arr = np.array(weights, dtype=float)
    w_norm = w_arr / np.sum(w_arr)

    # 2. Consenso preliminar para estimativa de House Effects intra-campanha (sem vazamento temporal)
    prelim_consensus: dict[str, float] = {}
    for c in candidates:
        vals = np.array([proj[c] for proj in projected_list], dtype=float)
        prelim_consensus[c] = float(np.sum(w_norm * vals))

    # Calcula viés relativo intra-campanha (peer house effect) por instituto com encolhimento
    inst_peer_bias: dict[str, dict[str, float]] = {}
    unique_insts = sorted(set(institutes_list))
    for inst in unique_insts:
        idxs = [i for i, name in enumerate(institutes_list) if name == inst]
        n_inst = len(idxs)
        shrink_peer = n_inst / (n_inst + 2.0)
        inst_peer_bias[inst] = {}
        for c in candidates:
            # Compara cada pesquisa do instituto com a média ponderada temporal próxima
            residuals: list[float] = []
            for idx in idxs:
                t_i = eligible_polls[idx].data_fim_campo
                peer_idxs = [
                    j
                    for j in range(len(eligible_polls))
                    if j != idx
                    and institutes_list[j] != inst
                    and abs((eligible_polls[j].data_fim_campo - t_i).days) <= 10
                ]
                if len(peer_idxs) >= 2:
                    peer_n_eff = np.array(
                        [
                            eligible_polls[j].tamanho_amostra
                            / max(1.0, eligible_polls[j].deff_estimado)
                            for j in peer_idxs
                        ],
                        dtype=float,
                    )
                    peer_dt = np.array(
                        [
                            abs((eligible_polls[j].data_fim_campo - t_i).days)
                            for j in peer_idxs
                        ],
                        dtype=float,
                    )
                    peer_time_w = np.exp(-peer_dt / cfg.tau_days)
                    peer_w = peer_n_eff * peer_time_w
                    peer_v = np.array([projected_list[j][c] for j in peer_idxs], dtype=float)
                    peer_mean = float(np.sum(peer_w * peer_v) / np.sum(peer_w))
                else:
                    peer_mean = prelim_consensus[c]
                residuals.append(projected_list[idx][c] - peer_mean)
            inst_peer_bias[inst][c] = float(np.mean(residuals)) * shrink_peer

    # 3. De-biasing das pesquisas combinando House Effects intra-campanha e Calibração Pós-1º Turno
    debiased_list: list[dict[str, float]] = []
    for idx, p in enumerate(eligible_polls):
        inst = p.instituto_nome_fantasia
        proj = projected_list[idx]
        corr_votes: dict[str, float] = {}
        for c in candidates:
            peer_b = inst_peer_bias.get(inst, {}).get(c, 0.0)
            if (
                calibration_t1
                and inst in calibration_t1
                and c in calibration_t1[inst].vies_direcional_t1
            ):
                t1_b = calibration_t1[inst].vies_direcional_t1[c]
                # Combina correção empírica da urna do 1º Turno com o efeito de casa do 2º Turno
                combined_bias = (
                    0.55 * cfg.shrinkage_alpha * t1_b + 0.45 * cfg.shrinkage_alpha * peer_b
                )
            else:
                combined_bias = cfg.shrinkage_alpha * peer_b
            corr_votes[c] = max(0.05, proj[c] - combined_bias)

        s_corr = sum(corr_votes.values())
        debiased_list.append({c: (v / s_corr) * 100.0 for c, v in corr_votes.items()})

    # 4. Estado latente nacional filtrado e tendência linear local (WLS Momentum)
    latent_level: dict[str, float] = {}
    daily_slopes: dict[str, float] = {}

    recent_mask = np.array([d <= cfg.momentum_window_days for d in days_ago_list], dtype=bool)
    has_momentum_window = int(np.sum(recent_mask)) >= 4

    has_national_polls = any(p.abrangencia == AbrangenciaEnum.NACIONAL for p in eligible_polls)
    if has_national_polls:
        base_mask = np.array(
            [p.abrangencia == AbrangenciaEnum.NACIONAL for p in eligible_polls], dtype=bool
        )
        w_base = w_arr[base_mask] / np.sum(w_arr[base_mask])
    else:
        base_mask = np.ones(len(eligible_polls), dtype=bool)
        w_base = w_norm

    for c in candidates:
        y_vec = np.array([d[c] for d in debiased_list], dtype=float)
        base_est = float(np.sum(w_base * y_vec[base_mask]))
        slope = 0.0

        if has_momentum_window:
            t_rel = -np.array(days_ago_list, dtype=float)[recent_mask]  # [-14 .. 0]
            y_rec = y_vec[recent_mask]
            w_rec = w_norm[recent_mask]
            w_rec = w_rec / np.sum(w_rec)
            t_mean = float(np.sum(w_rec * t_rel))
            y_mean = float(np.sum(w_rec * y_rec))
            var_t = float(np.sum(w_rec * ((t_rel - t_mean) ** 2)))
            if var_t > 1.0:
                cov_ty = float(np.sum(w_rec * (t_rel - t_mean) * (y_rec - y_mean)))
                raw_slope = cov_ty / var_t
                # Limita a inclinação diária para evitar extrapolações explosivas
                slope = float(np.clip(raw_slope, -0.35, 0.35))

        # Extrapola tendência com amortecimento exponencial até o dia da eleição (máx 4 dias efetivos)
        if dias_ate_eleicao <= 0:
            late_drift = 0.0
        else:
            effective_horizon = min(4.0, dias_ate_eleicao * math.exp(-dias_ate_eleicao / 20.0))
            # Se também houver pesquisas na janela final, incorpora o drift de última hora intra-janela
            late_drift = slope * min(2.0, effective_horizon + 1.25)

        latent_level[c] = max(0.05, base_est + late_drift)
        daily_slopes[c] = round(slope, 3)

    sum_latent = sum(latent_level.values())
    latent_level = {c: (v / sum_latent) * 100.0 for c, v in latent_level.items()}

    # 5. Pós-estratificação pelo Colégio Eleitoral do TSE (5 macrorregiões)
    regional_slices = compute_regional_electoral_breakdown(
        polls=eligible_polls,
        cutoff_date=effective_cutoff,
        candidates=candidates,
        national_baseline=latent_level,
        config=cfg,
        calibration_t1=calibration_t1,
    )

    subnational_count = sum(
        1
        for p in eligible_polls
        if p.abrangencia in (AbrangenciaEnum.ESTADUAL, AbrangenciaEnum.REGIONAL)
    )
    if regional_slices and subnational_count > 0:
        br_slice = regional_slices[-1]
        # Combina o estimador nacional direto com a síntese pós-estratificada do Colégio Eleitoral
        blend_geo = min(0.35, subnational_count / (len(eligible_polls) + 5.0))
        final_expected = {
            c: (1.0 - blend_geo) * latent_level[c]
            + blend_geo * br_slice.votos_projetados.get(c, latent_level[c])
            for c in candidates
        }
    else:
        final_expected = dict(latent_level)

    sum_final = sum(final_expected.values())
    final_expected = {c: (v / sum_final) * 100.0 for c, v in final_expected.items()}

    # 6. Quantificação de Incerteza Total e Simulação de Monte Carlo Student-t (nu = 5)
    # Combina variância amostral efetiva + dispersão entre institutos + erro sistêmico de urna
    horizon_uncertainty_factor = 1.0 + 0.035 * dias_ate_eleicao
    cand_sigmas: dict[str, float] = {}
    for c in candidates:
        y_vec = np.array([d[c] for d in debiased_list], dtype=float)
        mu_c = final_expected[c]
        between_var = float(np.sum(w_norm * ((y_vec - mu_c) ** 2)))
        # Variância amostral média ponderada
        avg_n_eff = float(
            np.sum(
                w_norm
                * np.array(
                    [p.tamanho_amostra / max(1.0, p.deff_estimado) for p in eligible_polls],
                    dtype=float,
                )
            )
        )
        p_prop = max(0.01, min(0.99, mu_c / 100.0))
        sampling_var = (p_prop * (1.0 - p_prop) / max(100.0, avg_n_eff)) * 10000.0

        # Candidatos menores possuem incerteza proporcional à sua ordem de grandeza
        scale_factor = min(1.0, max(0.15, mu_c / 35.0))
        sys_sigma = cfg.unobserved_error_sigma * scale_factor * horizon_uncertainty_factor
        total_sigma = math.sqrt(sampling_var + 0.35 * between_var + (sys_sigma**2))
        cand_sigmas[c] = max(0.15, total_sigma)

    rng = np.random.default_rng(cfg.random_seed + dias_ate_eleicao + turno * 100)
    n_cands = len(candidates)
    mu_vec = np.array([final_expected[c] for c in candidates], dtype=float)
    sigma_vec = np.array([cand_sigmas[c] for c in candidates], dtype=float)

    # Sorteios t-Student com preservação estrita do desvio padrão no simplex de votos válidos
    t_scale = (
        math.sqrt((cfg.student_t_df - 2.0) / cfg.student_t_df) if cfg.student_t_df > 2 else 1.0
    )
    if n_cands == 2:
        # No simplex bidimensional (p1 + p2 = 100), choques são estritamente antissimétricos
        sigma_shared = max(sigma_vec[0], sigma_vec[1])
        t_draw = rng.standard_t(df=cfg.student_t_df, size=(cfg.n_simulations, 1))
        shock_1 = t_draw * t_scale * sigma_shared
        shocks = np.hstack([shock_1, -shock_1])
        raw_sims = np.clip(mu_vec + shocks, 0.01, 99.99)
        row_sums = np.sum(raw_sims, axis=1, keepdims=True)
        sim_matrix = (raw_sims / row_sums) * 100.0
    else:
        # Para C >= 3, centraliza os choques e corrige a variância pelo fator sqrt(C / (C - 1))
        t_draws = rng.standard_t(df=cfg.student_t_df, size=(cfg.n_simulations, n_cands))
        raw_shocks = t_draws * t_scale * sigma_vec
        centered_shocks = raw_shocks - np.mean(raw_shocks, axis=1, keepdims=True)
        scaling_simplex = math.sqrt(n_cands / (n_cands - 1.0))
        shocks = centered_shocks * scaling_simplex
        raw_sims = np.clip(mu_vec + shocks, 0.01, 99.99)
        row_sums = np.sum(raw_sims, axis=1, keepdims=True)
        sim_matrix = (raw_sims / row_sums) * 100.0

    # Vencedor em cada simulação
    winners_idx = np.argmax(sim_matrix, axis=1)

    cand_predictions: list[CandidatePrediction] = []
    for idx, c in enumerate(candidates):
        col = sim_matrix[:, idx]
        ic_low, ic_high = np.percentile(col, [2.5, 97.5])
        prob_win = float(np.mean(winners_idx == idx) * 100.0)
        prob_r1_win = float(np.mean(col > 50.0) * 100.0)

        cand_predictions.append(
            CandidatePrediction(
                candidato=c,
                voto_esperado=round(float(mu_vec[idx]), 2),
                ic_95_inferior=round(float(ic_low), 2),
                ic_95_superior=round(float(ic_high), 2),
                probabilidade_vitoria=round(prob_win, 2),
                probabilidade_vitoria_1_turno=round(prob_r1_win, 2),
                tendencia_diaria_pp=daily_slopes[c],
            )
        )

    cand_predictions.sort(key=lambda x: x.voto_esperado, reverse=True)
    leader = cand_predictions[0]
    runner_up = cand_predictions[1] if len(cand_predictions) > 1 else leader

    idx_leader = candidates.index(leader.candidato)
    idx_runner = candidates.index(runner_up.candidato)
    margin_sims = sim_matrix[:, idx_leader] - sim_matrix[:, idx_runner]
    m_low, m_high = np.percentile(margin_sims, [2.5, 97.5])

    max_vote_per_sim = np.max(sim_matrix, axis=1)
    prob_second_round = (
        round(float(np.mean(max_vote_per_sim <= 50.0) * 100.0), 2) if turno == 1 else 0.0
    )

    # Pesos consolidados por instituto (em %)
    inst_weights_pct: dict[str, float] = {}
    for inst_name, w_val in zip(institutes_list, w_norm):
        inst_weights_pct[inst_name] = inst_weights_pct.get(inst_name, 0.0) + float(w_val * 100.0)
    inst_weights_pct = {
        k: round(v, 2)
        for k, v in sorted(inst_weights_pct.items(), key=lambda item: item[1], reverse=True)
    }

    # Subamostra de 1.000 sorteios por candidato para visualização leve na UI
    viz_step = max(1, cfg.n_simulations // 1000)
    dist_sim: dict[str, list[float]] = {
        c: [round(float(x), 2) for x in sim_matrix[::viz_step, idx]]
        for idx, c in enumerate(candidates)
    }

    n_nat = sum(1 for p in eligible_polls if p.abrangencia == AbrangenciaEnum.NACIONAL)
    n_est = sum(1 for p in eligible_polls if p.abrangencia == AbrangenciaEnum.ESTADUAL)
    n_reg = sum(1 for p in eligible_polls if p.abrangencia == AbrangenciaEnum.REGIONAL)

    return ElectionForecastResult(
        ano=year,
        turno=turno,
        cutoff_date=effective_cutoff,
        election_date=election_date,
        dias_ate_eleicao=dias_ate_eleicao,
        n_pesquisas_utilizadas=len(eligible_polls),
        n_pesquisas_nacionais=n_nat,
        n_pesquisas_estaduais=n_est,
        n_pesquisas_regionais=n_reg,
        n_institutos=len(unique_insts),
        calibrado_pos_t1=bool(calibration_t1),
        candidatos=cand_predictions,
        vencedor_previsto=leader.candidato,
        margem_esperada=round(leader.voto_esperado - runner_up.voto_esperado, 2),
        ic_95_margem=(round(float(m_low), 2), round(float(m_high), 2)),
        probabilidade_segundo_turno=prob_second_round,
        distribuicao_simulada=dist_sim,
        pesos_institutos=inst_weights_pct,
        agregacao_regional=regional_slices,
    )


def _compute_naive_baseline_estimate(
    eligible_polls: Sequence[PesquisaEleitoralSchema],
    candidates: Sequence[str],
) -> dict[str, float]:
    """Calcula a média simples cumulativa não calibrada (Baseline Ingênuo) das pesquisas.

    Toma a média aritmética simples (pesos iguais, sem decaimento temporal, sem ajuste
    de House Effects, sem pós-estratificação geográfica e sem calibração pós-1º Turno)
    de todas as pesquisas brutas disponíveis até a data de corte.

    Args:
        eligible_polls: Pesquisas disponíveis até a data de corte.
        candidates: Lista de candidatos avaliados.

    Returns:
        dict[str, float]: Estimativa percentual ingênua por candidato.

    Raises:
        None.
    """
    pool = list(eligible_polls)

    avg_dict: dict[str, float] = {}
    for c in candidates:
        avg_dict[c] = float(np.mean([float(p.votos_validos.get(c, 0.0)) for p in pool]))
    total = sum(avg_dict.values())
    if total <= 0.0:
        return {c: 100.0 / max(1, len(candidates)) for c in candidates}
    return {c: (v / total) * 100.0 for c, v in avg_dict.items()}


def run_point_in_time_backtest(
    polls: Sequence[PesquisaEleitoralSchema],
    tse_result: ResultadoOficialTSESchema,
    election_date: date,
    horizons_days: Sequence[int] = (30, 21, 14, 7, 3, 1),
    calibration_t1: dict[str, InstituteT1Calibration] | None = None,
    config: PredictiveModelConfig | None = None,
) -> pl.DataFrame:
    """Executa o backtesting histórico point-in-time em múltiplos horizontes antes da eleição.

    Para cada horizonte `h` (em dias antes da eleição), trunca os dados estritamente em
    `cutoff_date = election_date - timedelta(days=h)` e compara as previsões do modelo
    Estado-Espaço Hierárquico Calibrado contra o resultado oficial do TSE e contra o
    baseline ingênuo (média móvel simples sem calibração).

    Args:
        polls: Conjunto completo de pesquisas do turno avaliado.
        tse_result: Resultado oficial consolidado pelo TSE.
        election_date: Data oficial da eleição.
        horizons_days: Sequência de horizontes em dias antes do pleito (default: 30, 21, 14, 7, 3, 1).
        calibration_t1: Dicionário opcional de calibração pós-1º Turno.
        config: Configuração opcional do modelo preditivo.

    Returns:
        pl.DataFrame: Tabela detalhada de métricas por horizonte temporal.

    Raises:
        ValueError: Se `polls` for vazio.
    """
    if not polls:
        raise ValueError("A lista de pesquisas não pode ser vazia para o backtest.")

    cfg = config or PredictiveModelConfig.load_from_settings()
    oficial = tse_result.resultado_nominal
    sorted_real = sorted(oficial.keys(), key=lambda c: oficial[c], reverse=True)
    true_winner = sorted_real[0]
    true_runner_up = sorted_real[1] if len(sorted_real) > 1 else true_winner
    true_w_share = float(oficial[true_winner])
    true_r_share = float(oficial[true_runner_up])

    turno = polls[0].turno
    rows: list[dict[str, Any]] = []

    for h in sorted(horizons_days, reverse=True):
        cutoff = election_date - timedelta(days=int(h))
        eligible = [p for p in polls if p.data_fim_campo <= cutoff]
        if not eligible:
            continue

        forecast = predict_election_outcome(
            polls=eligible,
            election_date=election_date,
            cutoff_date=cutoff,
            turno=turno,
            calibration_t1=calibration_t1,
            config=cfg,
        )

        pred_map = {cp.candidato: cp for cp in forecast.candidatos}
        model_estimates = {cp.candidato: cp.voto_esperado for cp in forecast.candidatos}

        # Métricas do Modelo Estado-Espaço Calibrado
        ep_model_dict = calculate_weighted_poll_error(
            votos_validos_estimados=model_estimates,
            resultado_oficial=oficial,
        )
        ep_model = float(ep_model_dict["erro_total_ponderado"])
        m5_model = calculate_mosteller_m5(
            p_hat_1=model_estimates.get(true_winner, 0.0),
            p_hat_2=model_estimates.get(true_runner_up, 0.0),
            p_true_1=true_w_share,
            p_true_2=true_r_share,
        )

        # Métricas do Baseline Ingênuo (Média Móvel Simples não calibrada)
        naive_estimates = _compute_naive_baseline_estimate(eligible, list(oficial.keys()))
        ep_naive_dict = calculate_weighted_poll_error(
            votos_validos_estimados=naive_estimates,
            resultado_oficial=oficial,
        )
        ep_naive = float(ep_naive_dict["erro_total_ponderado"])
        m5_naive = calculate_mosteller_m5(
            p_hat_1=naive_estimates.get(true_winner, 0.0),
            p_hat_2=naive_estimates.get(true_runner_up, 0.0),
            p_true_1=true_w_share,
            p_true_2=true_r_share,
        )

        # Brier Score e Log-Loss para o vencedor oficial
        p_win_true = max(1e-4, min(1.0 - 1e-4, pred_map[true_winner].probabilidade_vitoria / 100.0))
        brier_score = (1.0 - p_win_true) ** 2
        log_loss = -math.log(p_win_true)

        # Cobertura empírica do IC 95% nos 2 principais candidatos
        covered_count = 0
        for c_eval in (true_winner, true_runner_up):
            cp = pred_map[c_eval]
            real_v = float(oficial[c_eval])
            if cp.ic_95_inferior <= real_v <= cp.ic_95_superior:
                covered_count += 1
        coverage_top2 = (covered_count / 2.0) * 100.0

        reducao_ep_pct = (
            ((ep_naive - ep_model) / max(1e-6, ep_naive)) * 100.0 if ep_naive > 0.0 else 0.0
        )

        rows.append(
            {
                "horizonte_dias": int(h),
                "data_corte": cutoff,
                "n_pesquisas": forecast.n_pesquisas_utilizadas,
                "vencedor_previsto": forecast.vencedor_previsto,
                "vencedor_real": true_winner,
                "acerto_vencedor": forecast.vencedor_previsto == true_winner,
                "prob_vitoria_vencedor_real": round(p_win_true * 100.0, 2),
                "voto_previsto_lider_real": pred_map[true_winner].voto_esperado,
                "voto_real_lider": round(true_w_share, 2),
                "ic_95_inf_lider": pred_map[true_winner].ic_95_inferior,
                "ic_95_sup_lider": pred_map[true_winner].ic_95_superior,
                "voto_previsto_vice_real": pred_map[true_runner_up].voto_esperado,
                "voto_real_vice": round(true_r_share, 2),
                "ic_95_inf_vice": pred_map[true_runner_up].ic_95_inferior,
                "ic_95_sup_vice": pred_map[true_runner_up].ic_95_superior,
                "erro_margem_m5_modelo": round(m5_model, 2),
                "erro_margem_m5_baseline": round(m5_naive, 2),
                "erro_ponderado_modelo": round(ep_model, 2),
                "erro_ponderado_baseline": round(ep_naive, 2),
                "reducao_erro_vs_baseline_pct": round(reducao_ep_pct, 2),
                "brier_score": round(brier_score, 4),
                "log_loss": round(log_loss, 4),
                "cobertura_ic95_pct": round(coverage_top2, 1),
            }
        )

    return pl.DataFrame(rows)


def evaluate_promotion_gates(
    backtest_df: pl.DataFrame,
    config: PredictiveModelConfig | None = None,
) -> dict[str, Any]:
    """Avalia os portões formais de qualidade e promoção (Quality Gates MLE) sobre o backtest.

    Verifica na véspera (T - 1 dia) e ao longo dos horizontes se o modelo supera o baseline
    ingênuo e cumpre os requisitos de calibração probabilística (Brier Score, Log-Loss,
    Cobertura IC 95% e Acurácia de Vencedor).

    Args:
        backtest_df: Polars DataFrame gerado por `run_point_in_time_backtest`.
        config: Configuração opcional contendo os limiares `promotion_gates`.

    Returns:
        dict[str, Any]: Dicionário com o status global (`promoted: bool`) e métricas auditadas.

    Raises:
        ValueError: Se `backtest_df` estiver vazio.
    """
    if backtest_df.height == 0:
        raise ValueError("O DataFrame de backtest não pode ser vazio para avaliação de gates.")

    cfg = config or PredictiveModelConfig.load_from_settings()
    gates = cfg.promotion_gates

    # Seleciona o horizonte mais próximo da eleição (ex.: T-1d ou menor horizonte disponível)
    min_h = int(backtest_df["horizonte_dias"].min())
    eve_row = backtest_df.filter(pl.col("horizonte_dias") == min_h).to_dicts()[0]

    mean_brier = float(backtest_df["brier_score"].mean())
    eve_brier = float(eve_row["brier_score"])
    eve_logloss = float(eve_row["log_loss"])
    mean_coverage = float(backtest_df["cobertura_ic95_pct"].mean()) / 100.0
    eve_ep_reduction = float(eve_row["reducao_erro_vs_baseline_pct"])
    mean_ep_reduction = float(backtest_df["reducao_erro_vs_baseline_pct"].mean())
    eve_winner_ok = bool(eve_row["acerto_vencedor"])

    checks = {
        "brier_score_ok": eve_brier <= gates.get("brier_score_max", 0.20),
        "log_loss_ok": eve_logloss <= gates.get("log_loss_max", 0.58),
        "coverage_ok": mean_coverage >= gates.get("ci_95_coverage_min", 0.80),
        "ep_reduction_ok": max(eve_ep_reduction, mean_ep_reduction)
        >= gates.get("ep_reduction_vs_naive_min_pct", 10.0),
        "winner_accuracy_ok": eve_winner_ok,
    }

    return {
        "promoted": all(checks.values()),
        "checks": checks,
        "metrics": {
            "eve_brier_score": round(eve_brier, 4),
            "mean_brier_score": round(mean_brier, 4),
            "eve_log_loss": round(eve_logloss, 4),
            "mean_ci95_coverage": round(mean_coverage * 100.0, 1),
            "eve_ep_reduction_pct": round(eve_ep_reduction, 2),
            "mean_ep_reduction_pct": round(mean_ep_reduction, 2),
            "eve_winner_correct": eve_winner_ok,
        },
        "thresholds": gates,
    }
