"""Componente visual de Storytelling Executivo (Cards de Síntese Imediata).

Fornece o resumo executivo de entrada do projeto Margem Eleitoral:
1. Manchete jornalística dinâmica interpretando o estado da corrida eleitoral.
2. Card de Agregação das Pesquisas (Nowcasting / Média Ponderada com barra bipartida
   e envelopes de credibilidade de 95%).
3. Card do Modelo Preditivo (Chance de Vitória Hoje com gauge semicircular e simulação
   de Monte Carlo).
4. Suporte a filtros rápidos (Votos Válidos vs. Inclui Indecisos).
"""

import math
from datetime import date
from typing import Any, Sequence

import polars as pl
import streamlit as st

from src.analytics.aggregator_model import compute_poll_aggregation_series
from src.analytics.predictive_model import (
    PredictiveModelConfig,
    compute_first_round_institute_calibration,
    predict_election_outcome,
)
from src.transformations.schemas import (
    AbrangenciaEnum,
    PesquisaEleitoralSchema,
    ResultadoOficialTSESchema,
)

CANDIDATE_METADATA_REGISTRY: dict[str, dict[str, str]] = {
    "Lula": {
        "name": "Lula",
        "short_name": "Lula",
        "party": "PT",
        "color": "#EF4444",
        "bg_tint": "rgba(239, 68, 68, 0.15)",
        "initials": "LU",
        "foto_url": "https://divulgacandcontas.tse.jus.br/divulga/rest/arquivo/img/2040602022/280001607829/BR",
    },
    "Flávio Bolsonaro": {
        "name": "Flávio Bolsonaro",
        "short_name": "Flávio",
        "party": "PL",
        "color": "#3B82F6",
        "bg_tint": "rgba(59, 130, 246, 0.15)",
        "initials": "FB",
        "foto_url": "https://divulgacandcontas.tse.jus.br/divulga/rest/arquivo/img/2022802018/190000624083/RJ",
    },
    "Bolsonaro": {
        "name": "Bolsonaro",
        "short_name": "Bolsonaro",
        "party": "PL",
        "color": "#3B82F6",
        "bg_tint": "rgba(59, 130, 246, 0.15)",
        "initials": "JB",
        "foto_url": "https://divulgacandcontas.tse.jus.br/divulga/rest/arquivo/img/2040602022/280001618036/BR",
    },
    "Jair Bolsonaro": {
        "name": "Bolsonaro",
        "short_name": "Bolsonaro",
        "party": "PL",
        "color": "#3B82F6",
        "bg_tint": "rgba(59, 130, 246, 0.15)",
        "initials": "JB",
        "foto_url": "https://divulgacandcontas.tse.jus.br/divulga/rest/arquivo/img/2040602022/280001618036/BR",
    },
    "Simone Tebet": {
        "name": "Simone Tebet",
        "short_name": "Tebet",
        "party": "MDB",
        "color": "#10B981",
        "bg_tint": "rgba(16, 185, 129, 0.15)",
        "initials": "ST",
        "foto_url": "https://divulgacandcontas.tse.jus.br/divulga/rest/arquivo/img/2040602022/280001607833/BR",
    },
    "Ciro Gomes": {
        "name": "Ciro Gomes",
        "short_name": "Ciro",
        "party": "PDT",
        "color": "#F59E0B",
        "bg_tint": "rgba(245, 158, 11, 0.15)",
        "initials": "CG",
        "foto_url": "https://divulgacandcontas.tse.jus.br/divulga/rest/arquivo/img/2040602022/280001600167/BR",
    },
    "Augusto Cury": {
        "name": "Augusto Cury",
        "short_name": "Cury",
        "party": "DC",
        "color": "#8B5CF6",
        "bg_tint": "rgba(139, 92, 246, 0.15)",
        "initials": "AC",
    },
    "Romeu Zema": {
        "name": "Romeu Zema",
        "short_name": "Zema",
        "party": "NOVO",
        "color": "#F97316",
        "bg_tint": "rgba(249, 115, 22, 0.15)",
        "initials": "RZ",
    },
    "Renan Santos": {
        "name": "Renan Santos",
        "short_name": "Renan",
        "party": "Missão",
        "color": "#0EA5E9",
        "bg_tint": "rgba(14, 165, 233, 0.15)",
        "initials": "RS",
    },
}

HERO_CARDS_CSS = """
.hero-card {
    background-color: #181B20;
    border: 1px solid #282D37;
    border-radius: 12px;
    padding: 20px 22px;
    height: 100%;
    box-sizing: border-box;
}
.hero-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    font-weight: 700;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 16px;
}
.hero-candidates-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}
.hero-cand-name {
    font-size: 15px;
    font-weight: 700;
    color: #F1F5F9;
}
.hero-cand-party {
    font-size: 11px;
    color: #94A3B8;
    background-color: #242933;
    padding: 1px 6px;
    border-radius: 4px;
    font-weight: 600;
}
.hero-cand-val {
    font-size: 34px;
    font-weight: 800;
    line-height: 1.1;
}
.hero-cand-val-sub {
    font-size: 11.5px;
    color: #94A3B8;
    margin-top: 3px;
}
.hero-vs-badge {
    font-size: 13px;
    font-weight: 700;
    color: #64748B;
}
.hero-bar-track {
    position: relative;
    width: 100%;
    height: 14px;
    border-radius: 7px;
    background-color: #242933;
    display: flex;
    margin: 18px 0 8px 0;
}
.hero-bar-split {
    display: flex;
    width: 100%;
    height: 100%;
    border-radius: 7px;
    overflow: hidden;
}
.hero-bar-threshold {
    position: absolute;
    left: 50%;
    top: -4px;
    bottom: -4px;
    width: 2px;
    border-left: 2px dashed #FFFFFF;
    z-index: 5;
}
.hero-bar-labels {
    display: flex;
    justify-content: space-between;
    font-size: 11.5px;
    color: #94A3B8;
    margin-top: 6px;
}
.hero-pills-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 18px;
}
.hero-pill {
    display: inline-flex;
    align-items: center;
    background-color: #20242C;
    border: 1px solid #333A48;
    border-radius: 20px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
    color: #CBD5E1;
}
.hero-pill-highlight {
    background-color: rgba(56, 189, 248, 0.12);
    border: 1px solid #38BDF8;
    color: #38BDF8;
}
.hero-pill-tie {
    background-color: rgba(245, 158, 11, 0.12);
    border: 1px solid #F59E0B;
    color: #FCD34D;
}
.hero-gauge-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 6px 0;
}
.hero-gauge-summary {
    font-size: 17.5px;
    font-weight: 700;
    margin-top: 10px;
    text-align: center;
    color: #F8FAFC;
}
.hero-gauge-subtext {
    font-size: 12px;
    color: #94A3B8;
    text-align: center;
    margin-top: 6px;
    line-height: 1.45;
    max-width: 330px;
}
"""


def _clean_html(html_str: str) -> str:
    """Higieniza e compacta strings HTML para renderização nativa segura no Streamlit.

    Remove quebras de linha e recuos que fazem o analisador CommonMark do Streamlit
    interpretar o markup HTML como bloco de código indentado.

    Args:
        html_str: Markup HTML bruto com potenciais quebras de linha e recuos.

    Returns:
        str: Markup HTML compactado e contínuo.

    Raises:
        None.
    """
    lines = [
        line.strip()
        for line in html_str.splitlines()
        if line.strip() and not line.strip().startswith("<!--")
    ]
    return "".join(lines)


def _format_ptbr_num(val: float, decimals: int = 1) -> str:
    """Formata valor numérico no padrão brasileiro com vírgula decimal.

    Args:
        val: Valor numérico em ponto flutuante.
        decimals: Quantidade de casas decimais.

    Returns:
        str: String formatada com vírgula decimal.

    Raises:
        None.
    """
    return f"{val:.{decimals}f}".replace(".", ",")


def _format_ptbr_int(val: int) -> str:
    """Formata número inteiro no padrão brasileiro com separador de milhar por ponto.

    Args:
        val: Número inteiro.

    Returns:
        str: String formatada com separador de milhar no padrão brasileiro.

    Raises:
        None.
    """
    return f"{val:,}".replace(",", ".")


def get_candidate_metadata(candidate_name: str) -> dict[str, str]:
    """Recupera metadados visuais e partidários de um candidato.

    Args:
        candidate_name: Nome do candidato.

    Returns:
        dict[str, str]: Dicionário contendo chaves:
            - 'name': Nome completo formatado.
            - 'short_name': Nome curto para manchetes e badges.
            - 'party': Sigla partidária.
            - 'color': Código hexadecimal da cor partidária.
            - 'bg_tint': Cor translúcida para fundos de destaque.
            - 'initials': Sigla de 2 letras para avatar estilizado.

    Raises:
        None.
    """
    if candidate_name in CANDIDATE_METADATA_REGISTRY:
        return dict(CANDIDATE_METADATA_REGISTRY[candidate_name])

    tokens = candidate_name.strip().split()
    initials = "".join([t[0] for t in tokens[:2]]).upper() if tokens else "CA"
    short_name = tokens[0] if tokens else candidate_name

    return {
        "name": candidate_name,
        "short_name": short_name,
        "party": "IND",
        "color": "#38BDF8",
        "bg_tint": "rgba(56, 189, 248, 0.15)",
        "initials": initials,
        "foto_url": None,
    }


def render_avatar_svg(meta: dict[str, str], size: int = 44) -> str:
    """Renderiza um avatar SVG estilizado circular para o candidato.

    Args:
        meta: Dicionário retornado por `get_candidate_metadata`.
        size: Dimensão em pixels de largura e altura (default: 44).

    Returns:
        str: String contendo o markup XML/SVG completo do avatar.

    Raises:
        None.
    """
    color = meta.get("color", "#38BDF8")
    initials = meta.get("initials", "CA")

    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 44 44" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg" style="border-radius: 50%; vertical-align: middle;">'
        f'<defs>'
        f'<linearGradient id="grad_{initials}" x1="0" y1="0" x2="44" y2="44" gradientUnits="userSpaceOnUse">'
        f'<stop stop-color="#242933"/>'
        f'<stop offset="1" stop-color="#181B20"/>'
        f'</linearGradient>'
        f'</defs>'
        f'<circle cx="22" cy="22" r="21" fill="url(#grad_{initials})" stroke="{color}" stroke-width="2"/>'
        f'<text x="22" y="27" text-anchor="middle" fill="#F8FAFC" font-size="14" font-weight="700" '
        f'font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif">{initials}</text>'
        f'</svg>'
    )


def render_candidate_avatar(meta: dict[str, str], size: int = 46) -> str:
    """Renderiza o avatar visual do candidato com a foto oficial do DivulgaCand ou fallback SVG.

    Args:
        meta: Dicionário retornado por `get_candidate_metadata`.
        size: Dimensão em pixels de largura e altura (default: 46).

    Returns:
        str: Markup HTML contendo a imagem oficial com recorte circular e
            fallback automático para o avatar vetorial com monograma.

    Raises:
        None.
    """
    color = meta.get("color", "#38BDF8")
    foto_url = meta.get("foto_url")
    svg_fallback = render_avatar_svg(meta, size=size)

    if not foto_url:
        return svg_fallback

    return (
        f'<img src="{foto_url}" width="{size}" height="{size}" alt="{meta["name"]}" '
        f'style="width: {size}px; height: {size}px; border-radius: 50%; object-fit: cover; '
        f'object-position: top center; border: 2px solid {color}; box-shadow: 0 2px 8px rgba(0,0,0,0.4); '
        f'vertical-align: middle; display: inline-block;" '
        f'onerror="this.style.display=\'none\'; if(this.nextElementSibling) this.nextElementSibling.style.display=\'inline-block\';" />'
        f'<span style="display: none; vertical-align: middle;">{svg_fallback}</span>'
    )


def render_gauge_svg(
    p_c1: float,
    p_c2: float,
    meta_c1: dict[str, str],
    meta_c2: dict[str, str],
    leader_prob: float,
) -> str:
    """Gera um arco semicircular (gauge radial) em SVG puro para o modelo preditivo.

    Args:
        p_c1: Probabilidade relativa de vitória do candidato 1 (0 a 100).
        p_c2: Probabilidade relativa de vitória do candidato 2 (0 a 100).
        meta_c1: Metadados do candidato 1 (lado esquerdo).
        meta_c2: Metadados do candidato 2 (lado direito).
        leader_prob: Probabilidade nominal do líder a ser exibida no centro.

    Returns:
        str: Markup SVG puro e responsivo com arco particionado e corte de 50%.

    Raises:
        None.
    """
    radius = 55.0
    circumference = math.pi * radius  # ~172.79
    color_c1 = meta_c1.get("color", "#EF4444")
    color_c2 = meta_c2.get("color", "#3B82F6")

    tot_p = max(0.001, p_c1 + p_c2)
    p1_ratio = max(0.0, min(1.0, p_c1 / tot_p))
    p2_ratio = max(0.0, min(1.0, p_c2 / tot_p))

    len_c1 = p1_ratio * circumference
    len_c2 = p2_ratio * circumference

    return (
        f'<svg viewBox="0 0 160 92" width="160" height="92" '
        f'xmlns="http://www.w3.org/2000/svg" style="display: block; margin: 0 auto;">'
        f'<path d="M 25 76 A 55 55 0 0 1 135 76" fill="none" stroke="#242933" stroke-width="12" '
        f'stroke-linecap="round"/>'
        f'<path d="M 25 76 A 55 55 0 0 1 135 76" fill="none" stroke="{color_c1}" stroke-width="12" '
        f'stroke-dasharray="{len_c1:.2f} {circumference:.2f}" stroke-dashoffset="0"/>'
        f'<path d="M 25 76 A 55 55 0 0 1 135 76" fill="none" stroke="{color_c2}" stroke-width="12" '
        f'stroke-dasharray="{len_c2:.2f} {circumference:.2f}" stroke-dashoffset="{-len_c1:.2f}"/>'
        f'<line x1="80" y1="13" x2="80" y2="25" stroke="#F8FAFC" stroke-width="2" stroke-dasharray="2,2"/>'
        f'<text x="80" y="70" text-anchor="middle" font-size="26" font-weight="800" fill="#F8FAFC" '
        f'font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif">{leader_prob:.0f}%</text>'
        f'</svg>'
    )


def compute_executive_snapshot(
    polls: Sequence[PesquisaEleitoralSchema],
    multiscope_polls: Sequence[PesquisaEleitoralSchema],
    election_date: date,
    turno_num: int,
    ano_eleicao: int,
    use_valid_votes: bool = True,
    t1_polls: Sequence[PesquisaEleitoralSchema] | None = None,
    t1_tse_result: ResultadoOficialTSESchema | None = None,
    t1_election_date: date | None = None,
) -> dict[str, Any]:
    """Calcula o snapshot analítico executivo consolidando Agregação e Modelo Preditivo.

    Args:
        polls: Lista das pesquisas registradas do turno ativo.
        multiscope_polls: Pesquisas multi-escopo (nacional, estadual e regional).
        election_date: Data oficial de realização do turno ativo.
        turno_num: Número do turno auditado (1 ou 2).
        ano_eleicao: Ano do ciclo eleitoral (ex.: 2026, 2022).
        use_valid_votes: Se True considera votos válidos; se False, votos totais.
        t1_polls: Pesquisas do 1º Turno para calibração empírica.
        t1_tse_result: Resultado oficial do 1º Turno pelo TSE.
        t1_election_date: Data oficial do 1º Turno.

    Returns:
        dict[str, Any]: Estrutura com todos os indicadores dos cards e manchete.

    Raises:
        None.
    """
    if not polls:
        return {}

    # 1. Executa o Modelo Preditivo com as pesquisas multi-escopo
    calib = None
    if turno_num == 2 and t1_polls and t1_tse_result and t1_election_date:
        calib = compute_first_round_institute_calibration(
            t1_polls, t1_tse_result, t1_election_date
        )

    config = PredictiveModelConfig.load_from_settings()
    forecast = predict_election_outcome(
        polls=multiscope_polls if multiscope_polls else polls,
        election_date=election_date,
        turno=turno_num,
        calibration_t1=calib,
        config=config,
    )

    # Identifica os dois candidatos em destaque
    top_cands = [cp.candidato for cp in forecast.candidatos if cp.candidato != "Outros"][:2]
    if len(top_cands) < 2:
        top_cands = sorted(
            list({c for p in polls for c in p.votos_validos.keys() if c != "Outros"})
        )[:2]

    c1_name = top_cands[0] if len(top_cands) > 0 else "Candidato 1"
    c2_name = top_cands[1] if len(top_cands) > 1 else "Candidato 2"

    meta1 = get_candidate_metadata(c1_name)
    meta2 = get_candidate_metadata(c2_name)

    # 2. Calcula Agregação Dinâmica das Pesquisas
    df_agg = compute_poll_aggregation_series(
        polls=polls,
        candidates=[c1_name, c2_name],
        use_valid_votes=use_valid_votes,
    )

    v1, v2 = 0.0, 0.0
    ic1_inf, ic1_sup = 0.0, 0.0
    ic2_inf, ic2_sup = 0.0, 0.0
    latest_poll_date = max(p.data_fim_campo for p in polls)

    if not df_agg.is_empty():
        max_dt = df_agg["data"].max()
        df_latest = df_agg.filter(pl.col("data") == max_dt)
        r1 = df_latest.filter(pl.col("candidato") == c1_name)
        r2 = df_latest.filter(pl.col("candidato") == c2_name)

        if not r1.is_empty():
            v1 = float(r1["media_ponderada"][0])
            ic1_inf = float(r1["ic_95_inf"][0])
            ic1_sup = float(r1["ic_95_sup"][0])
        if not r2.is_empty():
            v2 = float(r2["media_ponderada"][0])
            ic2_inf = float(r2["ic_95_inf"][0])
            ic2_sup = float(r2["ic_95_sup"][0])

    diff_pp = abs(v1 - v2)
    leader_agg_meta = meta1 if v1 >= v2 else meta2
    leader_agg_val = max(v1, v2)
    runner_agg_val = min(v1, v2)

    # Critério estatístico de empate técnico: sobreposição dos envelopes de 95%
    is_empate = max(ic1_inf, ic2_inf) <= min(ic1_sup, ic2_sup)

    # 3. Extrai probabilidades do modelo preditivo
    pred_map = {cp.candidato: cp for cp in forecast.candidatos}
    p_win_1 = pred_map.get(c1_name).probabilidade_vitoria if c1_name in pred_map else 0.0
    p_win_2 = pred_map.get(c2_name).probabilidade_vitoria if c2_name in pred_map else 0.0

    leader_pred_meta = meta1 if p_win_1 >= p_win_2 else meta2
    runner_pred_meta = meta2 if p_win_1 >= p_win_2 else meta1
    leader_pred_prob = max(p_win_1, p_win_2)
    runner_pred_prob = min(p_win_1, p_win_2)

    # Contagem de pesquisas por abrangência
    n_nacionais = sum(1 for p in polls if p.abrangencia == AbrangenciaEnum.NACIONAL)
    n_estaduais = sum(1 for p in polls if p.abrangencia == AbrangenciaEnum.ESTADUAL)

    # Manchete dinâmica
    turno_str = "1º turno" if turno_num == 1 else "2º turno"
    diff_str = _format_ptbr_num(diff_pp, 1)
    if is_empate:
        headline = f"Empate técnico, com {leader_agg_meta['short_name']} {diff_str} p.p. à frente"
    else:
        headline = (
            f"{leader_agg_meta['short_name']} lidera isolado com {diff_str} p.p. à frente"
        )

    subheadline = f"Média ponderada de todas as pesquisas de {turno_str} registradas no TSE."

    # Dados de 1º Turno (se aplicável para 2º turno)
    t1_info = ""
    if turno_num == 2 and t1_tse_result:
        res_t1 = t1_tse_result.resultado_nominal
        p1_t1 = res_t1.get(c1_name, 0.0)
        p2_t1 = res_t1.get(c2_name, 0.0)
        p1_str = _format_ptbr_num(p1_t1, 2)
        p2_str = _format_ptbr_num(p2_t1, 2)
        t1_info = (
            f"1º turno: {meta1['short_name']} {p1_str}% x {meta2['short_name']} {p2_str}%"
        )

    return {
        "headline": headline,
        "subheadline": subheadline,
        "c1_name": c1_name,
        "c2_name": c2_name,
        "meta1": meta1,
        "meta2": meta2,
        "v1": v1,
        "v2": v2,
        "ic1_inf": ic1_inf,
        "ic1_sup": ic1_sup,
        "ic2_inf": ic2_inf,
        "ic2_sup": ic2_sup,
        "diff_pp": diff_pp,
        "is_empate": is_empate,
        "leader_agg_meta": leader_agg_meta,
        "leader_agg_val": leader_agg_val,
        "runner_agg_val": runner_agg_val,
        "p_win_1": p_win_1,
        "p_win_2": p_win_2,
        "leader_pred_meta": leader_pred_meta,
        "runner_pred_meta": runner_pred_meta,
        "leader_pred_prob": leader_pred_prob,
        "runner_pred_prob": runner_pred_prob,
        "total_polls": len(polls),
        "n_nacionais": n_nacionais,
        "n_estaduais": n_estaduais,
        "latest_poll_date": latest_poll_date,
        "turno_num": turno_num,
        "ano_eleicao": ano_eleicao,
        "use_valid_votes": use_valid_votes,
        "t1_info": t1_info,
        "n_simulations": config.n_simulations,
        "calibrado_t1": calib is not None,
    }


def render_executive_story_cards(
    polls: Sequence[PesquisaEleitoralSchema],
    multiscope_polls: Sequence[PesquisaEleitoralSchema],
    election_date: date,
    turno_num: int,
    ano_eleicao: int,
    tse_result: ResultadoOficialTSESchema | None = None,
    t1_polls: Sequence[PesquisaEleitoralSchema] | None = None,
    t1_tse_result: ResultadoOficialTSESchema | None = None,
    t1_election_date: date | None = None,
) -> None:
    """Renderiza a Hero Section Executiva com manchete dinâmica e cards de síntese.

    Args:
        polls: Lista das pesquisas registradas do turno ativo.
        multiscope_polls: Pesquisas multi-escopo (nacional, estadual e regional).
        election_date: Data oficial de realização do turno ativo.
        turno_num: Número do turno auditado (1 ou 2).
        ano_eleicao: Ano do ciclo eleitoral (ex.: 2026, 2022).
        tse_result: Resultado oficial consolidado pelo TSE para o turno ativo.
        t1_polls: Pesquisas do 1º Turno para calibração empírica.
        t1_tse_result: Resultado oficial do 1º Turno pelo TSE.
        t1_election_date: Data oficial do 1º Turno.

    Returns:
        None.

    Raises:
        None.
    """
    if not polls:
        return

    # Injeção de CSS scoped para consistência e renderização imediata
    st.markdown(f"<style>{HERO_CARDS_CSS}</style>", unsafe_allow_html=True)

    # Controles rápidos de visualização (Pills)
    col_filter_space, col_filter_ctrl = st.columns([2.2, 1.0])
    with col_filter_ctrl:
        vote_mode = st.pills(
            "Base de Votos:",
            options=["Votos válidos", "Inclui indecisos"],
            default="Votos válidos",
            key=f"hero_vote_mode_{ano_eleicao}_{turno_num}",
            label_visibility="collapsed",
        )
    use_valid = vote_mode == "Votos válidos"
    label_votos = "dos votos válidos" if use_valid else "dos votos totais"

    snapshot = compute_executive_snapshot(
        polls=polls,
        multiscope_polls=multiscope_polls,
        election_date=election_date,
        turno_num=turno_num,
        ano_eleicao=ano_eleicao,
        use_valid_votes=use_valid,
        t1_polls=t1_polls,
        t1_tse_result=t1_tse_result,
        t1_election_date=t1_election_date,
    )
    if not snapshot:
        return

    # 1. Manchete Dinâmica de Storytelling
    headline_html = f"""
    <div style="margin-top: 4px; margin-bottom: 14px;">
        <div style="font-size: 26px; font-weight: 800; color: #F8FAFC; letter-spacing: -0.6px; line-height: 1.2;">
            {snapshot["headline"]}
        </div>
        <div style="font-size: 14px; color: #94A3B8; margin-top: 4px;">
            {snapshot["subheadline"]}
        </div>
    </div>
    """
    st.markdown(_clean_html(headline_html), unsafe_allow_html=True)

    # 2. Grid dos 2 Cards Executivos (Agregação vs Modelo Preditivo)
    col_card_agg, col_card_pred = st.columns([1.18, 0.82], gap="medium")

    # Proporções da barra de disputa (Tug-of-War Bar)
    v1 = snapshot["v1"]
    v2 = snapshot["v2"]
    meta1 = snapshot["meta1"]
    meta2 = snapshot["meta2"]
    tot_v = max(0.001, v1 + v2)
    w1 = (v1 / tot_v) * 100.0
    w2 = 100.0 - w1

    # Formatação numérica brasileira
    v1_str = _format_ptbr_num(v1, 1)
    v2_str = _format_ptbr_num(v2, 1)
    diff_str = _format_ptbr_num(snapshot["diff_pp"], 1)

    # Faixa de 95% do líder na agregação
    leader_meta = snapshot["leader_agg_meta"]
    if leader_meta["name"] == meta1["name"]:
        ic_inf, ic_sup = snapshot["ic1_inf"], snapshot["ic1_sup"]
    else:
        ic_inf, ic_sup = snapshot["ic2_inf"], snapshot["ic2_sup"]

    ic_inf_str = _format_ptbr_num(ic_inf, 1)
    ic_sup_str = _format_ptbr_num(ic_sup, 1)

    # Pills do Card 1
    pill_tie_class = (
        "hero-pill hero-pill-tie" if snapshot["is_empate"] else "hero-pill hero-pill-highlight"
    )
    pill_tie_text = "Empate técnico" if snapshot["is_empate"] else "Liderança fora da margem"
    pill_diff_text = f"{leader_meta['short_name']} à frente por {diff_str} p.p."
    pill_t1 = (
        f'<span class="hero-pill">{snapshot["t1_info"]}</span>' if snapshot["t1_info"] else ""
    )
    pill_polls_count = (
        f'<span class="hero-pill">{snapshot["total_polls"]} pesquisas registradas</span>'
    )

    card_agg_html = f"""
    <div class="hero-card">
        <div class="hero-card-header">
            <span>Média Ponderada das Pesquisas (Nowcasting)</span>
            <span title="Média com decaimento exponencial temporal (meia-vida de 14 dias), ponderada por tamanho da amostra e qualidade metodológica.">ⓘ</span>
        </div>
        <div class="hero-candidates-row">
            <div style="display: flex; align-items: center; gap: 12px;">
                {render_candidate_avatar(meta1, size=46)}
                <div>
                    <div style="display: flex; align-items: baseline; gap: 6px;">
                        <span class="hero-cand-name">{meta1["name"]}</span>
                        <span class="hero-cand-party">{meta1["party"]}</span>
                    </div>
                    <div class="hero-cand-val" style="color: {meta1["color"]};">
                        {v1_str}<span style="font-size: 20px;">%</span>
                    </div>
                    <div class="hero-cand-val-sub">{label_votos}</div>
                </div>
            </div>
            <div class="hero-vs-badge">×</div>
            <div style="display: flex; align-items: center; gap: 12px; text-align: right; flex-direction: row-reverse;">
                {render_candidate_avatar(meta2, size=46)}
                <div>
                    <div style="display: flex; align-items: baseline; gap: 6px; justify-content: flex-end;">
                        <span class="hero-cand-name">{meta2["name"]}</span>
                        <span class="hero-cand-party">{meta2["party"]}</span>
                    </div>
                    <div class="hero-cand-val" style="color: {meta2["color"]};">
                        {v2_str}<span style="font-size: 20px;">%</span>
                    </div>
                    <div class="hero-cand-val-sub">{label_votos}</div>
                </div>
            </div>
        </div>
        <div class="hero-bar-track">
            <div class="hero-bar-split">
                <div style="width: {w1:.1f}%; background-color: {meta1["color"]}; height: 100%;"></div>
                <div style="width: {w2:.1f}%; background-color: {meta2["color"]}; height: 100%;"></div>
            </div>
            <div class="hero-bar-threshold" title="Maioria Absoluta (50%)"></div>
        </div>
        <div class="hero-bar-labels">
            <span>Faixa de 95%: <b>{ic_inf_str}%</b> a <b>{ic_sup_str}%</b> para {leader_meta["short_name"]}</span>
            <span style="font-weight: 700; color: #CBD5E1;">50%</span>
        </div>
        <div class="hero-pills-row">
            <span class="{pill_tie_class}">{pill_tie_text}</span>
            <span class="hero-pill">{pill_diff_text}</span>
            {pill_t1}
            {pill_polls_count}
        </div>
    </div>
    """

    with col_card_agg:
        st.markdown(_clean_html(card_agg_html), unsafe_allow_html=True)

    # Card 2: Chance de Vitória (Modelo Preditivo)
    leader_pred_meta = snapshot["leader_pred_meta"]
    runner_pred_meta = snapshot["runner_pred_meta"]
    leader_prob = snapshot["leader_pred_prob"]
    runner_prob = snapshot["runner_pred_prob"]

    p1_ratio = snapshot["p_win_1"]
    p2_ratio = snapshot["p_win_2"]
    gauge_svg = render_gauge_svg(
        p_c1=p1_ratio,
        p_c2=p2_ratio,
        meta_c1=meta1,
        meta_c2=meta2,
        leader_prob=leader_prob,
    )

    n_sim_str = _format_ptbr_int(snapshot["n_simulations"])
    calib_pill = (
        '<span class="hero-pill hero-pill-highlight">Calibração Pós-1º Turno</span>'
        if snapshot["calibrado_t1"]
        else '<span class="hero-pill">Agregado Multi-Escopo</span>'
    )

    card_pred_html = f"""
    <div class="hero-card">
        <div class="hero-card-header">
            <span>Chance de Vitória Hoje</span>
            <span title="Probabilidade preditiva calculada por simulação estocástica de Monte Carlo (distribuição Student-t, nu=5) pós-estratificada e calibrada.">ⓘ</span>
        </div>
        <div class="hero-gauge-container">
            {gauge_svg}
            <div class="hero-gauge-summary">
                <span style="color: {leader_pred_meta["color"]}; font-weight: 800;">{leader_prob:.0f}%</span> {leader_pred_meta["short_name"]}
                <span style="color: #64748B; font-weight: 400; margin: 0 4px;">·</span>
                <span style="color: {runner_pred_meta["color"]}; font-weight: 800;">{runner_prob:.0f}%</span> {runner_pred_meta["short_name"]}
            </div>
            <div class="hero-gauge-subtext">
                Em quantos de {n_sim_str} cenários simulados cada candidato ultrapassa 50% dos votos válidos.
            </div>
        </div>
        <div class="hero-pills-row" style="justify-content: center; margin-top: 18px;">
            {calib_pill}
            <span class="hero-pill">{n_sim_str} simulações MLE</span>
        </div>
    </div>
    """

    with col_card_pred:
        st.markdown(_clean_html(card_pred_html), unsafe_allow_html=True)

    # 3. Micro-transição suave convidando à auditoria detalhada nos 7 Atos
    callout_html = """
    <div style="display: flex; align-items: center; justify-content: space-between;
                background-color: #15181E; border: 1px dashed #282D37; border-radius: 8px;
                padding: 8px 16px; margin-top: 14px; margin-bottom: 18px;">
        <span style="color: #94A3B8; font-size: 13px;">
            🔬 <b>Auditoria Científica Completa:</b> Explore abaixo o memorial metodológico, dinâmica temporal, rejeição e veredito científico em 7 Atos.
        </span>
        <span style="color: #38BDF8; font-size: 12px; font-weight: 600;">
            Atos 1 a 7 &darr;
        </span>
    </div>
    """
    st.markdown(_clean_html(callout_html), unsafe_allow_html=True)
