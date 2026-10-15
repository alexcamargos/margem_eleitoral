"""Componente Plotly para Forest Plot das pesquisas de véspera vs. apuração oficial.

Exibe as estimativas pontuais e os intervalos de confiança de 95% corrigidos por deff
frente à linha vertical de referência da apuração oficial do TSE.
"""

from typing import Any, Sequence

import plotly.graph_objects as go


def create_forest_plot(
    eve_evaluations: Sequence[dict[str, Any]],
    candidate_name: str,
    official_vote_percent: float,
) -> go.Figure:
    """Gera o Forest Plot interativo para o candidato avaliado.

    Args:
        eve_evaluations: Lista de levantamentos de véspera com:
            - 'instituto': Nome do instituto
            - 'campo_ate': Data ou string de fim de campo
            - 'estimativa': Ponto percentual estimado de votos válidos
            - 'ic_inf': Limite inferior do IC95%
            - 'ic_sup': Limite superior do IC95%
            - 'margem_erro': Margem de erro em p.p.
        candidate_name: Nome do candidato (ex.: 'Lula' ou 'Bolsonaro').
        official_vote_percent: Percentual oficial apurado pelo TSE.

    Returns:
        go.Figure: Figura interativa Plotly no padrão dark mode.

    Raises:
        None.
    """
    fig = go.Figure()

    # Ordena pesquisas cronologicamente pela data de campo mais recente (véspera imediata no topo)
    sorted_evals = sorted(
        eve_evaluations,
        key=lambda x: (x.get("data_fim") or x["campo_ate"], x["instituto"]),
        reverse=True,
    )

    y_labels = [f"{e['instituto']} ({e['campo_ate']})" for e in sorted_evals]
    estimativas = [e["estimativa"] for e in sorted_evals]
    ic_inf = [e["ic_inf"] for e in sorted_evals]
    ic_sup = [e["ic_sup"] for e in sorted_evals]
    erros_plus = [sup - est for est, sup in zip(estimativas, ic_sup)]
    erros_minus = [est - inf for est, inf in zip(estimativas, ic_inf)]

    # Determina cores: verde se cobriu a urna, vermelho se não cobriu
    covered_flags = [inf <= official_vote_percent <= sup for inf, sup in zip(ic_inf, ic_sup)]
    point_colors = ["#10B981" if cov else "#EF4444" for cov in covered_flags]

    # Barras de erro horizontais e estimativas pontuais
    fig.add_trace(
        go.Scatter(
            x=estimativas,
            y=y_labels,
            mode="markers",
            name="Estimativa Pontual ± IC95%",
            marker=dict(
                color=point_colors,
                size=9,
                line=dict(color="#FFFFFF", width=1),
            ),
            error_x=dict(
                type="data",
                symmetric=False,
                array=erros_plus,
                arrayminus=erros_minus,
                color="#64748B",
                thickness=1.8,
                width=6,
            ),
            customdata=list(zip(ic_inf, ic_sup, covered_flags)),
            hovertemplate=(
                "<b>%{y}</b><br>"
                + f"Estimativa ({candidate_name}): %{{x:.2f}}%<br>"
                + "IC 95%: [%{customdata[0]:.2f}%, %{customdata[1]:.2f}%]<br>"
                + "Cobriu a Urna: %{customdata[2]}<extra></extra>"
            ),
        )
    )

    # Linha vertical vermelha contrastante do resultado oficial do TSE
    fig.add_vline(
        x=official_vote_percent,
        line_color="#F43F5E",
        line_width=2.5,
        line_dash="solid",
        annotation_text=f"Urna TSE: {official_vote_percent:.2f}%",
        annotation_position="top right",
        annotation_font=dict(color="#FDA4AF", size=11, family="Inter, sans-serif"),
    )

    fig.update_layout(
        title=dict(
            text=f"Forest Plot: Pesquisas de Véspera vs. Urna Oficial — {candidate_name}",
            font=dict(size=14, color="#F8FAFC"),
        ),
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=max(500, len(sorted_evals) * 32),
        margin=dict(l=190, r=40, t=65, b=55),
        xaxis=dict(
            title="Percentual de Votos Válidos (%)",
            gridcolor="#282D37",
            zerolinecolor="#3D4452",
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=11, color="#E2E8F0"),
            gridcolor="#22262E",
        ),
        showlegend=False,
    )

    return fig
