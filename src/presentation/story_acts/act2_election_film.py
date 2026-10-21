"""Ato 2: O Filme da Eleição (Agregador Dinâmico).

Demonstra a dinâmica longitudinal da corrida eleitoral, confrontando a falácia de que
pesquisas passadas falharam quando na realidade capturaram uma dinâmica volátil de campanha.
"""

from datetime import date, timedelta
from typing import Sequence

import streamlit as st

from src.analytics.aggregator_model import (
    compute_phase_aggregation_metrics,
    compute_poll_aggregation_series,
)
from src.presentation.components.phase_story_chart import create_phases_comparison_chart
from src.presentation.components.trend_chart import create_trend_aggregator_chart
from src.transformations.schemas import PesquisaEleitoralSchema


def render_act2(polls: Sequence[PesquisaEleitoralSchema]) -> None:
    """Renderiza a narrativa e visualização do Agregador Dinâmico no Ato 2.

    Args:
        polls: Lista das pesquisas registradas do turno selecionado.

    Returns:
        None.

    Raises:
        None.
    """
    st.markdown("## Ato 2: O Filme da Eleição (Agregador Dinâmico)")
    st.markdown(
        """
        > *“Pesquisa eleitoral não é bola de cristal nem profecia: é uma fotografia do momento.”*

        Durante a campanha, a opinião pública se move em resposta a debates, revelações, propaganda
        e alianças. O **Agregador Dinâmico** extrai a verdadeira trajetória latente do eleitorado
        combinando centenas de pesquisas com decaimento temporal exponencial (meia-vida de 14 dias),
        garantindo que levantamentos mais recentes e com maiores amostras tenham maior peso.
        """
    )

    METHODOLOGY_LABELS = {
        "PRESENCIAL_DOMICILIAR": "Presencial Domiciliar",
        "PRESENCIAL_FLUXO": "Presencial (Pontos de Fluxo)",
        "TELEFONICA_CATI": "Telefônica (CATI)",
        "TELEFONICA_URA": "Telefônica (Robô / URA)",
        "ONLINE": "Online / Painel Digital",
    }

    CANDIDATE_COLORS = {
        "Lula": "#EF4444",
        "Flávio Bolsonaro": "#1D4ED8",
        "Bolsonaro": "#3B82F6",
        "Augusto Cury": "#8B5CF6",
        "Romeu Zema": "#F97316",
        "Renan Santos": "#0EA5E9",
        "Simone Tebet": "#10B981",
        "Ciro Gomes": "#F59E0B",
    }

    ano_pleito = polls[0].ano if polls else 2026
    turno_atual = polls[0].turno if (polls and hasattr(polls[0], "turno")) else 1

    # Linha 1: Seleção de Candidatos e Metodologias (espaço amplo para tags/pills sem truncamento)
    row1_col1, row1_col2 = st.columns([1.0, 1.0])
    with row1_col1:
        available_cands = sorted(
            list({c for p in polls for c in p.votos_validos.keys() if c != "Outros"})
        )
        default_cands = [
            c for c in ["Lula", "Flávio Bolsonaro", "Bolsonaro"] if c in available_cands
        ]
        if not default_cands and available_cands:
            default_cands = available_cands[: min(2, len(available_cands))]
        selected_candidates = st.multiselect(
            "Candidatos para Visualização:",
            options=available_cands,
            default=default_cands,
            key=f"act2_candidates_{ano_pleito}_{turno_atual}",
        )
        # Sanitiza candidatos caso haja resíduos de estados anteriores
        selected_candidates = [c for c in selected_candidates if c in available_cands]
    with row1_col2:
        metodologias_disponiveis = sorted(list({p.metodologia.value for p in polls}))
        filtro_metodologia = st.multiselect(
            "Filtrar por Metodologia de Coleta:",
            options=metodologias_disponiveis,
            default=metodologias_disponiveis,
            format_func=lambda m: METHODOLOGY_LABELS.get(m, m),
            key=f"act2_methods_{ano_pleito}_{turno_atual}",
        )

    # Opções de Horizonte Temporal: 3 fases canônicas no 1º turno e divisão em 3 semanas no 2º turno
    if turno_atual == 1:
        opcoes_horizonte = [
            "Ciclo Completo (Jul-Out)",
            "Campanha Oficial (Ago-Out)",
            "Reta Final (14 dias)",
        ]
    else:
        opcoes_horizonte = [
            "Ciclo Completo (2º Turno)",
            "1ª Semana (Arranjos & Alianças)",
            "2ª Semana (Horário Eleitoral & Debates)",
            "3ª Semana (Reta Final)",
        ]

    # Linha 2: Controles Horizontais de Escopo (Horizonte Temporal e Base de Votação)
    row2_col1, row2_col2 = st.columns([1.2, 0.8])
    with row2_col1:
        filtro_horizonte = st.radio(
            "Horizonte Temporal:",
            opcoes_horizonte,
            index=0,
            horizontal=True,
            help="Alterne entre a visão macro longitudinal e o foco nos períodos críticos da reta final.",
            key=f"act2_horizon_{ano_pleito}_{turno_atual}",
        )
    with row2_col2:
        tipo_metrica = st.radio(
            "Base de Votação:",
            ["Votos Válidos (Oficial)", "Votos Totais (Bruto)"],
            index=0,
            horizontal=True,
            help="Alterne entre votos válidos (sem brancos/nulos) e cenário estimulado bruto.",
            key=f"act2_metric_{ano_pleito}_{turno_atual}",
        )
        use_valid = "Válidos" in tipo_metrica

    # Pesquisas filtradas por metodologia
    methodology_polls = [p for p in polls if p.metodologia.value in filtro_metodologia]

    # =========================================================================
    # Seção 1: Trajetória Contínua do Agregador (Série Diária) - Exibida primeiro
    # =========================================================================
    st.markdown("### Trajetória Contínua do Agregador (Série Diária)")

    # Filtra pesquisas de acordo com o Horizonte Temporal selecionado no rádio
    filtered_polls = list(methodology_polls)
    if filtered_polls:
        max_date = max(p.data_fim_campo for p in filtered_polls)
        min_date = min(p.data_fim_campo for p in filtered_polls)

        if turno_atual == 1:
            if "Campanha Oficial" in filtro_horizonte:
                data_corte_campanha = date(ano_pleito, 8, 16)
                filtered_polls = [
                    p for p in filtered_polls if p.data_fim_campo >= data_corte_campanha
                ]
            elif "Reta Final" in filtro_horizonte:
                data_corte_reta_final = max_date - timedelta(days=14)
                filtered_polls = [
                    p for p in filtered_polls if p.data_fim_campo >= data_corte_reta_final
                ]
        else:
            if ano_pleito == 2026:
                t1_d = date(2026, 10, 4)
                t2_d = date(2026, 10, 25)
            elif ano_pleito == 2022:
                t1_d = date(2022, 10, 2)
                t2_d = date(2022, 10, 30)
            else:
                t1_d = min_date - timedelta(days=1)
                t2_d = max_date

            w1_s = t1_d + timedelta(days=1)
            w1_e = w1_s + timedelta(days=6)
            w2_s = w1_e + timedelta(days=1)
            w2_e = w2_s + timedelta(days=6)
            w3_s = w2_e + timedelta(days=1)
            w3_e = max(t2_d, max_date)

            if "1ª Semana" in filtro_horizonte:
                filtered_polls = [p for p in filtered_polls if w1_s <= p.data_fim_campo <= w1_e]
            elif "2ª Semana" in filtro_horizonte:
                filtered_polls = [p for p in filtered_polls if w2_s <= p.data_fim_campo <= w2_e]
            elif "3ª Semana" in filtro_horizonte:
                filtered_polls = [p for p in filtered_polls if w3_s <= p.data_fim_campo <= w3_e]

    if not filtered_polls:
        st.warning("Nenhuma pesquisa encontrada para os filtros selecionados.")
    else:
        # Computa agregação dinâmica da série diária
        with st.spinner("Computando trajetória latente e envelopes de credibilidade..."):
            df_agg = compute_poll_aggregation_series(
                polls=filtered_polls,
                candidates=selected_candidates,
                half_life_days=14.0,
                deff=1.3,
                use_valid_votes=use_valid,
            )

        fig = create_trend_aggregator_chart(
            df_agg=df_agg,
            polls=filtered_polls,
            candidates=selected_candidates,
        )
        st.plotly_chart(fig, width="stretch")

        st.markdown(
            """
            #### Entendendo as Fitas de Incerteza
            As faixas sombreadas representam o **Envelope de Credibilidade de 95%**. Elas combinam
            duas fontes de incerteza:
            1. **Variância Amostral ($deff$):** O erro estocástico intrínseco a cada tamanho amostral.
            2. **Variância Inter-Institutos:** A dispersão observada entre levantamentos realizados no mesmo período por diferentes metodologias.
            """
        )

    # =========================================================================
    # Seção 2: A História das Fases - Volume e Posição dos Candidatos
    # =========================================================================
    st.markdown("---")
    st.markdown("### A História das Fases: Volume de Pesquisas e Posição dos Candidatos")
    st.markdown(
        """
        Ao longo do processo eleitoral, o ritmo de pesquisas se intensifica dramaticamente e a intenção de voto
        cristaliza. Os cartões abaixo comparam as **3 fases do pleito**, sintetizando **quantas pesquisas saíram**
        e **onde cada candidato se posicionava** segundo a estimativa agregada.
        """
    )

    phase_summaries = compute_phase_aggregation_metrics(
        polls=methodology_polls,
        candidates=selected_candidates,
        ano_pleito=ano_pleito,
        turno=turno_atual,
        use_valid_votes=use_valid,
    )

    # Renderiza os 3 Cards KPI em colunas
    card_cols = st.columns(3)
    for i, s in enumerate(phase_summaries):
        with card_cols[i]:
            is_active = (s.rotulo_curto in filtro_horizonte) or (s.nome_fase in filtro_horizonte)
            border_style = "2px solid #38BDF8" if is_active else "1px solid #282D37"
            bg_card = "#1C2128" if is_active else "#181B20"
            badge_active = (
                "<span style='background-color:#0284C7; color:#FFFFFF; font-size:10px; "
                "font-weight:700; padding:2px 7px; border-radius:4px; letter-spacing:0.5px;'>SELEÇÃO ATIVA</span>"
                if is_active
                else ""
            )

            cands_html_list: list[str] = []
            for cand in selected_candidates:
                est = s.estimativas.get(cand)
                c_color = CANDIDATE_COLORS.get(cand, "#94A3B8")
                bullet = (
                    f"<span style='display:inline-block; width:9px; height:9px; border-radius:50%; "
                    f"background-color:{c_color}; margin-right:6px;'></span>"
                )

                if est and est.media_ponderada > 0:
                    delta_str = ""
                    if est.delta_anterior is not None:
                        d_col = (
                            "#10B981"
                            if est.delta_anterior > 0
                            else ("#EF4444" if est.delta_anterior < 0 else "#94A3B8")
                        )
                        delta_str = (
                            f" <span style='color:{d_col}; font-size:11px; font-weight:700;'>"
                            f"({est.delta_anterior:+.1f} pp)</span>"
                        )
                    cands_html_list.append(
                        f"<div style='margin-bottom:4px; font-size:13px;'>"
                        f"{bullet}<b>{cand}:</b> "
                        f"<span style='font-weight:700; font-size:14.5px; color:#F8FAFC;'>{est.media_ponderada:.1f}%</span> "
                        f"<span style='color:#94A3B8; font-size:11px;'>[{est.ic_95_inf:.1f}%–{est.ic_95_sup:.1f}%]</span>"
                        f"{delta_str}"
                        f"</div>"
                    )
                else:
                    cands_html_list.append(
                        f"<div style='margin-bottom:4px; font-size:12.5px; color:#64748B;'>"
                        f"{bullet}{cand}: Sem dados nesta fase</div>"
                    )

            cands_html = (
                "".join(cands_html_list)
                if cands_html_list
                else "<div style='color:#64748B;'>Nenhum candidato selecionado</div>"
            )

            lider_html = ""
            if s.lider and s.margem_lider_vice is not None:
                lider_html = (
                    f"<div style='margin-top:8px; padding-top:6px; border-top:1px dashed #282D37; "
                    f"font-size:11.5px; color:#94A3B8;'>"
                    f"🏆 Liderança: <b style='color:#F1F5F9;'>{s.lider}</b> "
                    f"(<span style='color:#38BDF8; font-weight:700;'>+{s.margem_lider_vice:.1f} pp</span>)"
                    f"</div>"
                )

            card_header = (
                f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;'>"
                f"<div><span style='font-size:16px; margin-right:5px;'>{s.icone}</span>"
                f"<b style='color:#F1F5F9; font-size:14px;'>{s.nome_fase}</b></div>"
                f"{badge_active}"
                f"</div>"
            )

            period_info = (
                f"<div style='color:#94A3B8; font-size:11.5px; margin-bottom:10px;'>"
                f"📅 {s.descricao_periodo} • {s.dias_duracao} dias"
                f"</div>"
            )

            volume_box = (
                f"<div style='background-color:#121417; border-radius:6px; padding:8px 10px; margin-bottom:10px; font-size:12.5px;'>"
                f"<span style='color:#F8FAFC; font-weight:700;'>{s.total_pesquisas} pesquisas</span> "
                f"<span style='color:#94A3B8;'>({s.percentual_total_pesquisas:.1f}% da base)</span><br>"
                f"<span style='color:#38BDF8; font-weight:600;'>⚡ {s.pesquisas_por_dia:.1f}</span> "
                f"<span style='color:#94A3B8;'>pesquisas/dia</span>"
                f"</div>"
            )

            card_html = (
                f"<div style='background-color:{bg_card}; border:{border_style}; border-radius:8px; padding:14px 16px; margin-bottom:12px; height:100%;'>"
                f"{card_header}"
                f"{period_info}"
                f"{volume_box}"
                f"{cands_html}"
                f"{lider_html}"
                f"</div>"
            )
            st.markdown(card_html, unsafe_allow_html=True)

    # Gráfico Plotly Comparativo das 3 Fases (Trajetória + Volume)
    if any(s.total_pesquisas > 0 for s in phase_summaries):
        fig_phases = create_phases_comparison_chart(
            summaries=phase_summaries,
            candidates=selected_candidates,
            candidate_colors=CANDIDATE_COLORS,
        )
        st.plotly_chart(fig_phases, width="stretch")
