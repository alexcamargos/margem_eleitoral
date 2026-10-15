"""Ato 4: Anatomia do Erro e Auditoria (Painel de Desempenho de Pesquisas).

Implementa a visualização refinada em duas camadas complementares:
1. Camada de Impacto Eleitoral & Decisão Pública: Erro Ponderado multivariado (D, F, X)
   e calibração estocástica dinâmica via simulação de Monte Carlo (Faixa do Acaso P90).
2. Camada de Auditoria Científica Formal: Métricas consagradas WAPOR/AAPOR (M3, M5, Log-Odds A),
   intervalos de confiança com deff e teste de cobertura nominal.
3. Grid de Small Multiples ('Inclinação ao longo da campanha').
4. Caixa Metodológica completa com todas as fórmulas matemáticas e fundamentos científicos.
"""

from typing import Any, Sequence

import numpy as np
import polars as pl
import streamlit as st

from src.analytics.house_effects import compute_campaign_house_effects
from src.analytics.metrics import (
    calculate_bias_log_odds,
    calculate_confidence_interval,
    calculate_mosteller_m3,
    calculate_mosteller_m5,
    calculate_weighted_poll_error,
    simulate_stochastic_poll_thresholds,
)
from src.presentation.components.bar_error_chart import create_weighted_error_bar_chart
from src.presentation.components.small_multiples import create_small_multiples_grid
from src.transformations.schemas import PesquisaEleitoralSchema, ResultadoOficialTSESchema


def render_act4(
    eve_polls: Sequence[PesquisaEleitoralSchema],
    all_polls: Sequence[PesquisaEleitoralSchema],
    tse_result: ResultadoOficialTSESchema,
) -> None:
    """Renderiza a tela de Auditoria e Desempenho de Pesquisas em duas camadas.

    Args:
        eve_polls: Lista das pesquisas de véspera avaliadas (campo até 72h).
        all_polls: Conjunto de todas as pesquisas da campanha para o grid de inclinação.
        tse_result: Apuração oficial do TSE.

    Returns:
        None.

    Raises:
        None.
    """
    # 1. Alerta metodológico dourado superior
    st.markdown(
        """
        <div style="background-color: #262112; border-left: 4px solid #D97706; padding: 14px 18px; border-radius: 6px; margin-bottom: 20px;">
            <span style="color: #FBBF24; font-weight: 600; font-size: 14px;">Atenção:</span>
            <span style="color: #F3F4F6; font-size: 13.5px; line-height: 1.5;">
                Os números abaixo apuram o comparativo entre o <b>resultado oficial das urnas</b> e o que cada instituto
                enxergou em seu último campo antes da eleição. Esta é uma métrica técnica de calibração estatística
                e seus números são calculados estritamente sobre a base oficial de votos válidos recalculados.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ranking = sorted(
        tse_result.resultado_nominal.keys(),
        key=lambda c: tse_result.resultado_nominal[c],
        reverse=True,
    )
    c1, c2 = ranking[0], ranking[1]
    p1_tse = tse_result.resultado_nominal[c1]
    p2_tse = tse_result.resultado_nominal[c2]

    # 2. Simulação de Monte Carlo para derivação dinâmica da Faixa do Acaso (P90)
    sample_sizes = [p.tamanho_amostra for p in eve_polls if p.tamanho_amostra > 0]
    median_n = int(np.median(sample_sizes)) if sample_sizes else 2000

    stoch_res = simulate_stochastic_poll_thresholds(
        resultado_oficial=tse_result.resultado_nominal,
        sample_size=median_n,
        deff=1.35,
        n_simulations=10000,
        random_seed=42,
    )
    thresholds = {"p25": stoch_res["p25"], "p75": stoch_res["p75"]}
    p90 = stoch_res["faixa_acaso_p90"]
    a50 = stoch_res["median_a50"]
    n_ef = int(stoch_res["effective_sample_size"])

    # Cards informativos de referência estocástica
    c_m1, c_m2, c_m3 = st.columns(3)
    with c_m1:
        st.metric(
            "Faixa do Acaso (P90)",
            f"{p90:.1f} p.p.",
            help="Em 9 de cada 10 amostras perfeitamente aleatórias, o erro ponderado fica em até este limite.",
        )
    with c_m2:
        st.metric(
            "Mediana do Acaso (A50)",
            f"{a50:.1f} p.p.",
            help="Erro mediano esperado sob a hipótese nula H0 de ausência de viés sistemático.",
        )
    with c_m3:
        st.metric(
            "Amostra Efetiva (n_ef)",
            f"{n_ef:,}",
            help=f"Amostra média ({median_n:,}) ajustada pelo efeito de delineamento (deff = 1.35).",
        )

    # 3. Processamento das pesquisas de véspera
    eval_records: list[dict[str, Any]] = []
    table_rows_eleitoral: list[dict[str, Any]] = []
    table_rows_formal: list[dict[str, Any]] = []

    for p in eve_polls:
        decomp = calculate_weighted_poll_error(
            votos_validos_estimados=p.votos_validos,
            resultado_oficial=tse_result.resultado_nominal,
            ranking_candidatos=ranking,
            thresholds=thresholds,
        )

        p1_est = p.votos_validos.get(c1, 0.0)
        p2_est = p.votos_validos.get(c2, 0.0)

        m3 = calculate_mosteller_m3(p1_est, p1_tse)
        m5 = calculate_mosteller_m5(p1_est, p2_est, p1_tse, p2_tse)
        log_odds = (
            calculate_bias_log_odds(p1_est, p2_est, p1_tse, p2_tse)
            if p1_est > 0 and p2_est > 0
            else 0.0
        )
        ci_inf, ci_sup, me = calculate_confidence_interval(p1_est, p.tamanho_amostra, deff=1.35)
        cobriu_urna = "Sim" if ci_inf <= p1_tse <= ci_sup else "Não"

        cands_str = " | ".join([f"{k} {v:.1f}%" for k, v in list(p.votos_validos.items())[:3]])

        rec = {
            "instituto": p.instituto_nome_fantasia,
            "campo_ate": p.data_fim_campo.strftime("%d/%m"),
            "erro_1_lugar": decomp["erro_1_lugar"],
            "erro_2_lugar": decomp["erro_2_lugar"],
            "erro_demais": decomp["erro_demais"],
            "erro_total_ponderado": decomp["erro_total_ponderado"],
            "disputa_decisiva": decomp["disputa_decisiva"],
            "eleitorado_fora_lugar": decomp["eleitorado_fora_lugar"],
            "penalidade_lado_errado": decomp["penalidade_lado_errado"],
            "faixa_acerto": decomp["faixa_acerto"],
        }
        eval_records.append(rec)

        table_rows_eleitoral.append(
            {
                "Instituto": p.instituto_nome_fantasia,
                "Campo até": p.data_fim_campo.strftime("%d/%m"),
                "Erro Ponderado (EP)": decomp["erro_total_ponderado"],
                "Disputa Decisiva (D)": decomp["disputa_decisiva"],
                "Eleitorado Fora Lugar (F)": decomp["eleitorado_fora_lugar"],
                "Lado Errado (X)": decomp["penalidade_lado_errado"],
                "Faixa do Acaso": decomp["faixa_acerto"],
                "Amostra (n)": f"{p.tamanho_amostra:,}",
                "Estimativas Principais": cands_str,
            }
        )

        table_rows_formal.append(
            {
                "Instituto": p.instituto_nome_fantasia,
                "Campo até": p.data_fim_campo.strftime("%d/%m"),
                "Erro Líder (M3)": m3,
                "Desvio Margem (M5)": m5,
                "Log-Odds Viés (A)": log_odds,
                "IC 95% Líder": f"[{ci_inf:.1f}%, {ci_sup:.1f}%]",
                "Margem Erro": f"±{me:.1f} p.p.",
                "Cobriu a Urna": cobriu_urna,
                "Amostra (n)": f"{p.tamanho_amostra:,}",
            }
        )

    # 4. Organização em Abas: Duas Camadas de Leitura
    tab_eleitoral, tab_formal = st.tabs(
        [
            "🏛️ Impacto Eleitoral & Responsabilização Pública",
            "🔬 Auditoria Científica Formal (WAPOR/AAPOR)",
        ]
    )

    with tab_eleitoral:
        st.markdown("### Erro ponderado de cada pesquisa frente à Faixa do Acaso")
        st.markdown(
            f"""
            <div style="color: #94A3B8; font-size: 13px; margin-bottom: 12px; line-height: 1.5;">
                O gráfico abaixo divide as pesquisas entre <b>Erro Abaixo do Típico</b> e <b>Erro Típico</b>.
                A linha vertical dourada demarca a <b>Faixa do Acaso ({p90:.1f} p.p.)</b>,
                limite onde se concentram 90% das pesquisas sob puro ruído amostral aleatório.
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig_bar = create_weighted_error_bar_chart(eval_records, faixa_acaso_p90=p90)
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown(
            "### Pesquisas consideradas *(organize a coluna para ordenar pelos componentes)*"
        )
        table_rows_sorted = sorted(
            table_rows_eleitoral, key=lambda r: float(r["Erro Ponderado (EP)"])
        )
        df_table = pl.DataFrame(table_rows_sorted).to_pandas()
        st.dataframe(
            df_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Erro Ponderado (EP)": st.column_config.NumberColumn(
                    "Erro Ponderado (EP)", format="%.2f"
                ),
                "Disputa Decisiva (D)": st.column_config.NumberColumn(
                    "Disputa Decisiva (D)", format="%.2f"
                ),
                "Eleitorado Fora Lugar (F)": st.column_config.NumberColumn(
                    "Eleitorado Fora Lugar (F)", format="%.2f"
                ),
                "Lado Errado (X)": st.column_config.NumberColumn("Lado Errado (X)", format="%.2f"),
                "Estimativas Principais": st.column_config.TextColumn(
                    "Estimativas Principais", width="large"
                ),
            },
        )

    with tab_formal:
        st.markdown("### Métricas Internacionais de Inferência e Cobertura Amostral")
        st.markdown(
            """
            <div style="color: #94A3B8; font-size: 13px; margin-bottom: 12px; line-height: 1.5;">
                Tabela de auditoria estatística padronizada conforme as diretrizes da <b>WAPOR/AAPOR</b>:
                desvio no líder (M3), desvio na margem (M5), razão de chances logarítmica (Log-Odds de Viés)
                e verificação de cobertura do intervalo de confiança de 95% ajustado por <i>deff</i>.
            </div>
            """,
            unsafe_allow_html=True,
        )
        df_formal = pl.DataFrame(table_rows_formal).to_pandas()
        st.dataframe(
            df_formal,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Erro Líder (M3)": st.column_config.NumberColumn("Erro Líder (M3)", format="%.2f"),
                "Desvio Margem (M5)": st.column_config.NumberColumn(
                    "Desvio Margem (M5)", format="%.2f"
                ),
                "Log-Odds Viés (A)": st.column_config.NumberColumn(
                    "Log-Odds Viés (A)", format="%.4f"
                ),
            },
        )

    # 5. Grid de Inclinação ao Longo da Campanha (House Effects Longitudinal)
    st.markdown("### Inclinação ao longo da campanha")
    st.markdown(
        f"""
        <div style="margin-bottom: 14px;">
            <div style="color: #CBD5E1; font-size: 13.5px; line-height: 1.6;">
                Cada painel abaixo mostra como o instituto estava em comparação com os outros a cada pesquisa:
                quanto a margem de <b>{c1}</b> sobre <b>{c2}</b> ficou acima (↑ mais {c1}) ou abaixo (↓ mais {c2})
                da média dos demais institutos com campo na mesma semana (±7 dias).
                <i>Não é comparação com o resultado e não é parte do cálculo do erro ponderado.</i>
            </div>
            <div style="color: #94A3B8; font-size: 12.5px; line-height: 1.6; margin-top: 6px;">
                Ordenados de acordo com a média da campanha; no título, a média e o intervalo de 80%.
                Somente institutos com pelo menos 2 pesquisas comparáveis (cada uma com ao menos 2 outros institutos na mesma semana).
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        house_effects_data = compute_campaign_house_effects(
            polls=all_polls,
            candidate_1=c1,
            candidate_2=c2,
            window_days=7,
            min_peer_institutes=2,
            min_comparable_polls=2,
            confidence_level=0.80,
        )
        fig_grid = create_small_multiples_grid(
            house_effects_data,
            candidate_1=c1,
            candidate_2=c2,
        )
        st.plotly_chart(fig_grid, use_container_width=True)

        excluded_list = house_effects_data.get("excluded_institutes", [])
        excluded_str = ", ".join(excluded_list) if excluded_list else "nenhum"
        st.markdown(
            f"""
            <div style="color: #64748B; font-size: 12px; margin-top: -8px; margin-bottom: 24px; line-height: 1.5;">
                <div>Linha tracejada: média do instituto; faixa: intervalo de 80% da média (mais clara quando inclui o zero).</div>
                <div style="margin-top: 3px;">Apenas 1 pesquisa comparável (ou menos): {excluded_str}.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception as exc:
        st.warning(f"Não foi possível calcular o comparativo de inclinação longitudinal: {exc}")

    # 6. Caixa Metodológica
    with st.expander(
        "📖 Como é calculado o erro ponderado (Metodologia e Fórmulas)", expanded=False
    ):
        st.markdown(
            """
            #### 1. Formulação do Erro Ponderado Multivariado ($EP$)
            O erro ponderado é sintetizado pela combinação convexa de três componentes:
            $$\\text{EP} = (1 - a) \\cdot D + a \\cdot F + \\frac{1}{2} X$$

            - **Disputa Decisiva ($D$):** Pondera os erros de margem ($e_{1 \\to 2}$ e $e_{2 \\to 3}$) pela
              competitividade real apurada na eleição através de pesos com decaimento exponencial:
              $$w_{1\\to 2} = \\exp\\left(-\\frac{R_1 - R_2}{15}\\right), \\quad w_{2\\to 3} = g \\cdot \\exp\\left(-\\frac{R_2 - R_3}{15}\\right)$$
              onde $g = 1$ se $R_1 < 50$ senão $\\exp\\left(-\\frac{R_1 - 50}{2{,}5}\\right)$.
            - **Eleitorado Fora do Lugar ($F$):** Mede a Distância de Variação Total ($L_1$ / Índice de Dissimilaridade de Duncan):
              $$F = \\frac{1}{2} \\left( \\sum_{c \\in L} |P_c - R_c| + \\left| (100 - \\sum P_c) - (100 - \\sum R_c) \\right| \\right)$$
              com peso dinâmico $a = 0{,}50 + 0{,}25 \\cdot \\exp\\left(-\\frac{|R_1 - 50|}{5}\\right)$, crescendo quando a eleição está na fronteira do 1º turno.
            - **Penalidade de Linhas Decisórias ($X$):** Cobra desvios nas fronteiras qualitativas da eleição (quem lidera, vaga no 2º turno e maioria de 50%),
              com atenuação exponencial $1 - \\exp(-\\delta)$ para não penalizar pesquisas quando o resultado oficial foi definido por fração de ponto.

            #### 2. Faixa do Acaso Dinâmica (Simulação de Monte Carlo)
            Em vez de limiares universais arbitrários, o sistema sorteia $N = 10.000$ amostras estocásticas
            perfeitas sob $H_0 \\sim \\text{Multinomial}(n_{\\text{ef}}, \\mathbf{p}_{\\text{oficial}})$,
            onde $n_{\\text{ef}} = n / deff$.
            - **Faixa do Acaso ($P_{90}$):** Limite empírico onde 90% das pesquisas perfeitamente aleatórias erram sob puro acaso.
            - **Limiares de Corte:** $P_{25}$ define a fronteira de erro *Abaixo do Típico* e $P_{75}$ a de erro *Acima do Típico*.

            #### 3. Conversão Obrigatória para Votos Válidos
            Todas as intenções são obrigatoriamente recalculadas para votos válidos antes do cálculo:
            $$\\hat{p}_{v,i} = \\frac{\\hat{p}_i}{1 - (\\hat{p}_{\\text{branco}} + \\hat{p}_{\\text{nulo}} + \\hat{p}_{\\text{indeciso}})}$$
            """
        )
