"""Ato 3: Quem é Menos Rejeitado? (Termômetro da Rejeição e Teto Eleitoral).

Renderiza a análise comparativa de rejeição dos candidatos ("em quem não votaria de jeito nenhum"):
1. Veredito sintético da reta final do 1º turno e dinamismo pós-1º turno.
2. Cartões métricos duplos de rejeição média por candidato.
3. Gráfico de Halteres (Dumbbell Plot / Cleveland Dot Plot) por instituto com notas metodológicas.
4. Feed cronológico das pesquisas de 2º turno com determinação de diferencial de pontos.
5. Formulação pedagógica do Teto Eleitoral e conexão com o Voto Potencial no 2º turno.
"""

import polars as pl
import streamlit as st

from src.analytics.rejection_analysis import structure_rejection_metrics
from src.ingestion.data_loader import get_rejection_dataset
from src.presentation.components.dumbbell_chart import create_rejection_dumbbell_chart


def render_act3(year: int = 2026, turno: int = 1, cargo: str = "Presidente da República") -> None:
    """Renderiza a narrativa e as visualizações analíticas de rejeição no Ato 3.

    Args:
        year: Ano do ciclo eleitoral (ex.: 2026, 2022).
        turno: Turno da eleição selecionado (1 ou 2).
        cargo: Cargo eletivo em auditoria (default: 'Presidente da República').

    Returns:
        None.

    Raises:
        None.
    """
    st.markdown("## Ato 3: Quem é Menos Rejeitado? (Termômetro da Rejeição)")

    if "PRESIDENTE" not in cargo.upper():
        st.info(
            f"ℹ️ O monitoramento longitudinal com dados empíricos de rejeição (voto negativo espontâneo e estimulado) "
            f"está parametrizado para a disputa presidencial. Para {cargo}, utilize as intenções de voto e estimativas "
            f"no **Ato 2 (Agregador Dinâmico)** e no **Ato 4 (Forest Plot)**."
        )
        return

    try:
        raw_dataset = get_rejection_dataset(year=year)
    except FileNotFoundError:
        st.warning(f"Dados de rejeição não disponíveis para o ciclo eleitoral {year}.")
        return

    data = structure_rejection_metrics(raw_dataset)

    c1 = data["candidatos"][0]
    c2 = data["candidatos"][1]
    c1_disp = data["display_names"].get(c1, c1)
    c2_disp = data["display_names"].get(c2, c2)
    c1_color = data["cores"].get(c1, "#EF4444")
    c2_color = data["cores"].get(c2, "#3B82F6")

    # 1. Cartão de Destaque Superior com Veredito Sintético
    st.markdown(
        f"""
        <div style="background-color: #181B20; border: 1px solid #282D37; border-radius: 8px; padding: 18px 20px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 18px; font-weight: 700; color: #F8FAFC;">{data["titulo_card"]}</span>
                <div>
                    <span style="display: inline-block; width: 14px; height: 14px; background-color: {c1_color}; border-radius: 3px; margin-right: 4px;"></span>
                    <span style="display: inline-block; width: 14px; height: 14px; background-color: {c2_color}; border-radius: 3px; margin-right: 6px;"></span>
                </div>
            </div>
            <div style="font-size: 13.5px; color: #94A3B8; line-height: 1.5;">
                {data["subtitulo_resumo"]}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Caixa Pedagógica de Conceito
    if data["conceito_pedagogico"]:
        st.markdown(
            f"""
            <div style="font-size: 14px; color: #CBD5E1; line-height: 1.6; margin-bottom: 22px;">
                {data["conceito_pedagogico"]}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 3. Seção 1: Reta Final do 1º Turno
    st.markdown("### Reta final do 1º turno")
    if data["texto_diagnostico"]:
        st.markdown(
            f"""
            <div style="font-size: 14px; color: #E2E8F0; margin-bottom: 16px; line-height: 1.5;">
                {data["texto_diagnostico"]}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Dois cartões métricos KPI destacados lado a lado
    med_c1 = data["media_rejeicao"].get(c1, 0.0)
    med_c2 = data["media_rejeicao"].get(c2, 0.0)
    tot_inst = data["total_institutos"]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div style="background-color: #2D1517; border-left: 4px solid {c1_color}; border-radius: 6px; padding: 14px 18px; margin-bottom: 16px;">
                <div style="font-size: 13px; font-weight: 600; color: #FCA5A5; text-transform: uppercase; letter-spacing: 0.5px;">{c1_disp}</div>
                <div style="font-size: 32px; font-weight: 700; color: #FFFFFF; line-height: 1.2; margin: 4px 0;">{med_c1:.1f}%</div>
                <div style="font-size: 12px; color: #FDA4AF;">rejeição média, {tot_inst} institutos</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div style="background-color: #172554; border-left: 4px solid {c2_color}; border-radius: 6px; padding: 14px 18px; margin-bottom: 16px;">
                <div style="font-size: 13px; font-weight: 600; color: #93C5FD; text-transform: uppercase; letter-spacing: 0.5px;">{c2_disp}</div>
                <div style="font-size: 32px; font-weight: 700; color: #FFFFFF; line-height: 1.2; margin: 4px 0;">{med_c2:.1f}%</div>
                <div style="font-size: 12px; color: #BFDBFE;">rejeição média, {tot_inst} institutos</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Texto do Placar Instituto por Instituto
    if data["texto_placar"]:
        st.markdown(
            f"""
            <div style="font-size: 13.5px; color: #94A3B8; margin-bottom: 12px; line-height: 1.5;">
                {data["texto_placar"]}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Gráfico Dumbbell Plot
    fig_dumbbell = create_rejection_dumbbell_chart(
        polls=data["pesquisas_instituto"],
        candidate_1=c1,
        candidate_2=c2,
        display_names=data["display_names"],
        candidate_colors=data["cores"],
    )
    st.plotly_chart(fig_dumbbell, width="stretch")

    # Notas metodológicas de rodapé do 1º turno
    if data["notas_metodologicas"]:
        notas_html = "".join(
            [f"<p style='margin: 4px 0;'>{n}</p>" for n in data["notas_metodologicas"]]
        )
        st.markdown(
            f"""
            <div style="font-size: 12px; color: #64748B; margin-top: 6px; margin-bottom: 28px; line-height: 1.5;">
                {notas_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 4. Seção 2: Depois do 1º Turno (Última pesquisa de cada instituto)
    segundo_turno_data = data.get("segundo_turno", {})
    pesquisas_feed = segundo_turno_data.get("pesquisas_feed", [])
    t2_polls = data.get("t2_pesquisas_instituto", [])

    if t2_polls:
        st.markdown("### Depois do 1º turno")

        # Texto diagnóstico do 2º turno
        if data.get("t2_texto_diagnostico"):
            st.markdown(
                f"""
                <div style="font-size: 14px; color: #E2E8F0; margin-bottom: 16px; line-height: 1.5;">
                    {data["t2_texto_diagnostico"]}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Dois cartões métricos KPI destacados lado a lado para o 2º turno
        t2_med_c1 = data["t2_media_rejeicao"].get(c1, 0.0)
        t2_med_c2 = data["t2_media_rejeicao"].get(c2, 0.0)
        t2_tot_inst = data["t2_total_institutos"]

        col1_t2, col2_t2 = st.columns(2)
        with col1_t2:
            st.markdown(
                f"""
                <div style="background-color: #2D1517; border-left: 4px solid {c1_color}; border-radius: 6px; padding: 14px 18px; margin-bottom: 16px;">
                    <div style="font-size: 13px; font-weight: 600; color: #FCA5A5; text-transform: uppercase; letter-spacing: 0.5px;">{c1_disp} (2º Turno)</div>
                    <div style="font-size: 32px; font-weight: 700; color: #FFFFFF; line-height: 1.2; margin: 4px 0;">{t2_med_c1:.1f}%</div>
                    <div style="font-size: 12px; color: #FDA4AF;">rejeição média, {t2_tot_inst} institutos (último campo)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col2_t2:
            st.markdown(
                f"""
                <div style="background-color: #172554; border-left: 4px solid {c2_color}; border-radius: 6px; padding: 14px 18px; margin-bottom: 16px;">
                    <div style="font-size: 13px; font-weight: 600; color: #93C5FD; text-transform: uppercase; letter-spacing: 0.5px;">{c2_disp} (2º Turno)</div>
                    <div style="font-size: 32px; font-weight: 700; color: #FFFFFF; line-height: 1.2; margin: 4px 0;">{t2_med_c2:.1f}%</div>
                    <div style="font-size: 12px; color: #BFDBFE;">rejeição média, {t2_tot_inst} institutos (último campo)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Texto do Placar do 2º Turno
        if data.get("t2_texto_placar"):
            st.markdown(
                f"""
                <div style="font-size: 13.5px; color: #94A3B8; margin-bottom: 12px; line-height: 1.5;">
                    {data["t2_texto_placar"]}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Gráfico Dumbbell Plot do 2º Turno (última pesquisa de cada instituto)
        fig_dumbbell_t2 = create_rejection_dumbbell_chart(
            polls=t2_polls,
            candidate_1=c1,
            candidate_2=c2,
            display_names=data["display_names"],
            candidate_colors=data["cores"],
            chart_title="% que não votaria de jeito nenhum no 2º turno — quanto mais à esquerda, menos rejeitado",
            include_dates_in_label=True,
        )
        st.plotly_chart(fig_dumbbell_t2, width="stretch")

        # Histórico detalhado cronológico das pesquisas em container colapsável com Tabela Interativa
        if pesquisas_feed:
            with st.expander(
                f"📋 Ver histórico cronológico completo de pesquisas publicadas no 2º turno ({len(pesquisas_feed)} levantamentos)"
            ):
                table_rows = []
                for p in pesquisas_feed:
                    inst = p.get("instituto", "")
                    inicio = p.get("campo_inicio", "")
                    fim = p.get("campo_fim", "")
                    periodo = f"{inicio} a {fim}" if inicio and fim else "-"
                    rejeicao = p.get("rejeicao", {})
                    v1 = float(rejeicao.get(c1, 0.0))
                    v2 = float(rejeicao.get(c2, 0.0))
                    diff = round(abs(v1 - v2), 1)

                    v_raw = p.get("veredito", "").strip().rstrip(".")
                    if not v_raw or v_raw.lower() == "empate":
                        v_clean = "Empate técnico"
                    else:
                        v_clean = v_raw

                    table_rows.append(
                        {
                            "Instituto": inst,
                            "Período de Campo": periodo,
                            f"Rejeição {c1_disp}": v1,
                            f"Rejeição {c2_disp}": v2,
                            "Diferença": diff,
                            "Veredito": v_clean,
                        }
                    )

                df_feed = pl.DataFrame(table_rows)
                st.dataframe(
                    df_feed,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Instituto": st.column_config.TextColumn(
                            "Instituto",
                            help="Instituto responsável pela realização da pesquisa",
                        ),
                        "Período de Campo": st.column_config.TextColumn(
                            "Período de Campo",
                            help="Datas de início e fim da coleta de campo",
                        ),
                        f"Rejeição {c1_disp}": st.column_config.NumberColumn(
                            f"Rejeição {c1_disp}",
                            help=f"Percentual de eleitores que não votariam de jeito nenhum em {c1_disp}",
                            format="%.0f%%",
                        ),
                        f"Rejeição {c2_disp}": st.column_config.NumberColumn(
                            f"Rejeição {c2_disp}",
                            help=f"Percentual de eleitores que não votariam de jeito nenhum em {c2_disp}",
                            format="%.0f%%",
                        ),
                        "Diferença": st.column_config.NumberColumn(
                            "Diferença (pp)",
                            help="Diferença absoluta em pontos percentuais entre os dois candidatos",
                            format="%.0f pp",
                        ),
                        "Veredito": st.column_config.TextColumn(
                            "Veredito",
                            help="Veredito analítico da pesquisa sobre qual concorrente tem menor rejeição",
                        ),
                    },
                )

        nota_projecao = segundo_turno_data.get("nota_projecao", "")
        if nota_projecao:
            st.markdown(
                f"""
                <div style="font-size: 12.5px; color: #64748B; line-height: 1.5; margin-top: 10px; margin-bottom: 24px;">
                    {nota_projecao}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 5. Seção 3: Implicações Metodológicas no Teto Eleitoral (Ponte com os Atos 4 a 7)
    with st.expander("🔍 Como a rejeição impacta o teto de votos no 2º turno e o Modelo Preditivo"):
        teto_1 = data["tetos_eleitorais"].get(c1, 50.0)
        teto_2 = data["tetos_eleitorais"].get(c2, 50.0)
        st.markdown(
            f"A rejeição estabelece o **teto eleitoral máximo teórico** de cada candidato:\n\n"
            f"$$\\text{{Teto}}_i = 100\\% - \\text{{Rejeição}}_i$$\n\n"
            f"* **{c1_disp}:** Rejeição média de **{med_c1:.1f}%** $\\to$ Teto eleitoral potencial de **{teto_1:.1f}%**\n"
            f"* **{c2_disp}:** Rejeição média de **{med_c2:.1f}%** $\\to$ Teto eleitoral potencial de **{teto_2:.1f}%**\n\n"
            "> **Por que não auditamos a rejeição contra a urna nos Atos seguintes?**\n"
            "> A urna eletrônica totaliza exclusivamente intenções positivas de voto (votos válidos, brancos e nulos).\n"
            "> Não existe um campo na urna para o eleitor registrar em quem rejeita votar.\n"
            "> Por esse motivo, os testes de hipótese e as métricas de precisão ($M_3$, $M_5$ e Erro Ponderado)\n"
            "> apresentados nos **Atos 4 e 5** são aplicados estritamente às intenções de votos válidos."
        )
