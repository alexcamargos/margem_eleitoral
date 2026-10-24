"""Modal interativo de consulta metodológica e documentação técnica da aplicação.

Exibe um diálogo modal com duas abas temáticas:
1. Resumo Estratégico e Metodologia: voltado a tomadores de decisão e usuários não-técnicos;
2. Resumo Estatístico e Matemático: voltado a estatísticos, cientistas de dados e analistas eleitorais.
"""

import streamlit as st


def render_documentation_content() -> None:
    """Renderiza o conteúdo estruturado em duas abas do guia metodológico e estatístico.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    tabs = st.tabs(
        [
            "Visão Estratégica e Decisões de Projeto (Não-Técnico)",
            "Metodologia Estatística e Matemática (Avançado)",
        ]
    )

    with tabs[0]:
        st.markdown(
            r"""
            ### Propósito e Missão do Projeto
            O projeto **Margem Eleitoral** foi construído para confrontar de forma técnica e transparente
            a crença popular de que divergências entre pesquisas eleitorais e os resultados apurados nas
            urnas eletrônicas seriam sinônimo de manipulação ou fraude.

            A plataforma aplica formulações consolidadas internacionalmente pela [**WAPOR**](https://wapor.org/) (*World Association for Public Opinion Research*)
            e pela [**AAPOR**](https://aapor.org/) (*American Association for Public Opinion Research*), permitindo que qualquer cidadão, jornalista
            ou analista possa auditar o desempenho histórico e a calibração de cada instituto com base em evidências verificáveis.
            Concebida como uma arquitetura modular extensível a múltiplos ciclos eleitorais, a solução tem sua validação
            inicial no MVP com dados de 2022 e 2026, estruturada para abranger outros anos e pleitos futuros.

            ---

            ### As Três Regras Fundamentais para Entender Pesquisas

            #### 1. Pesquisa é Fotografia, Não Previsão do Futuro
            Uma pesquisa eleitoral retrata com fidelidade as intenções dos entrevistados **naquele instante específico** em que
            as entrevistas foram coletadas. Uma eleição é um processo dinâmico: debates televisivos, notícias de última hora,
            migração de votos para candidaturas mais viáveis (*voto útil*) e indecisos que só decidem na fila da votação
            alteram o cenário até o fechamento das urnas.

            #### 2. A Regra de Ouro dos Votos Válidos
            * **Na pesquisa:** O entrevistador pergunta se o eleitor pretende votar em determinado candidato, votar em branco,
              anular ou se ainda está indeciso.
            * **Na urna eletrônica:** A Constituição Federal determina que **apenas os votos válidos são contabilizados**
              (brancos e nulos são expurgados do total).
            * **O erro comum:** Comparar os percentuais brutos de uma pesquisa (onde brancos, nulos e indecisos somam até 15% a 20%)
              diretamente com a apuração oficial do TSE. Para uma comparação honesta, as intenções brutas devem ser
              recalculadas sobre a base de votos válidos.

            #### 3. O Critério Rígido de Véspera (72 Horas)
            Apenas pesquisas cujo campo de coleta terminou a no máximo **72 horas antes da eleição** são comparadas com o resultado
            final da urna. Pesquisas anteriores a esse intervalo servem para entender a tendência e a evolução histórica da campanha
            (o "filme da eleição"), mas não têm validade para teste formal de acerto de véspera.

            ---

            ### Por Que Institutos Sérios Divergem Sem Que Haja Fraude?

            * **Modo de Coleta:** Levantamentos presenciais domiciliares (onde o entrevistador visita a residência) alcançam um perfil
              sociodemográfico ligeiramente distinto de pesquisas telefônicas (CATI via celular) ou pontos de fluxo em vias públicas.
            * **Abstenção Eleitoral:** No Brasil, cerca de 20% a 22% dos eleitores não comparecem às urnas no dia da votação.
              Na pesquisa, quase todos afirmam que pretendem votar. Se os eleitores de determinado candidato se abstêm em maior
              proporção por dificuldades financeiras ou logísticas de transporte, a apuração na urna refletirá essa diferença.
            * **Volatilidade de Reta Final:** Entre 10% e 18% dos eleitores brasileiros definem seu voto definitivo nos últimos 3 dias
              ou no próprio domingo da votação.

            ---

            ### Como Navegar pelos Sete Atos da Aplicação
            1. **Ato 1 (O Princípio da Incerteza):** Entenda como a Lei dos Grandes Números e o Teorema Central do Limite permitem que 2.000 entrevistados representem 156 milhões de eleitores.
            2. **Ato 2 (O Filme da Eleição):** Acompanhe a trajetória longitudinal no agregador dinâmico contínuo com decaimento exponencial e envelopes de incerteza de 80% e 95%.
            3. **Ato 3 (Quem é Menos Rejeitado?):** Explore o termômetro de rejeição eleitoral em gráfico de halteres (Dumbbell Plot), cartões de liderança competitiva e cálculo do teto eleitoral teórico ($100\% - \text{Rejeição}$).
            4. **Ato 4 (A Prova dos Fatos / Confronto de Véspera):** Visualize no Forest Plot se os intervalos de confiança dos institutos (ajustados com $deff$) cobriram a apuração oficial do TSE e confira a Taxa de Cobertura Empírica.
            5. **Ato 5 (Anatomia do Erro e Auditoria):** Analise o Erro Ponderado multivariado ($EP = (1-a)D + aF + 0{,}5X$), a calibração sob a Faixa do Acaso ($P_{90}$) via Monte Carlo e o grid de inclinação longitudinal (*tilt*).
            6. **Ato 6 (O Veredito Científico):** Veja a síntese dos testes inferenciais formais (teste $t$ pareado, Wilcoxon, ANOVA e decomposição de Total Survey Error de Groves et al.) demonstrando por que divergências refletem dinâmicas amostrais e não fraude.
            7. **Ato 7 (Modelo Preditivo & Previsão Eleitoral):** Explore o Modelo Estado-Espaço Hierárquico Calibrado com pós-estratificação pelo Colégio Eleitoral do TSE, calibração empírica pós-1º Turno, simulação Monte Carlo ($t$-Student, $\nu=5$), projeção Waterfall e Análise de Sensibilidade com 13 variantes metodológicas.
            """
        )

    with tabs[1]:
        st.markdown(
            """
            ### Fundamentação Estatística e Modelagem Matemática

            Esta aba apresenta o memorial formal dos algoritmos, equações e testes de hipótese implementados
            no motor analítico (`src/analytics/` e `src/transformations/`).

            ---

            ### 1. Conversão Canônica para Votos Válidos
            A conversão de votos brutos em votos válidos elimina a massa de não-válidos do denominador:
            """
        )
        st.latex(
            r"\hat{p}_{v,i} = \frac{\hat{p}_i}{1 - \frac{\hat{p}_{\text{branco\_nulo}} + \hat{p}_{\text{indeciso}}}{100}}"
        )
        st.markdown(
            """
            Para evitar anomalias decorrentes de arredondamentos divulgados pelos institutos, aplica-se a
            renormalização estocástica vetorial com fechamento estrito em 100,0%:
            """
        )
        st.latex(
            r"\hat{p}_{v,i}^{\text{norm}} = 100 \times \frac{\hat{p}_{v,i}}{\sum_{j=1}^{C} \hat{p}_{v,j}}"
        )

        st.markdown(
            r"""
            ---

            ### 2. Efeito de Delineamento (deff de Kish, 1965)
            As pesquisas eleitorais brasileiras utilizam amostragem estratificada probabilística por múltiplos
            estágios com conglomerados e cotas censitárias (não Amostragem Aleatória Simples).
            A correlação intraclasse ($\rho > 0$) inflaciona a variância amostral teórica:
            """
        )
        st.latex(
            r"\text{Var}(\hat{p}) = deff \times \frac{\hat{p}(1 - \hat{p})}{n}, \quad deff \in [1{,}2; 1{,}5]"
        )
        st.latex(r"SE(\hat{p}) = \sqrt{\text{Var}(\hat{p})}")
        st.markdown(
            """
            O intervalo de confiança bilateral de 95% adotado no Forest Plot e nos testes de cobertura é:
            """
        )
        st.latex(
            r"IC_{95\%} = \left[ \hat{p} - 1{,}96 \times SE(\hat{p}), \quad \hat{p} + 1{,}96 \times SE(\hat{p}) \right]"
        )

        st.markdown(
            r"""
            ---

            ### 3. Métricas Internacionais [WAPOR](https://wapor.org/) / [AAPOR](https://aapor.org/)
            * **Mosteller 3 ($M_3$):** Erro absoluto pontual do candidato líder:
            """
        )
        st.latex(r"M_3 = |\hat{p}_{\text{líder}} - P_{\text{líder}}|")
        st.markdown(
            r"""
            * **Mosteller 5 ($M_5$):** Erro absoluto na margem de vitória ($1º \times 2º$ colocado):
            """
        )
        st.latex(r"M_5 = |(\hat{p}_1 - \hat{p}_2) - (P_1 - P_2)|")
        st.markdown(
            r"""
            * **Log-Odds Ratio de Viés (Métrica A de Martin, Traugott & Mockabee, 2005):**
              Métrica simétrica e aditiva que afasta limites de escala fechada para testar assimetria direcional na razão de chances:
            """
        )
        st.latex(r"A = \ln \left( \frac{\hat{p}_1 / \hat{p}_2}{P_1 / P_2} \right)")

        st.markdown(
            r"""
            ---

            ### 4. Formulação Estrutural do Erro Ponderado (EP)
            Métrica multivariada e politicamente sensível que avalia a eleição como um todo:
            """
        )
        st.latex(r"EP = (1 - a) \times D + a \times F + 0{,}5 \times X")
        st.markdown(
            r"""
            Onde:
            * **$D$ (Disputa Decisiva):** Desvio nas margens críticas ($1º \times 2º$ e $2º \times 3º$) com pesos que decaem exponencialmente pela competitividade real:
              $$w_{1\to 2} = \exp\left(-\frac{\max(0, P_1 - P_2)}{15}\right)$$
            * **$F$ (Eleitorado Fora do Lugar):** Distância de Variação Total ($L_1$) / Índice de Dissimilaridade de Duncan, com peso adaptativo $a = 0{,}50 + 0{,}25 \exp(-|P_1 - 50|/5)$:
              $$F = \frac{1}{2} \left[ \sum_{c} |\hat{p}_c - P_c| + \left| (100 - \sum \hat{p}_c) - (100 - \sum P_c) \right| \right]$$
            * **$X$ (Lado Errado):** Penalização suave atenuada por saturação assintótica para inversão de liderança, inversão da vaga no 2º turno ou inversão da maioria de 50%.

            ---

            ### 5. Distribuição Nula sob H0 e Faixa do Acaso (Monte Carlo)
            Simulação de 10.000 amostras multinomiais $\mathbf{K} \sim \text{Multinomial}(n_{\text{eff}}, \mathbf{P}_{\text{oficial}})$
            com tamanho efetivo $n_{\text{eff}} = \lfloor n / deff \rfloor$.
            Da distribuição empírica nula de $EP$ são extraídos:
            * **$P_{25}$:** Limiar da faixa *Abaixo do Típico*;
            * **Mediana $A_{50}$:** Erro típico sob puro sorteio estocástico;
            * **$P_{75}$:** Limiar superior da faixa *Erro Típico*;
            * **$P_{90}$:** **Faixa do Acaso**. Limite superior dentro do qual 9 em cada 10 amostras puramente aleatórias se situam.

            ---

            ### 6. Agregador Temporal Contínuo e Incerteza Composta
            Ponderação dinâmica diária com decaimento exponencial de meia-vida de 14 dias:
            """
        )
        st.latex(
            r"W_i(t) = \exp\left(-\frac{\ln 2}{14}(t - t_{\text{fim\_campo}})\right) \times w_{\text{qualidade}}(i) \times \sqrt{n_i}"
        )
        st.markdown(
            """
            A incerteza composta integra a variância empírica entre os institutos e a variância amostral efetiva acumulada:
            """
        )
        st.latex(
            r"SE_{\text{total}}(t) = \sqrt{\max\left(0{,}25; \; \text{Var}_{\text{between}}(t) + \text{Var}_{\text{sampling}}(t)\right)}"
        )

        st.markdown(
            r"""
            ---

            ### 7. Decomposição do Total Survey Error (Groves et al., 2004)
            """
        )
        st.latex(
            r"MSE = \text{Bias}^2 + \text{Var}_{\text{Teórica}} + \text{Var}_{\text{Late Swing}} + \text{Var}_{\text{Estrutural}}"
        )
        st.markdown(
            r"""
            * **Teste t pareado e Teste de Wilcoxon:** Verificam se a média e a mediana dos resíduos $(\hat{p}_{v,i} - P_{\text{TSE}})$ diferem de zero ($H_0: \mu = 0$).
            * **ANOVA de Efeitos Fixos (Tipo II):** Avalia se o resíduo concentra significância estatística em institutos específicos ou no vetor metodológico (Presencial vs. CATI).

            ---

            ### 8. Modelo Preditivo Estado-Espaço Hierárquico Calibrado (Ato 7)
            Combina pesquisas **Nacionais**, **Estaduais** e **Regionais** sob pós-estratificação pelo Colégio Eleitoral do TSE ($\omega_{\text{SE}}=0{,}426, \omega_{\text{NE}}=0{,}271, \omega_{\text{S}}=0{,}147, \omega_{\text{N}}=0{,}086, \omega_{\text{CO}}=0{,}070$), correção de House Effects e calibração pós-1º Turno:
            """
        )
        st.latex(
            r"w_{\text{audit}, i} = \exp\left(-\lambda \cdot \text{EP}_{\text{T1}, i}\right), \quad \tilde{y}_{k, c} = y_{k, c}^{(\text{nac})} - \alpha_{\text{shrink}} \cdot \hat{\delta}_{i(k), c}"
        )
        st.latex(
            r"P(\text{Vitória}_A) = \frac{1}{N_{\text{sim}}} \sum_{s=1}^{N_{\text{sim}}} \mathbb{I}\left(\tilde{P}_A^{(s)} > \max_{B \neq A} \tilde{P}_B^{(s)}\right), \quad \tilde{\mathbf{P}}^{(s)} \sim t_{\nu=5}\left(\hat{\boldsymbol{\mu}}(T_{\text{eleição}}), \boldsymbol{\Sigma}_{\text{total}}\right)"
        )
        st.markdown(
            r"""
            ---

            ### 9. Termômetro da Rejeição e Teto Eleitoral Teórico (Ato 3)
            O teto eleitoral teórico de cada concorrente no 2º Turno é formulado por:
            """
        )
        st.latex(r"\text{Teto}_i = 100\% - \text{Rejeição}_i")
        st.markdown(
            r"""
            Diferenças na taxa de rejeição entre dois candidatos dentro do limiar de tolerância $\le 1{,}0$ pp são classificadas formalmente como empate técnico.

            ---

            ### 10. Análise de Sensibilidade Metodológica (13 Variantes)
            Audita a estabilidade da previsão comparando o modelo Principal ($P$) contra 12 variantes metodológicas ($S0$ a $S11$) que testam diferentes janelas de decaimento ($\tau \in [3, 21]$ dias), esquemas de ponderação e limites de voto potencial.
            """
        )


if hasattr(st, "dialog"):

    @st.dialog("Documentação e Metodologia do Projeto", width="large")
    def render_documentation_modal() -> None:
        """Renderiza a janela modal interativa de consulta metodológica e estatística.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        render_documentation_content()

else:

    def render_documentation_modal() -> None:
        """Renderiza a janela modal interativa de consulta metodológica e estatística.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        render_documentation_content()
