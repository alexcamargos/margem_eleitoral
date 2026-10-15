"""Decomposição de variância e efeitos de instituto (House Effects) e metodologia.

Utiliza modelos lineares (GLM/OLS) e ANOVA com statsmodels para isolar
se desvios observados são sistemáticos de determinados institutos ou metodologias
(presencial vs. telefônica vs. online).
"""

from typing import Any, Sequence

import pandas as pd
import polars as pl
import scipy.stats as stats
import statsmodels.api as sm
from statsmodels.formula.api import ols

from src.transformations.schemas import PesquisaEleitoralSchema


def fit_house_effects_model(
    df_polls: pl.DataFrame,
    target_candidate: str = "Lula",
    p_true: float = 48.43,
) -> dict[str, Any]:
    """Ajusta modelo de regressão para identificar efeitos de instituto e metodologia.

    Modela o resíduo da estimativa frente ao resultado oficial da urna:
    Resíduo_i = (p_hat_i - P_true) = beta_0 + beta_instituto * I_i + beta_metodo * M_i + eps_i

    Args:
        df_polls: Polars DataFrame contendo colunas 'instituto_nome_fantasia',
            'metodologia' e 'validos_{target_candidate}'.
        target_candidate: Nome do candidato a ser avaliado (default: 'Lula').
        p_true: Votação oficial apurada pelo TSE em percentual de votos válidos.

    Returns:
        dict[str, Any]: Dicionário contendo:
            - r_squared: Coeficiente de determinação R² do modelo.
            - institute_effects: Dicionário de institutos com seu coeficiente de viés e p-valor.
            - methodology_effects: Dicionário de metodologias com coeficiente e p-valor.
            - p_val_institutes_anova: Valor-p do teste F para o fator Instituto.
            - p_val_methodology_anova: Valor-p do teste F para o fator Metodologia.

    Raises:
        ValueError: Se a coluna do candidato não estiver no DataFrame ou se houver
            menos de 5 observações.
    """
    col_name = f"validos_{target_candidate}"
    if col_name not in df_polls.columns:
        raise ValueError(
            f"Coluna '{col_name}' não encontrada no DataFrame. Disponíveis: {df_polls.columns}"
        )

    if df_polls.height < 5:
        raise ValueError(
            f"Número insuficiente de pesquisas para estimar house effects: {df_polls.height}"
        )

    pdf = df_polls.select(["instituto_nome_fantasia", "metodologia", col_name]).to_pandas()

    pdf["residuo"] = pdf[col_name] - p_true
    pdf["instituto"] = pdf["instituto_nome_fantasia"].astype(str)
    pdf["metodologia"] = pdf["metodologia"].astype(str)

    n_obs = len(pdf)
    n_inst = pdf["instituto"].nunique()
    n_meth = pdf["metodologia"].nunique()

    # Verifica se cada instituto adota exclusivamente uma única metodologia (aninhamento)
    is_nested = bool(pdf.groupby("instituto")["metodologia"].nunique().max() == 1)

    # Seleção da fórmula principal para institutos
    if not is_nested and (n_inst + n_meth < n_obs) and n_inst > 1 and n_meth > 1:
        formula_main = "residuo ~ C(instituto) + C(metodologia)"
    elif n_inst > 1 and (n_inst + 1 < n_obs):
        formula_main = "residuo ~ C(instituto)"
    elif n_meth > 1 and (n_meth + 1 < n_obs):
        formula_main = "residuo ~ C(metodologia)"
    else:
        formula_main = "residuo ~ 1"

    model = ols(formula_main, data=pdf).fit()

    p_inst_f = 1.0
    p_meth_f = 1.0
    if model.df_resid > 0:
        try:
            anova_table = sm.stats.anova_lm(model, typ=2)
            if "C(instituto)" in anova_table.index:
                p_val_raw = anova_table.loc["C(instituto)", "PR(>F)"]
                p_inst_f = float(p_val_raw) if pd.notna(p_val_raw) else 1.0
            if "C(metodologia)" in anova_table.index:
                p_val_raw = anova_table.loc["C(metodologia)", "PR(>F)"]
                p_meth_f = float(p_val_raw) if pd.notna(p_val_raw) else 1.0
        except Exception:
            # Fallback seguro caso a matriz de covariância apresente singularidade
            pass

    # Extrai efeitos dos institutos
    inst_effects: dict[str, dict[str, float]] = {}
    for param_name, coef in model.params.items():
        if "C(instituto)" in param_name:
            clean_name = param_name.replace("C(instituto)[T.", "").replace("]", "")
            pval = (
                float(model.pvalues[param_name])
                if param_name in model.pvalues and pd.notna(model.pvalues[param_name])
                else 1.0
            )
            inst_effects[clean_name] = {
                "coeficiente": round(float(coef), 2),
                "p_valor": round(pval, 4),
            }

    # Se for aninhado e metodologia não estiver na fórmula principal, ajusta modelo auxiliar para metodologia
    meth_effects: dict[str, dict[str, float]] = {}
    if "C(metodologia)" in formula_main:
        for param_name, coef in model.params.items():
            if "C(metodologia)" in param_name:
                clean_name = param_name.replace("C(metodologia)[T.", "").replace("]", "")
                pval = (
                    float(model.pvalues[param_name])
                    if param_name in model.pvalues and pd.notna(model.pvalues[param_name])
                    else 1.0
                )
                meth_effects[clean_name] = {
                    "coeficiente": round(float(coef), 2),
                    "p_valor": round(pval, 4),
                }
    elif n_meth > 1 and (n_meth + 1 < n_obs):
        try:
            model_meth = ols("residuo ~ C(metodologia)", data=pdf).fit()
            if model_meth.df_resid > 0:
                anova_meth = sm.stats.anova_lm(model_meth, typ=2)
                if "C(metodologia)" in anova_meth.index:
                    p_val_raw = anova_meth.loc["C(metodologia)", "PR(>F)"]
                    p_meth_f = float(p_val_raw) if pd.notna(p_val_raw) else 1.0
            for param_name, coef in model_meth.params.items():
                if "C(metodologia)" in param_name:
                    clean_name = param_name.replace("C(metodologia)[T.", "").replace("]", "")
                    pval = (
                        float(model_meth.pvalues[param_name])
                        if param_name in model_meth.pvalues
                        and pd.notna(model_meth.pvalues[param_name])
                        else 1.0
                    )
                    meth_effects[clean_name] = {
                        "coeficiente": round(float(coef), 2),
                        "p_valor": round(pval, 4),
                    }
        except Exception:
            pass

    r2_val = float(model.rsquared) if pd.notna(model.rsquared) else 0.0

    return {
        "r_squared": round(r2_val, 3),
        "institute_effects": inst_effects,
        "methodology_effects": meth_effects,
        "p_val_institutes_anova": round(p_inst_f, 4),
        "p_val_methodology_anova": round(p_meth_f, 4),
    }


def compute_campaign_house_effects(
    polls: Sequence[PesquisaEleitoralSchema],
    candidate_1: str,
    candidate_2: str,
    window_days: int = 7,
    min_peer_institutes: int = 2,
    min_comparable_polls: int = 2,
    confidence_level: float = 0.80,
) -> dict[str, Any]:
    """Calcula a inclinação longitudinal (house effects) dos institutos em relação aos pares.

    Para cada levantamento de um instituto, calcula a margem (C1 - C2) e compara
    com a média dos demais institutos que tiveram campo no mesmo intervalo de tempo
    (±window_days). Isola o viés metodológico do instituto das flutuações macro da campanha.

    Args:
        polls: Lista ou sequência de pesquisas da campanha (PesquisaEleitoralSchema).
        candidate_1: Nome do primeiro candidato de referência (ex.: líder da eleição).
        candidate_2: Nome do segundo candidato de referência (ex.: segundo colocado).
        window_days: Janela temporal de dias para busca de pesquisas concorrentes (default: 7 dias).
        min_peer_institutes: Mínimo de institutos distintos concorrentes na janela para validar a comparação (default: 2).
        min_comparable_polls: Mínimo de pesquisas comparáveis para um instituto ser incluído no painel (default: 2).
        confidence_level: Nível de confiança para o intervalo da média do instituto (default: 0.80).

    Returns:
        dict[str, Any]: Dicionário contendo:
            - 'candidate_1': Nome do candidato 1.
            - 'candidate_2': Nome do candidato 2.
            - 'institutes': Lista ordenada de dicionários de institutos (da menor para a maior média),
              cada um contendo:
                - 'instituto': Nome fantasia do instituto.
                - 'mean_tilt': Média do tilt na campanha.
                - 'ci_lower': Limite inferior do intervalo de confiança.
                - 'ci_upper': Limite superior do intervalo de confiança.
                - 'includes_zero': Booleano indicando se o intervalo cobre o zero.
                - 'n_polls': Quantidade de pesquisas comparáveis.
                - 'points': Lista de pontos individuais ordenados por data ({'data': date, 'margin': float, 'peer_mean': float, 'tilt': float}).
            - 'excluded_institutes': Lista de nomes de institutos com menos pesquisas que o mínimo exigido.
            - 'total_comparable_polls': Contagem total de pesquisas comparáveis consideradas.

    Raises:
        ValueError: Se não houver pesquisas fornecidas ou dados insuficientes dos candidatos.
    """
    valid_items: list[dict[str, Any]] = []
    for p in polls:
        if candidate_1 in p.votos_validos and candidate_2 in p.votos_validos:
            margin = float(p.votos_validos[candidate_1]) - float(p.votos_validos[candidate_2])
            valid_items.append(
                {
                    "id": p.id_registro_tse,
                    "instituto": p.instituto_nome_fantasia,
                    "data_fim": p.data_fim_campo,
                    "margin": margin,
                }
            )

    if not valid_items:
        raise ValueError(
            f"Nenhuma pesquisa encontrada contendo votos válidos para '{candidate_1}' e '{candidate_2}'."
        )

    # Identificação de pesquisas comparáveis com pares na janela de ±window_days
    comparable_by_inst: dict[str, list[dict[str, Any]]] = {}
    for i, item in enumerate(valid_items):
        t_i = item["data_fim"]
        inst_i = item["instituto"]

        peer_by_inst: dict[str, list[float]] = {}
        for j, other in enumerate(valid_items):
            if i != j and other["instituto"] != inst_i:
                delta_days = abs((other["data_fim"] - t_i).days)
                if delta_days <= window_days:
                    peer_by_inst.setdefault(other["instituto"], []).append(other["margin"])

        if len(peer_by_inst) >= min_peer_institutes:
            # Média não enviesada por instituto concorrente
            peer_consensus = sum(
                sum(margins) / len(margins) for margins in peer_by_inst.values()
            ) / len(peer_by_inst)
            tilt = item["margin"] - peer_consensus

            comparable_by_inst.setdefault(inst_i, []).append(
                {
                    "data": item["data_fim"],
                    "margin": item["margin"],
                    "peer_mean": peer_consensus,
                    "tilt": tilt,
                }
            )

    included_institutes: list[dict[str, Any]] = []
    excluded_institutes: list[str] = []
    total_comparables = 0

    # Todos os institutos únicos presentes na base avaliada
    all_distinct_institutes = sorted(set(x["instituto"] for x in valid_items))

    for inst in all_distinct_institutes:
        pts = comparable_by_inst.get(inst, [])
        # Ordena pontos cronologicamente
        pts.sort(key=lambda x: x["data"])
        n = len(pts)

        if n >= min_comparable_polls:
            total_comparables += n
            tilts = [x["tilt"] for x in pts]
            mean_tilt = sum(tilts) / n

            if n > 1:
                sample_var = sum((x - mean_tilt) ** 2 for x in tilts) / (n - 1)
                sample_std = sample_var**0.5
                se = sample_std / (n**0.5)
                # t-Student com df = n - 1
                alpha = 1.0 - confidence_level
                t_crit = float(stats.t.ppf(1.0 - alpha / 2.0, df=n - 1))
                ci_margin = t_crit * se
                ci_lower = mean_tilt - ci_margin
                ci_upper = mean_tilt + ci_margin
            else:
                ci_lower = mean_tilt
                ci_upper = mean_tilt

            includes_zero = bool(ci_lower <= 0.0 <= ci_upper)

            included_institutes.append(
                {
                    "instituto": inst,
                    "mean_tilt": mean_tilt,
                    "ci_lower": ci_lower,
                    "ci_upper": ci_upper,
                    "includes_zero": includes_zero,
                    "n_polls": n,
                    "points": pts,
                }
            )
        else:
            excluded_institutes.append(inst)

    # Ordena da maior inclinação negativa (mais C2) para a maior positiva (mais C1)
    included_institutes.sort(key=lambda x: x["mean_tilt"])

    return {
        "candidate_1": candidate_1,
        "candidate_2": candidate_2,
        "institutes": included_institutes,
        "excluded_institutes": excluded_institutes,
        "total_comparable_polls": total_comparables,
    }
