"""Testes unitários funcionais para o módulo CLI do terminal (src/cli.py)."""

import argparse
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from src.cli import build_parser, cmd_add_poll, cmd_predict, cmd_process, cmd_status, cmd_sync


def test_build_parser_subcommands() -> None:
    """Verifica se todos os subcomandos esperados estão registrados no parser."""
    parser = build_parser()
    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    commands = list(subparsers_action.choices.keys())
    assert "status" in commands
    assert "sync" in commands
    assert "add-poll" in commands
    assert "process" in commands
    assert "predict" in commands


def test_cmd_status_execution(capsys: pytest.CaptureFixture[str]) -> None:
    """Valida a execução do comando status sem levantar exceções."""
    parser = build_parser()
    args = parser.parse_args(["status", "--year", "2026", "--turno", "2"])
    cmd_status(args)
    captured = capsys.readouterr()
    assert "Status do Ciclo Eleitoral: 2026 (Turno 2)" in captured.out
    assert "Pesquisas disponíveis" in captured.out


def test_cmd_sync_execution(mocker: MockerFixture, capsys: pytest.CaptureFixture[str]) -> None:
    """Valida a execução do comando sync chamando o coletor."""
    mocker.patch(
        "src.ingestion.pesqele_collector.PesqEleCollector.sync_official_second_round_polls",
        return_value=[MagicMock(), MagicMock()],
    )
    parser = build_parser()
    args = parser.parse_args(["sync", "--year", "2026"])
    cmd_sync(args)
    captured = capsys.readouterr()
    assert "Sincronizando Pesquisas Oficiais do TSE" in captured.out
    assert "Foram integradas e validadas 2 pesquisas" in captured.out


def test_cmd_process_execution(mocker: MockerFixture, capsys: pytest.CaptureFixture[str]) -> None:
    """Valida a execução do comando process chamando o pipeline ETL."""
    mock_run = mocker.patch("src.cli.run_etl_for_year")
    parser = build_parser()
    args = parser.parse_args(["process", "--year", "2026", "--turno", "2"])
    cmd_process(args)
    mock_run.assert_called_once_with(year=2026, turno=2)
    captured = capsys.readouterr()
    assert "Processando Pipeline de Dados" in captured.out


def test_cmd_predict_execution(capsys: pytest.CaptureFixture[str]) -> None:
    """Valida a execução do comando predict e exibição das previsões."""
    parser = build_parser()
    args = parser.parse_args(
        [
            "predict",
            "--year",
            "2026",
            "--turno",
            "2",
            "--cutoff",
            "2026-10-19",
            "--simulations",
            "500",
        ]
    )
    cmd_predict(args)
    captured = capsys.readouterr()
    assert "Ajuste e Execução dos Modelos Preditivos" in captured.out
    assert "Resultado da Projeção Probabilística" in captured.out
    assert "Flávio Bolsonaro" in captured.out or "Lula" in captured.out


def test_cmd_add_poll_execution(mocker: MockerFixture, capsys: pytest.CaptureFixture[str]) -> None:
    """Valida o comando add-poll simulando adição de registro e persistência."""
    mocker.patch("src.ingestion.pesqele_collector.PesqEleCollector.save_processed")

    # Mock apenas na chamada de escrita/leitura do CSV específico
    orig_open = open
    header_csv = "id_registro_tse,instituto,data_inicio_campo,data_fim_campo,data_divulgacao,tamanho_amostra,margem_erro,metodologia,deff,voto_bruto_Flávio Bolsonaro,voto_bruto_Lula,voto_bruto_Augusto Cury,voto_bruto_Renan Santos,voto_bruto_Ronaldo Caiado,voto_bruto_Romeu Zema,voto_bruto_Outros,brancos_nulos,indecisos,turno,abrangencia,uf,regiao\n"

    from io import StringIO

    class MockFile:
        def __init__(self, content: str):
            self.sio = StringIO(content)

        def __enter__(self):
            return self.sio

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def custom_open(file, *args, **kwargs):
        if "pesquisas_publicadas_2026.csv" in str(file):
            return MockFile(header_csv)
        return orig_open(file, *args, **kwargs)

    mocker.patch("builtins.open", side_effect=custom_open)

    parser = build_parser()
    args = parser.parse_args(
        [
            "add-poll",
            "--year",
            "2026",
            "--turno",
            "2",
            "--registro",
            "BR-99999/2026",
            "--instituto",
            "Datafolha",
            "--dt-inicio",
            "2026-10-17",
            "--dt-fim",
            "2026-10-18",
            "--dt-divulgacao",
            "2026-10-19",
            "--amostra",
            "2500",
            "--margem",
            "2.0",
            "--metodologia",
            "PRESENCIAL_DOMICILIAR",
            "--deff",
            "1.35",
            "--voto",
            "Lula=47.0",
            "--voto",
            "Flávio Bolsonaro=48.0",
            "--brancos-nulos",
            "3.0",
            "--indecisos",
            "2.0",
            "--abrangencia",
            "NACIONAL",
        ]
    )
    cmd_add_poll(args)
    captured = capsys.readouterr()
    assert "Inserindo Nova Pesquisa Divulgada" in captured.out
    assert "Votos Válidos Calculados" in captured.out
