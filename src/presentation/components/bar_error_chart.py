"""Componente Plotly para o gráfico de barras horizontais de erro ponderado de cada pesquisa.

Inspirado na referência visual analítica, divide as pesquisas por faixas de acerto
('Abaixo do Típico' e 'Erro Típico') com barras segmentadas para erro no 1º lugar,
2º lugar e demais disputas, indicando datas de campo e badges de erro.
"""

from typing import Any, Sequence

import plotly.graph_objects as go


def create_weighted_error_bar_chart(
    evaluations: Sequence[dict[str, Any]],
    faixa_acaso_p90: float | None = None,
) -> go.Figure:
    """Cria o gráfico de barras horizontais segmentadas por faixa de erro.

    Exibe as pesquisas divididas por faixas de acerto com segmentação por colocações,
    badges com o Erro Ponderado total (EP) e linha de referência estocástica da Faixa do Acaso (P90).

    Args:
        evaluations: Lista de dicionários contendo:
            - 'instituto': Nome fantasia do instituto.
            - 'campo_ate': Data ou string de término do campo (ex: '02/10').
            - 'erro_1_lugar': Erro no primeiro colocado.
            - 'erro_2_lugar': Erro no segundo colocado.
            - 'erro_demais': Erro nas outras colocações.
            - 'erro_total_ponderado': Erro total combinado (EP).
            - 'faixa_acerto': 'Abaixo do Típico', 'Erro Típico' ou 'Acima do Típico'.
            - 'disputa_decisiva' (opcional): Componente D.
            - 'eleitorado_fora_lugar' (opcional): Componente F.
            - 'penalidade_lado_errado' (opcional): Componente X.
        faixa_acaso_p90: Limite estocástico da Faixa do Acaso derivado via Monte Carlo (P90).

    Returns:
        go.Figure: Figura interativa Plotly configurada no estilo dark mode refinado.

    Raises:
        None.
    """
    fig = go.Figure()

    # Separa por categorias conforme referência visual
    abaixo_tipico = [e for e in evaluations if e["faixa_acerto"] == "Abaixo do Típico"]
    tipico = [e for e in evaluations if e["faixa_acerto"] != "Abaixo do Típico"]

    # Ordena para exibição no gráfico
    abaixo_tipico = sorted(abaixo_tipico, key=lambda x: x["erro_total_ponderado"])
    tipico = sorted(tipico, key=lambda x: x["erro_total_ponderado"])

    ordered_evals = abaixo_tipico + tipico
    y_labels = [f"{e['instituto']}  ({e['campo_ate']})" for e in ordered_evals]

    erro_1 = [e["erro_1_lugar"] for e in ordered_evals]
    erro_2 = [e["erro_2_lugar"] for e in ordered_evals]
    erro_demais = [e["erro_demais"] for e in ordered_evals]
    totais = [e["erro_total_ponderado"] for e in ordered_evals]

    custom_data = [
        [
            e.get("disputa_decisiva", 0.0),
            e.get("eleitorado_fora_lugar", 0.0),
            e.get("penalidade_lado_errado", 0.0),
            e["erro_total_ponderado"],
        ]
        for e in ordered_evals
    ]

    # Barra 1: Erro no 1º lugar (Azul escuro sólido)
    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=erro_1,
            name="Erro 1º lugar (disputa principal)",
            orientation="h",
            marker=dict(color="#4A90E2", line=dict(color="#2B5B84", width=1)),
            customdata=custom_data,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Erro 1º lugar: %{x:.2f} p.p.<br>"
                "Disputa Decisiva (D): %{customdata[0]:.2f} p.p.<br>"
                "Eleitorado Fora Lugar (F): %{customdata[1]:.2f} p.p.<br>"
                "Lado Errado (X): %{customdata[2]:.2f} p.p.<br>"
                "<b>EP Total: %{customdata[3]:.2f} p.p.</b><extra></extra>"
            ),
        )
    )

    # Barra 2: Erro no 2º lugar (Azul claro / ciano)
    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=erro_2,
            name="Erro 2º lugar",
            orientation="h",
            marker=dict(color="#70B0E0", line=dict(color="#3D6B8C", width=1)),
            hovertemplate="Erro 2º lugar: %{x:.2f} p.p.<extra></extra>",
        )
    )

    # Barra 3: Erro nas demais disputas (Laranja terracota)
    fig.add_trace(
        go.Bar(
            y=y_labels,
            x=erro_demais,
            name="Erro demais disputas",
            orientation="h",
            marker=dict(color="#E07A5F", line=dict(color="#96432D", width=1)),
            hovertemplate="Erro demais: %{x:.2f} p.p.<extra></extra>",
        )
    )

    # Adiciona anotações numéricas na ponta das barras (Badges)
    annotations = []
    for idx, (label, total) in enumerate(zip(y_labels, totais)):
        annotations.append(
            dict(
                x=erro_1[idx] + erro_2[idx] + erro_demais[idx] + 0.35,
                y=label,
                text=f"<b>{total:.1f}</b>",
                showarrow=False,
                font=dict(color="#F0F4F8", size=11, family="Inter, Segoe UI, sans-serif"),
                xanchor="left",
                yanchor="middle",
            )
        )

    # Linha divisória entre 'Abaixo do Típico' e 'Erro Típico'
    if abaixo_tipico and tipico:
        split_y = len(abaixo_tipico) - 0.5
        fig.add_hline(
            y=split_y,
            line_dash="dot",
            line_color="#4E5564",
            line_width=1.5,
            annotation_text="▲ ERRO ABAIXO DO TÍPICO  |  ▼ ERRO TÍPICO",
            annotation_position="bottom right",
            annotation_font=dict(color="#B0B8C5", size=10),
        )

    # Linha vertical da Faixa do Acaso (P90)
    if faixa_acaso_p90 is not None and faixa_acaso_p90 > 0:
        fig.add_vline(
            x=faixa_acaso_p90,
            line_dash="dash",
            line_color="#F59E0B",
            line_width=2,
            annotation_text=f"Faixa do Acaso (P90): {faixa_acaso_p90:.1f} p.p.",
            annotation_position="top right",
            annotation_font=dict(color="#FBBF24", size=11),
        )

    max_x = max(totais + ([faixa_acaso_p90] if faixa_acaso_p90 else []), default=10)

    fig.update_layout(
        barmode="stack",
        annotations=annotations,
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=max(540, len(ordered_evals) * 34),
        margin=dict(l=180, r=60, t=40, b=90),
        xaxis=dict(
            title=dict(
                text="Escala de Erro Ponderado (pontos percentuais)",
                font=dict(color="#CBD5E1", size=12),
            ),
            gridcolor="#282D37",
            zerolinecolor="#3D4452",
            range=[0, max_x + 2.2],
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=11, color="#E2E8F0"),
            gridcolor="#22262E",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.22,
            xanchor="center",
            x=0.5,
            font=dict(size=11, color="#CBD5E1"),
        ),
    )

    return fig
