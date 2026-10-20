"""Ponto de entrada raiz para execução da aplicação Streamlit.

Permite a execução direta via:
    uv run app.py
    python app.py
ou via servidor Streamlit / Streamlit Community Cloud:
    streamlit run app.py
"""

import importlib
import sys
from pathlib import Path

# Garante que a raiz do repositório esteja no sys.path para o Streamlit Cloud
_repo_root = Path(__file__).resolve().parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import streamlit as st

import src.presentation.app as _app_mod

if __name__ == "__main__":
    if st.runtime.exists():
        if "pytest" not in sys.modules:
            for k, mod in list(sys.modules.items()):
                if k.startswith("src.") and mod is not None:
                    try:
                        importlib.reload(mod)
                    except (ImportError, ModuleNotFoundError):
                        pass
        _app_mod.main()
    else:
        _app_mod.run()
