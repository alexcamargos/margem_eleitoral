"""Componente Plotly para a curva contínua do Agregador Dinâmico de Pesquisas.

Plota as trajetórias latentes dos candidatos ao longo da campanha com envelopes
sombreados de credibilidade estatística (80% e 95%) e pontos individuais dispersos.
"""

from typing import Sequence

import plotly.graph_objects as go
import polars as pl

from src.transformations.schemas import PesquisaEleitoralSchema


def create_trend_aggregator_chart(
    df_agg: pl.DataFrame,
    polls: Sequence[PesquisaEleitoralSchema],
    candidates: Sequence[str] = ("Lula", "Bolsonaro"),
) -> go.Figure:
    """Gera o gráfico longitudinal de tendência com bandas de incerteza.

    Args:
        df_agg: Polars DataFrame gerado por compute_poll_aggregation_series.
        polls: Lista das pesquisas eleitorais individuais para dispersão de pontos.
        candidates: Candidatos a plotar no gráfico.

    Returns:
        go.Figure: Gráfico Plotly configurado com fitas de incerteza.

    Raises:
        None.
    """
    fig = go.Figure()

    colors_cand = {
        "Lula": {"line": "#EF4444", "fill": "rgba(239, 68, 68, 0.15)"},
        "Flávio Bolsonaro": {"line": "#1D4ED8", "fill": "rgba(29, 78, 216, 0.15)"},
        "Bolsonaro": {"line": "#3B82F6", "fill": "rgba(59, 130, 246, 0.15)"},
        "Augusto Cury": {"line": "#8B5CF6", "fill": "rgba(139, 92, 246, 0.15)"},
        "Romeu Zema": {"line": "#F97316", "fill": "rgba(249, 115, 22, 0.15)"},
        "Renan Santos": {"line": "#0EA5E9", "fill": "rgba(14, 165, 233, 0.15)"},
        "Simone Tebet": {"line": "#10B981", "fill": "rgba(16, 185, 129, 0.15)"},
        "Ciro Gomes": {"line": "#F59E0B", "fill": "rgba(245, 158, 11, 0.15)"},
    }

    # Ordena candidatos para que o líder apareça primeiro na legenda
    order_map = {
        "Lula": 0,
        "Flávio Bolsonaro": 1,
        "Bolsonaro": 1,
        "Augusto Cury": 2,
        "Romeu Zema": 3,
        "Renan Santos": 4,
        "Simone Tebet": 5,
        "Ciro Gomes": 6,
    }
    ordered_cands = sorted(candidates, key=lambda c: order_map.get(c, 99))

    # 1. Plota pontos individuais de pesquisas (dispersão com tamanho proporcional a sqrt(n))
    for cand in ordered_cands:
        pts_x = [p.data_fim_campo for p in polls if cand in p.votos_validos]
        pts_y = [p.votos_validos[cand] for p in polls if cand in p.votos_validos]
        sizes = [
            max(4, min(12, (p.tamanho_amostra / 300.0) ** 0.5 * 3))
            for p in polls
            if cand in p.votos_validos
        ]
        insts = [
            f"{p.instituto_nome_fantasia} ({p.metodologia.value})"
            for p in polls
            if cand in p.votos_validos
        ]

        c_info = colors_cand.get(cand, {"line": "#94A3B8", "fill": "rgba(148, 163, 184, 0.12)"})

        fig.add_trace(
            go.Scatter(
                x=pts_x,
                y=pts_y,
                mode="markers",
                name=f"Pesquisas ({cand})",
                marker=dict(
                    color=c_info["line"],
                    opacity=0.35,
                    size=sizes,
                    line=dict(color="#FFFFFF", width=0.5),
                ),
                text=insts,
                hovertemplate="<b>%{text}</b><br>Data: %{x}<br>Estimativa: %{y:.1f}%<extra></extra>",
                showlegend=False,
            )
        )

    # 2. Plota curvas suavizadas e envelopes de 95%
    for cand in ordered_cands:
        sub = df_agg.filter(pl.col("candidato") == cand).sort("data")
        if sub.height == 0:
            continue

        dates = sub["data"].to_list()
        y_mean = sub["media_ponderada"].to_list()
        y_sup = sub["ic_95_sup"].to_list()
        y_inf = sub["ic_95_inf"].to_list()

        c_info = colors_cand.get(cand, {"line": "#94A3B8", "fill": "rgba(148, 163, 184, 0.12)"})

        # Fita superior (invisível) e fita inferior preenchida
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=y_sup,
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=y_inf,
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor=c_info["fill"],
                showlegend=False,
                hoverinfo="skip",
            )
        )

        # Linha contínua da média agregada
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=y_mean,
                mode="lines",
                name=f"Agregador: {cand}",
                line=dict(color=c_info["line"], width=3),
                hovertemplate=f"<b>{cand} (Agregado)</b><br>Data: %{{x}}<br>Estimativa: %{{y:.2f}}%<extra></extra>",
            )
        )

    # 3. Adiciona marcos de campanha conforme AGENTS.md
    if polls:
        min_date = min(p.data_fim_campo for p in polls)
        max_date = max(p.data_fim_campo for p in polls)

        ano = polls[0].ano if (hasattr(polls[0], "ano") and polls[0].ano) else min_date.year
        milestones = [
            (f"{ano}-08-16", "Início Propaganda"),
            (f"{ano}-08-26" if ano == 2022 else f"{ano}-08-28", "Horário Eleitoral"),
            (f"{ano}-09-29", "Debate na TV"),
            (f"{ano}-09-30" if ano == 2022 else f"{ano}-10-02", "Reta Final"),
        ]
        for m_str, m_label in milestones:
            from datetime import date as dt_date

            try:
                m_dt = dt_date.fromisoformat(m_str)
                if min_date <= m_dt <= max_date:
                    fig.add_vline(
                        x=m_str,
                        line_dash="dot",
                        line_color="#475569",
                        line_width=1.2,
                        annotation_text=m_label,
                        annotation_position="top left",
                        annotation_font=dict(size=9, color="#94A3B8"),
                    )
            except ValueError:
                pass

    fig.update_layout(
        title=dict(
            text="Agregador Dinâmico de Pesquisas (Trajetória Latente com Fitas de 95%)",
            font=dict(size=14, color="#F8FAFC"),
        ),
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=500,
        margin=dict(l=55, r=40, t=65, b=55),
        xaxis=dict(
            gridcolor="#282D37",
            zerolinecolor="#3D4452",
            tickformat="%d/%m",
        ),
        yaxis=dict(
            title="Intenção de Votos (%)",
            gridcolor="#282D37",
            zerolinecolor="#3D4452",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=11, color="#CBD5E1"),
        ),
    )

    return fig
