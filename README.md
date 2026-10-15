# Margem Eleitoral: Auditoria e Storytelling Científico de Pesquisas Eleitorais

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Package Manager](https://img.shields.io/badge/package%20manager-uv-blueviolet.svg)](https://docs.astral.sh/uv/)
[![Test Suite](https://img.shields.io/badge/tests-68%20passed-success.svg)](https://pytest.org/)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)](https://pytest-cov.readthedocs.io/)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-black.svg)](https://docs.astral.sh/ruff/)
[![Standards](https://img.shields.io/badge/standards-WAPOR%20%7C%20AAPOR-orange.svg)](https://wapor.org/)

Aplicação analítica interativa de **Data Storytelling** em Python projetada para auditar tecnicamente as pesquisas de intenção de voto registradas no Tribunal Superior Eleitoral (TSE). Desenvolvida sob uma arquitetura modular extensível a múltiplos anos e ciclos eleitorais, a metodologia do projeto é validada inicialmente no MVP com dados de 2022 e 2026, com suporte estrutural de expansão contínua para outros anos e pleitos futuros.

O projeto confronta o ceticismo popular e narrativas conspiratórias de fraude eleitoral a partir de **testes formais de hipótese estatística**, medição do ***Total Survey Error* (TSE)**, cálculo da taxa de cobertura de intervalos de confiança com **efeito de delineamento ($deff$)** e modelagem contínua de tendências latentes do eleitorado.

---

## Visão Geral e Propósito

Nas democracias contemporâneas, divergências entre levantamentos amostrais e a apuração oficial das urnas eletrônicas são frequentemente instrumentalizadas para questionar a lisura do processo eleitoral. 

O projeto **Margem Eleitoral** substitui o debate passional por **evidências matemáticas auditáveis**. A plataforma integra dois pilares visuais e analíticos de referência internacional (inspirados no jornalismo de dados de FiveThirtyEight e Plano Político):

1. **Agregador Dinâmico Contínuo:** Modelo temporal com decaimento exponencial (meia-vida de 14 dias), ponderação por qualidade metodológica e raiz da amostra ($\sqrt{n_i}$), extraindo a trajetória latente do eleitorado com envelopes de credibilidade de 80% e 95%.
2. **Painel de Auditoria e Desempenho de Institutos:** Plataforma de responsabilização que avalia a precisão de véspera, o viés partidário direcional (*house effects*) e o Erro Ponderado multivariado de cada instituto em relação à apuração oficial do TSE.

---

## Os Cinco Atos do Roteiro de Storytelling

A jornada do usuário na aplicação é estruturada pedagogicamente em cinco atos sequenciais:

1. **Ato 1: O Princípio da Incerteza:**
   * Desmistificação intuitiva do dilema de amostragem ($n \approx 2{.}000$ entrevistados vs. população de $156$ milhões de eleitores);
   * Simulador interativo demonstrando a Lei dos Grandes Números e o Teorema Central do Limite (TCL).
2. **Ato 2: O Filme da Eleição (Agregador Dinâmico):**
   * Curva suavizada diária com fitas de incerteza de 80% e 95% e dispersão pontual com transparência proporcional ao peso da pesquisa;
   * Marcos de campanha destacados sobre a série temporal e alternância entre votos totais e votos válidos.
3. **Ato 3: A Prova dos Fatos (Pesquisas de Véspera vs. Urna):**
   * *Forest Plot* confrontando estimativas pontuais e intervalos de confiança de 95% (ajustados com $deff$) contra a linha vertical da apuração do TSE;
   * Taxa de Cobertura Empírica calculada em tempo real com teste binomial exato de calibração.
4. **Ato 4: Anatomia do Erro e Auditoria:**
   * Gráfico de barras segmentadas por faixas de acerto (*Abaixo do Típico* vs. *Erro Típico*) confrontado com a *Faixa do Acaso ($P_{90}$)* derivada via simulação de Monte Carlo sob a hipótese nula ($H_0$);
   * Tabela classificatória interativa com ordenação por Erro Ponderado (EP), Mosteller $M_3$, $M_5$ e Log-Odds $A$;
   * Grid de *Small Multiples* exibindo a inclinação (*tilt*) de cada instituto frente ao consenso de pares contemporâneos em janelas de $\pm 7$ dias.
5. **Ato 5: O Veredito Científico:**
   * Diagnóstico inferencial formal: Teste $t$ de Student pareado e Teste de Wilcoxon sobre os resíduos;
   * Decomposição formal do *Total Survey Error* (Groves et al.) em variância teórica, excesso de dispersão, voto útil de última hora (*late swing*) e resíduo estrutural;
   * Parecer técnico demonstrando por que flutuações amostrais e abstenção diferencial explicam os dados sem qualquer evidência de fraude.

---

## Invariantes Metodológicas e Princípios Científicos

O projeto segue premissas estatísticas não-negociáveis respaldadas pelos padrões internacionais da WAPOR e AAPOR:

1. **Regra de Conversão de Votos Válidos:**
   * Nunca compare intenções brutas (com brancos, nulos e indecisos) com a apuração da urna.
   * Toda pesquisa é convertida canonicamente antes de qualquer cálculo de erro:
     $$\hat{p}_{v,i} = \frac{\hat{p}_i}{1 - \frac{\hat{p}_{\text{branco}} + \hat{p}_{\text{nulo}} + \hat{p}_{\text{indeciso}}}{100}}$$
2. **Critério Rígido de Véspera ($\le 72$ horas):**
   * Apenas pesquisas cujo campo encerrou a no máximo 72 horas antes da eleição são submetidas ao teste de véspera (*Forest Plot* e Erro Ponderado). Pesquisas anteriores pertencem exclusivamente à análise longitudinal de campanha.
3. **Efeito de Delineamento ($deff$ de Kish):**
   * As pesquisas brasileiras utilizam amostragem por cotas e conglomerados. O cálculo da variância incorpora o fator $deff \in [1{,}2; 1{,}5]$ (calibração padrão: $deff = 1{,}35$):
     $$\text{Var}(\hat{p}) = deff \times \frac{\hat{p}(1 - \hat{p})}{n}$$
4. **Métricas Padronizadas de Erro (WAPOR / AAPOR):**
   * **Mosteller 3 ($M_3$):** Desvio absoluto do candidato líder: $|\hat{p}_{\text{líder}} - P_{\text{líder}}|$.
   * **Mosteller 5 ($M_5$):** Desvio da margem de vitória: $|(\hat{p}_1 - \hat{p}_2) - (P_1 - P_2)|$.
   * **Log-Odds de Viés ($A$):** $\ln \left( \frac{\hat{p}_1 / \hat{p}_2}{P_1 / P_2} \right)$ para testar assimetria direcional na razão de chances.
5. **Formulação Estrutural do Erro Ponderado (EP):**
   $$EP = (1 - a) \times D + a \times F + 0{,}5 \times X$$
   onde $D$ é o erro nas margens com decaimento exponencial por competitividade, $F$ é o Eleitorado Fora do Lugar (Distância de Variação Total $L_1$ / Índice de Duncan) e $X$ é a penalização suave de fronteiras eleitorais.
6. **Distribuição Nula via Simulação de Monte Carlo ($H_0$):**
   * Sorteios multinomiais sobre o resultado oficial com tamanho efetivo $n_{\text{eff}} = n / deff$ ($10{.}000$ iterações) para estabelecer os percentis objetivos $P_{25}$, mediana $A_{50}$, $P_{75}$ e a **Faixa do Acaso ($P_{90}$)**.

---

## Arquitetura de Software e Tecnologias

A base de código é estruturada em camadas estritamente desacopladas:

```
margem_eleitoral/
├── config/
│   ├── settings.yaml            # Parâmetros de corte temporal, thresholds e metadados
│   └── taxonomy_mapping.yaml    # Harmonização de institutos, métodos e candidatos
├── data/
│   ├── raw/                     # Snapshots brutos imutáveis (PesqEle e API TSE)
│   └── processed/               # Datasets limpos e padronizados em Parquet e JSON
├── doc/                         # Documentação técnica completa espelhada
├── docs/                        # Documentação técnica e estatística modular
│   ├── 00_indice_geral.md       # Mapa de leitura e navegação
│   ├── 01_visao_geral_e_arquitetura.md
│   ├── 02_guia_estatistico_para_nao_estatisticos.md
│   ├── 03_metodologia_e_formulacoes_estatisticas.md
│   ├── 04_framework_tse_total_survey_error.md
│   ├── 05_jornada_data_storytelling_e_interface.md
│   ├── 06_referencias_bibliograficas_e_normas.md
│   └── 07_guia_de_desenvolvimento_e_reproducao.md
├── src/
│   ├── analytics/               # Computação estatística pura (sem UI)
│   │   ├── aggregator_model.py  # Média ponderada com decaimento t1/2 = 14 dias
│   │   ├── house_effects.py     # GLM, ANOVA de 2 fatores e tilt longitudinal
│   │   ├── hypothesis_tests.py  # Testes de Wilcoxon, t-Student, Binomial e TSE
│   │   └── metrics.py           # Mosteller, Log-Odds, Erro Ponderado e Monte Carlo
│   ├── ingestion/               # Coletores de dados e pipelines de ETL
│   │   ├── base.py              # Classe base abstrata para extração eleitoral
│   │   ├── data_loader.py       # Carregador com cache em sessão
│   │   ├── pesqele_collector.py # Ingestão e censo de registros do PesqEle
│   │   ├── pipeline.py          # Pipeline de transformação e persistência Parquet
│   │   └── tse_results.py       # Extração oficial da apuração do TSE
│   ├── presentation/            # Camada visual e storytelling
│   │   ├── app.py               # Ponto de entrada Streamlit (Dark Theme)
│   │   ├── components/          # Figuras interativas reutilizáveis em Plotly
│   │   └── story_acts/          # Roteiro dos Atos 1 a 5
│   └── transformations/         # Validação de contratos e normalização
│       ├── normalizer.py        # Harmonização taxonômica de nomes e métodos
│       ├── schemas.py           # Contratos estritos Pydantic v2
│       └── valid_votes.py       # Algoritmo de conversão para votos válidos
├── tests/                       # Suíte de 68 testes funcionais (pytest)
├── pyproject.toml               # Configuração do projeto e dependências uv
└── uv.lock                      # Trava determinística de dependências
```

---

## Como Executar

### 1. Pré-requisitos
* Python 3.12 ou superior
* Gerenciador de dependências [Astral uv](https://docs.astral.sh/uv/)

### 2. Instalação do Ambiente
```bash
uv sync --extra dev
```

### 3. Execução da Aplicação Interativa
Disparo direto via script registrado:
```bash
uv run app
```

Ou alternativamente:
```bash
uv run app.py
```
*(ou pelo comando tradicional: `uv run streamlit run src/presentation/app.py`)*

### 4. Execução dos Testes Automatizados e Cobertura
O repositório conta com **68 testes unitários** e de integração, com **91% de cobertura global**:
```bash
uv run pytest --cov=src --cov-report=term-missing tests/
```

### 5. Verificação de Lint e Estilo de Código
```bash
uv run ruff check src/ tests/
```

---

## Documentação Técnica de Suporte

A documentação detalhada foi modularizada na pasta [`docs/`](docs/00_indice_geral.md) (com espelho idêntico em [`doc/`](doc/00_indice_geral.md)):

* [**Doc 00: Sumário e Mapa de Navegação**](docs/00_indice_geral.md) — Índice temático completo.
* [**Doc 01: Visão Geral e Arquitetura de Software**](docs/01_visao_geral_e_arquitetura.md) — Princípios de SoC, contratos Pydantic v2, Polars e pipelines Parquet.
* [**Doc 02: Guia Estatístico para Não-Estatísticos**](docs/02_guia_estatistico_para_nao_estatisticos.md) — Explicações pedagógicas sem jargões: analogia do exame de sangue, margem de erro, votos válidos e $deff$.
* [**Doc 03: Metodologia e Formulações Estatísticas**](docs/03_metodologia_e_formulacoes_estatisticas.md) — Deduções matemáticas exaustivas em LaTeX de todas as equações, do Erro Ponderado ao Agregador.
* [**Doc 04: Framework de Total Survey Error (TSE)**](docs/04_framework_tse_total_survey_error.md) — Modelo de Groves et al. aplicado ao Brasil, abstenção diferencial e testes de hipótese antifraude.
* [**Doc 05: Jornada de Storytelling e Interface**](docs/05_jornada_data_storytelling_e_interface.md) — Roteiro dos 5 Atos, componentes visuais em Plotly, dark mode e sincronização do 2º Turno.
* [**Doc 06: Referências Bibliográficas e Normas**](docs/06_referencias_bibliograficas_e_normas.md) — Normas WAPOR/AAPOR, legislação do TSE e bibliografia científica seminal (Mosteller, Kish, Groves, Gelman, Silver).
* [**Doc 07: Guia de Engenharia e Reprodução**](docs/07_guia_de_desenvolvimento_e_reproducao.md) — Manual prático de operação, testes, matriz de cobertura, linters e pipelines de dados.

---

## Referências Principais

* **Mosteller, F. et al. (1949).** *The Pre-Election Polls of 1948*. Social Science Research Council.
* **Kish, L. (1965).** *Survey Sampling*. John Wiley & Sons.
* **Groves, R. M. et al. (2004).** *Survey Methodology*. John Wiley & Sons.
* **Martin, E. A., Traugott, M. W., & Mockabee, S. T. (2005).** "A Review and Proposal for a New Measure of Poll Accuracy". *Public Opinion Quarterly*, 69(4), 542–569.
* **Biemer, P. P. (2010).** "Total Survey Error: Design, Implementation, and Evaluation". *Public Opinion Quarterly*, 74(5), 817–848.
* **Silver, N. (2012).** *The Signal and the Noise*. Penguin Press.
* **WAPOR / AAPOR (2021).** *Codes of Professional Ethics and Polling Standards*.
