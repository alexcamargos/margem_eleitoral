"""Ponto de entrada raiz para execução da aplicação Streamlit.

Permite a execução direta via:
    uv run app.py
    python app.py
ou via servidor Streamlit / Streamlit Community Cloud:
    streamlit run app.py
"""

import importlib
import sys

import streamlit as st

import src.presentation.app as _app_mod

if __name__ == "__main__":
    if st.runtime.exists():
        if "pytest" not in sys.modules:
            importlib.reload(_app_mod)
        _app_mod.main()
    else:
        _app_mod.run()
