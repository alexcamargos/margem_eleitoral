"""Simulador interativo do Princípio da Incerteza e Teorema Central do Limite (TCL).

Permite visualizar a convergência estocástica e a formação da curva normal
a partir de sorteios amostrais simulados de uma população de eleitores.
"""

import numpy as np
import plotly.graph_objects as go
from scipy import stats


def create_sampling_simulator_figure(
    p_true: float = 50.0,
    sample_size: int = 2000,
    num_simulations: int = 1000,
    deff: float = 1.0,
) -> go.Figure:
    """Gera visualização da distribuição amostral para demonstração do TCL e LLN.

    Args:
        p_true: Proporção populacional real em percentual (default: 50.0).
        sample_size: Tamanho de cada amostra simulada (n).
        num_simulations: Quantidade de pesquisas repetidas independentes.
        deff: Fator de correção de efeito de delineamento (default: 1.0).

    Returns:
        go.Figure: Histograma das estimativas amostrais com curva gaussiana teórica.

    Raises:
        None.
    """
    p_prob = p_true / 100.0

    # Simula sorteios binomiais com variância inflacionada por deff
    samples = np.random.binomial(n=sample_size, p=p_prob, size=num_simulations)
    sample_pcts = (samples / sample_size) * 100.0
    if deff > 1.0:
        # Adiciona ruído estocástico de conglomerado para refletir o deff
        extra_se = np.sqrt((deff - 1.0) * p_true * (100.0 - p_true) / sample_size)
        sample_pcts += np.random.normal(0, extra_se, size=num_simulations)

    # Erro padrão teórico ajustado por deff
    se_teorico = np.sqrt(deff * p_true * (100.0 - p_true) / sample_size)
    me_teorica = 1.96 * se_teorico
    ic_inf = p_true - me_teorica
    ic_sup = p_true + me_teorica

    fig = go.Figure()

    # Histograma das proporções amostrais
    fig.add_trace(
        go.Histogram(
            x=sample_pcts,
            histnorm="probability density",
            name="Pesquisas Simuladas",
            marker=dict(color="#3B82F6", opacity=0.65, line=dict(color="#1D4ED8", width=1)),
            nbinsx=35,
        )
    )

    # Curva teórica Normal N(mu, sigma)
    x_grid = np.linspace(p_true - 4 * se_teorico, p_true + 4 * se_teorico, 200)
    y_normal = stats.norm.pdf(x_grid, loc=p_true, scale=se_teorico)

    fig.add_trace(
        go.Scatter(
            x=x_grid,
            y=y_normal,
            mode="lines",
            name=f"Curva Teórica (deff={deff:.2f})",
            line=dict(color="#F59E0B", width=3),
        )
    )

    # Linha vertical no parâmetro real
    fig.add_vline(
        x=p_true,
        line_color="#EF4444",
        line_width=2.2,
        line_dash="solid",
        annotation_text=f"Parâmetro Real ({p_true:.1f}%)",
        annotation_position="top left",
        annotation_font=dict(color="#FCA5A5", size=10),
    )

    # Linhas de margem de 95%
    fig.add_vline(
        x=ic_inf,
        line_color="#10B981",
        line_width=1.5,
        line_dash="dot",
        annotation_text=f"- Margem ({ic_inf:.1f}%)",
        annotation_position="bottom left",
        annotation_font=dict(color="#6EE7B7", size=9),
    )
    fig.add_vline(
        x=ic_sup,
        line_color="#10B981",
        line_width=1.5,
        line_dash="dot",
        annotation_text=f"+ Margem ({ic_sup:.1f}%)",
        annotation_position="bottom right",
        annotation_font=dict(color="#6EE7B7", size=9),
    )

    fig.update_layout(
        title=dict(
            text=f"Distribuição Amostral de {num_simulations:,} Pesquisas (n = {sample_size:,} | deff = {deff:.2f})",
            font=dict(size=13, color="#F8FAFC"),
        ),
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis=dict(
            title="Intenção de Voto Observada (%)",
            gridcolor="#282D37",
        ),
        yaxis=dict(
            title="Densidade de Probabilidade",
            gridcolor="#282D37",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=10, color="#CBD5E1"),
        ),
    )

    return fig
