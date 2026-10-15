"""Extrator e gerenciador dos resultados oficiais de totalização do TSE.

Processa a apuração oficial do TSE consumindo diretamente os endpoints da API oficial
de divulgação de resultados (resultados.tse.jus.br) e persistindo snapshots brutos em data/raw/{year}.
"""

import json
from pathlib import Path
from typing import Any

import httpx

from src.ingestion.base import BaseElectionDataExtractor
from src.transformations.normalizer import TaxonomyNormalizer
from src.transformations.schemas import ResultadoOficialTSESchema


class TSEResultsExtractor(BaseElectionDataExtractor):
    """Extrator de resultados consolidados de urnas emitidos oficialmente pelo TSE."""

    TSE_API_URL_2026_T1 = (
        "https://resultados.tse.jus.br/oficial/ele2026/6257/dados/br/br-c0001-e006257-u.json"
    )

    def __init__(self, year: int, turno: int = 1, raw_base_dir: str | Path | None = None) -> None:
        """Inicializa o extrator para o ano e turno especificados.

        Args:
            year: Ano eleitoral (ex.: 2026, 2022).
            turno: Turno da eleição (1 ou 2).
            raw_base_dir: Diretório base opcional para os dados brutos.

        Raises:
            ValueError: Se o turno for inválido.
        """
        super().__init__(year=year, raw_base_dir=raw_base_dir)
        if turno not in (1, 2):
            raise ValueError(f"Turno eleitoral inválido: {turno}. Esperado 1 ou 2.")
        self.turno = turno
        self.normalizer = TaxonomyNormalizer()

    def fetch_from_tse_api(self) -> ResultadoOficialTSESchema:
        """Consome a API oficial de resultados do TSE para o 1º Turno de 2026.

        Baixa o arquivo JSON oficial de totalização (br-c0001-e006257-u.json),
        salva o snapshot bruto em data/raw/2026/ e extrai os percentuais e votos oficiais.

        Args:
            None.

        Returns:
            ResultadoOficialTSESchema: Contrato validado com os dados da apuração oficial.

        Raises:
            httpx.HTTPError: Se houver falha de rede ou timeout na requisição.
            ValueError: Se a estrutura JSON retornada pelo TSE for incompatível.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) margem_eleitoral/0.1.0",
            "Accept": "application/json, text/plain, */*",
        }

        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(self.TSE_API_URL_2026_T1, headers=headers)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()

        # Salva o snapshot bruto imutável recebido diretamente do TSE
        raw_api_file = self.raw_dir / "br-c0001-e006257-u.json"
        raw_api_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        # Parsing dos blocos de votação oficial
        v_block = data.get("v", {})
        e_block = data.get("e", {})
        total_validos = int(v_block.get("vv", v_block.get("vvc", 0)))
        total_brancos = int(v_block.get("vb", 0))
        total_nulos = int(v_block.get("tvn", 0))
        total_abstencoes = int(e_block.get("a", 0))

        carg_list = data.get("carg", [])
        if not carg_list:
            raise ValueError("Bloco 'carg' não encontrado na resposta oficial do TSE.")

        carg = carg_list[0]
        cands_raw: list[tuple[str, float, int]] = []

        for agr in carg.get("agr", []):
            for par in agr.get("par", []):
                for c in par.get("cand", []):
                    raw_name = c.get("nmu") or c.get("nm") or "DESCONHECIDO"
                    cand_name = self.normalizer.normalize_candidate(raw_name)
                    pct_val = float(c.get("pvap", "0.0").replace(",", "."))
                    votos_val = int(c.get("vap", 0))
                    cands_raw.append((cand_name, pct_val, votos_val))

        cands_raw.sort(key=lambda x: x[1], reverse=True)

        resultado_nominal: dict[str, float] = {}
        for name, pct, _ in cands_raw:
            if pct >= 0.25:
                resultado_nominal[name] = pct

        # Agrupa candidatos minoritários (< 0.25%) em Outros para fechar exatamente 100.0%
        soma_principais = sum(resultado_nominal.values())
        resultado_nominal["Outros"] = round(100.0 - soma_principais, 2)

        result_obj = ResultadoOficialTSESchema(
            cargo="PRESIDENTE",
            turno=1,
            ano=2026,
            total_votos_validos=total_validos,
            total_brancos=total_brancos,
            total_nulos=total_nulos,
            total_abstencoes=total_abstencoes,
            resultado_nominal=resultado_nominal,
        )

        # Salva o arquivo de apuração normalizado em data/raw/2026/resultado_tse_2026_t1.json
        local_target = self.raw_dir / f"resultado_tse_{self.year}_t{self.turno}.json"
        local_target.write_text(result_obj.model_dump_json(indent=2), encoding="utf-8")

        return result_obj

    def extract_and_transform(self) -> ResultadoOficialTSESchema:
        """Carrega, valida e retorna a totalização oficial do TSE para o ano e turno.

        Para 2026 (Turno 1), consulta primeiramente a API oficial do TSE em tempo real
        com fallback para o snapshot bruto local caso a rede esteja indisponível.

        Args:
            None.

        Returns:
            ResultadoOficialTSESchema: Contrato validado contendo a apuração oficial do TSE.

        Raises:
            FileNotFoundError: Se o snapshot de dados brutos da apuração não for localizado.
            ValueError: Se os dados brutos violarem os invariantes de validação.
        """
        if self.year == 2026 and self.turno == 1:
            try:
                return self.fetch_from_tse_api()
            except Exception:
                # Fallback para snapshot local se a requisição à API falhar
                pass

        json_filename = f"resultado_tse_{self.year}_t{self.turno}.json"
        raw_file = self.raw_dir / json_filename

        if not raw_file.exists():
            raise FileNotFoundError(
                f"Arquivo de apuração oficial não encontrado em: {raw_file}. "
                f"Certifique-se de que o snapshot bruto correspondente exista em data/raw/{self.year}/."
            )

        with open(raw_file, encoding="utf-8") as f:
            raw_data = json.load(f)

        return ResultadoOficialTSESchema(**raw_data)

    def save_processed(self, dest_path: Path | None = None) -> Path:
        """Exporta o resultado oficial processado para arquivo JSON padronizado.

        Args:
            dest_path: Caminho de destino opcional. Se None, utiliza data/processed/resultado_oficial_{year}_t{turno}.json.

        Returns:
            Path: Caminho do arquivo gravado.

        Raises:
            OSError: Se falhar a gravação em disco.
        """
        result = self.extract_and_transform()
        if dest_path is None:
            repo_root = Path(__file__).resolve().parent.parent.parent
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True, exist_ok=True)
            dest_path = processed_dir / f"resultado_oficial_{self.year}_t{self.turno}.json"

        dest_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return dest_path
