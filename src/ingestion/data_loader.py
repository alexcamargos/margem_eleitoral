"""Carregador de dados de alta performance com cache para a aplicação analítica.

Lê os arquivos Parquet e JSON consolidados pelo pipeline de ETL e os converte
em contratos Pydantic tipados, segregando pesquisas de véspera de pesquisas históricas.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from src.ingestion.pesqele_collector import PesqEleCollector
from src.ingestion.pipeline import run_etl_for_year
from src.transformations.schemas import (
    MetodologiaEnum,
    PesquisaEleitoralSchema,
    ResultadoOficialTSESchema,
)


def load_election_settings() -> dict:
    """Carrega as configurações eleitorais e calendários do arquivo settings.yaml.

    Args:
        None.

    Returns:
        dict: Dicionário de configurações parseado.

    Raises:
        FileNotFoundError: Se settings.yaml não for encontrado.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    settings_file = repo_root / "config" / "settings.yaml"
    with open(settings_file, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_election_date(year: int, turno: int = 1) -> date:
    """Retorna a data oficial do pleito para o ano e turno desejados.

    Args:
        year: Ano eleitoral (ex.: 2026, 2022).
        turno: Turno da eleição (1 ou 2).

    Returns:
        date: Objeto date correspondente à votação.

    Raises:
        ValueError: Se a data do pleito não estiver cadastrada.
    """
    settings = load_election_settings()
    elections_cfg = settings.get("elections", {})
    yr_cfg = elections_cfg.get(year) or elections_cfg.get(str(year))

    if yr_cfg:
        date_str = yr_cfg.get("first_round_date" if turno == 1 else "second_round_date")
        if date_str:
            return date.fromisoformat(date_str)

    # Fallbacks históricos padrão
    if year == 2026:
        return date(2026, 10, 4) if turno == 1 else date(2026, 10, 25)
    if year == 2022:
        return date(2022, 10, 2) if turno == 1 else date(2022, 10, 30)

    raise ValueError(f"Data eleitoral não configurada para o ano {year} e turno {turno}.")


def polars_to_polls(df: pl.DataFrame) -> list[PesquisaEleitoralSchema]:
    """Converte um DataFrame Polars carregado de Parquet de volta em instâncias de PesquisaEleitoralSchema.

    Args:
        df: DataFrame Polars lido de data/processed/pesquisas_{year}.parquet.

    Returns:
        list[PesquisaEleitoralSchema]: Lista de contratos de pesquisas validadas.

    Raises:
        ValueError: Se as colunas obrigatórias não estiverem presentes no DataFrame.
    """
    polls: list[PesquisaEleitoralSchema] = []
    col_names = df.columns

    valid_cols = [c for c in col_names if c.startswith("validos_")]
    tot_cols = [c for c in col_names if c.startswith("totais_")]

    for row in df.iter_rows(named=True):
        validos = {
            c.replace("validos_", ""): float(row[c]) for c in valid_cols if row[c] is not None
        }
        totais = {c.replace("totais_", ""): float(row[c]) for c in tot_cols if row[c] is not None}

        dt_inicio = row["data_inicio_campo"]
        if isinstance(dt_inicio, str):
            dt_inicio = date.fromisoformat(dt_inicio)

        dt_fim = row["data_fim_campo"]
        if isinstance(dt_fim, str):
            dt_fim = date.fromisoformat(dt_fim)

        dt_div = row["data_divulgacao"]
        if isinstance(dt_div, str):
            dt_div = date.fromisoformat(dt_div)

        p = PesquisaEleitoralSchema(
            id_registro_tse=row["id_registro_tse"],
            instituto_razao_social=row["instituto_razao_social"],
            instituto_nome_fantasia=row["instituto_nome_fantasia"],
            data_inicio_campo=dt_inicio,
            data_fim_campo=dt_fim,
            data_divulgacao=dt_div,
            tamanho_amostra=row["tamanho_amostra"],
            margem_erro_declarada=row["margem_erro_declarada"],
            nivel_confianca=row["nivel_confianca"],
            metodologia=MetodologiaEnum(row["metodologia"]),
            deff_estimado=row["deff_estimado"],
            votos_totais=totais,
            votos_validos=validos,
            percentual_indecisos=row["percentual_indecisos"],
            percentual_brancos_nulos=row["percentual_brancos_nulos"],
            turno=row["turno"],
            cargo=row.get("cargo", "PRESIDENTE"),
            ano=row.get("ano", 2026),
        )
        polls.append(p)

    return polls


def get_election_dataset(
    year: int = 2026,
    turno: int = 1,
    cutoff_days: int = 3,
) -> tuple[ResultadoOficialTSESchema, list[PesquisaEleitoralSchema], list[PesquisaEleitoralSchema]]:
    """Carrega o resultado oficial do TSE e as pesquisas eleitorais para um dado pleito.

    Separa as pesquisas entre levantamentos de véspera (fim de campo <= cutoff_days antes da eleição)
    e o conjunto total longitudinal para o Agregador Dinâmico.

    Args:
        year: Ano eleitoral (ex.: 2026, 2022).
        turno: Turno da eleição (1 ou 2).
        cutoff_days: Limite em dias para inclusão no critério de véspera (default: 3 dias / 72h).

    Returns:
        tuple[ResultadoOficialTSESchema, list[PesquisaEleitoralSchema], list[PesquisaEleitoralSchema]]:
            (tse_result, eve_polls, all_polls).

    Raises:
        FileNotFoundError: Se os arquivos processados e brutos não puderem ser encontrados.
        ValueError: Em caso de inconsistências numéricas.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    processed_dir = repo_root / "data" / "processed"
    parquet_path = processed_dir / f"pesquisas_{year}.parquet"
    tse_json_path = processed_dir / f"resultado_oficial_{year}_t{turno}.json"

    # Se os arquivos processados não existirem, executa o pipeline de ETL sob demanda
    if not parquet_path.exists() or not tse_json_path.exists():
        run_etl_for_year(year=year, turno=turno)

    # 1. Carrega o resultado oficial
    with open(tse_json_path, encoding="utf-8") as f:
        tse_dict = json.load(f)
    tse_result = ResultadoOficialTSESchema(**tse_dict)

    # 2. Carrega as pesquisas via Polars Parquet
    df_polls = pl.read_parquet(parquet_path)
    all_polls = polars_to_polls(df_polls)

    # Filtra por turno
    all_polls_turno = [p for p in all_polls if p.turno == turno]

    # Se for o 2º turno de 2026 e ainda não houver pesquisas no Parquet, sincroniza automaticamente
    if turno == 2 and not all_polls_turno and year == 2026:
        collector = PesqEleCollector(year=year)
        collector.sync_official_second_round_polls()
        df_polls = pl.read_parquet(parquet_path)
        all_polls = polars_to_polls(df_polls)
        all_polls_turno = [p for p in all_polls if p.turno == turno]

    # 3. Segrega pesquisas de véspera (<= 72 horas / 3 dias da eleição)
    election_date = get_election_date(year=year, turno=turno)
    eve_polls = [
        p for p in all_polls_turno if (election_date - p.data_fim_campo).days <= cutoff_days
    ]

    return tse_result, eve_polls, all_polls_turno


def get_tse_registration_census(year: int = 2026) -> pl.DataFrame:
    """Carrega o censo completo de pesquisas registradas no TSE a partir do arquivo Parquet processado.

    Args:
        year: Ano eleitoral (default: 2026).

    Returns:
        pl.DataFrame: DataFrame contendo todos os registros presidenciais no TSE.

    Raises:
        None.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    parquet_path = repo_root / "data" / "processed" / f"pesquisas_registradas_tse_{year}.parquet"
    if parquet_path.exists():
        return pl.read_parquet(parquet_path)
    return pl.DataFrame()


def get_second_round_sync_summary(year: int = 2026) -> dict[str, Any]:
    """Retorna um sumário estruturado sobre o estado de sincronização das pesquisas do 2º Turno.

    Args:
        year: Ano eleitoral auditado (default: 2026).

    Returns:
        dict[str, Any]: Dicionário contendo total de pesquisas sincronizadas,
            quantidade de pesquisas de véspera, lista de institutos participantes
            e data mais recente de fim de campo.

    Raises:
        None.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    parquet_path = repo_root / "data" / "processed" / f"pesquisas_{year}.parquet"
    if not parquet_path.exists():
        return {
            "total_polls": 0,
            "eve_polls_count": 0,
            "institutes": [],
            "latest_field_date": None,
            "is_synced": False,
        }

    df = pl.read_parquet(parquet_path)
    all_polls = polars_to_polls(df)
    r2_polls = [p for p in all_polls if p.turno == 2]

    if not r2_polls:
        return {
            "total_polls": 0,
            "eve_polls_count": 0,
            "institutes": [],
            "latest_field_date": None,
            "is_synced": False,
        }

    election_date = get_election_date(year=year, turno=2)
    eve_count = sum(1 for p in r2_polls if (election_date - p.data_fim_campo).days <= 3)
    institutes = sorted(list({p.instituto_nome_fantasia for p in r2_polls}))
    latest_date = max(p.data_fim_campo for p in r2_polls)

    return {
        "total_polls": len(r2_polls),
        "eve_polls_count": eve_count,
        "institutes": institutes,
        "latest_field_date": latest_date,
        "is_synced": True,
    }
