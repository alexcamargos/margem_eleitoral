# Referências Bibliográficas e Normas Técnicas

Este documento reúne o arcabouço bibliográfico, as normas profissionais internacionais e a legislação eleitoral brasileira que fundamentam todas as decisões metodológicas, estatísticas e de engenharia de dados do projeto **margem_eleitoral**.

---

## Normas Profissionais e Códigos de Ética Internacionais

### 1. WAPOR (World Association for Public Opinion Research)
* **WAPOR Code of Professional Ethics and Practices (2021):**
  * Estabelece os padrões éticos e as boas práticas metodológicas para levantamentos eleitorais globais.
  * Determina a obrigatoriedade de divulgação pública de todos os parâmetros técnicos de campo: tamanho da amostra ($n$), margem de erro associada ao nível de confiança, método de amostragem, taxa de resposta, período exato de coleta e redação literal do questionário.
  * Recomenda que a apuração e o cotejamento com resultados eleitorais oficiais sejam realizados estritamente sobre a base de votos válidos recalculados.
* **WAPOR/ESOMAR Guideline on Opinion Polls and Published Surveys (2022):**
  * Diretrizes conjuntas sobre o reporte transparente de pesquisas de opinião na imprensa e na mídia digital, alertando sobre a necessidade de contextualização das incertezas amostrais e não-amostrais.

### 2. AAPOR (American Association for Public Opinion Research)
* **AAPOR Code of Professional Ethics and Practices (Revised 2020):**
  * Norma de referência para transparência metodológica e reprodutibilidade científica em ciências sociais quantitativas.
* **AAPOR Task Force on 2016 and 2020 Pre-Election Polling Reports (2017, 2021):**
  * Estudos seminais sobre erro de não-resposta diferencial, volatilidade de eleitores indecisos e a importância de modelos de probabilidade de comparecimento (*likely voter models*).
  * Formalização das métricas padronizadas de avaliação de precisão de véspera ($M_3$, $M_5$ e Log-Odds $A$).

---

## Legislação Eleitoral e Resoluções Normativas do Brasil

### 1. Marco Constitucional e Legal
* **Constituição da República Federativa do Brasil de 1988:**
  * **Art. 77, § 2º:** *“Será considerado eleito Presidente o candidato que, registrado por partido político, obtiver a maioria absoluta de votos, não computados os em branco e os nulos.”* Fundamento jurídico que torna mandatório o expurgo de brancos e nulos em qualquer comparação técnica com a urna.
* **Lei Federal nº 4.737, de 15 de julho de 1965 (Código Eleitoral):**
  * **Art. 211:** Estabelece a regra geral de cômputo dos votos válidos na apuração dos pleitos majoritários e proporcionais.
* **Lei Federal nº 9.504, de 30 de setembro de 1997 (Lei das Eleições):**
  * **Art. 33 a 35:** Fixa a obrigatoriedade de registro prévio de todas as pesquisas eleitorais perante a Justiça Eleitoral até cinco dias antes de sua divulgação pública, com especificação detalhada de contratante, metodologia e plano amostral.

### 2. Resoluções Normativas do Tribunal Superior Eleitoral (TSE)
* **Resolução TSE nº 23.600, de 12 de dezembro de 2019:**
  * Regulamenta os procedimentos para registro e divulgação de pesquisas eleitorais, operacionalizando o Sistema de Registro de Pesquisas Eleitorais (**PesqEle**).
  * Exige o depósito de questionários, indicação de bairros e municípios sorteados, descrição das variáveis de ponderação e declaração do profissional estatístico responsável com respectivo registro no CONRE (Conselho Regional de Estatística).
* **Resolução TSE nº 23.676, de 16 de dezembro de 2021:**
  * Dispõe sobre o acesso público e a integridade dos dados de registro no Portal de Dados Abertos do TSE, base consumida pelo coletor automatizado deste projeto (`src/ingestion/pesqele_collector.py`).

---

## Bibliografia Científica e Artigos Seminais

### 1. Amostragem, Variância e Efeito de Delineamento
* **Kish, L. (1965).** *Survey Sampling*. New York: John Wiley & Sons.
  * Obra clássica e fundadora que introduziu o conceito de **Efeito de Delineamento ($deff$)**, demonstrando formalmente a inflação da variância provocada por amostragem conglomerada e estratificação ponderada frente à amostragem aleatória simples.
* **Silva, P. L. N., & Bianchini, Z. M. (2020).** *Amostragem: Teoria e Prática Usando R*. Rio de Janeiro: Escola Nacional de Ciências Estatísticas (ENCE/IBGE).
  * Manual contemporâneo de referência no Brasil para cálculo de variância em planos amostrais complexos e amostragem estratificada sociodemográfica por cotas do Censo Demográfico.

### 2. Métricas de Acurácia e Avaliação de Pesquisas
* **Mosteller, F., Hyman, H., McCarthy, P. J., Marks, E. S., & Truman, D. B. (1949).** *The Pre-Election Polls of 1948: Report to the Committee on Analysis of Pre-Election Polls and Forecasts*. Social Science Research Council (SSRC), Bulletin 60. New York: SSRC.
  * O mais influente estudo na história das pesquisas eleitorais mundiais. Criado para investigar os desvios das pesquisas na eleição Truman vs. Dewey de 1948, estabeleceu a família de métricas $M_1$ a $M_8$ que baliza a literatura até a atualidade (especialmente $M_3$ e $M_5$).
* **Martin, E. A., Traugott, M. W., & Mockabee, S. T. (2005).** "A Review and Proposal for a New Measure of Poll Accuracy". *Public Opinion Quarterly*, 69(4), 542–569.
  * Artigo seminal que deduziu e propôs a **Métrica $A$ (Log-Odds Ratio de Viés)**, eliminando os problemas de escala percentual fechada e estabelecendo uma medida simétrica e aditiva para viés partidário.
* **Mitofsky, W. J. (1998).** "Review: Was 1996 Really a Good Year for the Polls?". *Public Opinion Quarterly*, 62(2), 230–249.
  * Discussão fundamental sobre métricas de margem de vitória e a sensibilidade do erro de véspera em disputas polarizadas.

### 3. O Paradigma do Total Survey Error (TSE)
* **Groves, R. M., Fowler, F. J., Couper, M. P., Lepkowski, J. M., Singer, E., & Tourangeau, R. (2004).** *Survey Methodology*. Hoboken, NJ: John Wiley & Sons.
  * Formalização canônica da arquitetura de **Total Survey Error (TSE)**, decompondo os levantamentos nas dimensões de Mensuração (validade de construto, erro de resposta, efeitos de entrevistador) e Representação (cobertura, amostragem, não-resposta e ponderação pós-campo).
* **Biemer, P. P. (2010).** "Total Survey Error: Design, Implementation, and Evaluation". *Public Opinion Quarterly*, 74(5), 817–848.
  * Revisão abrangente do modelo de erro total, demonstrando a interação entre erro estocástico e viés sistemático na composição do Erro Quadrático Médio ($MSE$).
* **Shirani-Mehr, H., Rothschild, D., Goel, S., & Gelman, A. (2018).** "Disentangling Bias and Variance in Election Polls". *Journal of the American Statistical Association*, 113(522), 607–614.
  * Estudo empírico em larga escala avaliando mais de 4.000 pesquisas eleitorais nos EUA, demonstrando que a variância empírica média das pesquisas é cerca de duas vezes superior à variância teórica calculada por AAS, corroborando a necessidade do $deff$ e da medição de excesso de dispersão.

### 4. Modelagem de Agregação e Séries Temporais Eleitorais
* **Jackman, S. (2005).** "Pooling the Polls Over an Election Campaign". *Australian Journal of Political Science*, 40(4), 499–517.
  * Modelagem de espaço de estados bayesiana para combinar múltiplas pesquisas eleitorais com decaimento temporal e estimação contínua da intenção latente de voto.
* **Silver, N. (2012).** *The Signal and the Noise: Why So Many Predictions Fail — but Some Don't*. New York: Penguin Press.
  * Metodologia prática de ponderação exponencial diária por meia-vida, correção de viés histórico de institutos (*house effects*) e combinação de bandas de incerteza empírica.
* **Gelman, A., & King, G. (1993).** "Why Are American Presidential Election Campaign Polls So Variable When Votes Are So Predictable?". *British Journal of Political Science*, 23(4), 409–451.
  * Trabalho seminal sobre a dinâmica de volatilidade de preferências durante a campanha e a convergência de eleitores indecisos na reta final.

### 5. Medidas de Dissimilaridade e Variação Total
* **Duncan, O. D., & Duncan, B. (1955).** "A Methodological Analysis of Segregation Indexes". *American Sociological Review*, 20(2), 210–217.
  * Artigo que originou o **Índice de Dissimilaridade de Duncan**, utilizado na componente $F$ (Eleitorado Fora do Lugar) como a métrica exata de distância $L_1$ para proporção de eleitores desalocados entre duas distribuições multinomiais.
