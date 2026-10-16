"""Ponto de entrada raiz para execução da aplicação Streamlit.

Permite a execução direta via:
    uv run app.py
    python app.py
ou via servidor Streamlit / Streamlit Community Cloud:
    streamlit run app.py
"""

import streamlit as st

from src.presentation.app import main, run

if __name__ == "__main__":
    if st.runtime.exists():
        main()
    else:
        run()

