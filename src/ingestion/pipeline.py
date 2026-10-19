"""Pipeline de orquestração de ETL para dados eleitorais e pesquisas.

Executa de ponta a ponta o processo de Extração, Transformação, Validação e Carga
para anos eleitorais específicos ou todos os pleitos configurados.
"""

import argparse
import sys

from src.ingestion.pesqele_collector import PesqEleCollector
from src.ingestion.tse_results import TSEResultsExtractor
from src.transformations.schemas import PesquisaEleitoralSchema, ResultadoOficialTSESchema


def run_etl_for_year(
    year: int, turno: int = 1
) -> tuple[ResultadoOficialTSESchema | None, list[PesquisaEleitoralSchema]]:
    """Executa o pipeline de ETL completo para um ano eleitoral e turno especificados.

    Args:
        year: Ano eleitoral a processar (ex.: 2026, 2022).
        turno: Turno da eleição (1 ou 2).

    Returns:
        tuple[ResultadoOficialTSESchema, list[PesquisaEleitoralSchema]]:
            Tupla com o resultado oficial validado e a lista de pesquisas processadas.

    Raises:
        FileNotFoundError: Se faltar arquivos brutos essenciais.
        ValueError: Se houver falha de validação nos esquemas.
    """
    print("\n=======================================================")
    print(f"[ETL] Iniciando para o Ciclo Presidencial: {year} (Turno {turno})")
    print("=======================================================")

    # 1. Extração e validação do Resultado Oficial do TSE
    print("1/3 Extraindo e validando apuracao oficial do TSE...")
    tse_extractor = TSEResultsExtractor(year=year, turno=turno)
    tse_result = tse_extractor.extract_and_transform()
    if tse_result is not None:
        tse_dest = tse_extractor.save_processed()
        print(f"   -> Apuracao oficial validada: {len(tse_result.resultado_nominal)} candidatos.")
        print(f"   -> Salvo em: {tse_dest}")
    else:
        print("   -> Apuracao oficial ainda nao realizada (pleito futuro / pendente).")

    # 2. Extração e validação das pesquisas do PesqEle
    print("2/3 Extraindo, normalizando e validando pesquisas registradas (PesqEle)...")
    pesqele_collector = PesqEleCollector(year=year)
    polls = pesqele_collector.extract_and_transform()
    polls_dest = pesqele_collector.save_processed()
    print(f"   -> Total de pesquisas processadas e validadas: {len(polls)} levantamentos.")
    print(f"   -> Salvo em formato Parquet em: {polls_dest}")

    # 3. Sumário e validação de consistência
    if tse_result is not None:
        candidatos_tse = set(tse_result.resultado_nominal.keys())
        candidatos_pesquisas = {c for p in polls for c in p.votos_validos.keys()}
        print("3/3 Verificando aderencia semantica dos candidatos...")
        print(f"   -> Candidatos TSE: {sorted(list(candidatos_tse))}")
        print(f"   -> Candidatos Pesquisas: {sorted(list(candidatos_pesquisas))}")
    else:
        print("3/3 Verificacao semantica TSE suspensa (apuracao pendente).")

    print(f"[OK] ETL concluido com sucesso para {year} (Turno {turno})!\n")
    return tse_result, polls


def main() -> None:
    """Ponto de entrada CLI para execução do ETL via terminal.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: Em caso de argumentos inválidos ou falhas de execução.
    """
    parser = argparse.ArgumentParser(
        description="Orquestrador de ETL para Dados Eleitorais e Pesquisas"
    )
    parser.add_argument(
        "--year",
        type=str,
        default="2026",
        help="Ano eleitoral a processar (ex: '2026', '2022' ou 'all')",
    )
    parser.add_argument(
        "--turno",
        type=int,
        default=1,
        choices=[1, 2],
        help="Turno da eleição (1 ou 2)",
    )

    args = parser.parse_args()

    years_to_process = [2026, 2022] if args.year.lower() == "all" else [int(args.year)]

    for yr in years_to_process:
        try:
            run_etl_for_year(year=yr, turno=args.turno)
        except Exception as e:
            print(f"[ERRO] Falha ao executar ETL para o ano {yr}: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
