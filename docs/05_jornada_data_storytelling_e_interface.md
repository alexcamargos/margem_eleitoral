# Jornada de Data Storytelling e Guia da Interface

A interface da aplicação **Margem Eleitoral** foi projetada para transformar dados estatísticos complexos e modelos matemáticos de alta densidade em uma experiência fluida, acessível e esclarecedora para o cidadão comum, jornalistas, gestores e especialistas.

Este documento detalha o roteiro narrativo em sete atos sequenciais, os cartões executivos superiores, os componentes visuais em Plotly e os recursos interativos de simulação, auditoria e sincronização contínua.

---

## O Roteiro Narrativo em Sete Atos

A experiência do usuário é guiada por uma estrutura pedagógica em sete atos sequenciais, concebida para desconstruir gradualmente preconceitos e construir o entendimento científico das pesquisas eleitorais:

```mermaid
flowchart LR
    Act1["Ato 1: O Princípio da Incerteza\n(Tamanho da amostra e TCL)"] --> 
    Act2["Ato 2: O Filme da Eleição\n(Agregador e Trajetória Temporal)"] --> 
    Act3["Ato 3: Quem é Menos Rejeitado?\n(Dumbbell Plot e Teto Eleitoral)"] --> 
    Act4["Ato 4: A Prova dos Fatos\n(Forest Plot e Cobertura de Véspera)"] --> 
    Act5["Ato 5: Anatomia do Erro\n(Erro Ponderado e Small Multiples)"] --> 
    Act6["Ato 6: O Veredito Científico\n(Inferência Formal e Total Survey Error)"] --> 
    Act7["Ato 7: Modelo Preditivo\n(Nowcasting e Projeção Monte Carlo)"]
```

---

## Hero Executive Story Cards (Síntese no Topo da Aplicação)

Antes da navegação pelos atos, o topo da interface apresenta os **Hero Executive Story Cards** (`src/presentation/components/executive_story_cards.py`), sintetizando de forma visual e imediata:
1. **Status Competitivo Atual:** Percentual estimado do líder e do vice-líder pelo Agregador Dinâmico Contínuo, com bandas de credibilidade de 95% e indicador de tendência diária (*momentum* em pp/dia).
2. **Projeção do Modelo Preditivo (Ato 7):** Probabilidade de vitória calibrada ($P(\text{Vitória})$), votação esperada em votos válidos e distância até o limiar de vitória.
3. **Placar de Apuração do TSE:** Totalização oficial apurada das urnas ou contador de dias restantes para a votação com contagem de pesquisas catalogadas.

---

## Detalhamento dos Atos Narrativos

### Ato 1: O Princípio da Incerteza
* **Objetivo:** Desmistificar o dilema intuitivo de como uma amostra de $\approx 2{.}000$ entrevistados consegue representar fielmente um universo de $156$ milhões de eleitores.
* **Componente Interativo:** *Simulador de Amostragem da Lei dos Grandes Números e Teorema Central do Limite* (`src/presentation/components/simulator.py`).
* **Controles Interativos:**
  * Tamanho da amostra ($n$ de $500$ a $5{.}000$);
  * Intenção real no universo ($p_{\text{real}}$ de $30\%$ a $70\%$);
  * Efeito de delineamento ($deff$ de $1{,}0$ a $2{,}0$);
  * Número de pesquisas simuladas ($200$ a $2{.}000$).
* **Entrega Cognitiva:** O usuário visualiza o histograma das amostras simuladas convergindo perfeitamente para a curva normal em forma de sino, compreendendo por que $95\%$ dos levantamentos caem dentro da margem teórica calculada.

### Ato 2: O Filme da Eleição (Agregador Dinâmico)
* **Objetivo:** Demonstrar que pesquisas capturam momentos voláteis e não o resultado final estático, ensinando a enxergar a trajetória longitudinal e não levantamentos isolados.
* **Componente Interativo:** *Trend Chart do Agregador Dinâmico* (`src/presentation/components/trend_chart.py`).
* **Recursos Visuais:**
  * Linhas contínuas de trajetória por candidato;
  * Fitas de incerteza e envelopes de credibilidade sombreados de $80\%$ e $95\%$;
  * Dispersão pontual de cada pesquisa registrada com opacidade proporcional ao seu peso estatístico ($W_i = w_{\text{tempo}} \times w_{\text{qualidade}} \times \sqrt{n_i}$);
  * Linhas verticais indicando marcos substantivos da campanha (início do horário eleitoral na TV, debates de grande repercussão, etc.).
* **Controles Interativos:**
  * Filtro metodológico (Todas, Presenciais Domiciliares, Telefônicas CATI, Online);
  * Alternância entre *Votos Válidos Recalculados* e *Votos Totais Brutos*.

### Ato 3: Quem é Menos Rejeitado? (Termômetro da Rejeição)
* **Objetivo:** Auditar as taxas de rejeição ("não votaria de jeito nenhum") e compreender o impacto do teto eleitoral na disputa de 2º Turno.
* **Componentes Interativos:**
  * **Gráfico de Halteres (*Dumbbell / Cleveland Dot Plot*):** Exibe a rejeição de cada concorrente instituto a instituto em linha horizontal conectando os dois pontos (`src/presentation/components/dumbbell_chart.py`);
  * **Cards Executivos de Rejeição Média:** Exibe a média aritmética da rejeição de cada candidato e a vantagem relativa em pontos;
  * **Teto Eleitoral Teórico:** Mede o teto máximo atingível ($\text{Teto}_i = 100\% - \text{Rejeição}_i$), indicando a inviabilidade de vitórias sem reversão de aversão política.

### Ato 4: A Prova dos Fatos (Pesquisas de Véspera vs. Urna)
* **Objetivo:** Confrontar de forma honesta as últimas estimativas divulgadas pelos institutos com o resultado oficial apurado pelo Tribunal Superior Eleitoral.
* **Critério de Inclusão Científica:** Estritamente pesquisas cujo campo de coleta encerrou a no máximo 72 horas antes da abertura das urnas ($t_{\text{eleição}} - t_{\text{fim\_campo}} \le 3\text{ dias}$).
* **Componente Interativo:** *Forest Plot de Véspera* (`src/presentation/components/forest_plot.py`).
* **Elementos Visuais:**
  * Eixo Y: Nomes dos institutos ordenados por proximidade temporal da eleição;
  * Eixo X: Percentual de votos válidos para o candidato selecionado no dropdown;
  * Barras horizontais de erro: Estimativa pontual $\pm 1{,}96 \times SE_{\text{ajustado}}$ (incorporando o $deff$ de Kish);
  * Linha vertical sólida contrastante: Apuração oficial da urna no TSE.
* **Métrica Central em Destaque:**
  * **Taxa de Cobertura Empírica:** Percentual de intervalos de confiança que cruzam a linha da apuração oficial frente à meta nominal teórica de $95\%$, com teste binomial exato de calibração.

### Ato 5: Anatomia do Erro e Auditoria de Institutos
* **Objetivo:** Fornecer um painel aprofundado de auditoria e responsabilização dos institutos em duas camadas complementares:
  1. *Camada de Impacto Eleitoral:* Erro Ponderado multivariado ($EP = (1-a)D + aF + 0{,}5X$) e calibração estocástica dinâmica via simulação de Monte Carlo.
  2. *Camada de Auditoria Científica:* Métricas consagradas WAPOR/AAPOR ($M_3$, $M_5$, Log-Odds $A$) e taxas de acerto da margem.
* **Componentes Visuais:**
  * **Gráfico de Barras Segmentadas de Erro Ponderado:** Decomposição visual dos erros divididos por faixas (*Abaixo do Típico* vs. *Erro Típico*) com a linha tracejada da *Faixa do Acaso ($P_{90}$)* derivada via Monte Carlo (`src/presentation/components/bar_error_chart.py`);
  * **Tabela Interativa e Auditável:** Tabela classificatória com busca, ordenação dinâmica por qualquer métrica de erro, data de campo e tamanho de amostra;
  * **Grid de Small Multiples de Inclinação Longitudinal (Tilt):** Matriz de subplots exibindo a inclinação de cada instituto em relação ao consenso de mercado em janelas móveis de $\pm 7$ dias, com intervalo $t$-Student de $80\%$ (`src/presentation/components/small_multiples.py`);
  * **Caixa Metodológica Expansível:** Memorial com todas as equações matemáticas exibidas em LaTeX para conferência técnica imediata.

### Ato 6: O Veredito Científico (Diagnóstico do TSE)
* **Objetivo:** Sintetizar o diagnóstico formal de inferência estatística respondendo de forma conclusiva à pergunta: *"Divergências pontuais configuram fraude eleitoral?"*.
* **Bateria de Diagnósticos Automatizados:**
  * Cards interativos com resultados do Teste $t$ de Student pareado, Teste de Wilcoxon e Teste Binomial exato;
  * Tabela de Análise de Variância (ANOVA de Tipo II) para isolar efeitos sistemáticos de institutos (*house effects*) e metodologia;
  * Decomposição formal do Total Survey Error ($MSE = \text{Bias}^2 + \text{Var}_{\text{Amostral}} + \text{Var}_{\text{Late Swing}} + \text{Var}_{\text{Estrutural}}$);
  * Parecer conclusivo fundamentado nos dados sobre abstenção diferencial e volatilidade de última hora.

### Ato 7: Modelo Preditivo & Previsão Eleitoral
* **Objetivo:** Projetar o desfecho da eleição utilizando um modelo estado-espaço com pós-estratificação pelo Colégio Eleitoral do TSE, calibração empírica pós-1º Turno e simulação de Monte Carlo com caudas pesadas.
* **Componentes Visuais:**
  * **Card de Projeção Waterfall:** Visualiza a contribuição líquida de cada macrorregião (SE, NE, S, N, CO) para a formação da maioria nacional (`src/presentation/components/waterfall_projection_card.py`);
  * **Gráficos de Densidade Probabilística:** Curvas de distribuição com caudas pesadas ($t$-Student, $\nu=5$) e probabilidade empírica de vitória;
  * **Tabela de Análise de Sensibilidade Metodológica:** Compara a projeção do modelo Principal contra 12 variantes metodológicas ($S0$ a $S11$) (`src/presentation/components/sensitivity_table_card.py`);
  * **Painel de Validação Retroativa (Point-in-Time Backtesting):** Demonstra o comportamento preditivo do modelo em diferentes datas de corte históricas ($T-30$ a $T-1$) sem vazamento de dados futuros.

---

## Modais de Apoio ao Usuário

A aplicação conta com dois modais de acesso rápido presentes no cabeçalho e na barra lateral:
1. **Modal de Consulta de Pesquisas (`src/presentation/components/polls_list_modal.py`):**
   * Acionado via botão "🗳️ Consultar Pesquisas";
   * Exibe a lista exaustiva de todas as pesquisas analisadas, com filtros por instituto, metodologia, período e visualização dos votos brutos, válidos, amostra e link oficial de registro no PesqEle do TSE.
2. **Modal de Documentação e Metodologia (`src/presentation/components/documentation_modal.py`):**
   * Acionado via botão "📖 Consultar Metodologia";
   * Apresenta duas abas temáticas: uma estratégica não-técnica e outra matemática avançada com todas as formulações em LaTeX.

---

## Sistema de Design Visual e Identidade da Interface

A interface adota a estética de **jornalismo analítico profissional em Dark Mode** (estilo *Plano Político* e *FiveThirtyEight*), desenhada para maximizar legibilidade, contraste e densidade de informação:

* **Paleta de Cores do Tema Dark Mode:**
  * Fundo da aplicação: `#121417` (cinza escuro profundo, reduzindo fadiga visual);
  * Superfície dos cartões e contêineres: `#181B20` com bordas sutis em `#282D37`;
  * Tipografia principal: `#F8FAFC` (branco suave) e `#CBD5E1` (cinza claro);
  * Badges de erro abaixo do típico: `#10B981` (verde esmeralda);
  * Badges de erro típico e alertas: `#F59E0B` (âmbar dourado);
  * Badges de erro acima do típico: `#EF4444` (vermelho carmim);
  * Linha oficial da urna TSE: `#F8FAFC` com halo contrastante.
* **Componentes Responsivos em Plotly:**
  * Todos os gráficos possuem tooltips informativos em formato HTML nativo;
  * Altura calculada dinamicamente conforme a quantidade de institutos auditados;
  * Suporte a zoom sincronizado e download direto da imagem em alta resolução.

---

## Sincronização Contínua, Multi-Cargos e Multi-Ciclos

Para viabilizar o acompanhamento contínuo da eleição em tempo real e a expansão para outros pleitos, a barra lateral da aplicação integra um módulo de controle:

1. **Seletor de Ano, Cargo e Estado (UF):**
   * Permite alternar instantaneamente entre os ciclos eleitorais de **2018**, **2022** e **2026**;
   * Permite alternar entre os cargos de **Presidente**, **Governador** e **Senador**;
   * Para cargos subnacionais (Governador e Senador), ativa dinamicamente a filtragem por **Estado (UF)** com mapeamento automático de todas as 27 unidades federativas.
2. **Formulário de Inserção de Pesquisa em Tempo Real:**
   * Permite cadastrar um novo levantamento de 2º Turno informando registro no TSE, instituto, metodologia, tamanho de amostra e percentuais brutos dos concorrentes.
   * O sistema valida as entradas contra o `ElectoralGatekeeper` (rejeitando multi-candidatos no 2T e conferindo fechamento ~100%), recalcula os votos válidos com validação estrita via Pydantic e injeta os dados na sessão.
3. **Integração com Dados Abertos do TSE e Feeds Web:**
   * Sincronização direta de novas pesquisas via API/Portal de Dados Abertos do TSE ou feed web aberto.
