"""Ponto de entrada CLI para coleta e expansão do banco de pesquisas eleitorais.

Utiliza o MultiOfficeCollector para raspar, padronizar e persistir pesquisas para
Presidente, Governador e Senador nos ciclos eleitorais de 2026, 2022 e 2018.
"""

import argparse
import json
from typing import Any

from src.ingestion.multi_office_collector import MultiOfficeCollector


def main() -> None:
    """Executa a coleta multi-cargo e multi-ano a partir dos argumentos da CLI."""
    parser = argparse.ArgumentParser(
        description="Coletor e Sincronizador Multi-Cargo de Pesquisas Eleitorais"
    )
    parser.add_argument(
        "--cargos",
        nargs="+",
        default=["presidente", "governador", "senador"],
        help="Cargos a sincronizar (ex: presidente governador senador)",
    )
    parser.add_argument(
        "--anos",
        nargs="+",
        type=int,
        default=[2026, 2022, 2018],
        help="Anos eleitorais a processar (ex: 2026 2022 2018)",
    )

    args = parser.parse_args()

    print("=====================================================================")
    print("Iniciando Sincronização e Extensão do Banco de Pesquisas Eleitorais")
    print(f"Cargos: {args.cargos}")
    print(f"Anos: {args.anos}")
    print("=====================================================================\n")

    collector = MultiOfficeCollector()
    summary: dict[str, Any] = collector.run_full_sync()

    print("\n---------------------------------------------------------------------")
    print("Relatório Final de Coleta e Persistência:")
    print("---------------------------------------------------------------------")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("\n[OK] Base de dados atualizada com sucesso!\n")


if __name__ == "__main__":
    main()
