# Guia de Engenharia, Testes e Reprodução

Este guia prático fornece as instruções detalhadas para configurar o ambiente de desenvolvimento, executar a aplicação interativa, rodar a suíte completa de 68 testes automatizados com medição de cobertura, verificar padrões de código e executar pipelines de ingestão de dados.

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
git clone https://github.com/usuario/margem_eleitoral.git
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

## Suíte de Testes Automatizados e Cobertura

O projeto adota uma rigorosa política de garantia de qualidade (QA) baseada em testes funcionais nativos do `pytest`, sem uso do módulo legado `unittest`.

### 1. Executar Todos os Testes
Para rodar a suíte completa de 68 testes:

```bash
uv run pytest tests/
```

### 2. Executar Testes com Relatório Detalhado de Cobertura
Para medir a cobertura linha a linha sobre todos os módulos de `src/`:

```bash
uv run pytest --cov=src --cov-report=term-missing tests/
```

### 3. Matriz de Cobertura Atual dos Módulos
A suíte atinge **91% de cobertura global**, cobrindo exaustivamente cálculos de variância, conversão de votos válidos, normalização de nomes, contratos Pydantic e renderização de componentes visuais:

| Módulo Avaliado | Linhas de Código | Linhas Cobertas | Cobertura (%) |
| :--- | :---: | :---: | :---: |
| `src/analytics/aggregator_model.py` | 51 | 48 | **94%** |
| `src/analytics/house_effects.py` | 122 | 112 | **92%** |
| `src/analytics/hypothesis_tests.py` | 47 | 41 | **87%** |
| `src/analytics/metrics.py` | 170 | 155 | **91%** |
| `src/ingestion/data_loader.py` | 90 | 73 | **81%** |
| `src/ingestion/pesqele_collector.py` | 165 | 141 | **85%** |
| `src/ingestion/pipeline.py` | 42 | 30 | **71%** |
| `src/ingestion/tse_results.py` | 75 | 70 | **93%** |
| `src/presentation/app.py` | 80 | 74 | **92%** |
| `src/presentation/components/bar_error_chart.py` | 29 | 29 | **100%** |
| `src/presentation/components/bias_chart.py` | 14 | 14 | **100%** |
| `src/presentation/components/forest_plot.py` | 17 | 17 | **100%** |
| `src/presentation/components/simulator.py` | 24 | 24 | **100%** |
| `src/presentation/components/small_multiples.py` | 92 | 86 | **93%** |
| `src/presentation/components/trend_chart.py` | 39 | 38 | **97%** |
| `src/presentation/story_acts/act1_uncertainty.py` | 22 | 22 | **100%** |
| `src/presentation/story_acts/act2_election_film.py` | 33 | 30 | **91%** |
| `src/presentation/story_acts/act3_eve_clash.py` | 38 | 35 | **92%** |
| `src/presentation/story_acts/act4_error_anatomy.py` | 74 | 72 | **97%** |
| `src/presentation/story_acts/act5_scientific_verdict.py` | 58 | 57 | **98%** |
| `src/transformations/normalizer.py` | 52 | 48 | **92%** |
| `src/transformations/schemas.py` | 51 | 50 | **98%** |
| `src/transformations/valid_votes.py` | 22 | 21 | **95%** |
| **TOTAL GERAL** | **1.434** | **1.301** | **91%** |

### 4. Inventário dos Arquivos de Teste
* `tests/test_valid_votes.py`: Validação de conversão para votos válidos, expurgo de brancos/nulos e tratamento de divisões por zero.
* `tests/test_schemas.py`: Verificação de cronologia de campo, regex de registro TSE e fechamento de 100% em votos válidos.
* `tests/test_normalizer.py`: Testes de harmonização taxonômica de nomes de institutos, candidatos com/sem acento e metodologias.
* `tests/test_metrics.py`: Conferência numérica exata de Mosteller $M_3$, $M_5$, Log-Odds $A$, Erro Ponderado $EP$ e Monte Carlo.
* `tests/test_hypothesis_tests.py`: Testes de Student pareado, Wilcoxon, binomial de cobertura e decomposição de TSE.
* `tests/test_aggregator.py`: Decaimento exponencial com meia-vida de 14 dias, pesos de qualidade e bandas de credibilidade.
* `tests/test_house_effects.py`: Ajuste de modelos lineares OLS, tabelas ANOVA de Tipo II e grid longitudinal de inclinação (tilt).
* `tests/test_components.py`: Construção sem falhas de figuras Plotly para Forest Plot, Small Multiples e barras segmentadas.
* `tests/test_story_acts.py`: Renderização segura e sem exceções dos cinco Atos Narrativos da aplicação.
* `tests/test_data_loader.py`: Carregamento colunar de arquivos Parquet e conversão bidirecional em contratos Pydantic.
* `tests/test_etl_pipeline.py`: Validação do fluxo completo de extração, transformação e carga em disco.
* `tests/test_second_round_sync.py`: Injeção de novas pesquisas em tempo real e reatividade do agregador no 2º Turno.
* `tests/test_app.py`: Inicialização do estado de sessão e montagem do ponto de entrada da aplicação.

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

## Execução do Pipeline de Ingestão e ETL

Para reprocessar os dados brutos e atualizar os arquivos consolidados em formato Parquet:

### 1. Ingestão e Processamento do Ciclo de 2026 (Exemplo de Validação do MVP)
```bash
uv run python -m src.ingestion.pipeline --year 2026
```

### 2. Ingestão e Processamento do Benchmark Histórico de 2022
```bash
uv run python -m src.ingestion.pipeline --year 2022
```

> **Suporte Multianual:** O parâmetro `--year <ano>` aceita qualquer ano eleitoral configurado, permitindo estender o pipeline para novos pleitos futuros além dos anos de validação do MVP.

O pipeline realiza automaticamente as seguintes operações:
1. Localiza os dados brutos em `data/raw/{ano}/` (ou realiza o download do arquivo ZIP de dados abertos do TSE caso ausente);
2. Aplica as regras de normalização de nomes de institutos e metodologias via `TaxonomyNormalizer`;
3. Converte todas as intenções brutas em votos válidos via `calculate_valid_votes`;
4. Instancia e valida cada registro sob o contrato `PesquisaEleitoralSchema`;
5. Salva o dataset consolidado em formato Apache Parquet colunar de alta performance em `data/processed/pesquisas_{ano}.parquet`.

---

## Garantia de Reprodutibilidade Científica

Para garantir que os resultados, percentis de corte da Faixa do Acaso ($P_{90}$) e intervalos estatísticos sejam $100\%$ idênticos em qualquer computador:
* **Semente Aleatória Fixa:** O gerador de números pseudo-aleatórios do NumPy na simulação estocástica de Monte Carlo utiliza semente fixa determinística (`random_seed=42`);
* **Taxonomia Imutável:** Mapeamentos de institutos e métodos residem em arquivo de configuração estático versionado (`config/taxonomy_mapping.yaml`);
* **Trava de Dependências:** O arquivo `uv.lock` bloqueia os hashes exatos de cada dependência do ambiente, eliminando riscos de divergências provocadas por atualizações externas de bibliotecas.
