"""Módulo de ingestão de dados de pesquisas e apuração eleitoral.

Exporta as classes canônicas de extração e sincronização de dados do TSE e da web.
"""

from src.ingestion.base import BaseElectionDataExtractor
from src.ingestion.pesqele_collector import PesqEleCollector
from src.ingestion.tse_results import TSEResultsExtractor
from src.ingestion.web_poll_extractor import WebPollExtractor

__all__ = [
    "BaseElectionDataExtractor",
    "PesqEleCollector",
    "TSEResultsExtractor",
    "WebPollExtractor",
]
