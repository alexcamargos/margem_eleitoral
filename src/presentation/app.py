"""Aplicação Principal de Auditoria e Storytelling de Pesquisas Eleitorais (Margem Eleitoral).

Ponto de entrada Streamlit com suporte a navegação por Atos, visualização analítica
no padrão dark mode da referência (Plano Político), e atualização contínua para múltiplos ciclos eleitorais.
"""

import sys
from pathlib import Path

import polars as pl
import streamlit as st
from streamlit.web import cli as stcli

from src.ingestion.data_loader import (
    get_election_dataset,
    get_election_date,
    get_tse_registration_census,
)
from src.presentation.components.documentation_modal import render_documentation_modal
from src.presentation.components.executive_story_cards import render_executive_story_cards
from src.presentation.story_acts.act1_uncertainty import render_act1
from src.presentation.story_acts.act2_election_film import render_act2
from src.presentation.story_acts.act3_rejection import render_act3
from src.presentation.story_acts.act4_eve_clash import render_act4
from src.presentation.story_acts.act5_error_anatomy import render_act5
from src.presentation.story_acts.act6_scientific_verdict import render_act6
from src.presentation.story_acts.act7_predictive_forecast import render_act7


def init_session_state() -> None:
    """Inicializa as estruturas mutáveis de sincronização na sessão do Streamlit.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    if "polls_synced_r2" not in st.session_state:
        st.session_state["polls_synced_r2"] = False


def apply_custom_css() -> None:
    """Aplica o estilo CSS dark mode customizado fiel à identidade visual de referência.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    st.markdown(
        """
        <style>
        /* Fundo geral e tipografia */
        .stApp {
            background-color: #121417;
            color: #E2E8F0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        /* Cabeçalho superior e breadcrumbs */
        .breadcrumb-text {
            color: #94A3B8;
            font-size: 13px;
            margin-bottom: 6px;
        }
        .main-header-title {
            font-size: 28px;
            font-weight: 700;
            color: #F8FAFC;
            margin-bottom: 18px;
            letter-spacing: -0.5px;
        }

        /* Banner de contexto oficial da eleição */
        .tse-summary-card {
            background-color: #181B20;
            border: 1px solid #282D37;
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 22px;
        }
        .tse-summary-title {
            font-size: 16px;
            font-weight: 700;
            color: #F1F5F9;
            margin-bottom: 6px;
        }
        .tse-summary-stats {
            color: #94A3B8;
            font-size: 13.5px;
            line-height: 1.5;
        }

        /* Ajustes de contraste para alertas, métricas, widgets e código inline no dark mode */
        div[data-testid="stAlert"] {
            color: #F8FAFC !important;
            border-radius: 6px;
        }
        div[data-testid="stAlert"] p {
            color: #F8FAFC !important;
            font-size: 13.5px;
        }
        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricLabel"] p {
            color: #CBD5E1 !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }
        div[data-testid="stMetricValue"] {
            color: #F8FAFC !important;
            font-size: 26px !important;
            font-weight: 700 !important;
        }
        section[data-testid="stSidebar"] {
            background-color: #181B20 !important;
            border-right: 1px solid #282D37 !important;
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span {
            color: #E2E8F0;
        }
        .stApp div[data-testid="stWidgetLabel"] p,
        .stApp div[data-testid="stRadio"] label p,
        .stApp div[data-testid="stRadio"] div[role="radiogroup"] p,
        .stApp div[data-testid="stCheckbox"] label span,
        .stApp div[data-testid="stCheckbox"] p,
        section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] p,
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label p {
            color: #E2E8F0 !important;
            font-weight: 500 !important;
        }
        .stApp div[data-testid="stCaptionContainer"] p {
            color: #94A3B8 !important;
        }
        .stApp code {
            background-color: #1E242C !important;
            color: #38BDF8 !important;
            border: 1px solid #282D37 !important;
            padding: 2px 6px !important;
            border-radius: 4px !important;
            font-size: 13px !important;
        }
        div[data-testid="stExpander"] details {
            background-color: #181B20 !important;
            border: 1px solid #282D37 !important;
            border-radius: 8px !important;
        }
        div[data-testid="stExpander"] summary p {
            color: #F1F5F9 !important;
            font-weight: 600 !important;
            font-size: 14px !important;
        }

        /* Ajustes dos botões e abas */
        .stTabs [data-baseweb="tab-list"],
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 6px !important;
            border-bottom: 1px solid #282D37 !important;
        }
        .stTabs [data-baseweb="tab"],
        button[data-baseweb="tab"] {
            background-color: #181B20 !important;
            border: 1px solid #282D37 !important;
            border-radius: 6px 6px 0 0 !important;
            color: #CBD5E1 !important;
            padding: 8px 14px !important;
            font-weight: 600 !important;
            font-size: 13px !important;
        }
        .stTabs [data-baseweb="tab"] p,
        button[data-baseweb="tab"] p {
            color: #CBD5E1 !important;
            font-weight: 600 !important;
            font-size: 13px !important;
        }
        .stTabs [aria-selected="true"],
        button[data-baseweb="tab"][aria-selected="true"] {
            background-color: #242933 !important;
            color: #38BDF8 !important;
            border-bottom: 2px solid #38BDF8 !important;
        }
        .stTabs [aria-selected="true"] p,
        button[data-baseweb="tab"][aria-selected="true"] p {
            color: #38BDF8 !important;
            font-weight: 700 !important;
        }

        /* Hero Executive Storytelling Cards */
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    """Ponto de entrada central da aplicação Streamlit.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    st.set_page_config(
        page_title="Margem Eleitoral | Auditoria Científica de Pesquisas Eleitorais",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()
    apply_custom_css()

    # Barra lateral de controles e extensão contínua para múltiplos ciclos eleitorais
    st.sidebar.markdown("## ⚙️ Parâmetros de Auditoria")
    ano_opcao = st.sidebar.selectbox(
        "Ciclo Eleitoral:",
        [2026, 2022],
        index=0,
        help="Base ativa oficial do ciclo eleitoral (dados de 2026 pós-1º Turno ou histórico de 2022).",
    )
    ano_eleicao = int(ano_opcao)

    st.sidebar.selectbox(
        "Cargo em Auditoria:",
        ["Presidente da República", "Governadores (Em breve)", "Senado (Em breve)"],
        index=0,
    )
    turno_selecionado = st.sidebar.radio(
        "Turno:", ["1º Turno (Consolidado)", "2º Turno (Contínuo)"], index=0
    )
    turno_num = 1 if "1º" in turno_selecionado else 2
    turno_label = "1º Turno" if turno_num == 1 else "2º Turno"

    # Carrega resultado oficial e pesquisas do turno selecionado via data_loader
    tse_result, eve_polls, all_polls = get_election_dataset(year=ano_eleicao, turno=turno_num)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📚 Guia e Metodologia")
    if st.sidebar.button(
        "📖 Consultar Metodologia",
        width="stretch",
        help="Abre o modal com o resumo estratégico não-técnico e o memorial estatístico avançado.",
    ):
        render_documentation_modal()

    # Header de Navegação Superior e Botão de Consulta Metodológica
    st.markdown(
        '<div class="breadcrumb-text">Início &gt; Margem Eleitoral &gt; Auditoria e Storytelling de Pesquisas</div>',
        unsafe_allow_html=True,
    )
    col_title, col_doc = st.columns([3, 1])
    with col_title:
        st.markdown(
            '<div class="main-header-title">Auditoria e Desempenho de Pesquisas Eleitorais</div>',
            unsafe_allow_html=True,
        )
    with col_doc:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        if st.button(
            "📖 Metodologia & Guia",
            width="stretch",
            help="Clique para abrir o modal com o resumo estratégico não-técnico e o memorial estatístico avançado.",
        ):
            render_documentation_modal()

    # Placar de Apuração do TSE e Censo do PesqEle
    has_concluded = tse_result is not None and getattr(tse_result, "apuracao_concluida", True)
    if has_concluded and tse_result is not None:
        votos_str = " | ".join(
            [f"<b>{k}:</b> {v:.2f}%" for k, v in tse_result.resultado_nominal.items()]
        )
        status_line = (
            f"<b>Votos apurados:</b> 100% &nbsp;&nbsp;|&nbsp;&nbsp; {votos_str}<br>"
            f"<span style='color: #64748B;'>Disputa com totalização oficial consolidada pelo TSE. "
            f"Total de votos válidos contabilizados oficialmente: {tse_result.total_votos_validos:,}.</span>"
        )
    else:
        status_line = (
            "<span style='color: #38BDF8; font-weight: 600;'>🟡 Campanha em Andamento</span> &nbsp;|&nbsp; "
            "<b>Votação Oficial:</b> 25/10/2026<br>"
            "<span style='color: #94A3B8;'>Apuração oficial aguardando abertura das urnas. "
            "Exibindo modo de <b>Projeção Contínua (Nowcasting)</b> baseado nas pesquisas registradas.</span>"
        )

    census_df = get_tse_registration_census(ano_eleicao)
    census_info_html = ""
    if census_df.height > 0:
        tot_reg = census_df.height
        insts_cons = census_df.filter(pl.col("instituto_consistente"))[
            "instituto_nome_fantasia"
        ].n_unique()
        census_info_html = (
            f"<br><span style='color: #38BDF8; font-size: 12.5px;'>"
            f"📋 <b>Censo PesqEle/TSE:</b> {tot_reg:,} pesquisas registradas "
            f"({insts_cons} institutos consistentes com &ge; 2 levantamentos) &nbsp;|&nbsp; "
            f"<b>Base de Pesquisas:</b> {len(all_polls)} levantamentos com intenções de voto.</span>"
        )

    st.markdown(
        f"""
        <div class="tse-summary-card">
            <div class="tse-summary-title">Presidente — {ano_eleicao} ({turno_label})</div>
            <div class="tse-summary-stats">
                {status_line}
                {census_info_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Carrega dados multi-escopo e calibração de 1º turno para o Storytelling e Modelo Preditivo
    _, _, multiscope_polls = get_election_dataset(
        year=ano_eleicao, turno=turno_num, include_subnational=True
    )
    election_dt = get_election_date(year=ano_eleicao, turno=turno_num)
    t1_tse_res = None
    t1_polls_all = None
    t1_dt = None
    if turno_num == 2:
        t1_tse_res, _, t1_polls_all = get_election_dataset(
            year=ano_eleicao, turno=1, include_subnational=True
        )
        t1_dt = get_election_date(year=ano_eleicao, turno=1)

    # Hero Executive Storytelling Cards (Síntese Imediata: Agregação & Modelo Preditivo)
    render_executive_story_cards(
        polls=all_polls,
        multiscope_polls=multiscope_polls,
        election_date=election_dt,
        turno_num=turno_num,
        ano_eleicao=ano_eleicao,
        tse_result=tse_result,
        t1_polls=t1_polls_all,
        t1_tse_result=t1_tse_res,
        t1_election_date=t1_dt,
    )

    # Navegação por Abas na sequência lógica e pedagógica dos Atos 1 a 7
    tabs = st.tabs(
        [
            "🔬 Princípio da Incerteza (Ato 1)",
            "📈 Agregador Dinâmico (Ato 2)",
            "🚫 Quem é Menos Rejeitado? (Ato 3)",
            "🎯 Forest Plot & Véspera (Ato 4)",
            "📊 Desempenho & Auditoria (Ato 5)",
            "⚖️ Veredito Científico (Ato 6)",
            "🔮 Modelo Preditivo & Previsão (Ato 7)",
        ]
    )

    with tabs[0]:
        render_act1()

    with tabs[1]:
        render_act2(polls=all_polls)

    with tabs[2]:
        render_act3(year=ano_eleicao, turno=turno_num)

    with tabs[3]:
        render_act4(
            eve_polls=eve_polls,
            tse_result=tse_result,
        )

    with tabs[4]:
        render_act5(
            eve_polls=eve_polls,
            all_polls=all_polls,
            tse_result=tse_result,
        )

    with tabs[5]:
        render_act6(
            eve_polls=eve_polls,
            tse_result=tse_result,
            all_polls=all_polls,
        )

    with tabs[6]:
        if "pytest" not in sys.modules:
            import importlib

            import src.presentation.components.predictive_charts as _pc_mod
            import src.presentation.story_acts.act7_predictive_forecast as _act7_mod

            importlib.reload(_pc_mod)
            importlib.reload(_act7_mod)
            render_act7_fn = _act7_mod.render_act7
        else:
            render_act7_fn = render_act7

        render_act7_fn(
            polls=multiscope_polls,
            tse_result=tse_result,
            election_date=election_dt,
            t1_polls=t1_polls_all,
            t1_tse_result=t1_tse_res,
            t1_election_date=t1_dt,
        )


def run() -> None:
    """Inicia a aplicação interativa do Streamlit via linha de comando ou renderiza a página ativa.

    Se o runtime do Streamlit já estiver em execução (ex.: Streamlit Community Cloud ou
    `streamlit run`), executa `main()` diretamente para evitar `RuntimeError: Runtime instance
    already exists!`. Caso contrário, delega a inicialização para o CLI oficial do Streamlit.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: Ao finalizar a execução do servidor Streamlit via CLI.
    """
    if st.runtime.exists():
        main()
        return

    app_path = Path(__file__).resolve()
    args = ["run", str(app_path), *sys.argv[1:]]
    sys.argv = ["streamlit", *args]
    sys.exit(stcli.main(args=args))


if __name__ == "__main__":
    run()
