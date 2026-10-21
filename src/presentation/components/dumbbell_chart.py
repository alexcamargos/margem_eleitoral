"""Componente Plotly para Gráfico de Halteres (Dumbbell / Cleveland Dot Plot) de Rejeição.

Renderiza a comparação visual das taxas de rejeição entre os dois concorrentes principais
por instituto, conectando os pontos por segmento horizontal e rotulando o veredito lateral.
"""

import math
from typing import Any, Sequence

import plotly.graph_objects as go


def create_rejection_dumbbell_chart(
    polls: Sequence[dict[str, Any]],
    candidate_1: str = "Lula",
    candidate_2: str = "Flávio Bolsonaro",
    display_names: dict[str, str] | None = None,
    candidate_colors: dict[str, str] | None = None,
    chart_title: str | None = None,
    include_dates_in_label: bool = False,
) -> go.Figure:
    """Gera o Dumbbell Plot interativo para comparação de taxas de rejeição por instituto.

    Args:
        polls: Sequência de dicionários com os levantamentos avaliados, contendo:
            - 'instituto': Nome do instituto
            - 'campo_inicio': Opcional, data inicial de campo
            - 'campo_fim': Opcional, data final de campo
            - 'onda_anterior': Booleano indicando se é da onda anterior
            - 'rejeicao': Dicionário com percentuais de rejeição por candidato
            - 'veredito': String do veredito ('Lula menos', 'Flávio menos', 'empate')
        candidate_1: Nome chave do primeiro candidato.
        candidate_2: Nome chave do segundo candidato.
        display_names: Dicionário de nomes de exibição (ex.: {'Flávio Bolsonaro': 'Flávio'}).
        candidate_colors: Dicionário de cores hexadecimais por candidato.
        chart_title: Título customizado opcional no topo do gráfico.
        include_dates_in_label: Se True, anexa as datas de campo ao rótulo do instituto.

    Returns:
        go.Figure: Figura interativa Plotly no padrão dark mode.

    Raises:
        ValueError: Se a lista de pesquisas estiver vazia.
    """
    if not polls:
        raise ValueError("A lista de pesquisas para o gráfico de halteres não pode estar vazia.")

    d_names = display_names or {candidate_1: candidate_1, candidate_2: candidate_2}
    c1_disp = d_names.get(candidate_1, candidate_1)
    c2_disp = d_names.get(candidate_2, candidate_2)

    colors = candidate_colors or {candidate_1: "#EF4444", candidate_2: "#3B82F6"}
    c1_color = colors.get(candidate_1, "#EF4444")
    c2_color = colors.get(candidate_2, "#3B82F6")

    # Prepara listas ordenadas preservando a ordem do topo à base
    institutos_labels: list[str] = []
    c1_vals: list[float] = []
    c2_vals: list[float] = []
    vereditos: list[str] = []

    for poll in polls:
        inst = str(poll.get("instituto", ""))
        c_ini = poll.get("campo_inicio")
        c_fim = poll.get("campo_fim")
        if include_dates_in_label and c_ini and c_fim:
            inst = f"{inst} ({c_ini} a {c_fim})"

        if poll.get("onda_anterior"):
            inst = f"{inst}*"

        institutos_labels.append(inst)
        rej = poll.get("rejeicao", {})
        val1 = float(rej.get(candidate_1, 0.0))
        val2 = float(rej.get(candidate_2, 0.0))
        c1_vals.append(val1)
        c2_vals.append(val2)
        vereditos.append(str(poll.get("veredito", "empate")))

    # Determinação dinâmica dos limites do eixo X para acomodar variações como 30% a 65%
    all_vals = c1_vals + c2_vals
    min_v = min(all_vals) if all_vals else 40.0
    max_v = max(all_vals) if all_vals else 60.0
    x_min = min(30.0, math.floor(min_v / 5.0) * 5.0 - 2.0)
    x_max = max(68.0, math.ceil(max_v / 5.0) * 5.0 + 8.0)
    annot_x = x_max - 6.0

    # Ticks em intervalos regulares de 5%
    tick_start = int(math.ceil(x_min / 5.0) * 5)
    tick_end = int(math.floor((x_max - 7.0) / 5.0) * 5)
    tickvals = list(range(tick_start, tick_end + 1, 5))

    fig = go.Figure()

    # 1. Traço de linhas horizontais cinzas conectando os pontos (Dumbbell segments)
    line_x: list[float | None] = []
    line_y: list[str | None] = []
    for inst, val1, val2 in zip(institutos_labels, c1_vals, c2_vals):
        line_x.extend([val1, val2, None])
        line_y.extend([inst, inst, None])

    fig.add_trace(
        go.Scatter(
            x=line_x,
            y=line_y,
            mode="lines",
            line=dict(color="#475569", width=2.2),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # 2. Marcadores do Candidato 1
    fig.add_trace(
        go.Scatter(
            x=c1_vals,
            y=institutos_labels,
            mode="markers",
            name=c1_disp,
            marker=dict(
                color=c1_color,
                size=11,
                line=dict(color="#181B20", width=1.5),
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                + f"Rejeição ({c1_disp}): %{{x:.1f}}%<br>"
                + "<extra></extra>"
            ),
        )
    )

    # 3. Marcadores do Candidato 2
    fig.add_trace(
        go.Scatter(
            x=c2_vals,
            y=institutos_labels,
            mode="markers",
            name=c2_disp,
            marker=dict(
                color=c2_color,
                size=11,
                line=dict(color="#181B20", width=1.5),
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                + f"Rejeição ({c2_disp}): %{{x:.1f}}%<br>"
                + "<extra></extra>"
            ),
        )
    )

    # 4. Anotações laterais à direita do gráfico indicando o veredito por instituto
    annotations: list[dict[str, Any]] = []
    for inst, veredito in zip(institutos_labels, vereditos):
        if "empate" in veredito.lower():
            txt_color = "#94A3B8"
        elif c1_disp.lower() in veredito.lower() or candidate_1.lower() in veredito.lower():
            txt_color = c1_color
        else:
            txt_color = c2_color

        annotations.append(
            dict(
                xref="x",
                yref="y",
                x=annot_x,
                y=inst,
                text=f"<b>{veredito}</b>",
                showarrow=False,
                xanchor="left",
                yanchor="middle",
                font=dict(size=10.5, color=txt_color, family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto"),
            )
        )

    title_text = chart_title or "% que não votaria de jeito nenhum — quanto mais à esquerda, menos rejeitado"
    left_margin = 210 if include_dates_in_label else 140

    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=12.5, color="#94A3B8"),
            x=0.0,
            xanchor="left",
        ),
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=max(450, len(institutos_labels) * 35),
        margin=dict(l=left_margin, r=130, t=50, b=45),
        xaxis=dict(
            range=[x_min, x_max],
            tickvals=tickvals,
            ticksuffix="%",
            gridcolor="#282D37",
            zeroline=False,
            tickfont=dict(size=11, color="#94A3B8"),
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=11.5, color="#E2E8F0"),
            gridcolor="#22262E",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=12, color="#E2E8F0"),
        ),
        annotations=annotations,
    )

    return fig

