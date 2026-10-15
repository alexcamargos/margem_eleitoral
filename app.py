"""Ponto de entrada raiz para execução da aplicação Streamlit.

Permite a execução direta via:
    uv run app.py
ou
    python app.py
"""

from src.presentation.app import run

if __name__ == "__main__":
    run()
