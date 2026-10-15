"""Normalizador de taxonomias para institutos, metodologias e candidatos.

Harmoniza nomenclaturas heterogêneas oriundas do PesqEle ou de diferentes publicações
para padrões unificados de análise.
"""

from pathlib import Path
from typing import Any

import yaml

from src.transformations.schemas import MetodologiaEnum


class TaxonomyNormalizer:
    """Carrega regras taxonômicas e realiza normalização de entidades eleitorais."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        """Inicializa o normalizador carregando o arquivo de mapeamento taxonômico.

        Args:
            config_path: Caminho para o arquivo YAML de taxonomia. Se None, utiliza
                o caminho padrão em config/taxonomy_mapping.yaml.

        Raises:
            FileNotFoundError: Se o arquivo de taxonomia não for localizado.
        """
        if config_path is None:
            config_path = (
                Path(__file__).resolve().parent.parent.parent / "config" / "taxonomy_mapping.yaml"
            )
        self.config_path = Path(config_path)

        if not self.config_path.exists():
            raise FileNotFoundError(f"Arquivo de taxonomia não encontrado em: {self.config_path}")

        with open(self.config_path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        self.institutes_map: dict[str, str] = {
            k.strip().upper(): v.strip() for k, v in data.get("institutes", {}).items()
        }
        self.methodologies_map: dict[str, str] = {
            k.strip().upper(): v.strip() for k, v in data.get("methodologies", {}).items()
        }
        self.candidates_map: dict[str, str] = {
            k.strip().upper(): v.strip() for k, v in data.get("candidate_aliases", {}).items()
        }

    @staticmethod
    def _strip_accents(text: str) -> str:
        """Remove acentos gráficos para comparação fonética e textual segura.

        Args:
            text: Texto de entrada com ou sem acentuação.

        Returns:
            str: Texto com caracteres acentuados convertidos para ASCII base.

        Raises:
            None.
        """
        import unicodedata

        return "".join(
            c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
        )

    def normalize_candidate(self, name: str) -> str:
        """Normaliza o nome do candidato para sua forma canônica.

        Args:
            name: Nome bruto do candidato.

        Returns:
            str: Nome canônico padronizado.

        Raises:
            None.
        """
        cleaned = self._strip_accents(name.strip().upper())
        # Mapeia chaves também sem acento
        stripped_map = {self._strip_accents(k): v for k, v in self.candidates_map.items()}

        if cleaned in stripped_map:
            return stripped_map[cleaned]

        # Prioriza chaves mais longas para evitar colisões (ex: 'FLAVIO BOLSONARO' antes de 'BOLSONARO')
        for key in sorted(stripped_map.keys(), key=len, reverse=True):
            if key in cleaned or cleaned in key:
                return stripped_map[key]

        return name.strip()

    def normalize_institute(self, name: str) -> str:
        """Normaliza a razão social ou nome fantasia para o nome padrão de exibição.

        Args:
            name: Nome bruto do instituto de pesquisa.

        Returns:
            str: Nome fantasia canônico padronizado.

        Raises:
            None.
        """
        cleaned = name.strip().upper()
        if cleaned in self.institutes_map:
            return self.institutes_map[cleaned]

        # Busca por correspondência parcial caso não haja correspondência exata
        for key, canonical in self.institutes_map.items():
            if key in cleaned or cleaned in key:
                return canonical

        return name.strip()

    def normalize_methodology(self, method: str) -> MetodologiaEnum:
        """Normaliza a descrição metodológica para o enum MetodologiaEnum correspondente.

        Args:
            method: String descritiva da metodologia utilizada no campo.

        Returns:
            MetodologiaEnum: Enumeração tipada correspondente.

        Raises:
            ValueError: Se a metodologia não puder ser mapeada para nenhuma categoria válida.
        """
        cleaned = method.strip().upper()
        mapped_key = self.methodologies_map.get(cleaned)

        if mapped_key:
            return MetodologiaEnum(mapped_key)

        # Tentativa de busca por substring
        for key, enum_val in self.methodologies_map.items():
            if key in cleaned:
                return MetodologiaEnum(enum_val)

        # Fallback padrão ou erro caso completamente desconhecido
        if "DOMICILIAR" in cleaned or "PRESENCIAL" in cleaned:
            return MetodologiaEnum.PRESENCIAL_DOMICILIAR
        if "TELEFONE" in cleaned or "CATI" in cleaned or "FONE" in cleaned:
            return MetodologiaEnum.TELEFONICA_CATI
        if "ONLINE" in cleaned or "INTERNET" in cleaned or "WEB" in cleaned:
            return MetodologiaEnum.ONLINE

        raise ValueError(f"Metodologia desconhecida ou não mapeável: '{method}'")
