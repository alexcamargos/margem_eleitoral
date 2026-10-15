"""Componente Plotly para grid de Small Multiples ('Inclinação ao longo da campanha').

Gera uma matriz de subplots com a evolução temporal da inclinação relativa de cada
instituto em comparação com o consenso dos pares na mesma janela semanal (±7 dias),
inspirado na referência visual do projeto.
"""

from datetime import date, datetime
from typing import Any, Sequence

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _format_ptbr_num(val: float, include_sign: bool = True) -> str:
    """Formata um número float no padrão pt-BR com vírgula e sinal opcional.

    Args:
        val: Valor float a ser formatado.
        include_sign: Se True, prefixa valores positivos com '+'.

    Returns:
        str: String formatada (ex.: '+1,7', '-3,0', '0,0').

    Raises:
        None.
    """
    if abs(val) < 0.05:
        return "0,0"
    sign_str = "+" if (include_sign and val > 0) else ""
    return f"{sign_str}{val:.1f}".replace(".", ",")


def create_small_multiples_grid(
    data: dict[str, Any] | Sequence[dict[str, Any]],
    candidate_1: str = "Candidato 1",
    candidate_2: str = "Candidato 2",
) -> go.Figure:
    """Cria grid de subplots mostrando a inclinação longitudinal por instituto.

    Exibe cada instituto em um mini-gráfico com sua média de campanha, intervalo de 80%,
    linha de base zero e pontos coloridos por inclinação individual frente aos pares.

    Args:
        data: Dicionário retornado por compute_campaign_house_effects (contendo 'institutes'),
            ou lista de institutos já sumarizados, ou dicionário legado inst -> list[points].
        candidate_1: Nome do primeiro concorrente (usado em tooltips).
        candidate_2: Nome do segundo concorrente (usado em tooltips).

    Returns:
        go.Figure: Figura Plotly com grade responsiva de 4 colunas.

    Raises:
        None.
    """
    # Normalização de dados para formato uniforme
    institutes_data: list[dict[str, Any]] = []

    if isinstance(data, dict) and "institutes" in data:
        institutes_data = list(data["institutes"])
        candidate_1 = data.get("candidate_1", candidate_1)
        candidate_2 = data.get("candidate_2", candidate_2)
    elif isinstance(data, list):
        institutes_data = list(data)
    elif isinstance(data, dict):
        # Compatibilidade com formato legado: dict[inst, list[points]]
        for inst_name, raw_points in data.items():
            pts = []
            for p in raw_points:
                tilt_val = p.get("tilt", p.get("desvio_tse", 0.0))
                pts.append(
                    {
                        "data": p.get("data"),
                        "margin": p.get("diferenca_estimada", p.get("margin", 0.0)),
                        "peer_mean": p.get("peer_mean", 0.0),
                        "tilt": tilt_val,
                    }
                )
            tilts = [x["tilt"] for x in pts]
            mean_val = sum(tilts) / len(tilts) if tilts else 0.0
            institutes_data.append(
                {
                    "instituto": inst_name,
                    "mean_tilt": mean_val,
                    "ci_lower": mean_val - 1.5,
                    "ci_upper": mean_val + 1.5,
                    "includes_zero": (mean_val - 1.5 <= 0.0 <= mean_val + 1.5),
                    "n_polls": len(pts),
                    "points": pts,
                }
            )
        institutes_data.sort(key=lambda x: x["mean_tilt"])

    if not institutes_data:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#181B20",
            plot_bgcolor="#181B20",
            title="Sem dados de inclinação disponíveis para os critérios selecionados",
        )
        return fig

    n_cols = 4
    n_rows = (len(institutes_data) + n_cols - 1) // n_cols

    # Montagem dos títulos com HTML styling
    titles: list[str] = []
    for inst_info in institutes_data:
        inst_name = inst_info["instituto"]
        mean_val = inst_info["mean_tilt"]
        ci_low = inst_info["ci_lower"]
        ci_high = inst_info["ci_upper"]
        n_p = inst_info["n_polls"]

        mean_str = _format_ptbr_num(mean_val, include_sign=True)
        low_str = _format_ptbr_num(ci_low, include_sign=False)
        high_str = _format_ptbr_num(ci_high, include_sign=False)

        if mean_val < -0.05:
            color = "#F87171"  # Vermelho suave para inclinação a favor do candidato 2
        elif mean_val > 0.05:
            color = "#38BDF8"  # Azul suave para inclinação a favor do candidato 1
        else:
            color = "#94A3B8"  # Neutro

        title_html = (
            f"<b>{inst_name}</b> "
            f"<span style='color:{color}; font-weight:700;'>{mean_str}</span> "
            f"<span style='color:#94A3B8; font-size:10px; font-weight:normal;'>"
            f"({low_str} a {high_str}; {n_p} pesquisas)</span>"
        )
        titles.append(title_html)

    fig = make_subplots(
        rows=n_rows,
        cols=n_cols,
        subplot_titles=titles,
        vertical_spacing=max(0.06, 0.22 / n_rows),
        horizontal_spacing=0.045,
    )

    # Identifica limites máximos para escala simétrica padronizada
    max_abs_tilt = 0.0
    for inst_info in institutes_data:
        for pt in inst_info.get("points", []):
            max_abs_tilt = max(max_abs_tilt, abs(float(pt.get("tilt", 0.0))))
        max_abs_tilt = max(max_abs_tilt, abs(float(inst_info.get("ci_lower", 0.0))))
        max_abs_tilt = max(max_abs_tilt, abs(float(inst_info.get("ci_upper", 0.0))))

    y_limit = max(10.0, ((int(max_abs_tilt) // 2) + 1) * 2.0)

    for idx, inst_info in enumerate(institutes_data):
        row = (idx // n_cols) + 1
        col = (idx % n_cols) + 1

        inst_name = inst_info["instituto"]
        mean_val = float(inst_info["mean_tilt"])
        ci_low = float(inst_info["ci_lower"])
        ci_high = float(inst_info["ci_upper"])
        includes_zero = bool(inst_info.get("includes_zero", False))
        points = inst_info.get("points", [])

        # 1. Faixa sombreada do intervalo de confiança de 80%
        if includes_zero:
            band_color = "rgba(148, 163, 184, 0.12)"  # Mais clara / neutra quando inclui zero
        elif mean_val < 0:
            band_color = "rgba(239, 68, 68, 0.16)"  # Tom avermelhado suave
        else:
            band_color = "rgba(56, 189, 248, 0.16)"  # Tom azulado suave

        fig.add_hrect(
            y0=ci_low,
            y1=ci_high,
            fillcolor=band_color,
            line_width=0,
            row=row,
            col=col,
        )

        # 2. Linha sólida de referência zero (consenso dos pares)
        fig.add_hline(
            y=0.0,
            line_color="#4B5563",
            line_width=1.0,
            row=row,
            col=col,
        )

        # 3. Linha tracejada da média histórica do instituto
        mean_line_color = (
            "#F87171" if mean_val < -0.05 else ("#38BDF8" if mean_val > 0.05 else "#94A3B8")
        )
        fig.add_hline(
            y=mean_val,
            line_dash="dash",
            line_color=mean_line_color,
            line_width=1.3,
            row=row,
            col=col,
        )

        if points:
            dates = [p["data"] for p in points]
            tilts = [float(p["tilt"]) for p in points]
            custom_data = [
                [
                    p.get("margin", 0.0),
                    p.get("peer_mean", 0.0),
                    inst_name,
                    p["data"].strftime("%d/%m")
                    if isinstance(p["data"], (date, datetime))
                    else str(p["data"]),
                ]
                for p in points
            ]

            # Cor de cada ponto individual conforme inclinação daquela pesquisa
            marker_colors = [
                "#38BDF8" if t > 0.05 else ("#F87171" if t < -0.05 else "#94A3B8") for t in tilts
            ]

            # 4. Linha de conexão sutil + marcadores de cada pesquisa
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=tilts,
                    mode="lines+markers",
                    name=inst_name,
                    line=dict(color="#64748B", width=1.5),
                    marker=dict(
                        size=5.5,
                        color=marker_colors,
                        line=dict(width=1, color="#0F172A"),
                    ),
                    customdata=custom_data,
                    hovertemplate=(
                        "<b>%{customdata[2]}</b><br>"
                        "Data: %{customdata[3]}<br>"
                        f"Margem ({candidate_1} vs {candidate_2}): %{{customdata[0]:+.1f}} p.p.<br>"
                        "Consenso dos pares (±7d): %{customdata[1]:+.1f} p.p.<br>"
                        "<b>Inclinação relativa: %{y:+.1f} p.p.</b><extra></extra>"
                    ),
                    showlegend=False,
                ),
                row=row,
                col=col,
            )

        # Configuração de eixos unificada
        fig.update_yaxes(
            range=[-y_limit, y_limit],
            tickvals=[-10, 0, 10] if y_limit <= 12 else [-y_limit, 0, y_limit],
            ticktext=["-10", "0", "+10"]
            if y_limit <= 12
            else [f"-{int(y_limit)}", "0", f"+{int(y_limit)}"],
            gridcolor="#22262E",
            zerolinecolor="#4B5563",
            zerolinewidth=1.0,
            tickfont=dict(size=8.5, color="#94A3B8"),
            row=row,
            col=col,
        )
        fig.update_xaxes(
            gridcolor="#22262E",
            tickfont=dict(size=8.5, color="#94A3B8"),
            tickformat="%d/%m",
            row=row,
            col=col,
        )

    # Dimensões dinâmicas proporcionais ao número de linhas
    chart_height = max(450, n_rows * 165 + 60)
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=chart_height,
        margin=dict(l=30, r=30, t=45, b=30),
    )

    # Ajusta estilo e alinhamento dos títulos dos subplots
    for ann in fig.layout.annotations:
        ann.font = dict(size=11, color="#F1F5F9")
        ann.xanchor = "left"
        if getattr(ann, "x", None) is not None:
            ann.x = max(0.0, float(ann.x) - 0.10)

    return fig
