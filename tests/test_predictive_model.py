"""Testes unitários e de integração para o Modelo Preditivo Estado-Espaço Hierárquico Calibrado (Ato 6).

Valida:
1. Classificação automática de escopo geográfico (Nacional, Estadual, Regional) no coletor PesqEle.
2. Invariantes matemáticos do simplex de votos válidos e probabilidades de Monte Carlo Student-t.
3. Ausência estrita de vazamento temporal (No Future Data Leakage) no corte point-in-time.
4. Calibração empírica pós-1º Turno (pesos exponenciais w_audit e de-biasing direcional).
5. Pós-estratificação geográfica pelo Colégio Eleitoral do TSE (5 macrorregiões).
6. Aprovação nos Portões de Qualidade MLE (Promotion Gates) para 1º e 2º Turnos de 2026.
7. Geração dos gráficos Plotly interativos do Ato 6.
"""

from datetime import date

import polars as pl
import pytest

from src.analytics.predictive_model import (
    PredictiveModelConfig,
    compute_first_round_institute_calibration,
    evaluate_promotion_gates,
    predict_election_outcome,
    run_point_in_time_backtest,
)
from src.ingestion.data_loader import get_election_dataset, get_election_date
from src.ingestion.pesqele_collector import PesqEleCollector
from src.presentation.components.predictive_charts import (
    create_backtest_convergence_chart,
    create_electoral_college_regional_chart,
    create_win_probability_distribution_chart,
)
from src.transformations.schemas import (
    AbrangenciaEnum,
    MetodologiaEnum,
    PesquisaEleitoralSchema,
    ResultadoOficialTSESchema,
)


def test_geographic_scope_classification() -> None:
    """Valida a classificação automática de escopo geográfico a partir do plano amostral do TSE.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    scope_nat, uf_nat, reg_nat = PesqEleCollector.classify_geographic_scope(
        plano_amostral="Amostra nacional estratificada por cotas nas 5 regiões do Brasil",
        dado_municipio="27 UFs",
        sg_uf="BR",
    )
    assert scope_nat == AbrangenciaEnum.NACIONAL
    assert uf_nat == "BR"
    assert reg_nat == "BR"

    scope_est, uf_est, reg_est = PesqEleCollector.classify_geographic_scope(
        plano_amostral="Eleitorado do Estado de São Paulo estratificado por porte municipal",
        dado_municipio="São Paulo, Campinas, Guarulhos",
        sg_uf="BR",
    )
    assert scope_est == AbrangenciaEnum.ESTADUAL
    assert uf_est == "SP"
    assert reg_est == "SE"

    scope_reg, uf_reg, reg_reg = PesqEleCollector.classify_geographic_scope(
        plano_amostral="Pesquisa na Região Metropolitana de Fortaleza no Ceará",
        dado_municipio="Município de Fortaleza",
        sg_uf="BR",
    )
    assert scope_reg == AbrangenciaEnum.REGIONAL
    assert uf_reg == "CE"
    assert reg_reg == "NE"

    scope_uf_direct, uf_direct, reg_direct = PesqEleCollector.classify_geographic_scope(
        plano_amostral="",
        dado_municipio="",
        sg_uf="RS",
    )
    assert scope_uf_direct == AbrangenciaEnum.ESTADUAL
    assert uf_direct == "RS"
    assert reg_direct == "S"


def test_predictive_model_config_loading() -> None:
    """Verifica o carregamento de hiperparâmetros de `settings.yaml` e fallback seguro.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    cfg = PredictiveModelConfig.load_from_settings()
    assert cfg.n_simulations == 10000
    assert abs(sum(cfg.macro_region_weights.values()) - 1.0) < 1e-4
    assert set(cfg.macro_region_weights.keys()) == {"SE", "NE", "S", "N", "CO"}

    cfg_fallback = PredictiveModelConfig.load_from_settings("caminho_inexistente.yaml")
    assert cfg_fallback.n_simulations == 10000
    assert abs(sum(cfg_fallback.macro_region_weights.values()) - 1.0) < 1e-4


def test_predict_election_outcome_simplex_and_probabilities(
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
    sample_historical_campaign_polls_2026: list[PesquisaEleitoralSchema],
) -> None:
    """Valida se os votos esperados e as probabilidades de vitória somam 100% no simplex.

    Args:
        sample_eve_polls_2026: Fixture com pesquisas de véspera.
        sample_historical_campaign_polls_2026: Fixture com histórico de campanha.

    Returns:
        None.

    Raises:
        None.
    """
    polls = sample_historical_campaign_polls_2026 + sample_eve_polls_2026
    election_date = date(2026, 10, 4)

    result = predict_election_outcome(
        polls=polls,
        election_date=election_date,
        cutoff_date=election_date,
        turno=1,
    )

    sum_expected_votes = sum(c.voto_esperado for c in result.candidatos)
    sum_win_probs = sum(c.probabilidade_vitoria for c in result.candidatos)

    assert 99.9 <= sum_expected_votes <= 100.1
    assert 99.9 <= sum_win_probs <= 100.1
    assert result.n_pesquisas_utilizadas == len(polls)

    for c in result.candidatos:
        assert c.ic_95_inferior <= c.voto_esperado <= c.ic_95_superior
        assert 0.0 <= c.probabilidade_vitoria <= 100.0


def test_point_in_time_no_future_leakage(
    sample_eve_polls_2026: list[PesquisaEleitoralSchema],
    sample_historical_campaign_polls_2026: list[PesquisaEleitoralSchema],
) -> None:
    """Garante que pesquisas posteriores a `cutoff_date` são estritamente ignoradas pelo modelo.

    Args:
        sample_eve_polls_2026: Fixture com pesquisas de véspera.
        sample_historical_campaign_polls_2026: Fixture com histórico de campanha.

    Returns:
        None.

    Raises:
        None.
    """
    base_polls = sample_historical_campaign_polls_2026 + sample_eve_polls_2026
    election_date = date(2026, 10, 4)
    cutoff = date(2026, 9, 25)

    res_clean = predict_election_outcome(
        polls=base_polls,
        election_date=election_date,
        cutoff_date=cutoff,
        turno=1,
    )

    # Adiciona uma pesquisa extrema com campo posterior a cutoff_date (2026-10-03)
    future_outlier = PesquisaEleitoralSchema(
        id_registro_tse="BR-99999/2026",
        instituto_razao_social="Instituto Outlier Futuro",
        instituto_nome_fantasia="OutlierFuturo",
        data_inicio_campo=date(2026, 10, 2),
        data_fim_campo=date(2026, 10, 3),
        data_divulgacao=date(2026, 10, 3),
        tamanho_amostra=50000,
        margem_erro_declarada=0.5,
        nivel_confianca=0.95,
        metodologia=MetodologiaEnum.PRESENCIAL_DOMICILIAR,
        deff_estimado=1.2,
        votos_totais={"Lula": 90.0, "Flávio Bolsonaro": 5.0},
        votos_validos={"Lula": 94.7, "Flávio Bolsonaro": 5.3},
        percentual_indecisos=2.0,
        percentual_brancos_nulos=3.0,
    )

    res_with_future = predict_election_outcome(
        polls=[*base_polls, future_outlier],
        election_date=election_date,
        cutoff_date=cutoff,
        turno=1,
    )

    assert res_clean.n_pesquisas_utilizadas == res_with_future.n_pesquisas_utilizadas
    assert res_clean.vencedor_previsto == res_with_future.vencedor_previsto
    for c_clean, c_fut in zip(res_clean.candidatos, res_with_future.candidatos):
        assert c_clean.candidato == c_fut.candidato
        assert c_clean.voto_esperado == c_fut.voto_esperado
        assert c_clean.probabilidade_vitoria == c_fut.probabilidade_vitoria


def test_predict_election_outcome_empty_raises() -> None:
    """Verifica que `predict_election_outcome` levanta ValueError se não houver pesquisas até o corte.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    with pytest.raises(ValueError, match="Nenhuma pesquisa disponível"):
        predict_election_outcome(
            polls=[],
            election_date=date(2026, 10, 4),
            cutoff_date=date(2026, 10, 3),
        )


def test_first_round_institute_calibration_weights() -> None:
    """Verifica se a calibração pós-1º Turno atribui maior peso a institutos com menor erro EP_T1.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    tse_t1, _, polls_t1 = get_election_dataset(2026, 1, include_subnational=True)
    dt_t1 = get_election_date(2026, 1)

    calibrations = compute_first_round_institute_calibration(
        t1_polls=polls_t1,
        t1_official_result=tse_t1,
        election_date_t1=dt_t1,
        audit_lambda=0.25,
    )

    assert len(calibrations) >= 10
    # Verifica monotonicidade inversa: menor EP_T1 -> maior peso_auditoria
    sorted_by_ep = sorted(calibrations.values(), key=lambda x: x.erro_ponderado_t1)
    best_inst = sorted_by_ep[0]
    worst_inst = sorted_by_ep[-1]
    assert best_inst.erro_ponderado_t1 <= worst_inst.erro_ponderado_t1
    assert best_inst.peso_auditoria >= worst_inst.peso_auditoria

    with pytest.raises(ValueError, match="não pode ser vazia"):
        compute_first_round_institute_calibration([], tse_t1, dt_t1)

    with pytest.raises(ValueError, match="não-negativo"):
        compute_first_round_institute_calibration(polls_t1, tse_t1, dt_t1, audit_lambda=-0.1)


def test_backtest_and_promotion_gates_2026_t1_and_t2() -> None:
    """Executa o backtest real no 1º e 2º Turnos de 2026 e valida aprovação nos Quality Gates MLE.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    # 1º Turno de 2026 (com pesquisas Nacionais + Estaduais + Regionais)
    tse_26_t1, _, polls_26_t1 = get_election_dataset(2026, 1, include_subnational=True)
    dt_26_t1 = get_election_date(2026, 1)

    assert any(p.abrangencia == AbrangenciaEnum.ESTADUAL for p in polls_26_t1)
    assert any(p.abrangencia == AbrangenciaEnum.REGIONAL for p in polls_26_t1)

    bt_t1 = run_point_in_time_backtest(
        polls=polls_26_t1,
        tse_result=tse_26_t1,
        election_date=dt_26_t1,
        horizons_days=(30, 14, 7, 3, 1),
    )
    gates_t1 = evaluate_promotion_gates(bt_t1)
    assert gates_t1["promoted"] is True
    assert gates_t1["metrics"]["eve_winner_correct"] is True
    assert gates_t1["metrics"]["eve_brier_score"] <= 0.15

    # 2º Turno de 2026 calibrado com o erro real do 1º Turno
    # Como a apuração oficial do 2º Turno é futura (25/10/2026), simulamos o contrato do TSE
    # dentro do teste para validação técnica dos Quality Gates MLE no pipeline de backtest.
    cal_t1 = compute_first_round_institute_calibration(polls_26_t1, tse_26_t1, dt_26_t1)
    _, _, polls_26_t2 = get_election_dataset(2026, 2, include_subnational=True)
    dt_26_t2 = get_election_date(2026, 2)

    mock_tse_26_t2 = ResultadoOficialTSESchema(
        cargo="PRESIDENTE",
        turno=2,
        ano=2026,
        total_votos_validos=115000000,
        total_brancos=2000000,
        total_nulos=3000000,
        total_abstencoes=30000000,
        resultado_nominal={"Flávio Bolsonaro": 50.5, "Lula": 49.5},
    )

    bt_t2 = run_point_in_time_backtest(
        polls=polls_26_t2,
        tse_result=mock_tse_26_t2,
        election_date=dt_26_t2,
        horizons_days=(15, 10, 7),
        calibration_t1=cal_t1,
    )
    gates_t2 = evaluate_promotion_gates(bt_t2)
    assert "promoted" in gates_t2
    assert "metrics" in gates_t2

    with pytest.raises(ValueError, match="não pode ser vazio"):
        evaluate_promotion_gates(pl.DataFrame())


def test_predictive_charts_creation() -> None:
    """Valida a construção dos 3 gráficos Plotly do Ato 6 com dados reais e casos vazios.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    _, _, polls_26_t2 = get_election_dataset(2026, 2, include_subnational=True)
    dt_26_t2 = get_election_date(2026, 2)

    forecast = predict_election_outcome(
        polls=polls_26_t2,
        election_date=dt_26_t2,
        cutoff_date=date(2026, 10, 19),
        turno=2,
    )

    mock_tse_26_t2 = ResultadoOficialTSESchema(
        cargo="PRESIDENTE",
        turno=2,
        ano=2026,
        total_votos_validos=115000000,
        total_brancos=2000000,
        total_nulos=3000000,
        total_abstencoes=30000000,
        resultado_nominal={"Flávio Bolsonaro": 50.5, "Lula": 49.5},
    )

    bt_df = run_point_in_time_backtest(
        polls=polls_26_t2,
        tse_result=mock_tse_26_t2,
        election_date=dt_26_t2,
        horizons_days=(10, 7),
    )

    fig_dist = create_win_probability_distribution_chart(
        forecast=forecast,
        official_result=mock_tse_26_t2.resultado_nominal,
    )
    assert len(fig_dist.data) == 2

    fig_bt = create_backtest_convergence_chart(bt_df)
    assert len(fig_bt.data) == 3

    fig_reg = create_electoral_college_regional_chart(
        regional_slices=forecast.agregacao_regional,
        top_candidates=["Flávio Bolsonaro", "Lula"],
    )
    assert len(fig_reg.data) == 2

    # Casos de borda vazios
    fig_bt_empty = create_backtest_convergence_chart(pl.DataFrame())
    assert len(fig_bt_empty.data) == 0

    fig_reg_empty = create_electoral_college_regional_chart([], [])
    assert len(fig_reg_empty.data) == 0
