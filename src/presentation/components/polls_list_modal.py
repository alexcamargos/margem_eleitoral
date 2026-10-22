"""Componente visual de listagem e auditoria detalhada de pesquisas eleitorais.

Exibe um modal/diálogo interativo contendo todas as pesquisas em análise para o ciclo,
cargo e turno selecionados, com cartões colapsáveis (accordions) fiéis ao padrão
de visualização do agregador (conforme referência visual do projeto).
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Sequence

import streamlit as st

from src.analytics.aggregator_model import calculate_poll_weight
from src.presentation.components.executive_story_cards import CANDIDATE_METADATA_REGISTRY
from src.transformations.schemas import MetodologiaEnum, PesquisaEleitoralSchema

MESES_PT: dict[int, str] = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}

METODOLOGIA_LABEL_MAP: dict[str, str] = {
    "ONLINE": "online",
    "TELEFONICA_CATI": "telefone (CATI)",
    "TELEFONICA_URA": "telefone (URA)",
    "PRESENCIAL_DOMICILIAR": "presencial domiciliar",
    "PRESENCIAL_FLUXO": "presencial (pontos de fluxo)",
}

POLLS_MODAL_CSS = """
<style>
.poll-card {
    background-color: #181B20;
    border: 1px solid #282D37;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 16px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    box-sizing: border-box;
}
.poll-card-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 2px;
}
.poll-inst-name {
    font-size: 19px;
    font-weight: 700;
    color: #F8FAFC;
    letter-spacing: -0.3px;
}
.poll-field-period {
    font-size: 13px;
    color: #94A3B8;
}
.poll-site-since {
    font-size: 12px;
    color: #64748B;
    margin-bottom: 12px;
}
.poll-bar-track {
    width: 100%;
    height: 28px;
    border-radius: 6px;
    overflow: hidden;
    display: flex;
    margin-bottom: 12px;
    background-color: #242933;
}
.poll-bar-seg {
    display: flex;
    align-items: center;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 13px;
    height: 100%;
    box-sizing: border-box;
}
.poll-bar-seg-left {
    padding-left: 10px;
    justify-content: flex-start;
}
.poll-bar-seg-right {
    padding-right: 10px;
    justify-content: flex-end;
}
.poll-bar-seg-center {
    justify-content: center;
}
.poll-metrics-row {
    display: flex;
    justify-content: space-between;
    padding-bottom: 10px;
    border-bottom: 1px dotted #282D37;
    margin-bottom: 10px;
}
.poll-metric-col {
    flex: 1;
}
.poll-metric-lbl {
    font-size: 11.5px;
    color: #94A3B8;
    margin-bottom: 2px;
}
.poll-metric-val {
    font-size: 17px;
    font-weight: 700;
    color: #F8FAFC;
}
.poll-details {
    margin-top: 10px;
}
.poll-summary {
    cursor: pointer;
    padding: 6px 12px;
    background-color: #1F242D;
    border: 1px solid #333A48;
    border-radius: 6px;
    color: #CBD5E1;
    font-size: 12.5px;
    font-weight: 600;
    list-style: none;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    user-select: none;
    transition: background-color 0.15s ease, border-color 0.15s ease;
}
.poll-summary:hover {
    background-color: #2A313C;
    border-color: #38BDF8;
    color: #F8FAFC;
}
.poll-summary::-webkit-details-marker {
    display: none;
}
.poll-details[open] .poll-summary-arrow {
    transform: rotate(90deg);
}
.poll-summary-arrow {
    display: inline-block;
    transition: transform 0.2s ease;
    font-size: 10px;
}
.poll-details-body {
    margin-top: 12px;
    background-color: #14171C;
    border: 1px solid #282D37;
    border-radius: 6px;
    padding: 12px 16px;
}
.poll-detail-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px solid rgba(40, 45, 55, 0.6);
    font-size: 13px;
}
.poll-detail-row:last-child {
    border-bottom: none;
}
.poll-detail-label {
    color: #94A3B8;
}
.poll-detail-value {
    color: #F8FAFC;
    font-weight: 500;
    text-align: right;
}
.poll-criteria-banner {
    background-color: #181B20;
    border: 1px solid #282D37;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 20px;
    color: #94A3B8;
    font-size: 13px;
    line-height: 1.55;
}
.poll-criteria-banner b {
    color: #F1F5F9;
}
.poll-criteria-banner a {
    color: #38BDF8;
    text-decoration: underline;
}
.poll-link {
    color: #38BDF8 !important;
    text-decoration: underline !important;
}
</style>
"""


def _load_extra_feed_metadata(year: int = 2026) -> dict[str, Any]:
    """Carrega metadados complementares do feed de pesquisas publicadas se disponível.

    Args:
        year: Ano eleitoral analisado (default: 2026).

    Returns:
        dict[str, Any]: Mapeamento de registros e coeficientes de calibração empírica.

    Raises:
        None.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    feed_path = repo_root / "data" / "raw" / str(year) / f"feed_pesquisas_publicadas_{year}.json"

    if not feed_path.exists():
        return {"pesquisas_by_tse": {}, "vies_by_inst": {}, "fator_vies": 0.5}

    try:
        with open(feed_path, encoding="utf-8") as f:
            feed_dict = json.load(f)

        pesquisas_by_tse = {
            str(p.get("registro_tse", "")).strip(): p
            for p in feed_dict.get("pesquisas", [])
            if "registro_tse" in p
        }

        vies_info = feed_dict.get("vies_1t", {})
        fator_vies = float(vies_info.get("fator", 0.5))
        vies_by_inst = {
            str(line.get("instituto", "")).strip(): float(line.get("vies", 0.0))
            for line in vies_info.get("linhas", [])
            if "instituto" in line
        }

        return {
            "pesquisas_by_tse": pesquisas_by_tse,
            "vies_by_inst": vies_by_inst,
            "fator_vies": fator_vies,
        }
    except (OSError, json.JSONDecodeError, ValueError):
        return {"pesquisas_by_tse": {}, "vies_by_inst": {}, "fator_vies": 0.5}


def _format_field_period_pt(d_ini: date, d_fim: date) -> str:
    """Formata o intervalo de datas do período de campo em português fluido.

    Args:
        d_ini: Data inicial do campo de entrevistas.
        d_fim: Data final do campo de entrevistas.

    Returns:
        str: String formatada (ex.: 'campo de 16 a 20 de outubro').

    Raises:
        None.
    """
    if d_ini == d_fim:
        mes = MESES_PT.get(d_fim.month, f"mês {d_fim.month}")
        return f"campo em {d_fim.day} de {mes}"

    if d_ini.month == d_fim.month and d_ini.year == d_fim.year:
        mes = MESES_PT.get(d_fim.month, f"mês {d_fim.month}")
        return f"campo de {d_ini.day} a {d_fim.day} de {mes}"

    mes_ini = MESES_PT.get(d_ini.month, f"mês {d_ini.month}")
    mes_fim = MESES_PT.get(d_fim.month, f"mês {d_fim.month}")
    return f"campo de {d_ini.day} de {mes_ini} a {d_fim.day} de {mes_fim}"


def _format_site_since(adicionada_iso: str | None, data_div: date) -> str:
    """Formata a anotação de data/hora de publicação ou inclusão no agregador.

    Args:
        adicionada_iso: Timestamp ISO 8601 de inclusão no site se disponível.
        data_div: Data de divulgação oficial da pesquisa.

    Returns:
        str: String formatada (ex.: 'No site desde 21/10 às 07h00' ou 'Divulgada em 21/10').

    Raises:
        None.
    """
    if adicionada_iso:
        try:
            # Trata formato ISO com offset timezone
            dt_str = adicionada_iso.replace("Z", "+00:00")
            dt = datetime.fromisoformat(dt_str)
            return f"No site desde {dt.day:02d}/{dt.month:02d} às {dt.hour:02d}h{dt.minute:02d}"
        except (ValueError, TypeError):
            pass

    return f"Divulgada em {data_div.day:02d}/{data_div.month:02d}"


def _clean_html_str(html_content: str) -> str:
    """Higieniza código HTML removendo recuos excessivos para evitar blocos code CommonMark.

    Args:
        html_content: String contendo marcação HTML com possíveis espaços no início das linhas.

    Returns:
        str: HTML sem recuos de quatro ou mais espaços no início de linhas.

    Raises:
        None.
    """
    return "\n".join(line.lstrip() for line in html_content.splitlines())


def _compute_poll_weights(
    polls: Sequence[PesquisaEleitoralSchema],
    half_life_days: float = 7.0,
) -> dict[str, float]:
    """Calcula o percentual relativo de peso de cada pesquisa na amostra atual.

    Wi = w_tempo * w_qualidade * sqrt(n), com decaimento exponencial temporal.

    Args:
        polls: Lista de pesquisas a avaliar.
        half_life_days: Meia-vida em dias do decaimento temporal (default: 7.0).

    Returns:
        dict[str, float]: Mapeamento do id_registro_tse para seu peso relativo em percentual (0 a 100).

    Raises:
        None.
    """
    if not polls:
        return {}

    ref_date = max(p.data_fim_campo for p in polls)
    raw_weights = {
        p.id_registro_tse: calculate_poll_weight(p, ref_date, half_life_days=half_life_days)
        for p in polls
    }
    sum_w = sum(raw_weights.values())

    if sum_w <= 0.0:
        return {p.id_registro_tse: 0.0 for p in polls}

    return {k: (w / sum_w) * 100.0 for k, w in raw_weights.items()}


def _build_poll_card_html(
    poll: PesquisaEleitoralSchema,
    weight_pct: float,
    extra_feed_data: dict[str, Any],
    turno_num: int,
) -> str:
    """Gera o HTML estruturado de um cartão de pesquisa alinhado à referência de UI/UX.

    Args:
        poll: Contrato de dados da pesquisa eleitoral.
        weight_pct: Peso relativo no agregador em percentual.
        extra_feed_data: Dicionário contendo dados extras do feed de pesquisas e viés.
        turno_num: Turno eleitoral (1 ou 2).

    Returns:
        str: Código HTML pronto para renderização via st.markdown.

    Raises:
        None.
    """
    pesquisas_by_tse = extra_feed_data.get("pesquisas_by_tse", {})
    vies_by_inst = extra_feed_data.get("vies_by_inst", {})
    fator_vies = extra_feed_data.get("fator_vies", 0.5)

    feed_item = pesquisas_by_tse.get(poll.id_registro_tse, {})
    adicionada_iso = feed_item.get("adicionada_em")

    field_period_str = _format_field_period_pt(poll.data_inicio_campo, poll.data_fim_campo)
    site_since_str = _format_site_since(adicionada_iso, poll.data_divulgacao)

    # Identifica candidatos ordenados por percentual de votos válidos
    validos = poll.votos_validos
    totais = poll.votos_totais

    cands_sorted = sorted(validos.keys(), key=lambda c: validos[c], reverse=True)

    # Definição das cores e dados para a barra de progresso
    bar_html_parts: list[str] = []
    c1_name = cands_sorted[0] if cands_sorted else "Candidato 1"
    c2_name = cands_sorted[1] if len(cands_sorted) > 1 else "Candidato 2"

    c1_meta = CANDIDATE_METADATA_REGISTRY.get(c1_name, {"color": "#EF4444", "short_name": c1_name})
    c2_meta = CANDIDATE_METADATA_REGISTRY.get(c2_name, {"color": "#3B82F6", "short_name": c2_name})

    c1_val = validos.get(c1_name, 0.0)
    c2_val = validos.get(c2_name, 0.0)

    # Cálculo da Correção de Viés (House Effect do 1º turno)
    # Se vies foi positivo no 1º turno (superestimou c1), correção é negativa.
    raw_vies = vies_by_inst.get(poll.instituto_nome_fantasia)
    if raw_vies is not None:
        bias_corr_pp = -float(raw_vies * fator_vies * 100.0)
    else:
        bias_corr_pp = 0.0

    sign_str = "+" if bias_corr_pp > 0 else ""
    bias_corr_str = f"{sign_str}{bias_corr_pp:.1f} p.p." if bias_corr_pp != 0.0 else "0,0 p.p."

    # Cálculo do 'Candidato usado' no agregador
    # Se houver rejeição, mistura 50% de votos válidos com 50% do voto potencial
    rejeicao_dict = poll.rejeicao
    rej_str = "não divulgada"
    voto_potencial_str = "-"
    c1_usado_val = c1_val + bias_corr_pp

    if rejeicao_dict and c1_name in rejeicao_dict and c2_name in rejeicao_dict:
        r1 = rejeicao_dict[c1_name]
        r2 = rejeicao_dict[c2_name]
        c1_short = c1_meta.get("short_name", c1_name)
        c2_short = c2_meta.get("short_name", c2_name)
        rej_str = f"{c1_short} {r1:.0f}% x {c2_short} {r2:.0f}%"

        nao_rej_1 = max(0.1, 100.0 - r1)
        nao_rej_2 = max(0.1, 100.0 - r2)
        pot_1 = (nao_rej_1 / (nao_rej_1 + nao_rej_2)) * 100.0
        voto_potencial_str = f"{pot_1:.1f}%"
        # Mistura 50% de intenção (já corrigida de viés) + 50% voto potencial
        c1_usado_val = 0.5 * (c1_val + bias_corr_pp) + 0.5 * pot_1

    # Renderização da barra bipartida (2º turno) ou empilhada (1º turno)
    if turno_num == 2 and len(cands_sorted) >= 2:
        tot_pair = c1_val + c2_val
        w1 = (c1_val / tot_pair * 100.0) if tot_pair > 0 else 50.0
        w2 = 100.0 - w1

        bar_html_parts.append(
            f'<div class="poll-bar-track">'
            f'<div class="poll-bar-seg poll-bar-seg-left" style="width: {w1:.1f}%; background-color: {c1_meta["color"]};">'
            f"{c1_val:.1f}%"
            f"</div>"
            f'<div class="poll-bar-seg poll-bar-seg-right" style="width: {w2:.1f}%; background-color: {c2_meta["color"]};">'
            f"{c2_val:.1f}%"
            f"</div>"
            f"</div>"
        )
    else:
        # 1º Turno: barra empilhada proporcional com todos os candidatos
        bar_html_parts.append('<div class="poll-bar-track">')
        sum_cands = sum(validos.values()) or 100.0
        for cand in cands_sorted[:6]:
            pct = validos[cand]
            width = (pct / sum_cands) * 100.0
            c_meta = CANDIDATE_METADATA_REGISTRY.get(cand, {"color": "#64748B"})
            label = f"{pct:.1f}%" if width >= 10.0 else ""
            bar_html_parts.append(
                f'<div class="poll-bar-seg poll-bar-seg-center" style="width: {width:.1f}%; background-color: {c_meta["color"]};" title="{cand}: {pct:.1f}%">'
                f"{label}"
                f"</div>"
            )
        bar_html_parts.append("</div>")

    # Linha de métricas resumo
    c1_display = c1_meta.get("short_name", c1_name)
    metric_label_usado = f"{c1_display} usado" if turno_num == 2 else f"{c1_display} válidos"
    metric_val_usado = f"{c1_usado_val:.1f}%" if turno_num == 2 else f"{c1_val:.1f}%"

    # Construção do 'Divulgado como'
    if turno_num == 2 and len(cands_sorted) >= 2:
        tot_c1 = totais.get(c1_name, 0.0)
        tot_c2 = totais.get(c2_name, 0.0)
        divulgado_como = (
            f"{c1_display} {tot_c1:.0f}% x {c2_meta.get('short_name', c2_name)} {tot_c2:.0f}%"
        )
    else:
        parts_tot = [f"{c}: {totais.get(c, 0.0):.1f}%" for c in cands_sorted[:4]]
        divulgado_como = " | ".join(parts_tot)
        if poll.percentual_brancos_nulos > 0:
            divulgado_como += f" (Brancos/Nulos: {poll.percentual_brancos_nulos:.1f}%)"
        if poll.percentual_indecisos > 0:
            divulgado_como += f" (Indecisos: {poll.percentual_indecisos:.1f}%)"

    # Válidos detalhado
    if turno_num == 2 and len(cands_sorted) >= 2:
        validos_detalhe = f"{c1_val:.1f}%"
    else:
        validos_detalhe = " | ".join([f"{c}: {validos[c]:.1f}%" for c in cands_sorted[:4]])

    # Links para Fontes
    fontes_links: list[str] = []
    raw_urls_feed = feed_item.get("urls", "")
    if raw_urls_feed:
        url_list = str(raw_urls_feed).split()
        for i, u in enumerate(url_list[:2], 1):
            fontes_links.append(f'<a href="{u}" target="_blank" class="poll-link">fonte {i} ↗</a>')
    elif poll.url_fonte_publicacao:
        fontes_links.append(
            f'<a href="{poll.url_fonte_publicacao}" target="_blank" class="poll-link">fonte 1 ↗</a>'
        )

    if poll.url_tse_pesqele:
        fontes_links.append(
            f'<a href="{poll.url_tse_pesqele}" target="_blank" class="poll-link">registro TSE ↗</a>'
        )

    fontes_html = " &nbsp;|&nbsp; ".join(fontes_links) if fontes_links else "Não informada"

    metodologia_val = (
        poll.metodologia.value
        if isinstance(poll.metodologia, MetodologiaEnum)
        else str(poll.metodologia)
    )
    modo_coleta_str = METODOLOGIA_LABEL_MAP.get(metodologia_val, metodologia_val.lower())

    # Formata número de entrevistados com separador de milhar (ponto)
    amostra_formatada = f"{poll.tamanho_amostra:,}".replace(",", ".")

    # Link TSE no valor do registro
    if poll.url_tse_pesqele:
        registro_tse_html = (
            f'<a href="{poll.url_tse_pesqele}" target="_blank" class="poll-link">'
            f"{poll.id_registro_tse} ↗"
            f"</a>"
        )
    else:
        registro_tse_html = poll.id_registro_tse

    card_html = f"""
    <div class="poll-card">
        <div class="poll-card-header">
            <div class="poll-inst-name">{poll.instituto_nome_fantasia}</div>
            <div class="poll-field-period">{field_period_str}</div>
        </div>
        <div class="poll-site-since">{site_since_str}</div>

        {"".join(bar_html_parts)}

        <div class="poll-metrics-row">
            <div class="poll-metric-col">
                <div class="poll-metric-lbl">Entrevistados</div>
                <div class="poll-metric-val">{amostra_formatada}</div>
            </div>
            <div class="poll-metric-col">
                <div class="poll-metric-lbl">{metric_label_usado}</div>
                <div class="poll-metric-val">{metric_val_usado}</div>
            </div>
            <div class="poll-metric-col">
                <div class="poll-metric-lbl">Peso</div>
                <div class="poll-metric-val">{weight_pct:.0f}%</div>
            </div>
        </div>

        <details class="poll-details">
            <summary class="poll-summary">
                <span class="poll-summary-arrow">▶</span>
                <span>Todos os detalhes</span>
            </summary>
            <div class="poll-details-body">
                <div class="poll-detail-row">
                    <span class="poll-detail-label">Registro TSE</span>
                    <span class="poll-detail-value">{registro_tse_html}</span>
                </div>
                <div class="poll-detail-row">
                    <span class="poll-detail-label">Campo</span>
                    <span class="poll-detail-value">{field_period_str.replace("campo ", "")}</span>
                </div>
                <div class="poll-detail-row">
                    <span class="poll-detail-label">Divulgada em</span>
                    <span class="poll-detail-value">{poll.data_divulgacao.day:02d}/{poll.data_divulgacao.month:02d}/{poll.data_divulgacao.year}</span>
                </div>
                <div class="poll-detail-row">
                    <span class="poll-detail-label">No site desde</span>
                    <span class="poll-detail-value">{site_since_str.replace("No site desde ", "").replace("Divulgada em ", "")}</span>
                </div>
                <div class="poll-detail-row">
                    <span class="poll-detail-label">Divulgado como</span>
                    <span class="poll-detail-value">{divulgado_como}</span>
                </div>
                <div class="poll-detail-row">
                    <span class="poll-detail-label">{c1_display} válidos</span>
                    <span class="poll-detail-value">{validos_detalhe}</span>
                </div>
                <div class="poll-detail-row">
                    <span class="poll-detail-label">Correção de viés</span>
                    <span class="poll-detail-value">{bias_corr_str}</span>
                </div>
                <div class="poll-detail-row">
                    <span class="poll-detail-label">Rejeição {c1_display} x {c2_meta.get("short_name", c2_name)}</span>
                    <span class="poll-detail-value">{rej_str}</span>
                </div>
                <div class="poll-detail-row">
                    <span class="poll-detail-label">Voto potencial (mistura)</span>
                    <span class="poll-detail-value">{voto_potencial_str}</span>
                </div>
                <div class="poll-detail-row">
                    <span class="poll-detail-label">Modo de coleta</span>
                    <span class="poll-detail-value">{modo_coleta_str}</span>
                </div>
                <div class="poll-detail-row">
                    <span class="poll-detail-label">{metric_label_usado}</span>
                    <span class="poll-detail-value">{metric_val_usado}</span>
                </div>
                <div class="poll-detail-row">
                    <span class="poll-detail-label">Margem de erro declarada</span>
                    <span class="poll-detail-value">&plusmn;{poll.margem_erro_declarada:.1f} p.p. (95% confiança)</span>
                </div>
                <div class="poll-detail-row">
                    <span class="poll-detail-label">Fontes</span>
                    <span class="poll-detail-value">{fontes_html}</span>
                </div>
            </div>
        </details>
    </div>
    """

    return _clean_html_str(card_html)


def render_polls_list_content(
    polls: Sequence[PesquisaEleitoralSchema],
    ano_eleicao: int = 2026,
    turno_num: int = 2,
    cargo: str = "Presidente da República",
) -> None:
    """Renderiza a lista completa de pesquisas auditadas dentro do modal ou container.

    Args:
        polls: Coleção de pesquisas eleitorais registradas e em análise.
        ano_eleicao: Ano do ciclo eleitoral (ex.: 2026, 2022).
        turno_num: Turno selecionado (1 ou 2).
        cargo: Cargo eletivo em auditoria (default: 'Presidente da República').

    Returns:
        None.

    Raises:
        None.
    """
    st.markdown(POLLS_MODAL_CSS, unsafe_allow_html=True)

    turno_label = "1º Turno" if turno_num == 1 else "2º Turno"

    # Banner de critérios metodológicos de inclusão
    st.markdown(
        f"""
        <div class="poll-criteria-banner">
            Só entram pesquisas nacionais, de <b>{turno_label}</b>, registradas no TSE, com números conferidos na fonte.
            Se o registro citado na divulgação ainda não aparece no cadastro aberto do TSE, a pesquisa entra como pendente e sai se ele não aparecer em até 5 dias.
            O peso de cada uma é proporcional ao número de entrevistados e cai pela metade a cada 7 dias desde o fim do campo
            (<i>pesquisas mais perto da eleição erram menos</i>).
            Quando a pesquisa divulga a rejeição, o percentual usado mistura a intenção de voto e o voto potencial
            (quem não rejeita cada candidato): metade vem do voto potencial.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not polls:
        st.info(
            f"Nenhuma pesquisa registrada encontrada para {cargo} no {turno_label} de {ano_eleicao}."
        )
        return

    # Controles de busca e ordenação
    col_search, col_sort = st.columns([2, 1])
    with col_search:
        search_query = (
            st.text_input(
                "Filtrar por Instituto ou Registro TSE:",
                placeholder="Ex.: Palver, Datafolha, BR-04612...",
                key="poll_modal_search_input",
            )
            .strip()
            .lower()
        )

    with col_sort:
        sort_mode = st.selectbox(
            "Ordenar por:",
            [
                "Mais recentes (fim de campo)",
                "Mais antigas (fim de campo)",
                "Maior número de entrevistados",
                "Maior peso no agregador",
            ],
            index=0,
            key="poll_modal_sort_select",
        )

    # Filtragem e cálculo de pesos
    extra_feed_data = _load_extra_feed_metadata(year=ano_eleicao)
    weights_map = _compute_poll_weights(polls, half_life_days=7.0)

    filtered_polls = [
        p
        for p in polls
        if not search_query
        or search_query in p.instituto_nome_fantasia.lower()
        or search_query in p.id_registro_tse.lower()
    ]

    # Aplicação de ordenação
    if sort_mode == "Mais recentes (fim de campo)":
        filtered_polls = sorted(
            filtered_polls,
            key=lambda x: (x.data_fim_campo, x.data_divulgacao),
            reverse=True,
        )
    elif sort_mode == "Mais antigas (fim de campo)":
        filtered_polls = sorted(
            filtered_polls,
            key=lambda x: (x.data_fim_campo, x.data_divulgacao),
            reverse=False,
        )
    elif sort_mode == "Maior número de entrevistados":
        filtered_polls = sorted(filtered_polls, key=lambda x: x.tamanho_amostra, reverse=True)
    elif sort_mode == "Maior peso no agregador":
        filtered_polls = sorted(
            filtered_polls,
            key=lambda x: weights_map.get(x.id_registro_tse, 0.0),
            reverse=True,
        )

    # Indicador de quantidade exibida
    st.markdown(
        f"<div style='color: #94A3B8; font-size: 13px; margin: 4px 0 16px 0;'>"
        f"Exibindo <b>{len(filtered_polls)}</b> de <b>{len(polls)}</b> pesquisas em análise para {cargo} ({ano_eleicao} — {turno_label}):"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Renderiza cada cartão em sequência
    cards_html_list: list[str] = []
    for poll in filtered_polls:
        w_pct = weights_map.get(poll.id_registro_tse, 0.0)
        card_html = _build_poll_card_html(
            poll=poll,
            weight_pct=w_pct,
            extra_feed_data=extra_feed_data,
            turno_num=turno_num,
        )
        cards_html_list.append(card_html)

    # Renderização consolidada via markdown com unsafe_allow_html
    st.markdown("".join(cards_html_list), unsafe_allow_html=True)


if hasattr(st, "dialog"):

    @st.dialog("Pesquisas Eleitorais em Análise", width="large")
    def render_polls_modal(
        polls: Sequence[PesquisaEleitoralSchema],
        ano_eleicao: int = 2026,
        turno_num: int = 2,
        cargo: str = "Presidente da República",
    ) -> None:
        """Abre a janela modal interativa com os cartões colapsáveis das pesquisas.

        Args:
            polls: Sequência de pesquisas registradas sob análise.
            ano_eleicao: Ano do ciclo eleitoral (ex.: 2026, 2022).
            turno_num: Turno selecionado (1 ou 2).
            cargo: Cargo eletivo em auditoria (default: 'Presidente da República').

        Returns:
            None.

        Raises:
            None.
        """
        render_polls_list_content(
            polls=polls,
            ano_eleicao=ano_eleicao,
            turno_num=turno_num,
            cargo=cargo,
        )

else:

    def render_polls_modal(
        polls: Sequence[PesquisaEleitoralSchema],
        ano_eleicao: int = 2026,
        turno_num: int = 2,
        cargo: str = "Presidente da República",
    ) -> None:
        """Renderiza diretamente os cartões em container (fallback se st.dialog não suportado).

        Args:
            polls: Sequência de pesquisas registradas sob análise.
            ano_eleicao: Ano do ciclo eleitoral (ex.: 2026, 2022).
            turno_num: Turno selecionado (1 ou 2).
            cargo: Cargo eletivo em auditoria (default: 'Presidente da República').

        Returns:
            None.

        Raises:
            None.
        """
        render_polls_list_content(
            polls=polls,
            ano_eleicao=ano_eleicao,
            turno_num=turno_num,
            cargo=cargo,
        )
