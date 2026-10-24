"""Ato 4: A Prova dos Fatos (Pesquisas de Véspera vs. Urna).

Apresenta o confronto formal entre as últimas estimativas divulgadas e a apuração
oficial do TSE por meio do Forest Plot e medição da Taxa de Cobertura Empírica.
"""

from typing import Any, Sequence

import streamlit as st

from src.analytics.metrics import (
    calculate_confidence_interval,
    calculate_coverage_rate,
)
from src.presentation.components.forest_plot import create_forest_plot
from src.transformations.schemas import PesquisaEleitoralSchema, ResultadoOficialTSESchema


def render_act4(
    eve_polls: Sequence[PesquisaEleitoralSchema],
    tse_result: ResultadoOficialTSESchema | None,
) -> None:
    """Renderiza a narrativa e os componentes do Forest Plot no Ato 4.

    Args:
        eve_polls: Lista das pesquisas que cumpriram o critério de véspera (<= 72h).
        tse_result: Resultado oficial apurado pelo TSE (ou None/pendente se eleição em andamento).

    Returns:
        None.

    Raises:
        None.
    """
    st.markdown("## Ato 4: A Prova dos Fatos (Pesquisas de Véspera vs. Urna)")

    if tse_result is None or not getattr(tse_result, "apuracao_concluida", True):
        st.markdown(
            """
            <div style="background-color: #1A202C; border-left: 4px solid #F59E0B; padding: 18px 20px; border-radius: 8px; margin-top: 15px; margin-bottom: 25px;">
                <div style="color: #FBBF24; font-weight: 700; font-size: 15px; margin-bottom: 6px;">
                    ⏳ Aguardando Totalização Oficial das Urnas pelo TSE (25/10/2026)
                </div>
                <div style="color: #E2E8F0; font-size: 13.5px; line-height: 1.6;">
                    O <b>Forest Plot</b> e o teste de cobertura nominal de 95% confrontam diretamente as estimativas de véspera
                    contra os votos válidos reais apurados nas urnas eletrônicas.<br>
                    Como o pleito do 2º Turno ainda está em andamento, esta auditoria formal será liberada imediatamente após
                    a divulgação dos boletins de urna pelo TSE.<br>
                    Para acompanhar o cenário dinâmico atual e as projeções probabilísticas, consulte o
                    <b>Ato 2 (Agregador Dinâmico)</b> e o <b>Ato 6 (Modelo Preditivo / Nowcasting)</b>.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        """
        > *“Apenas as pesquisas finalizadas a no máximo 72 horas antes da abertura das urnas "
        têm validade para confronto formal com o resultado oficial.”*

        Pesquisas anteriores a 72h capturam intenções antes da consolidação final e de movimentações
        tardias de voto útil (*late swing*). Abaixo, cada instituto é submetido ao teste de cobertura
        nominal de 95% corrigido pelo **efeito de delineamento ($deff = 1{,}35$)**.
        """
    )

    candidates_official = list(tse_result.resultado_nominal.keys())
    cand_focus = st.selectbox(
        "Selecione o Candidato para Auditoria no Forest Plot:",
        options=candidates_official,
        index=0,
    )
    p_true = tse_result.resultado_nominal[cand_focus]

    # Prepara avaliações de cada pesquisa de véspera
    evaluations: list[dict[str, Any]] = []
    intervals: list[tuple[float, float]] = []

    for p in eve_polls:
        if cand_focus in p.votos_validos:
            p_est = p.votos_validos[cand_focus]
            inf, sup, me = calculate_confidence_interval(
                p_percent=p_est,
                n_sample=p.tamanho_amostra,
                deff=p.deff_estimado,
                confidence_level=0.95,
            )
            evaluations.append(
                {
                    "instituto": p.instituto_nome_fantasia,
                    "campo_ate": p.data_fim_campo.strftime("%d/%m"),
                    "data_fim": p.data_fim_campo,
                    "estimativa": p_est,
                    "ic_inf": inf,
                    "ic_sup": sup,
                    "margem_erro": me,
                }
            )
            intervals.append((inf, sup))

    if not evaluations:
        st.warning(f"Nenhuma estimativa encontrada para '{cand_focus}' nas pesquisas de véspera.")
        return

    true_values = [p_true] * len(intervals)
    coverage_rate = calculate_coverage_rate(intervals, true_values)

    # Exibe KPIs de destaque
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Total Pesquisas de Véspera", f"{len(evaluations)}")
    with kpi2:
        st.metric(f"Urna TSE ({cand_focus})", f"{p_true:.2f}%")
    with kpi3:
        st.metric(
            "Taxa Cobertura Empírica",
            f"{coverage_rate:.1f}%",
            delta=f"{coverage_rate - 95.0:+.1f} p.p. vs meta",
            delta_color="normal" if coverage_rate >= 80.0 else "inverse",
        )
    with kpi4:
        st.metric("Meta Teórica Nominal", "95.0%")

    fig_forest = create_forest_plot(
        eve_evaluations=evaluations,
        candidate_name=cand_focus,
        official_vote_percent=p_true,
    )
    st.plotly_chart(fig_forest, width="stretch")

    if coverage_rate >= 80.0:
        st.success(
            f"✅ **Aderência Robusta:** {coverage_rate:.1f}% dos intervalos de confiança de 95% "
            f"capturaram o resultado oficial da urna ({p_true:.2f}%). As divergências observadas "
            "são plenamente compatíveis com a variância estocástica esperada."
        )
    else:
        st.warning(
            f"⚠️ **Alerta Metodológico:** A taxa de cobertura empírica foi de {coverage_rate:.1f}%, "
            "abaixo da meta teórica de 95%. Isso indica presença de fatores não-amostrais adicionais "
            "(como abstenção diferencial e decisão de última hora)."
        )


# Alias para retrocompatibilidade
render_act3 = render_act4
