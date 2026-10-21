"""Componente Plotly para a narrativa visual comparativa das 3 fases eleitorais.

Gera visualização com subplots combinados:
1. Trajetória latente de intenção de voto dos candidatos com envelopes de credibilidade de 95%.
2. Volume amostral de pesquisas publicadas em cada fase e taxa diária de produção de levantamentos.
"""

from typing import Sequence

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.analytics.aggregator_model import PhaseAggregationSummary


def create_phases_comparison_chart(
    summaries: Sequence[PhaseAggregationSummary],
    candidates: Sequence[str] = ("Lula", "Flávio Bolsonaro"),
    candidate_colors: dict[str, str] | None = None,
) -> go.Figure:
    """Gera o gráfico integrado comparativo das 3 fases do processo eleitoral.

    Args:
        summaries: Sequência de 3 sumários analíticos (PhaseAggregationSummary).
        candidates: Nomes dos candidatos a incluir no painel comparativo.
        candidate_colors: Mapeamento de cores hexadecimais por candidato (opcional).

    Returns:
        go.Figure: Figura interativa Plotly configurada no tema dark mode com 2 subplots.

    Raises:
        ValueError: Se a lista de sumários estiver vazia.
    """
    if not summaries:
        raise ValueError("A lista de sumários de fases não pode estar vazia.")

    colors_map = candidate_colors or {
        "Lula": "#EF4444",
        "Flávio Bolsonaro": "#1D4ED8",
        "Bolsonaro": "#3B82F6",
        "Augusto Cury": "#8B5CF6",
        "Romeu Zema": "#F97316",
        "Renan Santos": "#0EA5E9",
        "Simone Tebet": "#10B981",
        "Ciro Gomes": "#F59E0B",
    }

    # Categorias do eixo X compartilhadas
    fases_x = [s.rotulo_curto for s in summaries]

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.14,
        row_heights=[0.62, 0.38],
        subplot_titles=(
            "Estimativa Agregada por Fase (com Fitas de Credibilidade de 95%)",
            "Volume de Pesquisas e Ritmo Amostral por Fase",
        ),
    )

    # 1. Subplot Superior: Trajetórias dos Candidatos
    for cand in candidates:
        color = colors_map.get(cand, "#94A3B8")
        y_vals: list[float | None] = []
        err_plus: list[float] = []
        err_minus: list[float] = []
        custom_data_cand: list[list[str]] = []

        for s in summaries:
            est = s.estimativas.get(cand)
            if est and est.media_ponderada > 0:
                val = est.media_ponderada
                y_vals.append(val)
                err_plus.append(max(0.0, est.ic_95_sup - val))
                err_minus.append(max(0.0, val - est.ic_95_inf))
                delta_str = (
                    f"{est.delta_anterior:+.2f} pp" if est.delta_anterior is not None else "Marco 0"
                )
                custom_data_cand.append(
                    [
                        f"{est.ic_95_inf:.1f}%",
                        f"{est.ic_95_sup:.1f}%",
                        delta_str,
                        f"{est.media_periodo:.1f}%",
                    ]
                )
            else:
                y_vals.append(None)
                err_plus.append(0.0)
                err_minus.append(0.0)
                custom_data_cand.append(["-", "-", "-", "-"])

        # Linha e pontos com barras de erro
        fig.add_trace(
            go.Scatter(
                x=fases_x,
                y=y_vals,
                mode="lines+markers",
                name=cand,
                line=dict(color=color, width=3),
                marker=dict(
                    size=10,
                    color=color,
                    line=dict(color="#FFFFFF", width=1.2),
                ),
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=err_plus,
                    arrayminus=err_minus,
                    color=color,
                    thickness=1.5,
                    width=6,
                ),
                customdata=custom_data_cand,
                hovertemplate=(
                    f"<b>{cand}</b><br>"
                    "Fase: %{x}<br>"
                    "Estimativa Agregada: <b>%{y:.1f}%</b><br>"
                    "Intervalo 95%: [%{customdata[0]} a %{customdata[1]}]<br>"
                    "Média do Período: %{customdata[3]}<br>"
                    "Variação vs. Fase Anterior: <b>%{customdata[2]}</b>"
                    "<extra></extra>"
                ),
            ),
            row=1,
            col=1,
        )

    # 2. Subplot Inferior: Volume e Ritmo de Pesquisas por Fase
    bar_y = [s.total_pesquisas for s in summaries]
    bar_texts = [
        f"<b>{s.total_pesquisas} pesq.</b><br>({s.pesquisas_por_dia:.1f}/dia)"
        if s.total_pesquisas > 0
        else "<b>0 pesq.</b>"
        for s in summaries
    ]
    bar_custom = [
        [
            s.descricao_periodo,
            s.percentual_total_pesquisas,
            s.pesquisas_por_dia,
            s.dias_duracao,
        ]
        for s in summaries
    ]

    fig.add_trace(
        go.Bar(
            x=fases_x,
            y=bar_y,
            name="Pesquisas",
            marker=dict(
                color="rgba(56, 189, 248, 0.70)",
                line=dict(color="#38BDF8", width=1.5),
            ),
            text=bar_texts,
            textposition="auto",
            textfont=dict(size=11, color="#F8FAFC"),
            customdata=bar_custom,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Período: %{customdata[0]} (%{customdata[3]} dias)<br>"
                "Total de Pesquisas: <b>%{y} levantamentos</b> (%{customdata[1]:.1f}% da base)<br>"
                "Densidade Amostral: <b>%{customdata[2]:.2f} pesquisas/dia</b>"
                "<extra></extra>"
            ),
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=480,
        margin=dict(l=55, r=35, t=55, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=11, color="#CBD5E1"),
        ),
    )

    # Configuração dos eixos
    fig.update_yaxes(
        title_text="Intenção (%)",
        gridcolor="#282D37",
        zerolinecolor="#3D4452",
        row=1,
        col=1,
    )
    fig.update_yaxes(
        title_text="Nº Pesquisas",
        gridcolor="#282D37",
        zerolinecolor="#3D4452",
        row=2,
        col=1,
    )
    fig.update_xaxes(
        gridcolor="#282D37",
        zerolinecolor="#3D4452",
        row=1,
        col=1,
    )
    fig.update_xaxes(
        gridcolor="#282D37",
        zerolinecolor="#3D4452",
        row=2,
        col=1,
    )

    return fig
