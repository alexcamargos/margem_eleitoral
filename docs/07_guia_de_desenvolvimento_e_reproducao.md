# Guia de Engenharia, Testes e Reprodução

Este guia prático fornece as instruções detalhadas para configurar o ambiente de desenvolvimento, executar a aplicação interativa, utilizar a CLI de terminal `margem`, rodar a suíte completa de 186 testes automatizados com medição de cobertura, verificar padrões de código e executar pipelines de ingestão de dados.

---

## Requisitos de Sistema

* **Sistema Operacional:** Linux, macOS ou Windows 10/11 (x86_64 ou ARM64);
* **Interpretador Python:** Python 3.12 ou superior;
* **Gerenciador de Dependências:** [Astral uv](https://docs.astral.sh/uv/) (versão $\ge 0.1.0$).

> **Nota sobre o uv:** O Astral `uv` é o gerenciador de pacotes e resolvedor de dependências padrão deste projeto. Substitui com extrema velocidade o `pip`, `poetry` e `pipenv`. Não é necessário criar ambientes virtuais manualmente: o `uv` gerencia o diretório `.venv` de forma hermética.

---

## Instalação e Configuração do Ambiente

### 1. Clonar o Repositório
```bash
git clone https://github.com/alexcamargos/margem_eleitoral.git
cd margem_eleitoral
```

### 2. Instalar Dependências e Ferramentas de Desenvolvimento
O comando a seguir cria o ambiente virtual isolado em `.venv`, resolve todas as restrições do arquivo `pyproject.toml` e instala os pacotes de produção e desenvolvimento:

```bash
uv sync --extra dev
```

---

## Como Executar a Aplicação Interativa

A aplicação foi configurada com um script de entrada nativo registrado no `pyproject.toml`, permitindo inicialização direta via terminal:

### Modo Primário Recomendado
```bash
uv run app
```

### Modos Alternativos Suportados
Você também pode disparar a aplicação por meio do wrapper na raiz do projeto:
```bash
uv run app.py
```

Ou pelo comando verboso tradicional do Streamlit:
```bash
uv run streamlit run src/presentation/app.py
```

Após o disparo, a interface estará acessível no navegador padrão no endereço local:
`http://localhost:8501`

---

## Interface de Linha de Comando (CLI `margem`)

O utilitário CLI `margem` (`src/cli.py`) oferece controle total sobre dados, auditoria, ingestão e ajuste de modelos diretamente pelo terminal:

### 1. Consultar Status do Ciclo Eleitoral
```bash
uv run margem status --year 2026 --turno 2
```
Exibe apuração oficial, total de pesquisas disponíveis, pesquisas de véspera, institutos monitorados e status da sincronização do 2º Turno.

### 2. Sincronizar Pesquisas Oficiais ou Feed Web
```bash
# Sincronização oficial junto ao censo e repositório do TSE
uv run margem sync --year 2026

# Sincronização forçada com download do pacote bruto do TSE
uv run margem sync --year 2026 --force

# Sincronização via feed web aberto estruturado
uv run margem sync --year 2026 --feed-url "https://exemplo.com/feed_pesquisas.json"
```

### 3. Auditar Pesquisas contra o Censo Oficial do PesqEle
```bash
uv run margem audit --year 2026
```
Cruza os protocolos das pesquisas cadastradas com os registros formais do TSE e relata a taxa de conformidade cadastral e eventuais divergências.

### 4. Inserir Nova Pesquisa Manualmente (com Blindagem do Gatekeeper)
```bash
uv run margem add-poll --year 2026 --turno 2 \
  --registro "BR-01115/2026" \
  --instituto "Datafolha" \
  --dt-inicio "2026-10-21" --dt-fim "2026-10-23" --dt-divulgacao "2026-10-24" \
  --amostra 2000 --margem 2.0 --metodologia "PRESENCIAL_DOMICILIAR" --deff 1.35 \
  --voto "Lula=47.5" --voto "Flávio Bolsonaro=48.0" \
  --brancos-nulos 3.0 --indecisos 1.5
```
Aplica as validações do `ElectoralGatekeeper` (rejeitando multi-candidatos no 2T e conferindo soma ~100%), converte para votos válidos e persiste no CSV e Parquet.

### 5. Executar o Pipeline de Processamento (ETL)
```bash
uv run margem process --year 2026 --turno 2
```

### 6. Executar e Ajustar Modelos Preditivos via Terminal
```bash
uv run margem predict --year 2026 --turno 2 --simulations 10000 --tau 14.0
```
Gera a projeção do Agregador Dinâmico e do Modelo Preditivo Hierárquico com decomposição regional pelo Colégio Eleitoral e probabilidades de vitória via Monte Carlo.

---

## Suíte de Testes Automatizados e Cobertura

O projeto adota uma rigorosa política de garantia de qualidade (QA) baseada em testes funcionais nativos do `pytest`, sem uso do módulo legado `unittest`.

### 1. Executar Todos os Testes
Para rodar a suíte completa de **186 testes**:

```bash
uv run pytest tests/
```

### 2. Executar Testes com Relatório Detalhado de Cobertura
Para medir a cobertura linha a linha sobre todos os módulos de `src/`:

```bash
uv run pytest --cov=src --cov-report=term-missing tests/
```

### 3. Matriz de Cobertura Atual dos Módulos
A suíte atinge **87% de cobertura global**, avaliando 4.780 statements em 37 módulos:

| Módulo Avaliado | Statements | Miss | Cobertura (%) |
| :--- | :---: | :---: | :---: |
| `src/__init__.py` | 0 | 0 | **100%** |
| `src/analytics/__init__.py` | 3 | 0 | **100%** |
| `src/analytics/aggregator_model.py` | 147 | 8 | **95%** |
| `src/analytics/house_effects.py` | 123 | 10 | **92%** |
| `src/analytics/hypothesis_tests.py` | 60 | 7 | **88%** |
| `src/analytics/metrics.py` | 170 | 12 | **93%** |
| `src/analytics/predictive_model.py` | 481 | 20 | **96%** |
| `src/analytics/rejection_analysis.py` | 133 | 1 | **99%** |
| `src/analytics/sensitivity_analysis.py` | 99 | 6 | **94%** |
| `src/cli.py` | 301 | 66 | **78%** |
| `src/ingestion/__init__.py` | 5 | 0 | **100%** |
| `src/ingestion/base.py` | 27 | 13 | **52%** |
| `src/ingestion/data_loader.py` | 167 | 36 | **78%** |
| `src/ingestion/multi_office_collector.py` | 427 | 205 | **52%** |
| `src/ingestion/pesqele_collector.py` | 237 | 17 | **93%** |
| `src/ingestion/pipeline.py` | 46 | 14 | **70%** |
| `src/ingestion/tse_results.py` | 80 | 8 | **90%** |
| `src/ingestion/web_poll_extractor.py` | 219 | 32 | **85%** |
| `src/presentation/__init__.py` | 0 | 0 | **100%** |
| `src/presentation/app.py` | 160 | 26 | **84%** |
| `src/presentation/components/__init__.py` | 6 | 0 | **100%** |
| `src/presentation/components/bar_error_chart.py` | 29 | 0 | **100%** |
| `src/presentation/components/bias_chart.py` | 14 | 0 | **100%** |
| `src/presentation/components/documentation_modal.py` | 38 | 3 | **92%** |
| `src/presentation/components/dumbbell_chart.py` | 61 | 0 | **100%** |
| `src/presentation/components/executive_story_cards.py` | 163 | 5 | **97%** |
| `src/presentation/components/forest_plot.py` | 17 | 0 | **100%** |
| `src/presentation/components/institute_temporal_chart.py` | 77 | 11 | **86%** |
| `src/presentation/components/phase_story_chart.py` | 40 | 4 | **90%** |
| `src/presentation/components/polls_list_modal.py` | 181 | 15 | **92%** |
| `src/presentation/components/predictive_charts.py` | 55 | 1 | **98%** |
| `src/presentation/components/sensitivity_table_card.py` | 45 | 0 | **100%** |
| `src/presentation/components/simulator.py` | 24 | 0 | **100%** |
| `src/presentation/components/small_multiples.py` | 92 | 6 | **93%** |
| `src/presentation/components/trend_chart.py` | 45 | 3 | **93%** |
| `src/presentation/components/waterfall_projection_card.py` | 116 | 34 | **71%** |
| `src/presentation/story_acts/__init__.py` | 0 | 0 | **100%** |
| `src/presentation/story_acts/act1_uncertainty.py` | 22 | 0 | **100%** |
| `src/presentation/story_acts/act2_election_film.py` | 115 | 16 | **86%** |
| `src/presentation/story_acts/act3_rejection.py` | 88 | 0 | **100%** |
| `src/presentation/story_acts/act4_eve_clash.py` | 42 | 5 | **88%** |
| `src/presentation/story_acts/act5_error_anatomy.py` | 158 | 21 | **87%** |
| `src/presentation/story_acts/act6_scientific_verdict.py` | 81 | 10 | **88%** |
| `src/presentation/story_acts/act7_predictive_forecast.py` | 173 | 21 | **88%** |
| `src/transformations/__init__.py` | 5 | 0 | **100%** |
| `src/transformations/gatekeeper.py` | 43 | 3 | **93%** |
| `src/transformations/normalizer.py` | 52 | 4 | **92%** |
| `src/transformations/schemas.py` | 91 | 1 | **99%** |
| `src/transformations/valid_votes.py` | 22 | 1 | **95%** |
| **TOTAL GERAL** | **4.780** | **645** | **87%** |

### 4. Inventário dos 25 Arquivos de Teste
* `tests/test_aggregator.py`: Decaimento exponencial, meias-vidas e bandas de credibilidade.
* `tests/test_app.py`: Inicialização do estado de sessão, seletores e montagem de abas.
* `tests/test_cli.py`: Subcomandos da CLI `margem` (`status`, `sync`, `add-poll`, `audit`, `process`, `predict`).
* `tests/test_components.py`: Construção das figuras Plotly para Forest Plot, Small Multiples e barras segmentadas.
* `tests/test_data_loader.py`: Carregamento colunar Parquet, conversão de schemas e filtros de sessão.
* `tests/test_documentation_modal.py`: Renderização do modal metodológico com abas técnica e não-técnica.
* `tests/test_etl_pipeline.py`: Fluxo de ponta a ponta de extração, transformação e carga em disco.
* `tests/test_executive_story_cards.py`: Renderização dos Hero Cards com status competitivo e nowcasting.
* `tests/test_gatekeeper.py`: Portões de integridade eleitoral do 2º Turno (binariedade e partição 100%).
* `tests/test_house_effects.py`: Ajuste OLS/GLM, tabelas ANOVA de Tipo II e grid de tilt contemporâneo.
* `tests/test_hypothesis_tests.py`: Testes $t$ pareado, Wilcoxon, binomial de cobertura e Total Survey Error.
* `tests/test_metrics.py`: Conferência numérica de Mosteller $M_3$, $M_5$, Log-Odds $A$, Erro Ponderado $EP$ e Monte Carlo.
* `tests/test_multi_office_collector.py`: Coleta multi-ano (2018, 2022, 2026) e multi-cargo (Gov/Sen).
* `tests/test_normalizer.py`: Harmonização de institutos, fonética e taxonomia metodológica.
* `tests/test_phase_aggregation.py`: Agregação por fases de campanha e janelas temporais.
* `tests/test_polls_list_modal.py`: Modal de listagem e filtragem de pesquisas catalogadas.
* `tests/test_predictive_model.py`: Modelo estado-espaço hierárquico, Colégio Eleitoral e Monte Carlo ($t$-Student $\nu=5$).
* `tests/test_rejection_analysis.py`: Médias de rejeição, teto eleitoral e Cleveland Dot Plot.
* `tests/test_schemas.py`: Contratos Pydantic v2 de pesquisas, resultados oficiais e cronologia de campo.
* `tests/test_second_round_sync.py`: Injeção de pesquisas em tempo real e reatividade no 2º Turno.
* `tests/test_sensitivity_analysis.py`: Avaliação comparativa das 13 variantes metodológicas ($S0$ a $S11$).
* `tests/test_story_acts.py`: Renderização segura e sem exceções dos 7 Atos da aplicação.
* `tests/test_tse_cross_validation.py`: Validação cruzada com o censo do PesqEle do TSE.
* `tests/test_valid_votes.py`: Conversão canônica para votos válidos e expurgo de não-válidos.
* `tests/test_waterfall_projection_card.py`: Construção do card de projeção Waterfall regional.
* `tests/test_web_poll_extractor.py`: Ingestão, validação e auditoria de pesquisas publicadas na web.

---

## Verificação de Lint e Padronização de Código

O projeto impõe conformidade estrita com o PEP 8 utilizando o [Ruff](https://docs.astral.sh/ruff/):

```bash
uv run ruff check src/ tests/
```

Para formatar automaticamente eventuais desvios de espaçamento e ordenar blocos de import:
```bash
uv run ruff format src/ tests/
```

---

## Execução da Raspagem Multi-Cargo em Lote (`get.py`)

Para sincronizar e expandir o banco de pesquisas em lote para múltiplos cargos e anos:
```bash
uv run python get.py --cargos presidente governador senador --anos 2026 2022 2018
```

---

## Garantia de Reprodutibilidade Científica

Para garantir que os resultados, percentis de corte da Faixa do Acaso ($P_{90}$) e intervalos estatísticos sejam $100\%$ idênticos em qualquer computador:
* **Semente Aleatória Fixa:** O gerador de números pseudo-aleatórios do NumPy na simulação estocástica de Monte Carlo utiliza semente fixa determinística (`random_seed=42`);
* **Taxonomia Imutável:** Mapeamentos de institutos e métodos residem em arquivo de configuração estático versionado (`config/taxonomy_mapping.yaml`);
* **Trava de Dependências:** O arquivo `uv.lock` bloqueia os hashes exatos de cada dependência do ambiente, eliminando riscos de divergências provocadas por atualizações externas de bibliotecas.
