# Framework de Total Survey Error (TSE) e Auditoria Antifraude

O projeto **margem_eleitoral** adota o paradigma científico do **Total Survey Error (TSE)** — *Erro Total de Pesquisa* — formalizado por Robert Groves et al. (2004) e Paul Biemer (2010), como estrutura teórica fundamental para auditar a fidedignidade dos levantamentos eleitorais e confrontar formalmente hipóteses de fraude.

---

## O Paradigma do Total Survey Error

No senso comum e no debate político desinformado, existe a falsa presunção de que a **margem de erro amostral** divulgada pelos institutos representaria o erro total máximo possível da pesquisa. Quando a apuração da urna difere da estimativa por um valor superior à margem teórica, setores insatisfeitos frequentemente concluem, sem respaldo técnico, que houve "manipulação" ou "fraude".

A ciência de amostragem moderna demonstra que o erro amostral estocástico é apenas **uma entre diversas fontes concorrentes de erro** em um levantamento empírico. O framework TSE divide o processo em duas dimensões fundamentais:

```
                          Total Survey Error (TSE)
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│     Erro de Representação       │   │       Erro de Medição           │
│    (Quem nós entrevistamos?)   │   │  (O que o eleitor nos disse?)   │
├─────────────────────────────────┤   ├─────────────────────────────────┤
│ • Erro Amostral Estocástico     │   │ • Erro de Instrumento (Perguntas)│
│ • Erro de Cobertura             │   │ • Efeito do Entrevistador       │
│ • Não-Resposta Diferencial      │   │ • Voto Envergonhado / Desejab.  │
│ • Abstenção Diferencial (Urna)  │   │ • Volatilidade / Decisão Tardia │
└─────────────────────────────────┘   └─────────────────────────────────┘
```

---

## Fontes de Incerteza no Contexto Eleitoral Brasileiro

Ao auditar pesquisas para a eleição presidencial no Brasil, identificamos seis componentes críticos do TSE que operam independentemente de qualquer dolo ou manipulação partidária:

### 1. Erro Amostral Estocástico
Decorre da seleção de uma amostra de tamanho $n$ (tipicamente $2{.}000$ a $3{.}000$ eleitores) em vez do censo completo de $156$ milhões de eleitores.
* **Comportamento:** É simétrico, não-intencional e previsível pelas leis da probabilidade (Teorema Central do Limite).
* **Mitigação:** Incorporação do fator de delineamento ($deff \approx 1{,}35$) para compensar a amostragem conglomerada por setores censitários e cotas.

### 2. Erro de Cobertura
Ocorre quando o desenho da amostragem não atinge fatias específicas do eleitorado com a mesma probabilidade:
* **Pesquisas Telefônicas (CATI):** Dependem de posse de telefone celular ativo. Podem sub-representar populações de áreas rurais isoladas, eleitores de extrema vulnerabilidade social ou indivíduos que habitualmente não atendem chamadas de números desconhecidos.
* **Pesquisas Presenciais Domiciliares:** Podem enfrentar barreiras de acesso em condomínios fechados de alta renda ou em áreas urbanas de risco com restrições de segurança pública.

### 3. Erro de Não-Resposta Diferencial
Constitui o principal desafio metodológico contemporâneo da pesquisa de opinião pública mundial.
* Se a taxa de recusa em responder ao questionário fosse homogênea e aleatória em todo o país, a representatividade da amostra seria preservada.
* Contudo, quando a propensão a recusar a entrevista está **politicamente correlacionada** (por exemplo, eleitores desconfiados de instituições ou alinhados a discursos anti-sistema recusando participar da pesquisa em proporção maior que eleitores moderados), o instituto subestima involuntariamente esse segmento, a menos que utilize esquemas sofisticados de pós-estratificação.

### 4. Decisão de Última Hora e Voto Útil (Late Swing)
Pesquisas eleitorais não são urnas antecipadas. O eleitorado brasileiro toma decisões estratégicas cruciais na reta final:
* **Movimentação Pré-Véspera e Véspera ($T-3$ a $T-0$):** Dados do Datafolha e Quaest indicam que entre $10\%$ e $18\%$ dos eleitores decidem seu voto definitivo nos últimos dias da eleição ou no próprio dia da votação.
* **Voto Útil:** Eleitores de terceira via ou candidaturas menores frequentemente migram seus votos de forma abrupta para o primeiro colocado para tentar liquidar a disputa no 1º turno, ou para o segundo colocado para forçar a realização do 2º turno.

### 5. Abstenção Diferencial no Comparecimento à Urna
No Brasil, o voto é formalmente obrigatório, mas a taxa de abstenção histórica gira em torno de **$20\%$ a $21\%$** no primeiro turno (cerca de $30$ a $32$ milhões de cidadãos ausentes).
* Na pesquisa, a pergunta estimulada captura a **intenção subjetiva**, onde mais de $95\%$ dos entrevistados declaram que pretendem votar.
* No dia da eleição, o comparecimento físico efetivo é influenciado por barreiras de transporte, condições climáticas, obrigações de trabalho e desengajamento político.
* Se eleitores com menor escolaridade ou residentes em periferias se abstiverem em taxa $5$ pontos percentuais superior à de eleitores de maior renda, o resultado apurado pelo TSE será diferente da intenção declarada dias antes, **sem que tenha havido qualquer erro de apuração nas urnas eletrônicas**.

---

## Decomposição Algorítmica do Total Survey Error

O módulo `src/analytics/hypothesis_tests.py` implementa a função `decompose_total_survey_error`, que operacionaliza a decomposição formal do Erro Quadrático Médio ($MSE$) com base em Groves et al. (2004):

$$MSE = \text{Bias}^2 + \text{Var}_{\text{Empírica}}$$

Onde:
1. **Viés Médio ($\text{Bias}$):** Diferença entre a média das estimativas de véspera dos institutos e a apuração da urna:
   $$\text{Bias} = \frac{1}{K} \sum_{i=1}^{K} \hat{p}_{v,i} - P_{\text{TSE}}$$
2. **Variância Amostral Teórica ($\text{Var}_{\text{Teórica}}$):** Variância puramente estocástica esperada pelo tamanho das amostras e pelo $deff$:
   $$\text{Var}_{\text{Teórica}} = \frac{1}{K} \sum_{i=1}^{K} \left( deff \times \frac{P_{\text{TSE}}(100 - P_{\text{TSE}})}{n_i} \right)$$
3. **Variância Empírica Observada ($\text{Var}_{\text{Empírica}}$):** Dispersão real observada entre os institutos de véspera:
   $$\text{Var}_{\text{Empírica}} = \frac{1}{K - 1} \sum_{i=1}^{K} \left( \hat{p}_{v,i} - \bar{p}_{\text{véspera}} \right)^2$$
4. **Excesso de Dispersão Não-Amostral ($\text{Var}_{\text{Não-Amostral}}$):**
   $$\text{Var}_{\text{Não-Amostral}} = \max\left(0{,}0; \; \text{Var}_{\text{Empírica}} - \text{Var}_{\text{Teórica}}\right)$$
5. **Variância Atribuível a Movimentação Tardia (Late Swing):**
   Contrastando a série de pesquisas de véspera ($\le 72$h) com os levantamentos de pré-véspera ($T-7$ a $T-3$):
   $$\text{Var}_{\text{Late Swing}} = (\bar{p}_{\text{véspera}} - \bar{p}_{\text{pré-véspera}})^2$$
6. **Variância Estrutural Residual:**
   $$\text{Var}_{\text{Estrutural}} = \max\left(0{,}0; \; \text{Var}_{\text{Não-Amostral}} - \min(\text{Var}_{\text{Não-Amostral}}, \text{Var}_{\text{Late Swing}})\right)$$

Esta decomposição permite quantificar com exatidão científica quanto do desvio observado deveu-se à amostragem, quanto decorreu do voto útil de última hora e quanto resultou de efeitos metodológicos dos institutos.

---

## Formulação dos Testes Formais de Hipótese Antifraude

Para afastar discursos conspiratórios e submeter as alegações de manipulação ao crivo da inferência científica, o sistema formula o seguinte teste formal de hipótese:

$$\begin{cases}
H_0: & \text{As divergências observadas entre as pesquisas e o TSE são consistentes com ruído estocástico,} \\
     & \text{efeito de delineamento (deff), abstenção diferencial e movimentação tardia de voto.} \\
H_1: & \text{Há evidência empírica de desvio sistemático inexplicável ou manipulação fraudulenta.}
\end{cases}$$

O diagnóstico automatizado no Ato 5 da aplicação executa quatro baterias de testes estatísticos complementares:

### 1. Teste t de Student Pareado sobre os Resíduos
Testa se a média dos resíduos das pesquisas de véspera difere estatisticamente de zero:
$$\mu_{\text{resíduo}} = \mathbb{E}[\hat{p}_{v,i} - P_{\text{TSE}}] = 0$$
* **Estatística:** $t = \frac{\bar{d} - 0}{s_d / \sqrt{K}}$
* **Decisão:** Se $p\text{-valor} \ge 0{,}05$, **não se rejeita $H_0$**. Conclui-se que os erros oscilam estocasticamente em torno do zero, descartando viés direcionado contra determinado concorrente.

### 2. Teste de Postos Sinalizados de Wilcoxon
Alternativa não-paramétrica ao teste $t$, imune a premissas de normalidade da distribuição e imune a eventuais institutos com estimativas *outliers*:
* **Hipótese:** Mediana dos resíduos $= 0$.
* **Decisão:** Se $p\text{-valor} \ge 0{,}05$, confirma-se a simetria distributiva das divergências, sem polarização intencional.

### 3. Teste Binomial Exato de Cobertura Nominal
Avalia se a taxa empírica de cobertura dos intervalos de 95% ajustados com $deff$ diverge da probabilidade teórica de $95\%$:
* **Hipótese:** $H_0: \theta = 0{,}95$ vs $H_1: \theta < 0{,}95$ (unilateral à esquerda via `scipy.stats.binomtest`).
* **Decisão:** Avalia se os intervalos de confiança dos institutos foram devidamente calibrados ou se sofreram subcobertura estatística.

### 4. Análise de Variância (ANOVA) para House Effects
Testa se os desvios observados concentram-se em institutos específicos ou em metodologias particulares (presencial vs telefônica):
* **Fórmula:** $\text{Resíduo} \sim \text{C(instituto)} + \text{C(metodologia)}$
* **Decisão:** Se o fator instituto não for estatisticamente significativo ($p > 0{,}05$), afasta-se a tese de que determinado instituto atuou com direcionamento tendencioso em benefício de um candidato.

---

## Síntese do Veredito Científico

A auditoria científica estabelece conclusões transparentes e robustas:

1. **Inexistência de Prova de Fraude nas Divergências:**
   * A apuração das urnas eletrônicas pelo TSE é auditável, auditada por partidos políticos, universidades e forças armadas, e validada por relatórios de totalização e integridade de software.
   * As divergências entre pesquisas e urnas decorrem de dinâmicas mensuráveis de amostragem por cotas, não-resposta assimétrica, abstenção diferencial e decisão de última hora (*late swing*).
2. **Responsabilização Metodológica dos Institutos:**
   * Embora as divergências não constituam fraude, os institutos de pesquisa têm a obrigação técnica de aprimorar continuamente seus modelos de comparecimento provável (*likely voter models*), incorporar o $deff$ no anúncio público de margens de erro e adotar total transparência na divulgação de seus microdados.
3. **Fortalecimento Democrático:**
   * A desmistificação científica do erro amostral protege a integridade das eleições, educa a imprensa e o eleitorado, e substitui discursos passionais por evidências matemáticas auditáveis.
