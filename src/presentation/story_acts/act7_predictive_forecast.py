"""Ato 7: Modelo Preditivo & Previsão Eleitoral (Estado-Espaço Hierárquico Calibrado).

Renderiza o painel executivo de Nowcasting e Previsão Eleitoral Probabilística:
1. Narrativa contextualizada dinamicamente para o 1º Turno (validação retroativa antes da urna)
   e para o 2º Turno (previsão calibrada com os erros e vieses apurados no 1º Turno).
2. Cartões executivos em dark mode comparando lado a lado: Média Simples das Pesquisas vs.
   Previsão do Modelo Calibrado vs. Resultado Oficial da Urna TSE.
3. Pós-estratificação geográfica multi-escopo (Nacional, Estadual e Regional) pelo Colégio Eleitoral TSE.
4. Validação empírica retroativa (Backtesting sem vazamento temporal) e Quality Gates MLE.
"""

from datetime import date, timedelta
from typing import Sequence

import numpy as np
import polars as pl
import streamlit as st

from src.analytics.metrics import calculate_weighted_poll_error
from src.analytics.predictive_model import (
    PredictiveModelConfig,
    compute_first_round_institute_calibration,
    evaluate_promotion_gates,
    predict_election_outcome,
    run_point_in_time_backtest,
)
from src.presentation.components.predictive_charts import (
    create_backtest_convergence_chart,
    create_electoral_college_regional_chart,
    create_win_probability_distribution_chart,
)
from src.presentation.components.waterfall_projection_card import (
    render_waterfall_projection_breakdown,
)
from src.transformations.schemas import PesquisaEleitoralSchema, ResultadoOficialTSESchema


def _compute_simple_poll_average(
    polls: Sequence[PesquisaEleitoralSchema],
    cutoff_date: date,
    candidates: Sequence[str],
) -> dict[str, float]:
    """Calcula a média aritmética simples das pesquisas disponíveis até a data de corte.

    Args:
        polls: Pesquisas elegíveis.
        cutoff_date: Data limite da simulação.
        candidates: Lista de candidatos avaliados.

    Returns:
        dict[str, float]: Percentual médio simples por candidato (soma 100%).

    Raises:
        None.
    """
    valid = [p for p in polls if p.data_fim_campo <= cutoff_date]
    if not valid:
        return {c: 0.0 for c in candidates}
    raw = {
        c: float(np.mean([float(p.votos_validos.get(c, 0.0)) for p in valid])) for c in candidates
    }
    tot = sum(raw.values())
    if tot <= 0.0:
        return {c: 0.0 for c in candidates}
    return {c: round((v / tot) * 100.0, 2) for c, v in raw.items()}


def render_act7(
    polls: Sequence[PesquisaEleitoralSchema],
    tse_result: ResultadoOficialTSESchema | None,
    election_date: date,
    t1_polls: Sequence[PesquisaEleitoralSchema] | None = None,
    t1_tse_result: ResultadoOficialTSESchema | None = None,
    t1_election_date: date | None = None,
) -> None:
    """Renderiza a tela do Ato 7: Modelo Preditivo & Previsão Eleitoral.

    Args:
        polls: Pesquisas eleitorais do turno ativo (incluindo escopos Nacional, Estadual e Regional).
        tse_result: Resultado oficial consolidado pelo TSE para o turno ativo (ou None se pré-eleição).
        election_date: Data oficial de realização do turno ativo.
        t1_polls: Pesquisas do 1º Turno para calibração empírica de institutos no 2º Turno.
        t1_tse_result: Resultado oficial do 1º Turno para calibração de viés e pesos de auditoria.
        t1_election_date: Data oficial do 1º Turno.

    Returns:
        None.

    Raises:
        None.
    """
    st.markdown("## Ato 7: Modelo Preditivo & Previsão Eleitoral (Agregado Multi-Escopo Calibrado)")

    if not polls:
        st.info(
            "Nenhuma pesquisa disponível para o ciclo e turno selecionados. "
            "No 2º Turno, utilize o botão de sincronização na barra lateral."
        )
        return

    config = PredictiveModelConfig.load_from_settings()
    turno_ativo = polls[0].turno
    ano_ativo = polls[0].ano

    # 1. Banner Contextual Dinâmico por Turno (clareza imediata do objetivo da tela)
    if turno_ativo == 1:
        st.markdown(
            f"""
            <div style="background-color: #16202A; border-left: 4px solid #38BDF8; padding: 15px 20px; border-radius: 6px; margin-bottom: 20px;">
                <div style="color: #38BDF8; font-weight: 700; font-size: 14.5px; margin-bottom: 4px;">
                    Objetivo no 1º Turno ({ano_ativo}) — Validação Preditiva Antes da Abertura das Urnas (Backtesting)
                </div>
                <div style="color: #E2E8F0; font-size: 13.5px; line-height: 1.55;">
                    Aqui testamos se o modelo é capaz de prever o vencedor da eleição usando <b>exclusivamente as pesquisas divulgadas antes do dia da votação</b>
                    (combinando levantamentos <b>Nacionais</b>, <b>Estaduais</b> e <b>Regionais</b> ponderados pelo Colégio Eleitoral do TSE).
                    O resultado oficial do 1º Turno fica oculto do modelo e serve apenas como <b>gabarito de validação</b> para medir o acerto da previsão.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="background-color: #14241D; border-left: 4px solid #10B981; padding: 15px 20px; border-radius: 6px; margin-bottom: 20px;">
                <div style="color: #34D399; font-weight: 700; font-size: 14.5px; margin-bottom: 4px;">
                    Objetivo no 2º Turno ({ano_ativo}) — Previsão Calibrada com o Aprendizado do 1º Turno
                </div>
                <div style="color: #E2E8F0; font-size: 13.5px; line-height: 1.55;">
                    No 2º Turno, o modelo utiliza o <b>resultado real do 1º Turno</b> para auditar cada instituto de pesquisa:
                    institutos que tiveram menor erro no 1º Turno recebem <b>maior peso de credibilidade</b>, e o viés direcional observado no 1º Turno
                    é <b>descontado automaticamente</b> das pesquisas de 2º Turno (Nacionais, Estaduais e Regionais) para projetar quem sairá vitorioso.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Calcula calibração empírica do 1º Turno
    source_t1_polls = t1_polls if t1_polls else (polls if turno_ativo == 1 else [])
    source_t1_tse = t1_tse_result if t1_tse_result else (tse_result if turno_ativo == 1 else None)
    source_t1_date = (
        t1_election_date if t1_election_date else (election_date if turno_ativo == 1 else None)
    )

    calibration_map = None
    if source_t1_polls and source_t1_tse and source_t1_date:
        calibration_map = compute_first_round_institute_calibration(
            t1_polls=source_t1_polls,
            t1_official_result=source_t1_tse,
            election_date_t1=source_t1_date,
            audit_lambda=config.audit_lambda,
            config=config,
        )

    # 2. Barra de Controles de Simulação Interativa
    st.markdown("### Simulador Temporal da Previsão (Escolha o Momento da Campanha)")
    col_c1, col_c2, col_c3 = st.columns([1.4, 1.2, 1.2])

    max_days_back = 30 if turno_ativo == 1 else 15
    with col_c1:
        dias_antes = st.slider(
            "Simular previsão em quantos dias antes da eleição?",
            min_value=1,
            max_value=max_days_back,
            value=1,
            step=1,
            help=(
                "1 dia antes = Véspera da eleição. Ao mover para 7, 14 ou 30 dias antes, "
                "o modelo ignora todas as pesquisas posteriores àquela data."
            ),
        )

    cutoff_selected = election_date - timedelta(days=int(dias_antes))

    with col_c2:
        use_t1_cal = st.checkbox(
            "Calibrar institutos pelo desempenho real no 1º Turno",
            value=(turno_ativo == 2),
            disabled=(turno_ativo == 1),
            help=(
                "No 2º Turno, corrige o viés e pondera cada instituto pelo erro medido na urna do 1º Turno. "
                "No 1º Turno fica desativado para garantir validação cega sem uso de dados futuros."
            ),
        )

    with col_c3:
        include_geo = st.checkbox(
            "Incluir pesquisas Estaduais e Regionais (Colégio Eleitoral)",
            value=True,
            help="Combina pesquisas Nacionais (BR) com pesquisas Estaduais (UFs) e Regionais ponderadas pelas 5 macrorregiões do TSE.",
        )

    active_polls = (
        list(polls) if include_geo else [p for p in polls if p.abrangencia.value == "NACIONAL"]
    )
    if not active_polls:
        st.info(
            "O Modelo Preditivo requer pesquisas eleitorais com intenções de voto registradas "
            "para gerar projeções probabilísticas e Nowcasting."
        )
        return

    active_calibration = calibration_map if (use_t1_cal and turno_ativo == 2) else None

    earliest_field = min(p.data_fim_campo for p in active_polls)
    if cutoff_selected < earliest_field:
        cutoff_selected = earliest_field

    forecast = predict_election_outcome(
        polls=active_polls,
        election_date=election_date,
        cutoff_date=cutoff_selected,
        turno=turno_ativo,
        calibration_t1=active_calibration,
        config=config,
    )

    # 3. Painel Executivo em 3 Cartões Dark Mode (Sem truncamento e com Comparativo Direto)
    leader = forecast.candidatos[0]
    runner_up = forecast.candidatos[1] if len(forecast.candidatos) > 1 else leader
    c1_name = leader.candidato
    c2_name = runner_up.candidato

    has_official_concluded = tse_result is not None and getattr(
        tse_result, "apuracao_concluida", True
    )

    if has_official_concluded and tse_result is not None:
        oficial_dict = tse_result.resultado_nominal
        sorted_oficial = sorted(oficial_dict.keys(), key=lambda c: oficial_dict[c], reverse=True)
        real_winner = sorted_oficial[0]

        simple_avg = _compute_simple_poll_average(
            active_polls, forecast.cutoff_date, list(oficial_dict.keys())
        )
        model_est_map = {cp.candidato: cp.voto_esperado for cp in forecast.candidatos}
        ep_mod_now = calculate_weighted_poll_error(model_est_map, oficial_dict)[
            "erro_total_ponderado"
        ]
        ep_sim_now = calculate_weighted_poll_error(simple_avg, oficial_dict)["erro_total_ponderado"]
        gain_pct = (
            ((ep_sim_now - ep_mod_now) / max(1e-6, ep_sim_now)) * 100.0 if ep_sim_now > 0 else 0.0
        )

        acertou_vencedor = forecast.vencedor_previsto == real_winner
        badge_win_bg = (
            "rgba(16, 185, 129, 0.15)" if acertou_vencedor else "rgba(245, 158, 11, 0.15)"
        )
        badge_win_color = "#34D399" if acertou_vencedor else "#FBBF24"
        badge_win_text = (
            f"Acertou o Vencedor da Urna ({real_winner})"
            if acertou_vencedor
            else f"Urna apontou {real_winner} (virada posterior ao corte)"
        )
        real_c1 = float(oficial_dict.get(c1_name, 0.0))
        real_c2 = float(oficial_dict.get(c2_name, 0.0))
        simp_c1 = float(simple_avg.get(c1_name, 0.0))
        simp_c2 = float(simple_avg.get(c2_name, 0.0))
    else:
        oficial_dict = {}
        simple_avg = _compute_simple_poll_average(
            active_polls, forecast.cutoff_date, [c1_name, c2_name]
        )
        simp_c1 = float(simple_avg.get(c1_name, 0.0))
        simp_c2 = float(simple_avg.get(c2_name, 0.0))
        real_c1 = 0.0
        real_c2 = 0.0
        ep_mod_now = 0.0
        ep_sim_now = 0.0
        gain_pct = 0.0
        badge_win_bg = "rgba(56, 189, 248, 0.15)"
        badge_win_color = "#38BDF8"
        badge_win_text = f"Liderança Projetada: {forecast.vencedor_previsto} ({leader.probabilidade_vitoria:.1f}% de chances)"

    card_col1, card_col2, card_col3 = st.columns(3)

    with card_col1:
        r2_info_line = (
            f"Probabilidade de haver 2º Turno: <b>{forecast.probabilidade_segundo_turno:.1f}%</b>"
            if turno_ativo == 1
            else f"Margem projetada (1º − 2º): <b>{forecast.margem_esperada:+.2f} p.p.</b>"
        )
        st.markdown(
            f"""
            <div style="background-color: #181B20; border: 1px solid #282D37; border-radius: 8px; padding: 16px 18px; min-height: 215px;">
                <div style="color: #94A3B8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                    Vencedor Previsto pelo Modelo
                </div>
                <div style="color: #F8FAFC; font-size: 23px; font-weight: 700; margin-top: 4px; margin-bottom: 6px;">
                    {forecast.vencedor_previsto}
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px;">
                    <span style="color: #CBD5E1;">Probabilidade de Vitória:</span>
                    <span style="color: #38BDF8; font-weight: 700;">{leader.probabilidade_vitoria:.1f}%</span>
                </div>
                <div style="background-color: #282D37; border-radius: 4px; height: 7px; width: 100%; margin-bottom: 10px;">
                    <div style="background-color: #38BDF8; height: 7px; border-radius: 4px; width: {min(100.0, leader.probabilidade_vitoria):.1f}%;"></div>
                </div>
                <div style="color: #94A3B8; font-size: 12.5px; margin-bottom: 12px;">
                    {r2_info_line}
                </div>
                <div style="background-color: {badge_win_bg}; color: {badge_win_color}; border: 1px solid {badge_win_color}; border-radius: 4px; padding: 5px 8px; font-size: 11.5px; font-weight: 600; text-align: center;">
                    {badge_win_text}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with card_col2:
        if has_official_concluded and tse_result is not None:
            gain_color = "#34D399" if gain_pct >= 0 else "#FBBF24"
            gain_bg = "rgba(16, 185, 129, 0.15)" if gain_pct >= 0 else "rgba(245, 158, 11, 0.15)"
            st.markdown(
                f"""
                <div style="background-color: #181B20; border: 1px solid #282D37; border-radius: 8px; padding: 16px 18px; min-height: 215px;">
                    <div style="color: #94A3B8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
                        Placar: Média Simples vs. Modelo vs. Urna
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12.5px; padding: 5px 0; border-bottom: 1px solid #242933;">
                        <span style="color: #94A3B8;">1. Média Simples (Sem Modelo):</span>
                        <span style="color: #CBD5E1; font-family: monospace;">{c1_name}: {simp_c1:.1f}% | {c2_name}: {simp_c2:.1f}%</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12.5px; padding: 6px 0; border-bottom: 1px solid #242933;">
                        <span style="color: #38BDF8; font-weight: 600;">2. Modelo Preditivo Calibrado:</span>
                        <span style="color: #F8FAFC; font-weight: 700; font-family: monospace;">{c1_name}: {leader.voto_esperado:.2f}% | {c2_name}: {runner_up.voto_esperado:.2f}%</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12.5px; padding: 6px 0; margin-bottom: 10px;">
                        <span style="color: #FBBF24; font-weight: 600;">3. Resultado Oficial Urna TSE:</span>
                        <span style="color: #FBBF24; font-weight: 700; font-family: monospace;">{c1_name}: {real_c1:.2f}% | {c2_name}: {real_c2:.2f}%</span>
                    </div>
                    <div style="background-color: {gain_bg}; color: {gain_color}; border: 1px solid {gain_color}; border-radius: 4px; padding: 5px 8px; font-size: 11.5px; font-weight: 600; text-align: center;">
                        Erro Ponderado: Modelo {ep_mod_now:.2f} pp vs. Média Simples {ep_sim_now:.2f} pp ({gain_pct:+.1f}% de redução)
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="background-color: #181B20; border: 1px solid #282D37; border-radius: 8px; padding: 16px 18px; min-height: 215px;">
                    <div style="color: #94A3B8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
                        Placar: Média Simples vs. Modelo Preditivo
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12.5px; padding: 6px 0; border-bottom: 1px solid #242933;">
                        <span style="color: #94A3B8;">1. Média Simples Bruta:</span>
                        <span style="color: #CBD5E1; font-family: monospace;">{c1_name}: {simp_c1:.1f}% | {c2_name}: {simp_c2:.1f}%</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12.5px; padding: 8px 0; border-bottom: 1px solid #242933;">
                        <span style="color: #38BDF8; font-weight: 600;">2. Modelo Calibrado:</span>
                        <span style="color: #F8FAFC; font-weight: 700; font-family: monospace;">{c1_name}: {leader.voto_esperado:.2f}% | {c2_name}: {runner_up.voto_esperado:.2f}%</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12.5px; padding: 6px 0; margin-bottom: 10px;">
                        <span style="color: #64748B;">3. Urna Oficial TSE:</span>
                        <span style="color: #FBBF24; font-style: italic; font-size: 12px;">Aguardando apuração (25/10)</span>
                    </div>
                    <div style="background-color: rgba(56, 189, 248, 0.12); color: #38BDF8; border: 1px solid #0284C7; border-radius: 4px; padding: 5px 8px; font-size: 11.5px; font-weight: 600; text-align: center;">
                        Nowcasting Ativo: Projeção calculada com {len(active_polls)} pesquisas registradas
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with card_col3:
        cal_badge_txt = (
            "Calibração Pós-1º Turno ATIVA (Pesos EP_T1 + Correção de Viés)"
            if forecast.calibrado_pos_t1
            else "Modo Validação Cega (Sem usar resultado futuro)"
        )
        st.markdown(
            f"""
            <div style="background-color: #181B20; border: 1px solid #282D37; border-radius: 8px; padding: 16px 18px; min-height: 215px;">
                <div style="color: #94A3B8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
                    Raio-X das Pesquisas no Corte ({forecast.cutoff_date.strftime("%d/%m/%Y")})
                </div>
                <div style="color: #F8FAFC; font-size: 21px; font-weight: 700; margin-bottom: 6px;">
                    {forecast.n_pesquisas_utilizadas} pesquisas <span style="font-size: 13px; color: #94A3B8; font-weight: 500;">({forecast.n_institutos} institutos)</span>
                </div>
                <div style="font-size: 12.5px; color: #CBD5E1; line-height: 1.6; margin-bottom: 10px;">
                    • <b>Nacionais (BR):</b> {forecast.n_pesquisas_nacionais} levantamentos<br>
                    • <b>Estaduais (UFs):</b> {forecast.n_pesquisas_estaduais} levantamentos<br>
                    • <b>Regionais:</b> {forecast.n_pesquisas_regionais} levantamentos
                </div>
                <div style="background-color: #242933; color: #E2E8F0; border: 1px solid #334155; border-radius: 4px; padding: 5px 8px; font-size: 11.5px; font-weight: 600; text-align: center;">
                    {cal_badge_txt}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 4. Decomposição da Projeção (A CONTA: De onde vem a projeção)
    render_waterfall_projection_breakdown(
        forecast=forecast,
        t1_tse_result=source_t1_tse,
        polls=active_polls,
    )

    # 5. Gráfico de Simulação de Monte Carlo e Tabela Comparativa por Candidato
    st.markdown("### 1. Distribuição de Probabilidades e Placar por Candidato")
    st.markdown(
        """
        <div style="color: #94A3B8; font-size: 13px; margin-bottom: 12px; line-height: 1.5;">
            O gráfico à esquerda mostra os <b>10.000 cenários simulados</b> pelo modelo para os dois líderes
            (as linhas contínuas indicam a média prevista de cada candidato e a linha tracejada marca a maioria de 50%).
            À direita, a tabela compara a previsão central e o intervalo de 95% com a apuração oficial do TSE.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_dist, col_tbl = st.columns([1.35, 1.0])
    with col_dist:
        fig_dist = create_win_probability_distribution_chart(
            forecast=forecast,
            official_result=oficial_dict,
        )
        st.plotly_chart(fig_dist, width="stretch")

    with col_tbl:
        cand_rows = []
        for cp in forecast.candidatos:
            if has_official_concluded and tse_result is not None:
                real_v = float(oficial_dict.get(cp.candidato, 0.0))
                in_ci = cp.ic_95_inferior <= real_v <= cp.ic_95_superior
                cand_rows.append(
                    {
                        "Candidato": cp.candidato,
                        "Previsto (%)": round(cp.voto_esperado, 2),
                        "Urna TSE (%)": round(real_v, 2),
                        "Erro (pp)": round(cp.voto_esperado - real_v, 2),
                        "IC 95%": f"[{cp.ic_95_inferior:.1f}%, {cp.ic_95_superior:.1f}%]",
                        "Chances (%)": round(cp.probabilidade_vitoria, 1),
                        "Cobriu Urna": "Sim" if in_ci else "Não",
                    }
                )
            else:
                cand_rows.append(
                    {
                        "Candidato": cp.candidato,
                        "Previsto (%)": round(cp.voto_esperado, 2),
                        "IC 95%": f"[{cp.ic_95_inferior:.1f}%, {cp.ic_95_superior:.1f}%]",
                        "Chances (%)": round(cp.probabilidade_vitoria, 1),
                        "Tendência (pp/d)": round(cp.tendencia_diaria_pp, 2),
                        "Status Urna": "Aguardando 25/10",
                    }
                )
        if has_official_concluded:
            st.dataframe(
                pl.DataFrame(cand_rows),
                width="stretch",
                hide_index=True,
                column_config={
                    "Previsto (%)": st.column_config.NumberColumn("Previsto (%)", format="%.2f%%"),
                    "Urna TSE (%)": st.column_config.NumberColumn("Urna TSE (%)", format="%.2f%%"),
                    "Erro (pp)": st.column_config.NumberColumn("Erro (pp)", format="%+.2f"),
                    "Chances (%)": st.column_config.NumberColumn("Chances (%)", format="%.1f%%"),
                },
            )
        else:
            st.dataframe(
                pl.DataFrame(cand_rows),
                width="stretch",
                hide_index=True,
                column_config={
                    "Previsto (%)": st.column_config.NumberColumn("Previsto (%)", format="%.2f%%"),
                    "Chances (%)": st.column_config.NumberColumn("Chances (%)", format="%.1f%%"),
                    "Tendência (pp/d)": st.column_config.NumberColumn(
                        "Tendência (pp/d)", format="%+.2f"
                    ),
                },
            )

    st.markdown("---")

    # 5. Pós-Estratificação Geográfica pelo Colégio Eleitoral do TSE
    st.markdown("### 2. Agregação Geográfica: Pesquisas Nacionais, Estaduais e Regionais")
    st.markdown(
        """
        <div style="color: #94A3B8; font-size: 13px; margin-bottom: 12px; line-height: 1.5;">
            Como uma pesquisa feita apenas em São Paulo, Minas Gerais, Bahia ou Rio Grande do Sul entra na previsão nacional?
            O modelo projeta o placar em cada uma das <b>5 macrorregiões brasileiras</b> e multiplica pelo <b>peso oficial de eleitores do TSE</b>
            (Sudeste 42,6%, Nordeste 27,1%, Sul 14,7%, Norte 8,6% e Centro-Oeste 7,0%) para formar o agregado do Colégio Eleitoral.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_reg_chart, col_reg_tbl = st.columns([1.35, 1.0])
    top2_names = [cp.candidato for cp in forecast.candidatos[:2]]

    with col_reg_chart:
        fig_reg = create_electoral_college_regional_chart(
            regional_slices=forecast.agregacao_regional,
            top_candidates=top2_names,
        )
        st.plotly_chart(fig_reg, width="stretch")

    with col_reg_tbl:
        reg_rows = []
        for s in forecast.agregacao_regional:
            row_d: dict[str, object] = {
                "Macrorregião": f"{s.nome_regiao} ({s.regiao})",
                "Peso TSE (%)": round(s.peso_eleitorado * 100.0, 1),
                "Pesq. Locais": s.n_pesquisas,
            }
            for c_name in top2_names:
                row_d[f"{c_name} (%)"] = round(s.votos_projetados.get(c_name, 0.0), 2)
            row_d["Margem (pp)"] = s.margem_lider
            reg_rows.append(row_d)
        st.dataframe(
            pl.DataFrame(reg_rows),
            width="stretch",
            hide_index=True,
            column_config={
                "Peso TSE (%)": st.column_config.NumberColumn("Peso TSE (%)", format="%.1f%%"),
                "Margem (pp)": st.column_config.NumberColumn("Margem (pp)", format="%+.2f"),
            },
        )

    st.markdown("---")

    # 6. Backtesting Point-in-Time e Quality Gates MLE
    st.markdown("### 3. Evolução da Previsão ao Longo da Campanha (Backtesting Point-in-Time)")
    if not has_official_concluded or tse_result is None:
        st.markdown(
            """
            <div style="background-color: #181B20; border-left: 4px solid #38BDF8; padding: 14px 18px; border-radius: 6px; margin-bottom: 20px;">
                <span style="color: #38BDF8; font-weight: 600; font-size: 13.5px;">Validação Retrospectiva pós-Urna:</span>
                <span style="color: #CBD5E1; font-size: 13px; line-height: 1.5;">
                    O gráfico de convergência de backtesting e os <b>Quality Gates formais (Brier Score, Log-Loss e Cobertura)</b>
                    confrontam as previsões retroativas contra a apuração final do TSE. Para o 2º Turno, essa auditoria será gerada
                    assim que a apuração for oficializada em 25/10/2026.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="color: #94A3B8; font-size: 13px; margin-bottom: 12px; line-height: 1.5;">
                O teste abaixo reconstrói o que o modelo previa a <b>30, 21, 14, 7, 3 e 1 dia antes da eleição</b>,
                comparando o <b>Erro Ponderado do Modelo Calibrado</b> (barras azuis) contra o <b>Erro da Média Simples das Pesquisas</b> (barras cinzas).
                Quanto menor a barra, mais próxima a previsão ficou do resultado oficial da urna.
            </div>
            """,
            unsafe_allow_html=True,
        )

        horizons_bt = (30, 21, 14, 7, 3, 1) if turno_ativo == 1 else (15, 10, 7, 3, 1)
        bt_df = run_point_in_time_backtest(
            polls=active_polls,
            tse_result=tse_result,
            election_date=election_date,
            horizons_days=horizons_bt,
            calibration_t1=active_calibration,
            config=config,
        )
        gates_eval = evaluate_promotion_gates(bt_df, config=config)

        if gates_eval["promoted"]:
            st.success(
                f"**Validação Científica Aprovada:** Na véspera da eleição, o modelo acertou o vencedor com "
                f"Brier Score de {gates_eval['metrics']['eve_brier_score']:.4f} (meta ≤ {gates_eval['thresholds']['brier_score_max']:.2f}), "
                f"cobertura de {gates_eval['metrics']['mean_ci95_coverage']:.1f}% no intervalo de 95% "
                f"e reduziu o erro ponderado em {max(gates_eval['metrics']['eve_ep_reduction_pct'], gates_eval['metrics']['mean_ep_reduction_pct']):+.1f}% "
                f"em comparação à média simples das pesquisas."
            )
        else:
            st.warning(
                f"**Diagnóstico de Validação:** "
                f"Brier Score Véspera = {gates_eval['metrics']['eve_brier_score']:.4f} | "
                f"Cobertura IC 95% = {gates_eval['metrics']['mean_ci95_coverage']:.1f}% | "
                f"Redução de Erro vs. Média Simples = {gates_eval['metrics']['eve_ep_reduction_pct']:+.1f}%."
            )

        fig_bt = create_backtest_convergence_chart(bt_df)
        st.plotly_chart(fig_bt, width="stretch")

        # Formata as datas como string dd/mm/aaaa para evitar timestamps '00:00:00' na tabela
        bt_rows_formatted = []
        for r in bt_df.to_dicts():
            dt_val = r["data_corte"]
            dt_str = dt_val.strftime("%d/%m/%Y") if hasattr(dt_val, "strftime") else str(dt_val)
            h_val = int(r["horizonte_dias"])
            bt_rows_formatted.append(
                {
                    "Momento": f"T - {h_val}d ({dt_str})",
                    "Pesquisas": int(r["n_pesquisas"]),
                    "Vencedor Previsto": str(r["vencedor_previsto"]),
                    "Chances Vencedor Real (%)": float(r["prob_vitoria_vencedor_real"]),
                    "Previsto 1º (%)": float(r["voto_previsto_lider_real"]),
                    "Urna 1º (%)": float(r["voto_real_lider"]),
                    "Erro Modelo (pp)": float(r["erro_ponderado_modelo"]),
                    "Erro Média Simples (pp)": float(r["erro_ponderado_baseline"]),
                    "Redução de Erro (%)": float(r["reducao_erro_vs_baseline_pct"]),
                    "Brier Score": float(r["brier_score"]),
                }
            )

        st.dataframe(
            pl.DataFrame(bt_rows_formatted),
            width="stretch",
            hide_index=True,
            column_config={
                "Chances Vencedor Real (%)": st.column_config.NumberColumn(
                    "Chances Vencedor Real (%)", format="%.1f%%"
                ),
                "Previsto 1º (%)": st.column_config.NumberColumn(
                    "Previsto 1º (%)", format="%.2f%%"
                ),
                "Urna 1º (%)": st.column_config.NumberColumn("Urna 1º (%)", format="%.2f%%"),
                "Erro Modelo (pp)": st.column_config.NumberColumn(
                    "Erro Modelo (pp)", format="%.2f"
                ),
                "Erro Média Simples (pp)": st.column_config.NumberColumn(
                    "Erro Média Simples (pp)", format="%.2f"
                ),
                "Redução de Erro (%)": st.column_config.NumberColumn(
                    "Redução de Erro (%)", format="%+.1f%%"
                ),
                "Brier Score": st.column_config.NumberColumn("Brier Score", format="%.4f"),
            },
        )

    # 7. Credenciais de Calibração Pós-1º Turno por Instituto
    if calibration_map:
        with st.expander(
            "🏅 Ver Ranking de Credibilidade dos Institutos (Auditoria do 1º Turno e Pesos no Modelo)"
        ):
            cal_rows = []
            for inst_name, cal_obj in sorted(
                calibration_map.items(), key=lambda x: x[1].erro_ponderado_t1
            ):
                bias_top = " | ".join(
                    f"{k}: {v:+.2f} pp" for k, v in list(cal_obj.vies_direcional_t1.items())[:2]
                )
                cal_rows.append(
                    {
                        "Instituto": inst_name,
                        "Pesquisas no 1º Turno": cal_obj.n_pesquisas_t1,
                        "Erro Ponderado no 1º Turno (EP_T1)": cal_obj.erro_ponderado_t1,
                        "Multiplicador de Credibilidade": cal_obj.peso_auditoria,
                        "Viés Medido no 1º Turno (Top 2)": bias_top,
                        "Peso Final na Previsão Atual (%)": forecast.pesos_institutos.get(
                            inst_name, 0.0
                        ),
                    }
                )
            st.dataframe(
                pl.DataFrame(cal_rows),
                width="stretch",
                hide_index=True,
                column_config={
                    "Erro Ponderado no 1º Turno (EP_T1)": st.column_config.NumberColumn(
                        "Erro no 1º Turno (EP)", format="%.2f"
                    ),
                    "Multiplicador de Credibilidade": st.column_config.NumberColumn(
                        "Fator Credibilidade exp(-λ·EP)", format="%.3f"
                    ),
                    "Peso Final na Previsão Atual (%)": st.column_config.NumberColumn(
                        "Participação no Modelo (%)", format="%.2f%%"
                    ),
                },
            )

    # 8. Memorial Metodológico do Modelo Preditivo
    with st.expander("📐 Memorial Matemático — Modelo Estado-Espaço Hierárquico Calibrado"):
        st.markdown(
            r"""
            #### Formulação Estrutural do Modelo Preditivo

            1. **Peso Composto por Levantamento ($W_k$):**
               $$W_k = \left(\frac{n_k}{\text{deff}_k}\right) \cdot \exp\left(-\frac{t_{\text{corte}} - t_k}{\tau}\right) \cdot w_{\text{escopo}}(a_k) \cdot w_{\text{audit}, i(k)}$$
               Onde $n_k / \text{deff}_k$ é o tamanho efetivo da amostra, $\tau = 7\text{ dias}$ é a meia-vida temporal, $w_{\text{escopo}} \in \{1.00\text{ (Nacional)}, 0.75\text{ (Estadual)}, 0.45\text{ (Regional)}\}$ e $w_{\text{audit}, i} = \exp(-\lambda \cdot \text{EP}_{\text{T1}, i})$ é a credencial empírica pós-1º Turno.

            2. **De-biasing Hierárquico (House Effects + Calibração de 1º Turno):**
               $$\tilde{y}_{k, c} = y_{k, c}^{(\text{nac})} - \alpha_{\text{shrink}} \cdot \left(0.55 \cdot \hat{\delta}_{\text{T1}, i(k), c} + 0.45 \cdot \hat{\delta}_{\text{peer}, i(k), c}\right)$$

            3. **Pós-Estratificação pelo Colégio Eleitoral do TSE:**
               $$\mu_{\text{colégio}, c} = \sum_{r \in \{\text{SE, NE, S, N, CO}\}} \omega_r \cdot \left[\gamma_r \bar{y}_{r, c} + (1 - \gamma_r)\left(\mu_{\text{nac}, c} + \Delta_{\text{reg}, r, c}\right)\right]$$
               Com pesos oficiais $\omega_{\text{SE}}=0.426$, $\omega_{\text{NE}}=0.271$, $\omega_{\text{S}}=0.147$, $\omega_{\text{N}}=0.086$, $\omega_{\text{CO}}=0.070$.

            4. **Simulação de Monte Carlo com Caudas Pesadas ($t$-Student, $\nu = 5$):**
               $$P(\text{Vitória}_A) = \frac{1}{N_{\text{sim}}} \sum_{s=1}^{N_{\text{sim}}} \mathbb{I}\left(\tilde{P}_A^{(s)} > \max_{B \neq A} \tilde{P}_B^{(s)}\right), \quad N_{\text{sim}} = 10.000$$
            """
        )


# Alias para retrocompatibilidade
render_act6 = render_act7
