"""Ato 2: O Filme da Eleição (Agregador Dinâmico).

Demonstra a dinâmica longitudinal da corrida eleitoral, confrontando a falácia de que
pesquisas passadas falharam quando na realidade capturaram uma dinâmica volátil de campanha.
"""

from typing import Sequence

import streamlit as st

from src.analytics.aggregator_model import compute_poll_aggregation_series
from src.presentation.components.trend_chart import create_trend_aggregator_chart
from src.transformations.schemas import PesquisaEleitoralSchema


def render_act2(polls: Sequence[PesquisaEleitoralSchema]) -> None:
    """Renderiza a narrativa e visualização do Agregador Dinâmico no Ato 2.

    Args:
        polls: Lista das pesquisas registradas do turno selecionado.

    Returns:
        None.

    Raises:
        None.
    """
    st.markdown("## Ato 2: O Filme da Eleição (Agregador Dinâmico)")
    st.markdown(
        """
        > *“Pesquisa eleitoral não é bola de cristal nem profecia: é uma fotografia do momento.”*

        Durante a campanha, a opinião pública se move em resposta a debates, revelações, propaganda
        e alianças. O **Agregador Dinâmico** extrai a verdadeira trajetória latente do eleitorado
        combinando centenas de pesquisas com decaimento temporal exponencial (meia-vida de 14 dias),
        garantindo que levantamentos mais recentes e com maiores amostras tenham maior peso.
        """
    )

    METHODOLOGY_LABELS = {
        "PRESENCIAL_DOMICILIAR": "Presencial Domiciliar",
        "PRESENCIAL_FLUXO": "Presencial (Pontos de Fluxo)",
        "TELEFONICA_CATI": "Telefônica (CATI)",
        "TELEFONICA_URA": "Telefônica (Robô / URA)",
        "ONLINE": "Online / Painel Digital",
    }

    ano_pleito = polls[0].ano if polls else 2026
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1.2, 1.2, 1.0])
    with col_ctrl1:
        available_cands = sorted(
            list({c for p in polls for c in p.votos_validos.keys() if c != "Outros"})
        )
        default_cands = [
            c for c in ["Lula", "Flávio Bolsonaro", "Bolsonaro"] if c in available_cands
        ]
        if not default_cands and available_cands:
            default_cands = available_cands[: min(2, len(available_cands))]
        selected_candidates = st.multiselect(
            "Candidatos para Visualização:",
            options=available_cands,
            default=default_cands,
            key=f"act2_candidates_{ano_pleito}",
        )
        # Sanitiza candidatos caso haja resíduos de estados anteriores
        selected_candidates = [c for c in selected_candidates if c in available_cands]
    with col_ctrl2:
        metodologias_disponiveis = sorted(list({p.metodologia.value for p in polls}))
        filtro_metodologia = st.multiselect(
            "Filtrar por Metodologia de Coleta:",
            options=metodologias_disponiveis,
            default=metodologias_disponiveis,
            format_func=lambda m: METHODOLOGY_LABELS.get(m, m),
            key=f"act2_methods_{ano_pleito}",
        )
    with col_ctrl3:
        tipo_metrica = st.radio(
            "Base de Votação:",
            ["Votos Válidos (Oficial)", "Votos Totais (Bruto)"],
            index=0,
            horizontal=False,
            help="Alterne entre votos válidos (sem brancos/nulos) e cenário estimulado bruto.",
        )
        use_valid = "Válidos" in tipo_metrica

    filtered_polls = [p for p in polls if p.metodologia.value in filtro_metodologia]

    if not filtered_polls:
        st.warning("Nenhuma pesquisa encontrada para os filtros selecionados.")
        return

    # Computa agregação dinâmica
    with st.spinner("Computando trajetória latente e envelopes de credibilidade..."):
        df_agg = compute_poll_aggregation_series(
            polls=filtered_polls,
            candidates=selected_candidates,
            half_life_days=14.0,
            deff=1.3,
            use_valid_votes=use_valid,
        )

    fig = create_trend_aggregator_chart(
        df_agg=df_agg,
        polls=filtered_polls,
        candidates=selected_candidates,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        """
        ### Entendendo as Fitas de Incerteza
        As faixas sombreadas representam o **Envelope de Credibilidade de 95%**. Elas combinam
        duas fontes de incerteza:
        1. **Variância Amostral ($deff$):** O erro estocástico intrínseco a cada tamanho amostral.
        2. **Variância Inter-Institutos:** A dispersão observada entre levantamentos realizados no mesmo período por diferentes metodologias.
        """
    )
