"""Ponto de entrada do pacote margem_eleitoral.

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
    print("Iniciando margem_eleitoral (Auditoria e Storytelling de Pesquisas 2026)...")
    run()


if __name__ == "__main__":
    main()
