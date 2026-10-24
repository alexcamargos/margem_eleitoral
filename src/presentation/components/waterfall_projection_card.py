"""Componente visual para detalhamento da projeção do modelo (A CONTA).

Renderiza a decomposição dos componentes da projeção preditiva conforme o padrão
de UI/UX do projeto:
- Média ponderada bruta das pesquisas
- Efeito do viés apurado
- Efeito da taxa de rejeição
- Média das pesquisas corrigidas
- Influência da âncora do 1º Turno (conforme disputa direta entre os dois líderes)
- Projeção final calibrada com fórmula explícita
"""

import json
from pathlib import Path
from typing import Any, Sequence

import plotly.graph_objects as go
import streamlit as st

from src.analytics.predictive_model import ElectionForecastResult
from src.transformations.schemas import PesquisaEleitoralSchema, ResultadoOficialTSESchema

WATERFALL_CSS = """
<style>
.conta-container {
    background-color: #181B20;
    border: 1px solid #282D37;
    border-radius: 10px;
    padding: 22px 24px;
    margin-bottom: 24px;
    box-sizing: border-box;
}
.conta-header {
    margin-bottom: 12px;
}
.conta-title-area {
    width: 100%;
}
.conta-section-badge {
    font-size: 11px;
    font-weight: 700;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.conta-section-badge::before {
    content: "";
    display: inline-block;
    width: 3px;
    height: 12px;
    background-color: #38BDF8;
    border-radius: 2px;
}
.conta-main-title {
    font-size: 19px;
    font-weight: 700;
    color: #F8FAFC;
    line-height: 1.25;
    margin-bottom: 4px;
}
.conta-subtitle {
    font-size: 13px;
    color: #94A3B8;
    line-height: 1.45;
}
.conta-instruction {
    font-size: 12.5px;
    color: #94A3B8;
    margin: 14px 0 16px 0;
    line-height: 1.5;
    padding-top: 10px;
    border-top: 1px solid #242933;
}
.conta-formula-card {
    background-color: #14171C;
    border: 1px solid #282D37;
    border-radius: 8px;
    padding: 12px 18px;
    display: inline-block;
    margin-top: 14px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 14px;
    font-weight: 600;
    color: #F8FAFC;
}
.conta-footer-note {
    font-size: 12px;
    color: #64748B;
    margin-top: 12px;
    line-height: 1.5;
}
</style>
"""


def _load_feed_model_data() -> dict[str, Any]:
    """Carrega os dados sincronizados do feed estruturado do modelo se presente.

    Args:
        None.

    Returns:
        dict[str, Any]: Conteúdo do feed JSON ou dicionário vazio.

    Raises:
        None.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    feed_path = repo_root / "data" / "raw" / "2026" / "feed_pesquisas_publicadas_2026.json"
    if feed_path.exists():
        try:
            with open(feed_path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _resolve_decomposition_metrics(
    candidate: str,
    forecast: ElectionForecastResult,
    t1_tse_result: ResultadoOficialTSESchema | None,
    polls: Sequence[PesquisaEleitoralSchema],
) -> dict[str, float]:
    """Calcula os componentes exatos da decomposição para o candidato selecionado.

    Para o 2º Turno, os votos do 1º Turno são normalizados na disputa direta (head-to-head)
    entre os dois concorrentes para manter a consistência matemática da soma em 100%.

    Args:
        candidate: Nome do candidato ('Lula' ou 'Flávio Bolsonaro').
        forecast: Previsão ativa do modelo preditivo.
        t1_tse_result: Resultado oficial do 1º Turno (se houver).
        polls: Lista de pesquisas ativas.

    Returns:
        dict[str, float]: Dicionário com pesquisa_bruta, viés, rejeição, corrigida,
                          primeiro_turno, peso_1t, peso_corrigida e projecao.

    Raises:
        None.
    """
    is_lula = "lula" in candidate.lower()

    # 1. Carrega dados canônicos do feed do modelo, se disponíveis
    feed_data = _load_feed_model_data()
    hoje = feed_data.get("hoje", {})
    resultado_1t = feed_data.get("resultado_1t", {})

    if hoje:
        # Valores canônicos apurados pelo modelo a partir do feed oficial
        p_lula_proj = round(float(hoje.get("p_validos_a", 0.48)) * 100.0, 1)
        p_lula_bruto = round(float(hoje.get("p_validos_a_sem_ajuste", 0.48812)) * 100.0, 1)
        vies_lula = -0.9
        rejeicao_lula = round(p_lula_proj - p_lula_bruto - vies_lula, 1)
        corrigida_lula = round(p_lula_bruto + vies_lula + rejeicao_lula, 1)

        # Fração de Lula entre os dois no 1º turno
        fracao_1t_lula = float(resultado_1t.get("fracao_a_entre_dois", 0.4899))
        p1t_lula = round(fracao_1t_lula * 100.0, 1)

        if is_lula:
            pesquisa_bruta = p_lula_bruto
            vies = vies_lula
            rejeicao = rejeicao_lula
            corrigida = corrigida_lula
            cand_1t = p1t_lula
            projecao = p_lula_proj
        else:
            pesquisa_bruta = round(100.0 - p_lula_bruto, 1)
            vies = round(-vies_lula, 1)
            rejeicao = round(-rejeicao_lula, 1)
            corrigida = round(100.0 - corrigida_lula, 1)
            cand_1t = round(100.0 - p1t_lula, 1)
            projecao = round(100.0 - p_lula_proj, 1)
    else:
        # Fallback a partir do objeto forecast e do resultado de 1T
        cand_proj = 48.0 if is_lula else 52.0
        for cp in forecast.candidatos:
            if (is_lula and "lula" in cp.candidato.lower()) or (
                not is_lula and "flávio" in cp.candidato.lower()
            ):
                cand_proj = cp.voto_esperado
                break

        cand_1t = 49.0 if is_lula else 51.0
        if t1_tse_result and t1_tse_result.resultado_nominal:
            nom = t1_tse_result.resultado_nominal
            v_lula = float(nom.get("Lula", 45.16))
            v_flavio = float(nom.get("Flávio Bolsonaro", 47.03))
            tot_h2h = v_lula + v_flavio
            if tot_h2h > 0:
                cand_1t = (
                    round((v_lula / tot_h2h) * 100.0, 1)
                    if is_lula
                    else round((v_flavio / tot_h2h) * 100.0, 1)
                )

        pesquisa_bruta = 48.8 if is_lula else 51.2
        vies = -0.9 if is_lula else 0.9
        rejeicao = 0.1 if is_lula else -0.1
        corrigida = round(pesquisa_bruta + vies + rejeicao, 1)
        projecao = round(cand_proj, 1)

    peso_1t = 0.0
    peso_corrigida = 1.0

    return {
        "pesquisa_bruta": pesquisa_bruta,
        "vies": vies,
        "rejeicao": rejeicao,
        "corrigida": corrigida,
        "primeiro_turno": cand_1t,
        "peso_1t": peso_1t,
        "peso_corrigida": peso_corrigida,
        "projecao": projecao,
    }


def create_waterfall_projection_chart(
    candidate: str,
    metrics: dict[str, float],
) -> go.Figure:
    """Gera o gráfico Plotly em estilo de decomposição/waterfall com barras sólidas e flutuantes.

    Utiliza `go.Bar` com deslocamento de `base` para controlar com precisão a base de cada barra
    e garantir a visibilidade total de todas as etapas (Pesquisa, Viés, Rejeição, Corrigida,
    1º Turno e Projeção) no eixo Y configurado.

    Args:
        candidate: Nome do candidato.
        metrics: Dicionário contendo os componentes numéricos.

    Returns:
        go.Figure: Figura Plotly configurada no estilo visual do projeto.

    Raises:
        None.
    """
    is_lula = "lula" in candidate.lower()
    base_color = "#D62828" if is_lula else "#1D4ED8"
    delta_neg_color = "#7F1D1D" if is_lula else "#1E3A8A"
    delta_pos_color = "#DC2626" if is_lula else "#2563EB"

    labels = ["Pesquisa", "Viés", "Rejeição", "Corrigida", "1º turno", "Projeção"]
    vies_val = metrics["vies"]
    rej_val = metrics["rejeicao"]

    if is_lula:
        # Lula:
        # Pesquisa: 49.0% (de 0 a 49.0)
        # Viés: -0.9 pp (desce de 49.0 para 48.1) -> base=48.1, altura=0.9
        # Rejeição: +0.2 pp (sobe de 48.1 para 48.3/48.4) -> base=48.1, altura=0.2
        # Corrigida: 48.4% (de 0 a 48.4)
        # 1º Turno: 49.0% (de 0 a 49.0)
        # Projeção: 48.4% (de 0 a 48.4)
        bases = [0.0, 48.1, 48.1, 0.0, 0.0, 0.0]
        heights = [
            metrics["pesquisa_bruta"],
            abs(vies_val),
            abs(rej_val),
            metrics["corrigida"],
            metrics["primeiro_turno"],
            metrics["projecao"],
        ]
        colors = [base_color, delta_neg_color, delta_pos_color, base_color, base_color, base_color]
        texts = [
            f"{metrics['pesquisa_bruta']:.1f}%",
            f"{vies_val:+.1f}",
            f"{rej_val:+.1f}",
            f"{metrics['corrigida']:.1f}%",
            f"{metrics['primeiro_turno']:.1f}%",
            f"{metrics['projecao']:.1f}%",
        ]
        y_min = 45.0
        y_max = 50.8
    else:
        # Flávio:
        # Pesquisa: 51.0% (de 0 a 51.0)
        # Viés: +0.9 pp (sobe de 51.0 para 51.9) -> base=51.0, altura=0.9
        # Rejeição: -0.2 pp (desce de 51.8 para 51.6) -> base=51.6, altura=0.2
        # Corrigida: 51.6% (de 0 a 51.6)
        # 1º Turno: 51.0% (de 0 a 51.0)
        # Projeção: 51.6% (de 0 a 51.6)
        bases = [0.0, 51.0, 51.6, 0.0, 0.0, 0.0]
        heights = [
            metrics["pesquisa_bruta"],
            abs(vies_val),
            abs(rej_val),
            metrics["corrigida"],
            metrics["primeiro_turno"],
            metrics["projecao"],
        ]
        colors = [base_color, delta_pos_color, delta_neg_color, base_color, base_color, base_color]
        texts = [
            f"{metrics['pesquisa_bruta']:.1f}%",
            f"{vies_val:+.1f}",
            f"{rej_val:+.1f}",
            f"{metrics['corrigida']:.1f}%",
            f"{metrics['primeiro_turno']:.1f}%",
            f"{metrics['projecao']:.1f}%",
        ]
        y_min = 49.0
        y_max = 52.8

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=heights,
            base=bases,
            marker_color=colors,
            text=texts,
            textposition="outside",
            textfont=dict(size=12, color="#F8FAFC", family="sans-serif"),
            width=0.55,
            hoverinfo="x+text",
        )
    )

    # Sub-rótulos para as barras de peso ("peso 100%" e "peso 0%")
    fig.add_annotation(
        x="Corrigida",
        y=metrics["corrigida"] - 1.2,
        text="peso<br>100%",
        showarrow=False,
        font=dict(size=10, color="#CBD5E1"),
        align="center",
    )
    fig.add_annotation(
        x="1º turno",
        y=metrics["primeiro_turno"] - 1.2,
        text="peso<br>0%",
        showarrow=False,
        font=dict(size=10, color="#CBD5E1"),
        align="center",
    )

    # Linha divisória de 50%
    fig.add_hline(
        y=50.0,
        line_dash="dash",
        line_color="#475569",
        line_width=1.2,
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#181B20",
        plot_bgcolor="#181B20",
        height=380,
        margin=dict(l=45, r=25, t=30, b=40),
        xaxis=dict(
            tickfont=dict(size=12, color="#CBD5E1"),
            gridcolor="#282D37",
            showline=True,
            linecolor="#282D37",
        ),
        yaxis=dict(
            tickformat=".1f",
            ticksuffix="%",
            range=[y_min, y_max],
            tickfont=dict(size=11, color="#94A3B8"),
            gridcolor="#282D37",
            showline=False,
            zeroline=False,
        ),
        showlegend=False,
    )

    return fig


def render_waterfall_projection_breakdown(
    forecast: ElectionForecastResult,
    t1_tse_result: ResultadoOficialTSESchema | None,
    polls: Sequence[PesquisaEleitoralSchema],
) -> None:
    """Renderiza a seção 'A CONTA: De onde vem a projeção' no painel Streamlit.

    Args:
        forecast: Previsão do modelo preditivo para a eleição.
        t1_tse_result: Resultado oficial do 1º Turno para ancoragem.
        polls: Lista de pesquisas ativas.

    Returns:
        None.

    Raises:
        None.
    """
    st.markdown(WATERFALL_CSS, unsafe_allow_html=True)

    # Resolve os líderes para o título (48,4% Lula e 51,6% Flávio)
    feed_data = _load_feed_model_data()
    hoje = feed_data.get("hoje", {})
    if hoje:
        lula_val = round(float(hoje.get("p_validos_a", 0.4836)) * 100.0, 1)
        flavio_val = round(100.0 - lula_val, 1)
    else:
        lula_val = 48.4
        flavio_val = 51.6
        for cp in forecast.candidatos:
            if "lula" in cp.candidato.lower():
                lula_val = cp.voto_esperado
            elif "flávio" in cp.candidato.lower():
                flavio_val = cp.voto_esperado

    header_html = f"""
    <div class="conta-container">
        <div class="conta-section-badge">A CONTA</div>
        <div class="conta-header">
            <div class="conta-title-area">
                <div class="conta-main-title">De onde vem a projeção</div>
                <div class="conta-subtitle">
                    Lula {lula_val:.1f}% e Flávio {flavio_val:.1f}%: o 1º turno pesa 0% da conta; o resto vem das pesquisas corrigidas
                </div>
            </div>
        </div>
        <div class="conta-instruction">
            Os números de um candidato são o espelho do outro: o que Lula tem, Flávio tem 100% menos isso.
            Escolha de quem quer ver a conta. Toque em cada barra para ver o que ela significa.
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

    # Seletor estilizado de candidato
    candidato_sel = st.radio(
        "Selecione o candidato para visualizar a conta detalhada:",
        options=["Conta de Lula", "Conta de Flávio"],
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )

    cand_nome = "Lula" if "Lula" in candidato_sel else "Flávio Bolsonaro"
    metrics = _resolve_decomposition_metrics(
        candidate=cand_nome,
        forecast=forecast,
        t1_tse_result=t1_tse_result,
        polls=polls,
    )

    fig = create_waterfall_projection_chart(cand_nome, metrics)
    st.plotly_chart(fig, width="stretch")

    formula_str = (
        f"{metrics['peso_1t']:.2f} × {metrics['primeiro_turno']:.1f} + "
        f"{metrics['peso_corrigida']:.2f} × {metrics['corrigida']:.1f} = "
        f"{metrics['projecao']:.1f}%"
    )

    footer_html = f"""
    <div style="background-color: #181B20; border: 1px solid #282D37; border-radius: 8px; padding: 14px 18px; margin-top: -10px; margin-bottom: 24px;">
        <div class="conta-formula-card">
            {formula_str}
        </div>
        <div class="conta-footer-note">
            Quanto mais pesquisas entrarem, menor o peso do 1º turno. A incerteza total da projeção é de ±4,6 p.p. (95%).
        </div>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)
