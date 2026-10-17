"""Componentes gráficos Plotly para o Modelo Preditivo e Previsão Eleitoral (Ato 6).

Fornece visualizações interativas em dark mode para:
1. Distribuição estocástica de Monte Carlo dos votos válidos simulados e linha de maioria (50%).
2. Curva de convergência do Backtesting Point-in-Time (Modelo Calibrado vs. Média Simples).
3. Decomposição regional pós-estratificada pelo Colégio Eleitoral do TSE (5 macrorregiões).
"""

from typing import Sequence

import plotly.graph_objects as go
import polars as pl
from plotly.subplots import make_subplots

from src.analytics.predictive_model import ElectionForecastResult, RegionalForecastSlice

CANDIDATE_COLORS: dict[str, dict[str, str]] = {
    "Lula": {"line": "#EF4444", "fill": "rgba(239, 68, 68, 0.35)"},
    "Flávio Bolsonaro": {"line": "#3B82F6", "fill": "rgba(59, 130, 246, 0.35)"},
    "Bolsonaro": {"line": "#3B82F6", "fill": "rgba(59, 130, 246, 0.35)"},
    "Augusto Cury": {"line": "#8B5CF6", "fill": "rgba(139, 92, 246, 0.35)"},
    "Simone Tebet": {"line": "#10B981", "fill": "rgba(16, 185, 129, 0.35)"},
    "Ciro Gomes": {"line": "#F59E0B", "fill": "rgba(245, 158, 11, 0.35)"},
}


def create_win_probability_distribution_chart(
    forecast: ElectionForecastResult,
    official_result: dict[str, float] | None = None,
) -> go.Figure:
    """Cria o histograma de densidade da simulação de Monte Carlo para os candidatos líderes.

    Plota as distribuições posteriores simuladas (Student-t, nu=5) dos dois principais
    candidatos com legenda inferior limpa e sem sobreposição de rótulos verticais.

    Args:
        forecast: Objeto `ElectionForecastResult` retornado por `predict_election_outcome`.
        official_result: Dicionário opcional com o resultado nominal oficial do TSE.

    Returns:
        go.Figure: Figura Plotly interativa formatada em dark mode.

    Raises:
        None.
    """
    fig = go.Figure()
    top_cands = forecast.candidatos[:2]

    for cp in top_cands:
        cand = cp.candidato
        samples = forecast.distribuicao_simulada.get(cand, [])
        if not samples:
            continue

        c_style = CANDIDATE_COLORS.get(
            cand, {"line": "#38BDF8", "fill": "rgba(56, 189, 248, 0.35)"}
        )
        real_hover = ""
        if official_result and cand in official_result and float(official_result[cand]) > 0.0:
            real_hover = f"<br>Urna TSE: {float(official_result[cand]):.2f}%"

        fig.add_trace(
            go.Histogram(
                x=samples,
                histnorm="probability density",
                name=(
                    f"{cand} (Previsto: {cp.voto_esperado:.1f}% | "
                    f"Vitória: {cp.probabilidade_vitoria:.1f}%)"
                ),
                marker=dict(
                    color=c_style["fill"],
                    line=dict(color=c_style["line"], width=1.2),
                ),
                opacity=0.72,
                nbinsx=40,
                hovertemplate=(
                    f"<b>{cand}</b><br>"
                    "Cenário Simulado: %{x:.2f}%<br>"
                    f"Média Prevista: {cp.voto_esperado:.2f}%<br>"
                    f"Chances de Vitória: {cp.probabilidade_vitoria:.1f}%"
                    f"{real_hover}<br>"
                    "Densidade: %{y:.3f}<extra></extra>"
                ),
            )
        )

        # Linha vertical da média prevista de cada candidato (sem texto sobreposto)
        fig.add_vline(
            x=cp.voto_esperado,
            line_dash="solid",
            line_color=c_style["line"],
            line_width=2.2,
        )

    # Linha divisória de 50% (Maioria Absoluta) discreta e sem colisão com o título
    fig.add_vline(
        x=50.0,
        line_dash="dash",
        line_color="#94A3B8",
        line_width=1.4,
    )
    fig.add_annotation(
        x=50.0,
        y=1.02,
        xref="x",
        yref="paper",
        text="Maioria (50%)",
        showarrow=False,
        font=dict(color="#CBD5E1", size=11),
        xanchor="center",
        yanchor="bottom",
    )

    fig.update_layout(
        title=dict(
            text=(
                "Distribuição de 10.000 Cenários Simulados — "
                f"Corte em {forecast.cutoff_date.strftime('%d/%m/%Y')}"
            ),
            font=dict(size=14, color="#F8FAFC"),
            y=0.95,
            x=0.01,
            xanchor="left",
        ),
        barmode="overlay",
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=440,
        margin=dict(l=55, r=25, t=68, b=100),
        xaxis=dict(
            title=dict(
                text="Percentual de Votos Válidos (%)",
                font=dict(size=12, color="#CBD5E1"),
                standoff=10,
            ),
            gridcolor="#282D37",
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="Densidade de Cenários", font=dict(size=12, color="#CBD5E1")),
            gridcolor="#282D37",
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=11.5, color="#E2E8F0"),
        ),
    )
    return fig


def create_backtest_convergence_chart(backtest_df: pl.DataFrame) -> go.Figure:
    """Cria o gráfico comparativo de convergência Point-in-Time (Modelo vs. Média Simples).

    Exibe em dois eixos coordenados a redução do Erro Ponderado (EP) do Modelo Estado-Espaço
    Calibrado frente à média simples não calibrada ao longo dos horizontes (T-30d até T-1d),
    junto à evolução da probabilidade atribuída ao vencedor real da eleição.

    Args:
        backtest_df: Polars DataFrame retornado por `run_point_in_time_backtest`.

    Returns:
        go.Figure: Figura Plotly com duplo eixo Y em dark mode.

    Raises:
        None.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if backtest_df.height == 0:
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#181B20",
            plot_bgcolor="#181B20",
            height=380,
        )
        return fig

    df_sorted = backtest_df.sort("horizonte_dias", descending=True)
    labels_x = [
        f"{h} dias antes" if h > 1 else "Véspera (1d)"
        for h in df_sorted["horizonte_dias"].to_list()
    ]
    ep_mod = df_sorted["erro_ponderado_modelo"].to_list()
    ep_base = df_sorted["erro_ponderado_baseline"].to_list()
    prob_win = df_sorted["prob_vitoria_vencedor_real"].to_list()
    winner_name = df_sorted["vencedor_real"].to_list()[0]

    fig.add_trace(
        go.Bar(
            x=labels_x,
            y=ep_base,
            name="Erro da Média Simples (Sem Modelo)",
            marker=dict(color="rgba(148, 163, 184, 0.40)", line=dict(color="#94A3B8", width=1)),
            text=[f"{v:.2f}" for v in ep_base],
            textposition="auto",
            hovertemplate="Horizonte: %{x}<br>Erro Média Simples: %{y:.2f} pp<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Bar(
            x=labels_x,
            y=ep_mod,
            name="Erro do Modelo Preditivo Calibrado",
            marker=dict(color="rgba(56, 189, 248, 0.80)", line=dict(color="#38BDF8", width=1.2)),
            text=[f"{v:.2f}" for v in ep_mod],
            textposition="auto",
            hovertemplate="Horizonte: %{x}<br>Erro Modelo Calibrado: %{y:.2f} pp<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=labels_x,
            y=prob_win,
            mode="lines+markers+text",
            name=f"Chances de Vitória de {winner_name} (%)",
            line=dict(color="#10B981", width=3),
            marker=dict(size=8, color="#10B981", line=dict(color="#FFFFFF", width=1)),
            text=[f"{p:.1f}%" for p in prob_win],
            textposition="top center",
            textfont=dict(color="#34D399", size=11),
            hovertemplate=(
                f"Horizonte: %{{x}}<br>Chances de Vitória ({winner_name}): %{{y:.1f}}%<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title=dict(
            text="Evolução do Erro Ponderado e das Chances de Vitória ao Longo da Campanha",
            font=dict(size=14, color="#F8FAFC"),
            y=0.95,
            x=0.01,
            xanchor="left",
        ),
        barmode="group",
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=440,
        margin=dict(l=55, r=55, t=60, b=100),
        xaxis=dict(
            title=dict(
                text="Momento da Previsão (Dias Antes da Votação)",
                font=dict(size=12, color="#CBD5E1"),
                standoff=10,
            ),
            gridcolor="#282D37",
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=11.5, color="#E2E8F0"),
        ),
    )

    fig.update_yaxes(
        title_text="Erro Ponderado Total (menor = mais preciso)",
        gridcolor="#282D37",
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text=f"Chances de Vitória — {winner_name} (%)",
        range=[0, 115],
        showgrid=False,
        secondary_y=True,
    )
    return fig


def create_electoral_college_regional_chart(
    regional_slices: Sequence[RegionalForecastSlice],
    top_candidates: Sequence[str],
) -> go.Figure:
    """Cria o gráfico de barras agrupadas da projeção por macrorregião e Colégio Eleitoral TSE.

    Mostra como os levantamentos estaduais e regionais em cada macrorregião (SE, NE, S, N, CO)
    são ponderados pelo peso oficial do eleitorado do TSE para formar a síntese nacional.

    Args:
        regional_slices: Lista de objetos `RegionalForecastSlice` das 5 macrorregiões + 'BR'.
        top_candidates: Nomes dos candidatos principais a exibir.

    Returns:
        go.Figure: Figura Plotly interativa em dark mode.

    Raises:
        None.
    """
    fig = go.Figure()
    if not regional_slices or not top_candidates:
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#181B20",
            plot_bgcolor="#181B20",
            height=360,
        )
        return fig

    x_labels = [
        f"<b>{s.nome_regiao}</b><br>({s.peso_eleitorado * 100:.1f}% do TSE)"
        for s in regional_slices
    ]

    for cand in top_candidates[:2]:
        c_style = CANDIDATE_COLORS.get(
            cand, {"line": "#38BDF8", "fill": "rgba(56, 189, 248, 0.70)"}
        )
        y_vals = [float(s.votos_projetados.get(cand, 0.0)) for s in regional_slices]

        fig.add_trace(
            go.Bar(
                x=x_labels,
                y=y_vals,
                name=cand,
                marker=dict(color=c_style["line"], opacity=0.88),
                text=[f"{v:.1f}%" for v in y_vals],
                textposition="auto",
                hovertemplate=(
                    f"<b>{cand}</b><br>%{{x}}<br>Votos Válidos Projetados: %{{y:.2f}}%<extra></extra>"
                ),
            )
        )

    fig.add_hline(
        y=50.0,
        line_dash="dash",
        line_color="#94A3B8",
        line_width=1.2,
    )

    fig.update_layout(
        title=dict(
            text="Projeção por Macrorregião e Síntese Nacional (Colégio Eleitoral TSE)",
            font=dict(size=14, color="#F8FAFC"),
            y=0.95,
            x=0.01,
            xanchor="left",
        ),
        barmode="group",
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=430,
        margin=dict(l=55, r=25, t=60, b=95),
        xaxis=dict(gridcolor="#282D37", tickangle=0),
        yaxis=dict(
            title=dict(text="Votos Válidos Projetados (%)", font=dict(size=12, color="#CBD5E1")),
            range=[0, 78],
            gridcolor="#282D37",
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.22,
            xanchor="center",
            x=0.5,
            font=dict(size=12, color="#E2E8F0"),
        ),
    )
    return fig
