"""Componente visual para exibição da Análise de Sensibilidade e Robustez (Ato 7).

Apresenta a comparação entre a regra Principal (P) e as 12 variantes metodológicas (S0 a S11):
- Diagnóstico executivo em card dark mode com veredito de robustez.
- Gráfico Plotly horizontal (Dot/Forest Plot) com linha de maioria de 50%.
- Tabela interativa com formatação de precisão e regras metodológicas detalhadas.
- Memorial didático dos 5 eixos de perturbação estatística.
"""

from typing import Sequence

import plotly.graph_objects as go
import polars as pl
import streamlit as st

from src.analytics.sensitivity_analysis import (
    SensitivityReport,
    SensitivityVariantResult,
    get_sensitivity_report,
)
from src.transformations.schemas import PesquisaEleitoralSchema

SENSITIVITY_CSS = """
<style>
.sens-container {
    background-color: #181B20;
    border: 1px solid #282D37;
    border-radius: 10px;
    padding: 22px 24px;
    margin-top: 14px;
    margin-bottom: 22px;
    box-sizing: border-box;
}
.sens-badge {
    font-size: 11px;
    font-weight: 700;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.sens-badge::before {
    content: "";
    display: inline-block;
    width: 3px;
    height: 12px;
    background-color: #F59E0B;
    border-radius: 2px;
}
.sens-main-title {
    font-size: 20px;
    font-weight: 700;
    color: #F8FAFC;
    line-height: 1.25;
    margin-bottom: 4px;
}
.sens-subtitle {
    font-size: 13.5px;
    color: #94A3B8;
    line-height: 1.5;
}
.sens-verdict-card {
    background-color: #14171C;
    border-left: 4px solid #10B981;
    border-radius: 6px;
    padding: 14px 18px;
    margin: 16px 0 10px 0;
    color: #E2E8F0;
    font-size: 13.5px;
    line-height: 1.55;
}
.sens-metric-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    margin-top: 14px;
}
.sens-metric-item {
    background-color: #1E222A;
    border: 1px solid #282D37;
    border-radius: 6px;
    padding: 10px 14px;
    flex: 1 1 200px;
}
.sens-metric-label {
    font-size: 11px;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.sens-metric-val {
    font-size: 17px;
    font-weight: 700;
    color: #F8FAFC;
    margin-top: 3px;
}
</style>
"""


def create_sensitivity_forest_plot(
    variants: Sequence[SensitivityVariantResult],
    candidate_a: str = "Lula",
    candidate_b: str = "Flávio",
) -> go.Figure:
    """Gera um gráfico horizontal interativo (Dot Plot) comparando todas as 13 variantes.

    Plota cada variante em ordem com sua estimativa para o candidato A e a linha de 50%,
    destacando a variante Principal (P) com formatação visual prioritária.

    Args:
        variants: Lista ordenada das 13 variantes avaliadas.
        candidate_a: Nome do candidato A.
        candidate_b: Nome do candidato B.

    Returns:
        go.Figure: Figura Plotly interativa formatada em tema escuro.

    Raises:
        None.
    """
    fig = go.Figure()

    if not variants:
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#181B20",
            plot_bgcolor="#181B20",
            height=300,
        )
        return fig

    # Inverte a ordem para que P fique no topo do eixo vertical
    reversed_variants = list(reversed(variants))

    y_labels = [f"<b>{v.codigo}</b> — {v.variante}" for v in reversed_variants]
    x_vals_a = [round(v.p_validos_a * 100.0, 1) for v in reversed_variants]
    x_margins = [round(v.margem * 100.0, 1) for v in reversed_variants]
    probs_a = [round(v.prob_a * 100.0, 1) for v in reversed_variants]

    colors = [
        "#F59E0B" if v.codigo == "P" else ("#EF4444" if v.p_validos_a >= 0.50 else "#38BDF8")
        for v in reversed_variants
    ]
    sizes = [15 if v.codigo == "P" else 10 for v in reversed_variants]
    symbols = ["star" if v.codigo == "P" else "circle" for v in reversed_variants]

    # Linhas de conexão cinza da base até cada ponto
    for idx, (label, val_a) in enumerate(zip(y_labels, x_vals_a)):
        fig.add_shape(
            type="line",
            x0=46.0,
            y0=idx,
            x1=val_a,
            y1=idx,
            line=dict(color="#282D37", width=1.5, dash="dot"),
        )

    hover_texts = [
        (
            f"<b>{v.codigo}: {v.variante}</b><br>"
            f"• {candidate_a}: {x_vals_a[i]:.1f}% dos válidos<br>"
            f"• {candidate_b}: {100.0 - x_vals_a[i]:.1f}% dos válidos<br>"
            f"• Margem: {x_margins[i]:+.1f} p.p.<br>"
            f"• Chances {candidate_a}: {probs_a[i]:.1f}%<br>"
            f"• Favorito: {v.favorito}<br>"
            f"• Regra: {v.regra}"
        )
        for i, v in enumerate(reversed_variants)
    ]

    fig.add_trace(
        go.Scatter(
            x=x_vals_a,
            y=y_labels,
            mode="markers+text",
            marker=dict(
                size=sizes,
                color=colors,
                symbol=symbols,
                line=dict(color="#FFFFFF", width=1.2),
            ),
            text=[f" {v:.1f}%" for v in x_vals_a],
            textposition="middle right",
            textfont=dict(color="#CBD5E1", size=11),
            hovertext=hover_texts,
            hoverinfo="text",
            name="Válidos Lula",
        )
    )

    # Linha divisória de maioria de 50%
    fig.add_vline(
        x=50.0,
        line_dash="dash",
        line_color="#E2E8F0",
        line_width=1.5,
    )
    fig.add_annotation(
        x=50.0,
        y=1.03,
        xref="x",
        yref="paper",
        text="Maioria (50%)",
        showarrow=False,
        font=dict(color="#E2E8F0", size=11, family="sans-serif"),
        xanchor="center",
        yanchor="bottom",
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=520,
        margin=dict(l=190, r=40, t=45, b=45),
        xaxis=dict(
            title=dict(
                text=f"Votos Válidos Projetados para {candidate_a} (%)",
                font=dict(size=12, color="#CBD5E1"),
            ),
            range=[46.0, 51.5],
            ticksuffix="%",
            gridcolor="#282D37",
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(size=11.5, color="#CBD5E1"),
            gridcolor="#282D37",
            showline=True,
            linecolor="#282D37",
        ),
        showlegend=False,
    )

    return fig


def render_sensitivity_analysis_section(
    polls: Sequence[PesquisaEleitoralSchema] | None = None,
    candidate_a: str = "Lula",
    candidate_b: str = "Flávio",
) -> None:
    """Renderiza a seção completa de Análise de Sensibilidade e Robustez na Aba 7.

    Args:
        polls: Lista opcional de pesquisas ativas.
        candidate_a: Nome do candidato A (padrão: 'Lula').
        candidate_b: Nome do candidato B (padrão: 'Flávio').

    Returns:
        None.

    Raises:
        None.
    """
    st.markdown(SENSITIVITY_CSS, unsafe_allow_html=True)

    report: SensitivityReport = get_sensitivity_report(
        polls=polls,
        candidate_a=candidate_a,
        candidate_b=candidate_b,
    )

    header_html = f"""
    <div class="sens-container">
        <div class="sens-badge">Teste de Robustez Metodológica</div>
        <div class="sens-main-title">13 Formas de Calcular a Previsão (Análise de Sensibilidade)</div>
        <div class="sens-subtitle">
            O <b>Caminho Principal (P)</b> é a regra adotada oficialmente pelo projeto.
            Abaixo testamos como a previsão se comporta sob outras 12 variações de ponderação,
            decaimento temporal, correção de viés e voto potencial.
        </div>
        <div class="sens-verdict-card">
            <b>Veredito Científico:</b> {report.resumo_veredito}
        </div>
        <div class="sens-metric-strip">
            <div class="sens-metric-item">
                <div class="sens-metric-label">Vencedor por Consenso</div>
                <div class="sens-metric-val" style="color: #38BDF8;">{report.favorito_consenso} ({report.concordancia_favorito_pct:.0f}% das variações)</div>
            </div>
            <div class="sens-metric-item">
                <div class="sens-metric-label">Faixa {candidate_a} (Válidos)</div>
                <div class="sens-metric-val">{report.min_p_validos_a:.1f}% a {report.max_p_validos_a:.1f}%</div>
            </div>
            <div class="sens-metric-item">
                <div class="sens-metric-label">Chances {candidate_a}</div>
                <div class="sens-metric-val">{report.min_prob_a:.1f}% a {report.max_prob_a:.1f}%</div>
            </div>
            <div class="sens-metric-item">
                <div class="sens-metric-label">Total de Variações</div>
                <div class="sens-metric-val">13 modelos auditados</div>
            </div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

    # 1. Gráfico Horizontal de Sensibilidade
    st.markdown("#### Comparativo Gráfico das 13 Variações")
    st.markdown(
        """
        <div style="font-size: 13px; color: #94A3B8; margin-bottom: 10px;">
            A linha vertical em <b>50%</b> marca a maioria necessária para vencer o 2º turno.
            A estrela dourada destaca a variante <b>Principal (P)</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    fig = create_sensitivity_forest_plot(
        variants=report.variantes,
        candidate_a=candidate_a,
        candidate_b=candidate_b,
    )
    st.plotly_chart(fig, width="stretch")

    # 2. Tabela Tabular Completa
    st.markdown("#### Tabela Detalhada com as 13 Regras de Ponderação")

    table_rows = []
    for v in report.variantes:
        table_rows.append(
            {
                "Código": v.codigo,
                "Variante": v.variante,
                f"{candidate_a} válidos": f"{v.p_validos_a * 100.0:.1f}%",
                "Diferença": f"{v.margem * 100.0:+.1f} p.p.",
                f"Chance {candidate_a}": f"{v.prob_a * 100.0:.1f}%",
                "Favorito": v.favorito,
                "Regra Metodológica": v.regra,
            }
        )

    df_sens = pl.DataFrame(table_rows)
    st.dataframe(
        df_sens,
        width="stretch",
        hide_index=True,
        column_config={
            "Código": st.column_config.TextColumn("Código", width="small"),
            "Variante": st.column_config.TextColumn("Variante", width="medium"),
            f"{candidate_a} válidos": st.column_config.TextColumn(
                f"{candidate_a} válidos", width="small"
            ),
            "Diferença": st.column_config.TextColumn("Diferença", width="small"),
            f"Chance {candidate_a}": st.column_config.TextColumn(
                f"Chance {candidate_a}", width="small"
            ),
            "Favorito": st.column_config.TextColumn("Favorito", width="small"),
            "Regra Metodológica": st.column_config.TextColumn("Regra Metodológica", width="large"),
        },
    )

    # 3. Memorial Metodológico Didático
    with st.expander("🔬 Entenda os 5 Eixos da Análise de Sensibilidade"):
        st.markdown(
            r"""
            A **Curva de Especificação (*Specification Curve Analysis*)** testa sistematicamente se o resultado
            da eleição decorre de uma escolha subjetiva de parâmetros ou se expressa um padrão robusto nos dados:

            1. **Ponderação Amostral e Temporal (`S1`, `S2`, `S3`, `S4`, `S5`):**
               - *`S1` (Peso igual):* Avalia se a disparidade de $n$ entre institutos está puxando a média.
               - *`S2` (Sem meia-vida):* Compara a média com a hipótese de que o tempo não altera a intenção de voto.
               - *`S3` (Teto amostral em 3.000):* Evita que amostras muito grandes dominem o peso da amostra sem ganhos proporcionais de precisão.
               - *`S4` (Só a última pesquisa por instituto):* Neutraliza o viés de saturação (*flooding*) de institutos que publicam várias ondas na semana.
               - *`S5` ($n$ pela margem de erro):* Garante consistência paramétrica via fórmula clássica $n \approx 1,96^2 \cdot 0,25 / \text{ME}^2$.

            2. **Ancoragem no 1º Turno (`S6`):**
               - *`S6` (Sem âncora):* Mostra que, na reta final da eleição (onde o peso temporal da âncora de 04/10 cai para $<0,2\%$),
                 o modelo com âncora (`P`) e sem âncora (`S6`) convergem exatamente para a mesma estimativa ($48,1\%$).

            3. **Calibração de Viés de 1º Turno (`S0`, `S7`, `S9`):**
               - *`S0` (Sem ajuste):* Mostra a média bruta sem compensar erros medidos na urna ($49,0\%$).
               - *`S7` (Ajuste 100% integral):* Desconta todo o erro de 1º turno sem encolhimento ($47,1\%$).
               - *`S9` (Viés por modo):* Corrige pelo erro agregado de cada metodologia (presencial, telefone ou online) em vez de cada instituto.

            4. **Voto Potencial e Teto de Rejeição (`S10`, `S11`):**
               - *`S10` (Sem rejeição):* Mede apenas a intenção de voto explícita ($47,9\%$).
               - *`S11` (Só voto potencial $100 - \text{rejeição}$):* Mede a inclinação estrutural do eleitorado ($48,2\%$).
               - O modelo Principal (`P`) equilibra 50% intenção e 50% potencial ($48,1\%$).

            5. **Sinais Digitais Exógenos (`S8`):**
               - *`S8` (Sinal de redes):* Desloca a previsão pela variação de buscas e YouTube. Por não ter atingido a meta
                 mínima de redução de erro no teste retroativo fora da amostra, permanece exclusivamente nesta análise de sensibilidade,
                 sem interferir na estimativa oficial (`P`).
            """
        )
