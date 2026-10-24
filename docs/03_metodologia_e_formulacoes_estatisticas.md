# Metodologia e Formulações Estatísticas

Este documento constitui o tratado matemático e estatístico formal do projeto **Margem Eleitoral**. Todas as equações, deduções e algoritmos implementados no código-fonte são aqui especificados com rigor formal, acompanhados de suas justificativas teóricas e respaldo na literatura científica de amostragem e opinião pública.

---

## 1. Conversão Canônica para Votos Válidos

### 1.1 Justificativa Jurídico-Estatística
A legislação eleitoral brasileira (Constituição Federal de 1988, art. 77, § 2º; Código Eleitoral, Lei nº 4.737/1965, art. 211) estabelece que a proclamação dos resultados eleitorais e a definição do vencedor baseiam-se **exclusivamente na totalização dos votos válidos**, expurgando-se os votos em branco e os votos nulos.

Em levantamentos amostrais estimulados de opinião pública, o instrumento de coleta oferece opções que não constituem voto válido (brancos, nulos, "não sabe", "não respondeu" ou indecisos). Consequentemente, **comparar intenções de voto brutas diretamente com os percentuais apurados na urna eletrônica é um erro matemático elementar**, pois os denominadores das duas razões são distintos.

### 1.2 Formulação Matemática
Seja $\hat{p}_i$ o percentual bruto de intenção de voto do candidato $i$, $\hat{p}_{\text{branco\_nulo}}$ o percentual declarado de votos em branco ou nulos, e $\hat{p}_{\text{indeciso}}$ o percentual de eleitores indecisos ou sem resposta.

O percentual recalculado de votos válidos para o candidato $i$, denotado por $\hat{p}_{v,i}$, é obtido por:

$$\hat{p}_{v,i} = \frac{\hat{p}_i}{1 - \frac{\hat{p}_{\text{branco\_nulo}} + \hat{p}_{\text{indeciso}}}{100}}$$

Para assegurar o fechamento exato em $100{,}0\%$ em face de erros de truncamento ou arredondamento numérico na divulgação dos institutos, o vetor é submetido a uma renormalização vetorial estocástica em `src/transformations/valid_votes.py`:

$$\hat{p}_{v,i}^{\text{norm}} = 100 \times \frac{\hat{p}_{v,i}}{\sum_{j=1}^{C} \hat{p}_{v,j}}$$

onde $C$ é o número total de candidatos listados na pesquisa.

### 1.3 Condições de Fronteira e Invariantes
O algoritmo impõe as seguintes restrições:
* $\hat{p}_{\text{branco\_nulo}} \ge 0$ e $\hat{p}_{\text{indeciso}} \ge 0$;
* $\hat{p}_{\text{branco\_nulo}} + \hat{p}_{\text{indeciso}} < 100{,}0\%$;
* $\sum_{i=1}^{C} \hat{p}_i > 0$;
* Lança exceção tipada `InvalidVoteCalculationError` caso ocorra divisão por zero ou dados degenerados.

---

## 2. Efeito de Delineamento (deff de Kish) e Intervalos de Confiança

### 2.1 Limitações da Amostragem Aleatória Simples (AAS)
A fórmula clássica de erro padrão comumente ensinada em cursos introdutórios pressupõe Amostragem Aleatória Simples com reposição (AAS):

$$SE_{\text{AAS}} = \sqrt{\frac{p(1 - p)}{n}}$$

No contexto de pesquisas eleitorais brasileiras, a AAS é inviável por razões de custo, dispersão geográfica e ausência de cadastro telefônico universal. Os institutos utilizam amostragem probabilística estratificada por múltiplos estágios com seleção sistemática de conglomerados (municípios e setores censitários) e cotas sociodemográficas (gênero, idade, escolaridade e renda).

### 2.2 Formulação do Efeito de Delineamento (Kish, 1965)
A existência de correlação intra-conglomerado ($\rho > 0$) implica que indivíduos residentes na mesma localidade ou pertencentes à mesma cota apresentam maior homogeneidade política entre si do que indivíduos selecionados aleatoriamente pelo país.

Para corrigir a subestimação da variância, aplica-se o fator de correção de efeito de delineamento ($deff$ — *Design Effect*), conceituado por Leslie Kish (1965):

$$deff = \frac{\text{Var}_{\text{Complexa}}(\hat{p})}{\text{Var}_{\text{AAS}}(\hat{p})} = 1 + (m - 1)\rho$$

onde $m$ é o tamanho médio do conglomerado e $\rho$ é a taxa de correlação intraclasse.

### 2.3 Variância Ajustada e Erro Padrão
Para as pesquisas eleitorais brasileiras de amplitude nacional, a literatura empírica fixa $deff \in [1{,}2; 1{,}5]$, com valor modal de calibração em **$deff = 1{,}35$**.

A variância e o erro padrão corrigidos implementados em `src/analytics/metrics.py` são dados por:

$$\text{Var}(\hat{p}) = deff \times \frac{\hat{p}(1 - \hat{p})}{n}$$

$$SE(\hat{p}) = \sqrt{\text{Var}(\hat{p})} = \sqrt{deff \times \frac{\hat{p}(1 - \hat{p})}{n}}$$

### 2.4 Intervalos de Confiança Bilaterais de 95%
Para um nível de confiança nominal de $1 - \alpha = 0{,}95$ ($z_{1 - \alpha/2} = 1{,}95996 \approx 1{,}96$), o intervalo de confiança bilateral é:

$$IC_{95\%} = \left[ \max\left(0{,}0; \; \hat{p} - 1{,}96 \times SE(\hat{p})\right), \quad \min\left(100{,}0; \; \hat{p} + 1{,}96 \times SE(\hat{p})\right) \right]$$

---

## 3. Métricas Padronizadas de Acurácia (WAPOR / AAPOR)

Para avaliar o desempenho e o viés das pesquisas frente aos resultados oficiais das urnas ($P$), o projeto implementa as métricas internacionais da *World Association for Public Opinion Research* (WAPOR) e da *American Association for Public Opinion Research* (AAPOR).

### 3.1 Métrica Mosteller 3 ($M_3$)
Formulada no relatório clássico do *Social Science Research Council* sobre a eleição norte-americana de 1948 (Mosteller et al., 1949), a métrica $M_3$ mede o erro absoluto simples da estimativa do candidato líder:

$$M_3 = |\hat{p}_{\text{líder}} - P_{\text{líder}}|$$

### 3.2 Métrica Mosteller 5 ($M_5$)
A métrica $M_5$ avalia o erro na margem de vitória (diferença entre o primeiro e o segundo colocado):

$$M_5 = |(\hat{p}_1 - \hat{p}_2) - (P_1 - P_2)|$$

O $M_5$ é especialmente sensível em eleições polarizadas, pois captura se o instituto errou a distância competitiva entre os concorrentes principais.

### 3.3 Log-Odds Ratio de Viés Direcional (Métrica A)
Proposta por Martin, Traugott e Mockabee (2005) e adotada pela AAPOR, a métrica $A$ afasta os limites artificiais de escalas percentuais e mede a assimetria na razão de chances (*odds ratio*):

$$A = \ln \left( \frac{\hat{p}_1 / \hat{p}_2}{P_1 / P_2} \right) = \ln \left( \frac{\hat{p}_1}{\hat{p}_2} \right) - \ln \left( \frac{P_1}{P_2} \right)$$

**Propriedades Matemáticas da Métrica A:**
* Se $A = 0$: a razão de chances estimada pelo instituto espelha com perfeição a razão de chances da urna;
* Se $A > 0$: sobrestimação relativa do Candidato 1 em detrimento do Candidato 2;
* Se $A < 0$: sobrestimação relativa do Candidato 2 em detrimento do Candidato 1;
* É estritamente simétrica e aditiva sob inversão de candidatos: $A_{2,1} = -A_{1,2}$.

---

## 4. Formulação Estrutural do Erro Ponderado (EP)

Para além de métricas unidimensionais, a aplicação implementa a decomposição do **Erro Ponderado (EP)** em `calculate_weighted_poll_error`, estruturada em três componentes complementares:

$$EP = (1 - a) \times D + a \times F + 0{,}5 \times X$$

```
              ┌───────────────────────────────────────────────┐
              │             Erro Ponderado (EP)               │
              └──────────────────────┬────────────────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           ▼                         ▼                         ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│ Disputa Decisiva(D) │   │Eleitorado Fora L.(F)│   │  Lado Errado (X)    │
│  Margem ponderada   │   │ Total Variation L1  │   │ Inversão de linhas  │
│ por competitividade │   │     (Duncan Index)  │   │  críticas atenuada  │
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘
```

### 4.1 Componente D: Disputa Decisiva
Avalia os erros nas margens de vitória ($1º \times 2º$) e de classificação para o segundo turno ($2º \times 3º$), com pesos que decaem exponencialmente conforme a margem real se amplia:

$$e_{1\to 2} = (\hat{p}_1 - \hat{p}_2) - (P_1 - P_2)$$
$$w_{1\to 2} = \exp\left( -\frac{\max(0, P_1 - P_2)}{15} \right)$$

Se houver terceiro colocado relevante ($C \ge 3$):
$$e_{2\to 3} = (\hat{p}_2 - \hat{p}_3) - (P_2 - P_3)$$
$$g = \begin{cases} 1{,}0 & \text{se } P_1 < 50\% \\ \exp\left( -\frac{P_1 - 50}{2{,}5} \right) & \text{se } P_1 \ge 50\% \end{cases}$$
$$w_{2\to 3} = g \times \exp\left( -\frac{\max(0, P_2 - P_3)}{15} \right)$$
$$D = \frac{w_{1\to 2} |e_{1\to 2}| + w_{2\to 3} |e_{2\to 3}|}{\max(10^{-6}, w_{1\to 2} + w_{2\to 3})}$$

Se não houver terceiro colocado (ex.: 2º Turno), $D = |e_{1\to 2}|$.

### 4.2 Componente F: Eleitorado Fora do Lugar (Distância de Variação Total $L_1$)
Mede a proporção exata de eleitores que teriam de mudar de voto para a pesquisa espelhar perfeitamente o resultado oficial da urna. Baseia-se no Índice de Dissimilaridade de Duncan (Duncan & Duncan, 1955) e na Distância de Variação Total da teoria da probabilidade:

$$F = \frac{1}{2} \left[ \sum_{c \in \mathcal{C}} |\hat{p}_c - P_c| + \left| \left(100 - \sum_{c} \hat{p}_c\right) - \left(100 - \sum_{c} P_c\right) \right| \right]$$

O peso $a$ atribuído a $F$ é dinâmico e atinge o ápice quando a eleição está na fronteira dos $50\%$ (definição de 1º turno):

$$a = 0{,}50 + 0{,}25 \times \exp\left( -\frac{|P_1 - 50|}{5} \right)$$

### 4.3 Componente X: Penalidade Suave de Fronteiras Decisórias
Penaliza o instituto se a estimativa inverteu uma fronteira substantiva da eleição, atenuando a penalidade caso a margem oficial estivesse muito próxima de zero:

1. **Inversão da Liderança ($X_{\text{lead}}$):**
   $$d_{\text{lead}} = 0{,}5 \times \max\left(0, \max_{c \ne 1} \hat{p}_c - \hat{p}_1\right)$$
   $$\Delta_{\text{lead}} = 0{,}5 \times \max(0, P_1 - P_2)$$
   $$X_{\text{lead}} = d_{\text{lead}} \times \left(1 - \exp(-\Delta_{\text{lead}})\right)$$

2. **Inversão da Vaga no Segundo Turno ($X_{\text{round2}}$):**
   $$d_{\text{round2}} = 0{,}5 \times g \times \max\left(0, \max_{c \notin \{1,2\}} \hat{p}_c - \min(\hat{p}_1, \hat{p}_2)\right)$$
   $$\Delta_{\text{round2}} = 0{,}5 \times \max(0, P_2 - P_3)$$
   $$X_{\text{round2}} = d_{\text{round2}} \times \left(1 - \exp(-\Delta_{\text{round2}})\right)$$

3. **Inversão da Maioria Absoluta de 50% ($X_{50}$):**
   Se $P_1 \ge 50\%$: $d_{50} = \max(0, 50 - \hat{p}_1, \max_{c \ne 1} \hat{p}_c - 50)$.
   Se $P_1 < 50\%$: $d_{50} = \max(0, \max_{c} \hat{p}_c - 50)$.
   $$\Delta_{50} = |P_1 - 50|$$
   $$X_{50} = d_{50} \times \left(1 - \exp(-\Delta_{50})\right)$$

$$X = X_{\text{lead}} + X_{\text{round2}} + X_{50}$$

---

## 5. Simulação de Monte Carlo sob a Hipótese Nula (H0)

Para definir objetivamente se o Erro Ponderado de uma pesquisa decorre do ruído estatístico natural ou de deficiências de campo, a aplicação executa em tempo real o algoritmo `simulate_stochastic_poll_thresholds`:

### 5.1 Algoritmo da Distribuição Nula Estocástica
1. **Definição da População Teórica:** O vetor de proporções da apuração oficial $\mathbf{p}_{\text{oficial}} = (P_1, P_2, \dots, P_C) / 100$ define a probabilidade de sucesso de uma distribuição multinomial.
2. **Tamanho Efetivo de Amostra:** Ajusta-se a amostra mediana pelo efeito de delineamento:
   $$n_{\text{eff}} = \left\lfloor \frac{n}{deff} \right\rfloor$$
3. **Sorteios Multinomiais Sintéticos:** Geram-se $M = 10{.}000$ amostras independentes sob $H_0$ (puro sorteio amostral):
   $$\mathbf{K}^{(m)} \sim \text{Multinomial}(n_{\text{eff}}, \mathbf{p}_{\text{oficial}}), \quad m = 1, \dots, M$$
   $$\hat{\mathbf{p}}^{(m)} = 100 \times \frac{\mathbf{K}^{(m)}}{n_{\text{eff}}}$$
4. **Cálculo do Erro Ponderado:** Para cada vetor sintético $\hat{\mathbf{p}}^{(m)}$, computa-se $EP^{(m)}$ em relação a $\mathbf{p}_{\text{oficial}}$.

### 5.2 Limiares de Calibração Empírica
Da distribuição ordenada dos $10{.}000$ valores simulados de $EP^{(m)}$, extraem-se os percentis:
* **Percentil 25 ($P_{25}$):** Limiar superior da faixa **"Abaixo do Típico"** (pesquisas com precisão acima da média amostral);
* **Mediana ($P_{50}$ ou $A_{50}$):** Mediana do erro puramente estocástico;
* **Percentil 75 ($P_{75}$):** Limiar superior da faixa **"Erro Típico"**;
* **Percentil 90 ($P_{90}$):** **Faixa do Acaso**. Em $9$ de cada $10$ pesquisas perfeitas sorteadas sob pura aleatoriedade, o Erro Ponderado situa-se abaixo desse valor. Pesquisas cujo erro observado está abaixo de $P_{90}$ encontram-se rigorosamente dentro da margem de plausibilidade estocástica.

---

## 6. Agregador Dinâmico Contínuo de Pesquisas

O modelo de agregação temporal implementado em `src/analytics/aggregator_model.py` reconstrói a trajetória latente do eleitorado sem a instabilidade de médias móveis simples e sem o atraso de filtros defasados.

### 6.1 Função de Decaimento Temporal Exponencial
Uma pesquisa realizada há 30 dias não pode ter o mesmo peso de um levantamento concluído ontem. Adota-se o modelo de meia-vida de 14 dias (Silver, 2012; Jackman, 2005):

$$w_{\text{tempo}}(t) = \exp \left( -\frac{\ln(2)}{14} \cdot (t_{\text{ref}} - t_{\text{fim\_campo}}) \right)$$

Se a pesquisa for posterior à data de referência ($t_{\text{fim\_campo}} > t_{\text{ref}}$), $w_{\text{tempo}}(t) = 0$.

### 6.2 Ponderação por Qualidade Metodológica e Tamanho de Amostra
O peso total da pesquisa $i$ no instante $t$ é:

$$W_i(t) = w_{\text{tempo}}(t) \times w_{\text{qualidade}}(i) \times \sqrt{n_i}$$

Os pesos de qualidade $w_{\text{qualidade}}$ são calibrados conforme o histórico de cobertura:
* Presencial Domiciliar: $1{,}10$
* Online: $1{,}05$
* Telefônica CATI: $1{,}00$
* Presencial em Pontos de Fluxo: $0{,}90$
* Telefônica URA: $0{,}85$

### 6.3 Estimador Ponderado Diário
Para cada dia $t$, a intenção latente média do candidato $c$ é:

$$\hat{\mu}_c(t) = \frac{\sum_{i=1}^{K} W_i(t) \hat{p}_{v,i,c}}{\sum_{i=1}^{K} W_i(t)}$$

### 6.4 Envelopes de Credibilidade (80% e 95%)
A incerteza do agregador combina dois componentes ortogonais:
1. **Variância entre pesquisas ($\text{Var}_{\text{between}}$):** Dispersão empírica observada entre as estimativas de diferentes institutos contemporâneos:
   $$\text{Var}_{\text{between}}(t) = \sum_{i=1}^{K} \frac{W_i(t)}{\sum_j W_j(t)} \left( \hat{p}_{v,i,c} - \hat{\mu}_c(t) \right)^2$$
2. **Variância amostral efetiva ($\text{Var}_{\text{sampling}}$):** Amostra efetiva acumulada pelo conjunto de pesquisas:
   $$n_{\text{eff, agg}}(t) = \frac{\left(\sum_i W_i(t)\right)^2}{\sum_i W_i(t)^2}$$
   $$\text{Var}_{\text{sampling}}(t) = deff \times \frac{\hat{\mu}_c(t) (100 - \hat{\mu}_c(t))}{\max(100, n_{\text{eff, agg}}(t))}$$

O erro padrão total é:
$$SE_{\text{total}}(t) = \sqrt{\max\left(0{,}25; \; \text{Var}_{\text{between}}(t) + \text{Var}_{\text{sampling}}(t)\right)}$$

Bandas de incerteza:
* **Envelope de 80%:** $\hat{\mu}_c(t) \pm 1{,}28155 \times SE_{\text{total}}(t)$
* **Envelope de 95%:** $\hat{\mu}_c(t) \pm 1{,}95996 \times SE_{\text{total}}(t)$

---

## 7. Modelagem de Efeitos de Casa (House Effects) e ANOVA

### 7.1 Regressão Linear com Efeitos Fixos (GLM / OLS)
Para testar formalmente se as discrepâncias de estimativas são provocadas pela marca do instituto ou pelo método de coleta, ajusta-se o modelo linear em `src/analytics/house_effects.py`:

$$\text{Resíduo}_{i,j} = (\hat{p}_{v,i} - P_{\text{TSE}}) = \beta_0 + \sum_{k} \beta_{\text{inst},k} I_{i,k} + \sum_{m} \beta_{\text{met},m} M_{i,m} + \varepsilon_i$$

A significância conjunta dos fatores é avaliada pela tabela de **Análise de Variância (ANOVA) de Tipo II**:
* Se $p_{\text{instituto}} < 0{,}05$: rejeita-se a hipótese nula de que os institutos compartilham a mesma calibração média;
* Se $p_{\text{metodologia}} < 0{,}05$: há evidência de que a tecnologia de abordagem (presencial vs telefônica) induz viés sistemático.

### 7.2 Inclinação Longitudinal de Campanha (Small Multiples Tilt)
Para isolar a inclinação de cada empresa sem depender do resultado final da urna, o algoritmo `compute_campaign_house_effects` calcula o desvio de cada pesquisa em relação ao **consenso de pares concorrentes** em uma janela móvel de $\pm 7$ dias:

$$\text{Tilt}_{i,k} = (\hat{p}_{1,i} - \hat{p}_{2,i}) - \bar{m}_{\text{concorrentes}}(t_i \pm 7\text{ dias})$$

Para cada instituto $I$, calcula-se a média longitudinal $\bar{\delta}_I$ e o respectivo intervalo de confiança via distribuição $t$ de Student com $n_I - 1$ graus de liberdade ao nível de 80%:

$$IC_{80\%}(\bar{\delta}_I) = \bar{\delta}_I \pm t_{0{,}90; \, n_I - 1} \times \frac{s_I}{\sqrt{n_I}}$$

Se o intervalo cobre o zero ($IC \cap \{0\} \ne \emptyset$), o instituto operou em conformidade com o consenso médio de mercado. Se todo o intervalo estiver estritamente acima de zero, o instituto exibiu viés estrutural favorável ao Candidato 1.

---

## 8. Modelagem de Rejeição e Teto Eleitoral Teórico (Ato 3)

O módulo `src/analytics/rejection_analysis.py` modela a aversão declarada dos eleitores a cada candidatura ("não votaria de jeito nenhum"):

### 8.1 Agregação e Média Simples de Rejeição
Para um conjunto de pesquisas com rejeição declarada, a taxa média observada do candidato $c$ é obtida por:

$$\bar{R}_c = \frac{1}{K_c} \sum_{k=1}^{K_c} R_{k, c}$$

onde $K_c$ é a quantidade de pesquisas com medição válida para o candidato $c$.

### 8.2 Teto Eleitoral Teórico
Em disputas polarizadas de 2º Turno, a taxa de rejeição define a barreira superior intransponível de crescimento eleitoral, sob a premissa de que eleitores com aversão categórica não são convertíveis:

$$\text{Teto}_c = 100\% - \bar{R}_c$$

Se um concorrente exibe rejeição de $52{,}0\%$, seu teto máximo teórico é de $48{,}0\%$, tornando matematicamente improvável a vitória sem a quebra prévia da resistência subjetiva do eleitorado.

### 8.3 Classificação de Liderança e Empate Técnico em Rejeição
Dada a natureza sensível da métrica, diferenças entre dois concorrentes dentro de um limiar $\epsilon = 1{,}0$ ponto percentual são formalmente tratadas como empate técnico:

$$\text{Veredito} = \begin{cases} 
\text{"Empate Técnico"}, & \text{se } |R_1 - R_2| \le 1{,}0\text{ pp} \\
\text{"Candidato 1 menos rejeitado"}, & \text{se } R_1 < R_2 - 1{,}0 \\
\text{"Candidato 2 menos rejeitado"}, & \text{se } R_2 < R_1 - 1{,}0
\end{cases}$$

---

## 9. Modelo Preditivo Estado-Espaço Hierárquico Calibrado (Ato 7)

Implementado em `src/analytics/predictive_model.py`, o modelo preditivo sintetiza pesquisas em múltiplos recortes territoriais com pós-estratificação demográfica, de-biasing histórico e simulação estocástica de trajetórias.

### 9.1 Ponderação de Escopo Geográfico
Pesquisas com abrangências distintas recebem pesos proporcionais à sua cobertura amostral:

$$w_{\text{escopo}} = \begin{cases}
1{,}00, & \text{Nacional} \\
0{,}75, & \text{Estadual} \\
0{,}45, & \text{Regional (Macrorregião)}
\end{cases}$$

### 9.2 Pós-Estratificação pelo Colégio Eleitoral do TSE
O eleitorado nacional é repartido em 5 macrorregiões oficiais do TSE com os respectivos pesos demográficos $\omega_r$:

$$\omega_{\text{SE}} = 0{,}426, \quad \omega_{\text{NE}} = 0{,}271, \quad \omega_{\text{S}} = 0{,}147, \quad \omega_{\text{N}} = 0{,}086, \quad \omega_{\text{CO}} = 0{,}070$$

A intenção latente nacional $\hat{\mu}_{\text{nac}}(t)$ é a média ponderada das intenções projetadas regionalmente:

$$\hat{\mu}_{\text{nac}}(t) = \sum_{r \in \{\text{SE, NE, S, N, CO}\}} \omega_r \hat{\mu}_r(t)$$

Para garantir consistência estocástica, os diferenciais estruturais regionais $D_{r, c}$ (em relação à média nacional) satisfazem a condição de soma-zero estrita:

$$\sum_{r} \omega_r D_{r, c} = 0{,}0$$

### 9.3 Calibração Empírica Pós-1º Turno (De-biasing)
No 2º Turno, o modelo aproveita o desempenho verificado de cada instituto no 1º Turno:
1. **Ponderação por Precisão Auditada:** O peso de auditoria decai exponencialmente com o Erro Ponderado no 1º Turno ($EP_{\text{T1}}$):
   $$w_{\text{audit}, i} = \exp\left(-\lambda \cdot EP_{\text{T1}, i}\right), \quad \lambda = 0{,}25$$
2. **Encolhimento de Viés Direcional (Bias Shrinkage):** A estimativa é corrigida pelo viés histórico encolhido em direção a zero:
   $$\tilde{y}_{k, c} = y_{k, c} - \alpha_{\text{shrink}} \cdot \hat{\delta}_{i(k), c}, \quad \alpha_{\text{shrink}} = 0{,}45$$

### 9.4 Simulação de Monte Carlo com Caudas Pesadas ($t$-Student, $\nu = 5$)
Para modelar choques eleitorais inesperados e volatilidade de reta final com maior realismo que a curva normal, os $N_{\text{sim}} = 10{.}000$ cenários de resultado na data da eleição $T_{\text{eleição}}$ são gerados a partir de uma distribuição multivariada $t$ de Student com $\nu = 5$ graus de liberdade:

$$\tilde{\mathbf{P}}^{(s)} \sim t_{\nu=5}\left(\hat{\boldsymbol{\mu}}(T_{\text{eleição}}), \; \boldsymbol{\Sigma}_{\text{total}}\right), \quad s = 1, \dots, N_{\text{sim}}$$

onde $\boldsymbol{\Sigma}_{\text{total}} = \boldsymbol{\Sigma}_{\text{amostral}} + \boldsymbol{\Sigma}_{\text{tempo}} + \boldsymbol{\Sigma}_{\text{estrutural}}$ incorpora o erro de amostragem acumulado, a incerteza de momentum e o resíduo do Total Survey Error.

A probabilidade empírica de vitória do Candidato $A$ é dada pela proporção de trajetórias simuladas em que $A$ supera os demais concorrentes:

$$P(\text{Vitória}_A) = \frac{1}{N_{\text{sim}}} \sum_{s=1}^{N_{\text{sim}}} \mathbb{I}\left( \tilde{P}_A^{(s)} > \max_{B \neq A} \tilde{P}_B^{(s)} \right)$$

### 9.5 Backtesting Retroativo (Point-in-Time) e Portões de Qualidade
Para assegurar ausência de vazamento de dados futuros (*data leakage*), o algoritmo simula a data de corte em horizontes retrospectivos ($T-30, T-21, T-14, T-7, T-3, T-1$). O modelo deve atender aos seguintes portões formais de promoção:
* Erro absoluto médio do líder: $M_3 \le 2{,}0$ pp;
* Erro médio na margem: $M_5 \le 3{,}5$ pp;
* Calibração probabilística: Brier Score $\le 0{,}15$;
* Taxa de cobertura nominal empírica do envelope de 95%: $\ge 80{,}0\%$.

---

## 10. Análise de Sensibilidade Metodológica (13 Variantes)

O motor analítico implementado em `src/analytics/sensitivity_analysis.py` submete as projeções a um teste de estresse contra 12 formulações concorrentes ($S0$ a $S11$), garantindo que a previsão do modelo Principal ($P$) não seja um artefato espúrio de hiperparâmetros arbitrários:

| Código | Variante Metodológica | Racional e Regra de Ajuste |
| :---: | :--- | :--- |
| **$P$** | **Modelo Principal Oficial** | Pós-estratificação TSE, calibração T1, meia-vida $\tau=14$d, Monte Carlo $t$-Student ($\nu=5$). |
| **$S0$** | Média Aritmética Simples | Sem decaimento temporal nem ponderação amostral ou metodológica. |
| **$S1$** | Ponderação por Amostra ($\sqrt{n}$) | Pondera exclusivamente pelo volume amostral, sem decaimento temporal. |
| **$S2$** | Decaimento Exponencial Acelerado | Meia-vida ultra-curta de 3 dias ($\tau=3$d), priorizando extrema volatilidade. |
| **$S3$** | Decaimento Exponencial Conservador | Meia-vida longa de 21 dias ($\tau=21$d), suavizando oscilações pontuais. |
| **$S4$** | Ponderação Estrita de Qualidade | Pondera apenas pelo método de coleta (Presencial Domiciliar = 1,10; CATI = 1,00; URA = 0,85). |
| **$S5$** | Calibração de Viés de 1º Turno Pura | Aplica de-biasing com base no histórico do 1º Turno sem ajuste de escopo regional. |
| **$S6$** | Correção de Consenso Contemporâneo | Subtrai o viés longitudinal relativo frente aos pares na janela de $\pm 7$ dias (*peer tilt*). |
| **$S7$** | De-biasing Duplo (T1 + Peer Tilt) | Combina simultaneamente o encolhimento de viés do 1º Turno e a correção por pares. |
| **$S8$** | Re-ponderação Subnacional TSE Pura | Aplica exclusivamente a pós-estratificação pelas 5 macrorregiões do Colégio Eleitoral. |
| **$S9$** | Limite Superior de Teto por Rejeição | Trunca o percentual projetado pelo teto teórico derived da rejeição ($100\% - \text{Rejeição}$). |
| **$S10$** | Simulação Normal Gaussiana Leve | Substitui a cauda pesada de $t$-Student por distribuição normal padrão ($\nu \to \infty$). |
| **$S11$** | Modelo Integrado com Voto Potencial | Incorpora os eleitores indecisos a partir de modelos de propensão e rejeição cruzada. |

