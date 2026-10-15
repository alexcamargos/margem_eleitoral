"""Classes-base e abstrações para coletores e extratores de dados eleitorais.

Define protocolos e classes abstratas para padronizar o ciclo de vida de extração,
transformação, validação e persistência dos dados do TSE e do PesqEle.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx


class BaseElectionDataExtractor(ABC):
    """Classe-base abstrata para extração e processamento de dados do TSE."""

    def __init__(self, year: int, raw_base_dir: str | Path | None = None) -> None:
        """Inicializa o extrator para um determinado ano eleitoral.

        Args:
            year: Ano do pleito eleitoral (ex.: 2026, 2022).
            raw_base_dir: Diretório base para persistência de dados brutos.
                Se None, utiliza o caminho padrão data/raw/{year}.

        Raises:
            ValueError: Se o ano fornecido for inválido.
        """
        if year < 1989:
            raise ValueError(f"Ano eleitoral inválido para eleições diretas no Brasil: {year}")

        self.year = year
        repo_root = Path(__file__).resolve().parent.parent.parent
        self.raw_dir = (
            Path(raw_base_dir) if raw_base_dir else repo_root / "data" / "raw" / str(year)
        )
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def download_file_if_missing(
        self,
        url: str,
        destination_filename: str,
        timeout_seconds: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> Path:
        """Baixa um arquivo remoto caso ele não exista no diretório bruto local.

        Args:
            url: URL completa do recurso remoto no TSE ou CDN.
            destination_filename: Nome do arquivo a ser salvo localmente.
            timeout_seconds: Tempo limite da requisição HTTP em segundos.
            headers: Cabeçalhos HTTP adicionais para a requisição.

        Returns:
            Path: Caminho absoluto para o arquivo baixado ou já existente.

        Raises:
            httpx.HTTPError: Se a requisição HTTP falhar e o arquivo não existir localmente.
        """
        dest_path = self.raw_dir / destination_filename
        if dest_path.exists() and dest_path.stat().st_size > 0:
            return dest_path

        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) margem_eleitoral/0.1.0"
        }
        if headers:
            default_headers.update(headers)

        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            response = client.get(url, headers=default_headers)
            response.raise_for_status()
            dest_path.write_bytes(response.content)

        return dest_path

    @abstractmethod
    def extract_and_transform(self) -> Any:
        """Executa a extração, transformação e validação dos dados eleitorais.

        Args:
            None.

        Returns:
            Any: Objeto ou lista de objetos estruturados e validados.

        Raises:
            NotImplementedError: Deve ser implementado pelas subclasses.
        """
        raise NotImplementedError("Subclasses devem implementar extract_and_transform()")
