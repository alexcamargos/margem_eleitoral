"""Ato 1: O Princípio da Incerteza.

Desmistifica o dilema intuitivo de como uma amostra de ~2.000 eleitores
consegue representar um universo eleitoral de mais de 150 milhões de cidadãos.
"""

import streamlit as st

from src.presentation.components.simulator import create_sampling_simulator_figure


def render_act1() -> None:
    """Renderiza a narrativa e os componentes interativos do Ato 1.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    st.markdown("## Ato 1: O Princípio da Incerteza")
    st.markdown(
        """
        > *“Como é possível que apenas 2.000 pessoas representem a vontade de 156 milhões de brasileiros?”*

        Essa é a dúvida central que alimenta o ceticismo popular e teorias infundadas sobre pesquisas.
        A resposta não reside em política ou adivinhação, mas na [**Lei dos Grandes Números**](https://pt.wikipedia.org/wiki/Lei_dos_grandes_n%C3%BAmeros)
        e no [**Teorema Central do Limite (TCL)**](https://pt.wikipedia.org/wiki/Teorema_central_do_limite).
        """
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(
            """
            ### A Analogia do Exame de Sangue
            Quando você faz um hemograma completo, o laboratório não precisa retirar todos os 5 litros
            de sangue do seu corpo. Bastam **5 mililitros bem homogeneizados** para diagnosticar com
            extrema precisão o estado de saúde global.

            Em amostragem probabilística e por cotas calibradas, a **margem de erro teórica independe quase que
            totalmente do tamanho da população ($N$)** quando $N > 100.000$, dependendo essencialmente
            do tamanho amostral ($n$) e do **efeito de delineamento ($deff$)**.
            """
        )
        st.latex(r"\text{Margem de Erro} \approx 1{,}96 \times \sqrt{deff \times \frac{p(1-p)}{n}}")

    with col2:
        st.markdown("### Simulador Interativo de Amostragem")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            sample_size = st.slider(
                "Tamanho da Amostra (n):",
                min_value=500,
                max_value=5000,
                value=2000,
                step=250,
                help="Arraste para ver como o erro diminui com o aumento da amostra.",
            )
            p_real = st.slider("Intenção Real no Universo (%):", 30.0, 70.0, 50.0, 1.0)
        with col_s2:
            deff_val = st.slider(
                "Efeito de Delineamento (deff):",
                min_value=1.0,
                max_value=2.0,
                value=1.35,
                step=0.05,
                help="Fator de correção de variância para amostragem por cotas no Brasil (1.2 a 1.5).",
            )
            num_sims = st.select_slider(
                "Número de Pesquisas Simuladas:",
                [200, 500, 1000, 2000],
                value=1000,
            )

    fig = create_sampling_simulator_figure(
        p_true=p_real,
        sample_size=sample_size,
        num_simulations=num_sims,
        deff=deff_val,
    )
    st.plotly_chart(fig, use_container_width=True)

    margem_calculada = 1.96 * (((deff_val * 0.5 * 0.5) / sample_size) ** 0.5) * 100
    st.markdown(
        f"""
        <div style="background-color: #172554; border-left: 4px solid #38BDF8; padding: 14px 18px; border-radius: 6px; margin-top: 15px;">
            <span style="color: #38BDF8; font-weight: 700; font-size: 14px;">Conclusão Estatística:</span>
            <p style="color: #F8FAFC; font-size: 13.5px; line-height: 1.5; margin: 4px 0 0 0;">
                Com amostra <b>n = {sample_size:,}</b> e delineamento <b>deff = {deff_val:.2f}</b>, a margem de erro teórica máxima
                é de aproximadamente <b>± {margem_calculada:.2f} pontos percentuais</b>. Em 95 de cada 100 pesquisas idênticas
                conduzidas pelo mesmo método, o resultado observado estará estritamente contido nessa faixa por pura aleatoriedade estocástica.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
