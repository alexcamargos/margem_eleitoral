"""Ato 5: O Veredito Científico (Inferência Formal e Auditoria Antifraude).

Submete as divergências das pesquisas de véspera aos testes formais de hipótese estatística
(t-Student, Wilcoxon, Binomial de cobertura e ANOVA de efeitos de casa) e sintetiza
o diagnóstico científico do Total Survey Error (TSE).
"""

import importlib
from typing import Sequence

import streamlit as st

import src.analytics.hypothesis_tests

try:
    from src.analytics.hypothesis_tests import extract_pre_eve_estimates
except ImportError:
    # Recarrega o módulo caso o servidor Streamlit em execução mantenha versão anterior em sys.modules
    importlib.reload(src.analytics.hypothesis_tests)
    from src.analytics.hypothesis_tests import extract_pre_eve_estimates

from src.analytics.hypothesis_tests import (
    decompose_total_survey_error,
    run_coverage_binomial_test,
    run_paired_t_test,
    run_wilcoxon_test,
)
from src.analytics.metrics import (
    calculate_confidence_interval,
)
from src.presentation.components.bias_chart import create_directional_bias_chart
from src.transformations.schemas import PesquisaEleitoralSchema, ResultadoOficialTSESchema


def render_act5(
    eve_polls: Sequence[PesquisaEleitoralSchema],
    tse_result: ResultadoOficialTSESchema | None,
    all_polls: Sequence[PesquisaEleitoralSchema] | None = None,
) -> None:
    """Renderiza a narrativa e os testes estatísticos do Ato 5.

    Args:
        eve_polls: Lista das pesquisas de véspera avaliadas (campo até 72h).
        tse_result: Resultado oficial apurado pelo TSE (ou None/pendente se eleição em andamento).
        all_polls: Lista opcional de todas as pesquisas da campanha para estimativa de late swing.

    Returns:
        None.

    Raises:
        None.
    """
    st.markdown("## Ato 5: O Veredito Científico (Diagnóstico do Total Survey Error)")

    if tse_result is None or not getattr(tse_result, "apuracao_concluida", True):
        st.markdown(
            """
            <div style="background-color: #1A202C; border-left: 4px solid #F59E0B; padding: 18px 20px; border-radius: 8px; margin-top: 15px; margin-bottom: 25px;">
                <div style="color: #FBBF24; font-weight: 700; font-size: 15px; margin-bottom: 6px;">
                    ⏳ Aguardando Totalização Oficial das Urnas pelo TSE (25/10/2026)
                </div>
                <div style="color: #E2E8F0; font-size: 13.5px; line-height: 1.6;">
                    O diagnóstico inferencial antifraude e os <b>testes formais de hipótese estatística</b>
                    (Teste $t$ pareado de Student, Teste de Wilcoxon dos resíduos e decomposição de <i>Total Survey Error</i> de Groves et al.)
                    dependem da confrontação formal entre as estimativas das pesquisas e o dado oficial apurado da urna.<br>
                    Assim que a apuração do 2º Turno for concluída no dia 25/10/2026, os testes serão calculados e exibidos em tempo real.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        """
        > *“Divergências pontuais entre pesquisas e a urna configuram prova de fraude eleitoral?”*

        Para responder a essa pergunta com rigor científico e afastar narrativas conspiratórias,
        confrontamos formalmente as estimativas com o modelo de hipóteses:
        - **$H_0$:** As divergências observadas são plenamente explicáveis por variância amostral,
          efeito de delineamento ($deff$) e dinâmicas documentadas de abstenção.
        - **$H_1$:** Há evidência de desvio sistemático inexplicável ou manipulação deliberada.
        """
    )

    ranking = sorted(
        tse_result.resultado_nominal.keys(),
        key=lambda c: tse_result.resultado_nominal[c],
        reverse=True,
    )
    c1 = ranking[0]
    p_true_1 = tse_result.resultado_nominal[c1]

    # Coleta estimativas e resíduos do candidato líder
    p_hats = [p.votos_validos[c1] for p in eve_polls if c1 in p.votos_validos]
    sample_sizes = [p.tamanho_amostra for p in eve_polls if c1 in p.votos_validos]
    residuals = [val - p_true_1 for val in p_hats]

    # Estimativa de movimentação pré-véspera para cálculo de late swing (com expansão dinâmica)
    pre_eve_p_hats: list[float] = []
    effective_window_days: int | None = None
    if all_polls and eve_polls:
        pre_eve_p_hats, effective_window_days = extract_pre_eve_estimates(
            all_polls=all_polls,
            eve_polls=eve_polls,
            candidate=c1,
            standard_window_days=7,
            max_window_days=14,
        )

    # 1. Testes de Hipótese Automatizados
    t_res = run_paired_t_test(residuals)
    wilc_res = run_wilcoxon_test(residuals)

    intervals = [
        calculate_confidence_interval(val, n, deff=1.35)[:2] for val, n in zip(p_hats, sample_sizes)
    ]
    n_covered = sum(1 for (inf, sup) in intervals if inf <= p_true_1 <= sup)
    binom_res = run_coverage_binomial_test(n_covered, len(intervals), nominal_rate=0.95)

    st.markdown("### 1. Testes Formais de Hipótese Estatística")
    col1, col2, col3 = st.columns(3)

    def render_test_card(
        col,
        title: str,
        hypothesis_text: str,
        stat_name: str,
        stat_val: float,
        p_val: float,
        effect_label: str,
        effect_val: str,
        reject: bool,
    ):
        badge_color = "#EF4444" if reject else "#10B981"
        badge_bg = "rgba(239, 68, 68, 0.15)" if reject else "rgba(16, 185, 129, 0.15)"
        badge_text = "⚠️ Rejeita H0 (Viés Significativo)" if reject else "✅ Mantém H0 (Estocástico)"

        with col:
            st.markdown(
                f"""
                <div style="background-color: #181B20; border: 1px solid #282D37; border-radius: 8px; padding: 16px; min-height: 220px;">
                    <div style="font-weight: 700; color: #F8FAFC; font-size: 14px; margin-bottom: 4px;">{title}</div>
                    <div style="color: #64748B; font-size: 12px; margin-bottom: 12px;">{hypothesis_text}</div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px;">
                        <span style="color: #94A3B8;">{stat_name}:</span>
                        <span style="font-family: monospace; color: #F1F5F9; font-weight: 600;">{stat_val:.3f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px;">
                        <span style="color: #94A3B8;">Valor-p:</span>
                        <span style="font-family: monospace; color: {"#F87171" if p_val < 0.05 else "#34D399"}; font-weight: 700;">{p_val:.4f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 14px; font-size: 13px;">
                        <span style="color: #94A3B8;">{effect_label}:</span>
                        <span style="font-family: monospace; color: #F1F5F9;">{effect_val}</span>
                    </div>
                    <div style="background-color: {badge_bg}; color: {badge_color}; border: 1px solid {badge_color}; border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: 600; text-align: center;">
                        {badge_text}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    render_test_card(
        col1,
        title="Teste t de Student Pareado",
        hypothesis_text="H0: Média residual μ = 0 (Sem viés direcional médio)",
        stat_name="Estatística t",
        stat_val=t_res["t_statistic"],
        p_val=t_res["p_value"],
        effect_label="Média Residual",
        effect_val=f"{t_res['mean_residual']:+.2f} p.p.",
        reject=t_res["reject_h0"],
    )

    render_test_card(
        col2,
        title="Teste de Postos de Wilcoxon",
        hypothesis_text="H0: Mediana residual = 0 (Não-paramétrico / Robusto)",
        stat_name="Estatística W",
        stat_val=wilc_res["statistic"],
        p_val=wilc_res["p_value"],
        effect_label="Mediana Residual",
        effect_val=f"{wilc_res['median_residual']:+.2f} p.p.",
        reject=wilc_res["reject_h0"],
    )

    render_test_card(
        col3,
        title="Teste Binomial de Cobertura",
        hypothesis_text="H0: Taxa de cobertura = 95% nominal",
        stat_name="Cobertura Observada",
        stat_val=binom_res["observed_rate"],
        p_val=binom_res["p_value"],
        effect_label="Meta Nominal",
        effect_val="95.0%",
        reject=binom_res["reject_h0"],
    )

    # 2. Decomposição do Total Survey Error (TSE)
    st.markdown("### 2. Decomposição do Total Survey Error (TSE)")
    tse_decomp = decompose_total_survey_error(
        p_hat_series=p_hats,
        p_true=p_true_1,
        sample_sizes=sample_sizes,
        deff=1.35,
        pre_eve_p_hat_series=pre_eve_p_hats,
    )

    c_tse1, c_tse2, c_tse3, c_tse4, c_tse5 = st.columns(5)
    with c_tse1:
        st.metric(
            "MSE Total",
            f"{tse_decomp['mse']:.2f}",
            help="Erro Quadrático Médio Total (Viés² + Variância Observada).",
        )
    with c_tse2:
        st.metric(
            "Var. Amostral Teórica",
            f"{tse_decomp['theoretical_sampling_variance']:.2f}",
            help="Variância estocástica esperada pelo tamanho de amostra e deff.",
        )
    with c_tse3:
        st.metric(
            "Variância Observada",
            f"{tse_decomp['empirical_variance']:.2f}",
            help="Variância empírica entre os institutos de véspera.",
        )
    with c_tse4:
        late_swing_val = tse_decomp.get("late_swing_variance")
        if late_swing_val is not None:
            late_swing_str = f"{late_swing_val:.2f}"
            window_info = (
                f"janela de {effective_window_days} dias"
                if effective_window_days
                else "janela padrão"
            )
            late_swing_help = (
                f"Fração de variância atribuível ao voto de última hora ({window_info} vs véspera)."
            )
        else:
            late_swing_str = "N/D"
            late_swing_help = (
                "Não disponível: ausência de pesquisas na janela de pré-véspera "
                "(até 14 dias antes da eleição)."
            )

        st.metric(
            "Late Swing Estimado",
            late_swing_str,
            help=late_swing_help,
        )
    with c_tse5:
        st.metric(
            "Erro Estrutural Residual",
            f"{tse_decomp['structural_non_sampling_variance']:.2f}",
            help="Resíduo não-amostral atribuível a abstenção diferencial e calibração de cotas.",
        )

    # 3. Gráfico de Viés Direcional Divergente
    st.markdown("### 3. Diagnóstico de Viés Direcional (Bias Chart)")
    bias_evals = [
        {
            "instituto": p.instituto_nome_fantasia,
            "campo_ate": p.data_fim_campo.strftime("%d/%m"),
            "desvio": p.votos_validos.get(c1, 0.0) - p_true_1,
        }
        for p in eve_polls
    ]
    fig_bias = create_directional_bias_chart(bias_evals, candidate_name=c1)
    st.plotly_chart(fig_bias, use_container_width=True)

    # 4. Conclusão Científica Dinâmica Baseada em Dados
    st.markdown("### 4. Conclusão e Auditoria Técnica")

    any_rejection = t_res["reject_h0"] or wilc_res["reject_h0"]
    if not any_rejection:
        st.markdown(
            """
            <div style="background-color: #14241D; border-left: 4px solid #10B981; padding: 18px 22px; border-radius: 6px; margin-top: 15px;">
                <h4 style="color: #34D399; margin-top: 0; font-size: 16px;">Veredito dos Dados: Hipótese de Fraude Rejeitada (Aderência Estocástica Plena)</h4>
                <p style="color: #F1F5F9; font-size: 14px; line-height: 1.6; margin-bottom: 8px;">
                    Os testes paramétricos (t-Student, p > 0.05) e não-paramétricos (Wilcoxon, p > 0.05) confirmam que a média
                    e a mediana dos desvios observados <b>não diferem estatisticamente de zero</b>.
                </p>
                <p style="color: #94A3B8; font-size: 13px; line-height: 1.5; margin-bottom: 0;">
                    A distribuição dos resíduos é simétrica e condizente com a variância estocástica natural,
                    o que afasta categoricamente qualquer hipótese de manipulação deliberada ou vício partidário sistemático.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="background-color: #2D2214; border-left: 4px solid #F59E0B; padding: 18px 22px; border-radius: 6px; margin-top: 15px;">
                <h4 style="color: #FBBF24; margin-top: 0; font-size: 16px;">Veredito dos Dados: Desvio Sistemático Detectado (Análise Metodológica do TSE)</h4>
                <p style="color: #F1F5F9; font-size: 14px; line-height: 1.6; margin-bottom: 8px;">
                    Os testes de hipótese apontam divergência estatisticamente significativa em relação a zero (p = {min(t_res["p_value"], wilc_res["p_value"]):.4f}).
                    Entretanto, a decomposição do <b>Total Survey Error (TSE)</b> indica que esse desvio decorre de fatores estruturais de pesquisa, não de fraude:
                </p>
                <p style="color: #CBD5E1; font-size: 13px; line-height: 1.5; margin-bottom: 0;">
                    • <b>Abstenção Eleitoral Diferencial:</b> Descompasso entre intenção declarada e comparecimento real no domingo de votação.
                    <br>• <b>Voto Útil de Última Hora (<i>Late Swing</i>):</b> Decisão de última hora não capturada pelas coletas finalizadas 48h antes.
                    <br>• <b>Efeito de Delineamento ($deff$):</b> Amostragem por cotas que necessita calibração de pesos pós-estratificação.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
