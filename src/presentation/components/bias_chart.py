"""Componente Plotly para o gráfico de barras divergentes de viés direcional (Bias Chart).

Permite diagnosticar se os erros dos institutos foram distribuídos estocasticamente
ao redor de zero ou se apresentaram polarização direcional sistemática.
"""

from typing import Any, Sequence

import plotly.graph_objects as go


def create_directional_bias_chart(
    evaluations: Sequence[dict[str, Any]],
    candidate_name: str = "Lula",
) -> go.Figure:
    """Gera gráfico de barras divergentes centrado em zero para os erros residuais.

    Args:
        evaluations: Lista de levantamentos com:
            - 'instituto': Nome do instituto
            - 'campo_ate': Data do campo
            - 'desvio': Resíduo (p_hat - P_true) em pontos percentuais
        candidate_name: Nome do candidato referência.

    Returns:
        go.Figure: Gráfico divergente configurado no Plotly.

    Raises:
        None.
    """
    sorted_evals = sorted(evaluations, key=lambda x: x["desvio"])

    y_labels = [f"{e['instituto']} ({e['campo_ate']})" for e in sorted_evals]
    desvios = [e["desvio"] for e in sorted_evals]

    colors = ["#3B82F6" if d >= 0 else "#EF4444" for d in desvios]

    fig = go.Figure()

    text_labels = [f" {d:+.2f} p.p." if d >= 0 else f"{d:+.2f} p.p. " for d in desvios]

    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=desvios,
            text=text_labels,
            textposition="outside",
            textfont=dict(color="#F1F5F9", size=10, family="Inter, sans-serif"),
            orientation="h",
            marker=dict(color=colors, line=dict(color="#1F2937", width=1)),
            hovertemplate=(
                "<b>%{y}</b><br>" + f"Desvio ({candidate_name}): %{{x:+.2f}} p.p.<extra></extra>"
            ),
        )
    )

    fig.add_vline(
        x=0.0,
        line_color="#E2E8F0",
        line_width=1.5,
        line_dash="solid",
    )

    max_abs = max([abs(d) for d in desvios], default=4.0)
    fig.update_layout(
        title=dict(
            text=f"Viés Direcional por Instituto ({candidate_name}: Sobrestimação [+] vs. Subestimação [-])",
            font=dict(size=14, color="#F8FAFC"),
        ),
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=max(480, len(sorted_evals) * 30),
        margin=dict(l=180, r=60, t=55, b=50),
        xaxis=dict(
            title="Divergência frente à Urna (pontos percentuais)",
            gridcolor="#282D37",
            zerolinecolor="#E2E8F0",
            range=[-max_abs - 1.5, max_abs + 1.5],
        ),
        yaxis=dict(
            tickfont=dict(size=11, color="#E2E8F0"),
            gridcolor="#22262E",
        ),
        showlegend=False,
    )

    return fig
