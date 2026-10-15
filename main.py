"""Ponto de entrada do pacote Margem Eleitoral.

Para executar a aplicação interativa:
    uv run app
"""

from src.presentation.app import run


def main() -> None:
    """Executa a aplicação interativa Streamlit.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: Ao finalizar a execução do servidor Streamlit.
    """
    print("Iniciando Margem Eleitoral (Auditoria e Storytelling Científico de Pesquisas Eleitorais)...")
    run()


if __name__ == "__main__":
    main()
