"""Componente Plotly para a trajetória longitudinal das pesquisas de um instituto.

Permite inspecionar a evolução temporal de todas as pesquisas realizadas por um instituto
específico ao longo da campanha para os principais concorrentes, comparando sua trajetória
diretamente contra os dados dos demais institutos e o resultado oficial apurado pelo TSE.
"""

from datetime import date, timedelta
from typing import Sequence

import plotly.graph_objects as go

from src.transformations.schemas import PesquisaEleitoralSchema, ResultadoOficialTSESchema

CANDIDATE_COLORS: dict[str, str] = {
    "Flávio Bolsonaro": "#3B82F6",
    "Flávio": "#3B82F6",
    "Lula": "#EF4444",
    "Augusto Cury": "#A855F7",
    "Cury": "#A855F7",
    "Bolsonaro": "#3B82F6",
    "Simone Tebet": "#10B981",
    "Tebet": "#10B981",
    "Ciro Gomes": "#F59E0B",
    "Ciro": "#F59E0B",
    "Ronaldo Caiado": "#EC4899",
    "Caiado": "#EC4899",
    "Romeu Zema": "#F97316",
    "Zema": "#F97316",
    "Renan Santos": "#0EA5E9",
    "Renan": "#0EA5E9",
}

SHORT_NAMES: dict[str, str] = {
    "Flávio Bolsonaro": "Flávio",
    "Lula": "Lula",
    "Luiz Inácio Lula da Silva": "Lula",
    "Augusto Cury": "Cury",
    "Jair Bolsonaro": "Bolsonaro",
    "Bolsonaro": "Bolsonaro",
    "Simone Tebet": "Tebet",
    "Ciro Gomes": "Ciro",
    "Ronaldo Caiado": "Caiado",
    "Romeu Zema": "Zema",
    "Renan Santos": "Renan",
}


def get_candidate_short_name(candidate: str) -> str:
    """Retorna o nome curto simplificado para legendas e anotações.

    Args:
        candidate: Nome completo do candidato.

    Returns:
        str: Nome encurtado (ex: 'Flávio', 'Lula', 'Cury').

    Raises:
        None.
    """
    if candidate in SHORT_NAMES:
        return SHORT_NAMES[candidate]
    return candidate.split()[0]


def get_candidate_color(candidate: str, index: int = 0) -> str:
    """Retorna a cor padronizada associada ao candidato com fallback determinístico.

    Args:
        candidate: Nome completo ou curto do candidato.
        index: Índice sequencial caso seja necessário usar cor da paleta fallback.

    Returns:
        str: Código hexadecimal da cor.

    Raises:
        None.
    """
    if candidate in CANDIDATE_COLORS:
        return CANDIDATE_COLORS[candidate]
    short = get_candidate_short_name(candidate)
    if short in CANDIDATE_COLORS:
        return CANDIDATE_COLORS[short]
    fallback_palette = ["#38BDF8", "#F43F5E", "#A855F7", "#10B981", "#F59E0B", "#F97316"]
    return fallback_palette[index % len(fallback_palette)]


def create_institute_temporal_chart(
    institute_name: str,
    all_polls: Sequence[PesquisaEleitoralSchema],
    tse_result: ResultadoOficialTSESchema | None,
    election_date: date,
    candidates: Sequence[str] | None = None,
    campaign_start_date: date | None = None,
) -> go.Figure:
    """Cria o gráfico de série temporal comparando as pesquisas de um instituto com o cenário geral e as urnas.

    Exibe os dados dos demais institutos como nuvem dispersa translúcida, a trajetória
    do instituto auditado em linha contínua com marcadores cheios, e o resultado oficial
    das urnas marcado na data da eleição por triângulos indicativos.

    Args:
        institute_name: Nome fantasia do instituto selecionado para detalhamento.
        all_polls: Conjunto de todas as pesquisas da campanha.
        tse_result: Resultado oficial consolidado das urnas (ou None).
        election_date: Data oficial do pleito (linha vertical de fechamento).
        candidates: Lista opcional de candidatos a plotar. Se omitido, seleciona
            automaticamente os 3 candidatos mais votados no resultado oficial.
        campaign_start_date: Data de corte inicial para o horizonte temporal
            (por padrão 16/08 para pleitos de 1º turno).

    Returns:
        go.Figure: Figura Plotly interativa formatada no padrão visual escuro do projeto.

    Raises:
        None.
    """
    fig = go.Figure()

    # 1. Definição da data de início de campanha
    if campaign_start_date is None:
        if election_date.month == 10 and election_date.day <= 10:
            campaign_start_date = date(election_date.year, 8, 16)
        else:
            all_dates = [p.data_fim_campo for p in all_polls]
            campaign_start_date = (
                min(all_dates) if all_dates else election_date - timedelta(days=30)
            )

    # 2. Segregação das pesquisas da campanha e do instituto
    camp_polls = [
        p
        for p in all_polls
        if campaign_start_date is None or p.data_fim_campo >= campaign_start_date
    ]
    inst_polls = sorted(
        [p for p in camp_polls if p.instituto_nome_fantasia == institute_name],
        key=lambda p: p.data_fim_campo,
    )
    if not inst_polls:
        # Fallback caso o instituto possua pesquisas apenas antes da data de corte
        inst_polls = sorted(
            [p for p in all_polls if p.instituto_nome_fantasia == institute_name],
            key=lambda p: p.data_fim_campo,
        )
    other_polls = [p for p in camp_polls if p.instituto_nome_fantasia != institute_name]

    # 3. Determinação dos candidatos em foco
    if candidates is not None and len(candidates) > 0:
        target_candidates = list(candidates)
    elif tse_result and tse_result.resultado_nominal:
        sorted_official = sorted(
            [c for c in tse_result.resultado_nominal.keys() if c != "Outros"],
            key=lambda c: tse_result.resultado_nominal[c],
            reverse=True,
        )
        target_candidates = sorted_official[:3]
    else:
        candidates_found = {c for p in inst_polls for c in p.votos_validos.keys() if c != "Outros"}
        target_candidates = sorted(list(candidates_found))[:3]

    # 4. Cálculo do limite do eixo Y
    all_observed_vals: list[float] = []
    for cand in target_candidates:
        if tse_result and tse_result.resultado_nominal and cand in tse_result.resultado_nominal:
            all_observed_vals.append(float(tse_result.resultado_nominal[cand]))
        for p in camp_polls:
            if cand in p.votos_validos:
                all_observed_vals.append(float(p.votos_validos[cand]))

    max_val = max(all_observed_vals) if all_observed_vals else 50.0
    y_max = max(60.0, float(max_val) + 12.0)

    # 5. Adiciona os pontos dispersos dos demais institutos (pontos claros translúcidos)
    for idx, cand in enumerate(target_candidates):
        color = get_candidate_color(cand, idx)
        short_name = get_candidate_short_name(cand)

        other_dates = [p.data_fim_campo for p in other_polls if cand in p.votos_validos]
        other_vals = [p.votos_validos[cand] for p in other_polls if cand in p.votos_validos]
        other_texts = [p.instituto_nome_fantasia for p in other_polls if cand in p.votos_validos]

        if other_dates:
            fig.add_trace(
                go.Scatter(
                    x=other_dates,
                    y=other_vals,
                    mode="markers",
                    name=f"Demais institutos ({short_name})",
                    marker=dict(
                        color=color,
                        opacity=0.28,
                        size=6.5,
                        line=dict(width=0),
                    ),
                    text=other_texts,
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        "Data: %{x|%d/%m/%Y}<br>"
                        f"{short_name}: " + "%{y:.1f}%<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

    # 6. Adiciona as pesquisas do instituto auditado (linha contínua + marcadores destacados)
    for idx, cand in enumerate(target_candidates):
        color = get_candidate_color(cand, idx)
        short_name = get_candidate_short_name(cand)

        inst_dates = [p.data_fim_campo for p in inst_polls if cand in p.votos_validos]
        inst_vals = [p.votos_validos[cand] for p in inst_polls if cand in p.votos_validos]
        sample_sizes = [
            f"{p.tamanho_amostra:,} entrevistas" for p in inst_polls if cand in p.votos_validos
        ]

        if inst_dates:
            fig.add_trace(
                go.Scatter(
                    x=inst_dates,
                    y=inst_vals,
                    mode="lines+markers",
                    name=short_name,
                    line=dict(color=color, width=3.0),
                    marker=dict(
                        color=color,
                        size=8.5,
                        line=dict(color="#FFFFFF", width=1.0),
                    ),
                    text=sample_sizes,
                    hovertemplate=(
                        f"<b>{institute_name}</b> (%{{text}})<br>"
                        "Data: %{x|%d/%m/%Y}<br>"
                        f"<b>{short_name}: " + "%{y:.1f}%</b><extra></extra>"
                    ),
                    showlegend=True,
                )
            )

    # 7. Linha divisória da eleição
    fig.add_shape(
        type="line",
        x0=election_date,
        x1=election_date,
        y0=0,
        y1=y_max,
        line=dict(color="#CBD5E1", width=1.5, dash="dash"),
    )
    fig.add_annotation(
        x=election_date,
        y=y_max - 2,
        text="eleição",
        showarrow=False,
        font=dict(
            color="#CBD5E1",
            size=13,
            family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        ),
        xanchor="center",
        yanchor="bottom",
    )

    # 8. Marcadores de resultado oficial (triângulos apontando para baixo)
    if (
        tse_result
        and getattr(tse_result, "apuracao_concluida", True)
        and tse_result.resultado_nominal
    ):
        for idx, cand in enumerate(target_candidates):
            if cand in tse_result.resultado_nominal:
                val_oficial = tse_result.resultado_nominal[cand]
                color = get_candidate_color(cand, idx)
                short_name = get_candidate_short_name(cand)
                val_ptbr = f"{val_oficial:.1f}".replace(".", ",")

                fig.add_trace(
                    go.Scatter(
                        x=[election_date],
                        y=[val_oficial],
                        mode="markers+text",
                        marker=dict(symbol="triangle-down", size=13, color=color),
                        text=[f"  {short_name} {val_ptbr}"],
                        textposition="middle right",
                        textfont=dict(
                            color=color,
                            size=13,
                            family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                        ),
                        hovertemplate=(
                            f"<b>Resultado Oficial (TSE)</b><br>"
                            f"{short_name}: {val_ptbr}%<extra></extra>"
                        ),
                        showlegend=False,
                    )
                )

    # 9. Configurações de layout, temas e legendas
    earliest_inst_date = inst_polls[0].data_fim_campo if inst_polls else campaign_start_date
    start_x = min(campaign_start_date, earliest_inst_date)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=450,
        margin=dict(l=45, r=110, t=35, b=65),
        xaxis=dict(
            type="date",
            tickformat="%d/%m",
            showgrid=False,
            linecolor="#282D37",
            range=[start_x - timedelta(days=2), election_date + timedelta(days=6)],
        ),
        yaxis=dict(
            tickformat=".0f",
            ticksuffix="%",
            gridcolor="#23272F",
            zeroline=True,
            zerolinecolor="#282D37",
            range=[0, y_max],
            dtick=10,
        ),
        legend=dict(
            orientation="h",
            y=-0.16,
            x=0.0,
            xanchor="left",
            font=dict(size=12, color="#E2E8F0"),
        ),
    )

    # Sub-legenda informativa no canto inferior direito
    fig.add_annotation(
        text=(
            f"<b>linha:</b> {institute_name} &nbsp;·&nbsp; "
            "<b>pontos claros:</b> os demais institutos &nbsp;·&nbsp; "
            "<b>triângulo:</b> resultado"
        ),
        xref="paper",
        yref="paper",
        x=1.0,
        y=-0.16,
        xanchor="right",
        yanchor="top",
        showarrow=False,
        font=dict(size=11, color="#94A3B8"),
    )

    return fig
