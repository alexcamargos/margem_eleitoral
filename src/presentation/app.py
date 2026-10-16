"""Aplicação Principal de Auditoria e Storytelling de Pesquisas Eleitorais (Margem Eleitoral).

Ponto de entrada Streamlit com suporte a navegação por Atos, visualização analítica
no padrão dark mode da referência (Plano Político), e atualização contínua para múltiplos ciclos eleitorais.
"""

import sys
from datetime import date
from pathlib import Path

import polars as pl
import streamlit as st
from streamlit.web import cli as stcli

from src.ingestion.data_loader import (
    get_election_dataset,
    get_second_round_sync_summary,
    get_tse_registration_census,
)
from src.ingestion.pesqele_collector import PesqEleCollector
from src.presentation.components.documentation_modal import render_documentation_modal
from src.presentation.story_acts.act1_uncertainty import render_act1
from src.presentation.story_acts.act2_election_film import render_act2
from src.presentation.story_acts.act3_eve_clash import render_act3
from src.presentation.story_acts.act4_error_anatomy import render_act4
from src.presentation.story_acts.act5_scientific_verdict import render_act5


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

        /* Ajustes de contraste para alertas e métricas no dark mode */
        div[data-testid="stAlert"] {
            color: #F8FAFC !important;
            border-radius: 6px;
        }
        div[data-testid="stAlert"] p {
            color: #F8FAFC !important;
            font-size: 13.5px;
        }
        div[data-testid="stMetricLabel"] {
            color: #CBD5E1 !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }
        div[data-testid="stMetricValue"] {
            color: #F8FAFC !important;
            font-size: 26px !important;
            font-weight: 700 !important;
        }

        /* Ajustes dos botões e abas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: 1px solid #282D37;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #181B20;
            border: 1px solid #282D37;
            border-radius: 6px 6px 0 0;
            color: #94A3B8;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 13.5px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #242933 !important;
            color: #38BDF8 !important;
            border-bottom: 2px solid #38BDF8 !important;
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
    st.sidebar.markdown(f"### 📥 Sincronização Oficial TSE (2º Turno - {ano_eleicao})")
    st.sidebar.markdown(
        "<span style='font-size: 12.5px; color: #94A3B8;'>"
        "Conecte-se diretamente à base do <b>PesqEle / Dados Abertos do TSE</b> para baixar "
        "automaticamente todas as pesquisas registradas e divulgadas do 2º Turno.</span>",
        unsafe_allow_html=True,
    )

    btn_sync = st.sidebar.button(
        "🔄 Sincronizar Pesquisas do TSE",
        type="primary",
        use_container_width=True,
        help="Dispara a ingestão automatizada do pacote oficial de pesquisas eleitorais registradas no TSE.",
    )

    if btn_sync:
        with st.sidebar:
            with st.spinner("Conectando ao TSE e sincronizando pesquisas do 2º Turno..."):
                try:
                    collector = PesqEleCollector(year=ano_eleicao)
                    synced_polls = collector.sync_official_second_round_polls(force_download=True)
                    st.session_state["polls_synced_r2"] = True
                    st.session_state["last_sync_time"] = date.today().strftime("%d/%m/%Y")
                    st.success(
                        f"✅ {len(synced_polls)} pesquisas do 2º Turno sincronizadas com sucesso do TSE!"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao sincronizar dados com o TSE: {e}")

    # Exibe cartão de status da sincronização
    sync_summary = get_second_round_sync_summary(ano_eleicao)
    if sync_summary["is_synced"]:
        st.sidebar.markdown(
            f"""
            <div style="background-color: #181B20; border: 1px solid #282D37; border-radius: 6px; padding: 10px 12px; margin-top: 10px;">
                <span style="font-size: 11.5px; color: #38BDF8; font-weight: 600;">● SINCRONIZADO COM O TSE</span><br>
                <span style="font-size: 12px; color: #E2E8F0;"><b>Total 2º Turno:</b> {sync_summary["total_polls"]} levantamentos</span><br>
                <span style="font-size: 12px; color: #94A3B8;"><b>Pesquisas de Véspera:</b> {sync_summary["eve_polls_count"]}</span><br>
                <span style="font-size: 12px; color: #94A3B8;"><b>Institutos Ativos:</b> {len(sync_summary["institutes"])}</span><br>
                <span style="font-size: 11.5px; color: #64748B;">Último campo: {sync_summary["latest_field_date"].strftime("%d/%m/%Y") if sync_summary["latest_field_date"] else "N/D"}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            """
            <div style="background-color: #181B20; border: 1px dashed #475569; border-radius: 6px; padding: 10px 12px; margin-top: 10px;">
                <span style="font-size: 12px; color: #94A3B8;">
                    Nenhuma pesquisa de 2º Turno carregada ainda. Clique no botão acima para sincronizar automaticamente da fonte oficial.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📚 Guia e Metodologia")
    if st.sidebar.button(
        "📖 Consultar Metodologia",
        use_container_width=True,
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
            use_container_width=True,
            help="Clique para abrir o modal com o resumo estratégico não-técnico e o memorial estatístico avançado.",
        ):
            render_documentation_modal()

    # Placar de Apuração do TSE e Censo do PesqEle
    votos_str = " | ".join(
        [f"<b>{k}:</b> {v:.2f}%" for k, v in tse_result.resultado_nominal.items()]
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
            f"<b>Base Auditada:</b> {len(all_polls)} pesquisas completas com intenções de voto.</span>"
        )

    st.markdown(
        f"""
        <div class="tse-summary-card">
            <div class="tse-summary-title">Presidente — {ano_eleicao} ({turno_label})</div>
            <div class="tse-summary-stats">
                <b>Votos apurados:</b> 100% &nbsp;&nbsp;|&nbsp;&nbsp; {votos_str}
                <br>
                <span style="color: #64748B;">
                    Disputa com totalização oficial consolidada pelo TSE.
                    Total de votos válidos contabilizados oficialmente: {tse_result.total_votos_validos:,}.
                </span>
                {census_info_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Navegação por Abas na sequência lógica e pedagógica dos Atos 1 a 5
    tabs = st.tabs(
        [
            "🔬 Princípio da Incerteza (Ato 1)",
            "📈 Agregador Dinâmico (Ato 2)",
            "🎯 Forest Plot & Véspera (Ato 3)",
            "📊 Desempenho & Auditoria (Ato 4)",
            "⚖️ Veredito Científico (Ato 5)",
        ]
    )

    with tabs[0]:
        render_act1()

    with tabs[1]:
        render_act2(polls=all_polls)

    with tabs[2]:
        render_act3(
            eve_polls=eve_polls,
            tse_result=tse_result,
        )

    with tabs[3]:
        render_act4(
            eve_polls=eve_polls,
            all_polls=all_polls,
            tse_result=tse_result,
        )

    with tabs[4]:
        render_act5(
            eve_polls=eve_polls,
            tse_result=tse_result,
            all_polls=all_polls,
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

