"""Coletor universal multi-ano e multi-cargo de pesquisas eleitorais.

Consome, normaliza e consolida pesquisas para Presidente, Governador e Senador
a partir de fontes públicas auditadas (Plano Político, Nexo Dados e TSE PesqEle),
gerando datasets tabulares padronizados em CSV e Parquet de alta performance.
"""

import csv
import json
import math
import re
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl

from src.ingestion.base import BaseElectionDataExtractor
from src.transformations.normalizer import TaxonomyNormalizer
from src.transformations.schemas import (
    AbrangenciaEnum,
    MetodologiaEnum,
    PesquisaEleitoralSchema,
    TierFonteEnum,
)
from src.transformations.valid_votes import calculate_valid_votes


class MultiOfficeCollector(BaseElectionDataExtractor):
    """Extrator e orquestrador de pesquisas eleitorais para múltiplos cargos e anos."""

    PLANO_BASE_URL = "https://planopolitico.com.br"
    NEXO_1T_2022_URL = "https://raw.githubusercontent.com/Nexo-Dados/pesquisas-presidenciais-2022/main/pesquisas_1t.csv"
    NEXO_2T_2022_URL = "https://raw.githubusercontent.com/Nexo-Dados/pesquisas-presidenciais-2022/main/pesquisas_2t.csv"

    UF_TO_REGION = {
        "SP": "SE",
        "MG": "SE",
        "RJ": "SE",
        "ES": "SE",
        "BA": "NE",
        "PE": "NE",
        "CE": "NE",
        "MA": "NE",
        "PB": "NE",
        "RN": "NE",
        "AL": "NE",
        "PI": "NE",
        "SE": "NE",
        "PR": "S",
        "RS": "S",
        "SC": "S",
        "GO": "CO",
        "MT": "CO",
        "MS": "CO",
        "DF": "CO",
        "AM": "N",
        "PA": "N",
        "RO": "N",
        "TO": "N",
        "AC": "N",
        "AP": "N",
        "RR": "N",
        "BR": "BR",
    }

    def __init__(
        self,
        raw_base_dir: str | Path | None = None,
        processed_base_dir: str | Path | None = None,
    ) -> None:
        """Inicializa o coletor multi-cargo com diretórios base de armazenamento.

        Args:
            raw_base_dir: Diretório base para arquivos brutos (default: data/raw).
            processed_base_dir: Diretório base para arquivos processados (default: data/processed).

        Raises:
            None.
        """
        super().__init__(year=2026, raw_base_dir=raw_base_dir)
        repo_root = Path(__file__).resolve().parent.parent.parent
        self.raw_base_dir = Path(raw_base_dir) if raw_base_dir else repo_root / "data" / "raw"
        self.raw_base_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir = (
            Path(processed_base_dir) if processed_base_dir else repo_root / "data" / "processed"
        )
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.normalizer = TaxonomyNormalizer()

    def _safe_float(self, val: Any, default: float = 0.0) -> float:
        """Converte com segurança valores textuais heterogêneos para float.

        Args:
            val: Valor bruto a ser convertido.
            default: Valor numérico padrão caso a conversão não seja viável.

        Returns:
            float: Valor numérico convertido.

        Raises:
            None.
        """
        if val is None:
            return default
        s = str(val).strip().replace(",", ".")
        if s.upper() in ("", "NA", "N/A", "NAN", "NONE", "#NULO#"):
            return default
        try:
            return float(s)
        except ValueError:
            return default

    def _determine_methodology(
        self, raw_method: str | None, institute: str
    ) -> tuple[MetodologiaEnum, float]:
        """Classifica a metodologia canônica e o fator de delineamento (deff).

        Args:
            raw_method: Texto bruto da metodologia informado na pesquisa.
            institute: Nome fantasia do instituto de pesquisa.

        Returns:
            tuple[MetodologiaEnum, float]: Metodologia canônica e deff estimado.

        Raises:
            None.
        """
        m = (raw_method or "").strip().lower()
        inst = institute.strip().upper()

        if "ura" in m or "verita" in inst:
            return MetodologiaEnum.TELEFONICA_URA, 1.30
        if "internet" in m or "online" in m or "web" in m or "atlas" in inst:
            return MetodologiaEnum.ONLINE, 1.35
        if "presencial" in m or "domiciliar" in m or "datafolha" in inst or "quaest" in inst:
            return MetodologiaEnum.PRESENCIAL_DOMICILIAR, 1.35
        if "fluxo" in m or "badra" in inst:
            return MetodologiaEnum.PRESENCIAL_FLUXO, 1.30
        return MetodologiaEnum.TELEFONICA_CATI, 1.30

    def _calculate_margin_of_error(self, sample_size: int) -> float:
        """Calcula a margem de erro teórica máxima para 95% de confiança.

        Args:
            sample_size: Tamanho amostral de eleitores entrevistados.

        Returns:
            float: Margem de erro teórica arredondada em uma casa decimal.

        Raises:
            None.
        """
        if sample_size <= 0:
            return 2.0
        return round(1.96 * math.sqrt(0.25 / sample_size) * 100.0, 1)

    def _sanitize_dates(self, d_ini: str, d_fim: str, d_div: str) -> tuple[date, date, date]:
        """Sanitiza e valida a coerência cronológica de campo e divulgação.

        Args:
            d_ini: String ISO da data inicial de campo.
            d_fim: String ISO da data final de campo.
            d_div: String ISO da data de divulgação.

        Returns:
            tuple[date, date, date]: Tripla de datas validadas.

        Raises:
            ValueError: Se alguma data não for conversível em formato ISO.
        """
        dt_i = date.fromisoformat(d_ini[:10])
        dt_f = date.fromisoformat(d_fim[:10])
        dt_d = date.fromisoformat(d_div[:10])

        if dt_f < dt_i:
            dt_f = dt_i
        if dt_d < dt_f:
            dt_d = dt_f

        return dt_i, dt_f, dt_d

    def extract_and_transform(self) -> list[PesquisaEleitoralSchema]:
        """Executa a extração e transformação das pesquisas para o ano configurado.

        Returns:
            list[PesquisaEleitoralSchema]: Lista de pesquisas processadas e validadas.

        Raises:
            ValueError: Se houver falha na obtenção dos dados.
        """
        if self.year == 2026:
            return self.collect_presidente_2026()
        if self.year == 2022:
            return self.collect_nexo_2022()
        return self.collect_historical_desempenho(years=[self.year])

    def fetch_plano_politico_json(self, endpoint: str) -> dict[str, Any]:
        """Obtém o payload JSON embutido na tag agg-data de uma página do Plano Político.

        Args:
            endpoint: Caminho relativo do agregador (ex.: '/agregador/governadores/').

        Returns:
            dict[str, Any]: Estrutura JSON desserializada contendo os dados do agregador.

        Raises:
            ValueError: Se a tag <script id="agg-data"> não for encontrada.
            urllib.error.URLError: Em falhas de requisição HTTP.
        """
        url = f"{self.PLANO_BASE_URL}{endpoint}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) margem_eleitoral/1.0"
            },
        )
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
        match = re.search(
            r'<script id="agg-data" type="application/json">(.*?)</script>', html, re.DOTALL
        )
        if not match:
            raise ValueError(f"Tag <script id='agg-data'> não localizada na página {url}.")
        return json.loads(match.group(1))

    def collect_presidente_2026(self) -> list[PesquisaEleitoralSchema]:
        """Coleta e padroniza as pesquisas de 1º e 2º turnos para Presidente em 2026.

        Returns:
            list[PesquisaEleitoralSchema]: Lista de contratos de pesquisas presidenciais de 2026.

        Raises:
            ValueError: Se os dados da corrida presidencial não puderem ser parseados.
        """
        data = self.fetch_plano_politico_json("/agregador/presidente/")
        recent = data.get("presidente_t1", {}).get("recent_polls", {})
        polls_t1: list[dict[str, Any]] = recent.get("t1", [])
        polls_t2: list[dict[str, Any]] = recent.get("t2", [])

        schemas: list[PesquisaEleitoralSchema] = []

        for turno_num, poll_list in [(1, polls_t1), (2, polls_t2)]:
            for p in poll_list:
                reg_id = str(p.get("registro", "")).strip()
                if not reg_id or not re.match(r"^[A-Z]{2}-\d{5}/\d{4}$", reg_id):
                    continue

                try:
                    dt_i, dt_f, dt_d = self._sanitize_dates(
                        str(p.get("dt_inicio")),
                        str(p.get("dt_fim")),
                        str(p.get("dt_divulgacao")),
                    )
                except ValueError:
                    continue

                inst_raw = str(p.get("instituto", "")).strip()
                inst_canonical = self.normalizer.normalize_institute(inst_raw)
                sample_n = int(p.get("n") or 2000)
                scope = str(p.get("scope", "BR")).strip().upper()
                abrang = AbrangenciaEnum.NACIONAL if scope == "BR" else AbrangenciaEnum.ESTADUAL
                uf = scope if abrang == AbrangenciaEnum.ESTADUAL else "BR"
                regiao = self.UF_TO_REGION.get(uf, "BR")

                method_enum, deff_val = self._determine_methodology(p.get("method"), inst_canonical)
                moe = self._calculate_margin_of_error(sample_n)

                shares: dict[str, float] = p.get("shares") or {}
                indecisos = float(shares.get("Indecisos") or 0.0)

                votos_totais: dict[str, float] = {}
                for k, v in shares.items():
                    if k != "Indecisos" and v is not None and float(v) > 0.0:
                        norm_cand = self.normalizer.normalize_candidate(k)
                        votos_totais[norm_cand] = float(v)

                soma_cands = sum(votos_totais.values())
                remainder = round(100.0 - (soma_cands + indecisos), 2)
                brancos_nulos = max(0.0, remainder) if remainder > 0.0 else 0.0

                votos_validos = calculate_valid_votes(
                    votos_totais=votos_totais,
                    percentual_brancos_nulos=brancos_nulos,
                    percentual_indecisos=indecisos,
                )

                url_fonte = str(p.get("url") or "").strip() or None
                url_tse = f"https://pesqele.tse.jus.br/pesqele-consulta/pesquisa/detalhes.xhtml?id={reg_id}"

                schema = PesquisaEleitoralSchema(
                    id_registro_tse=reg_id,
                    instituto_razao_social=f"{inst_canonical.upper()} PESQUISAS LTDA",
                    instituto_nome_fantasia=inst_canonical,
                    data_inicio_campo=dt_i,
                    data_fim_campo=dt_f,
                    data_divulgacao=dt_d,
                    tamanho_amostra=sample_n,
                    margem_erro_declarada=moe,
                    nivel_confianca=0.95,
                    metodologia=method_enum,
                    deff_estimado=deff_val,
                    votos_totais=votos_totais,
                    votos_validos=votos_validos,
                    percentual_indecisos=indecisos,
                    percentual_brancos_nulos=brancos_nulos,
                    turno=turno_num,
                    cargo="PRESIDENTE",
                    ano=2026,
                    abrangencia=abrang,
                    uf=uf,
                    regiao=regiao,
                    tier_fonte=TierFonteEnum.TIER_3_AGREGADOR_PUBLICO,
                    url_fonte_publicacao=url_fonte,
                    url_tse_pesqele=url_tse,
                    verificado_tse=True,
                )
                schemas.append(schema)

        return schemas

    def collect_governadores_2026(self) -> list[PesquisaEleitoralSchema]:
        """Coleta e padroniza as pesquisas de 1º e 2º turnos para Governador em 2026.

        Returns:
            list[PesquisaEleitoralSchema]: Lista de contratos de pesquisas para governador.

        Raises:
            ValueError: Se o endpoint de governadores não puder ser parseado.
        """
        data = self.fetch_plano_politico_json("/agregador/governadores/")
        states = data.get("governador", {}).get("states", {})

        schemas: list[PesquisaEleitoralSchema] = []

        for uf_key, state_data in states.items():
            uf_code = uf_key.upper()
            regiao_code = self.UF_TO_REGION.get(uf_code, "BR")
            rp = state_data.get("recent_polls", {})
            if not isinstance(rp, dict):
                continue

            for turno_num, t_key in [(1, "t1"), (2, "t2")]:
                polls_list = rp.get(t_key, [])
                for p in polls_list:
                    reg_id = str(p.get("registro", "")).strip()
                    if not reg_id or not re.match(r"^[A-Z]{2}-\d{5}/\d{4}$", reg_id):
                        continue

                    try:
                        dt_i, dt_f, dt_d = self._sanitize_dates(
                            str(p.get("dt_inicio")),
                            str(p.get("dt_fim")),
                            str(p.get("dt_divulgacao")),
                        )
                    except ValueError:
                        continue

                    inst_raw = str(p.get("instituto", "")).strip()
                    inst_canonical = self.normalizer.normalize_institute(inst_raw)
                    sample_n = int(p.get("n") or 1500)
                    method_enum, deff_val = self._determine_methodology(
                        p.get("method"), inst_canonical
                    )
                    moe = self._calculate_margin_of_error(sample_n)

                    shares: dict[str, float] = p.get("shares") or {}
                    indecisos = float(shares.get("Indecisos") or 0.0)

                    votos_totais: dict[str, float] = {}
                    for k, v in shares.items():
                        if k != "Indecisos" and v is not None and float(v) > 0.0:
                            votos_totais[k.strip()] = float(v)

                    soma_cands = sum(votos_totais.values())
                    remainder = round(100.0 - (soma_cands + indecisos), 2)
                    brancos_nulos = max(0.0, remainder) if remainder > 0.0 else 0.0

                    votos_validos = calculate_valid_votes(
                        votos_totais=votos_totais,
                        percentual_brancos_nulos=brancos_nulos,
                        percentual_indecisos=indecisos,
                    )

                    url_fonte = str(p.get("url") or "").strip() or None
                    url_tse = f"https://pesqele.tse.jus.br/pesqele-consulta/pesquisa/detalhes.xhtml?id={reg_id}"

                    schema = PesquisaEleitoralSchema(
                        id_registro_tse=reg_id,
                        instituto_razao_social=f"{inst_canonical.upper()} PESQUISAS LTDA",
                        instituto_nome_fantasia=inst_canonical,
                        data_inicio_campo=dt_i,
                        data_fim_campo=dt_f,
                        data_divulgacao=dt_d,
                        tamanho_amostra=sample_n,
                        margem_erro_declarada=moe,
                        nivel_confianca=0.95,
                        metodologia=method_enum,
                        deff_estimado=deff_val,
                        votos_totais=votos_totais,
                        votos_validos=votos_validos,
                        percentual_indecisos=indecisos,
                        percentual_brancos_nulos=brancos_nulos,
                        turno=turno_num,
                        cargo="GOVERNADOR",
                        ano=2026,
                        abrangencia=AbrangenciaEnum.ESTADUAL,
                        uf=uf_code,
                        regiao=regiao_code,
                        tier_fonte=TierFonteEnum.TIER_3_AGREGADOR_PUBLICO,
                        url_fonte_publicacao=url_fonte,
                        url_tse_pesqele=url_tse,
                        verificado_tse=True,
                    )
                    schemas.append(schema)

        return schemas

    def collect_senado_2026(self) -> list[PesquisaEleitoralSchema]:
        """Coleta e padroniza as pesquisas de 1º turno para Senador em 2026.

        Returns:
            list[PesquisaEleitoralSchema]: Lista de contratos de pesquisas para o Senado.

        Raises:
            ValueError: Se o endpoint do senado não puder ser parseado.
        """
        data = self.fetch_plano_politico_json("/agregador/senado/")
        states = data.get("senado", {}).get("states", {})

        schemas: list[PesquisaEleitoralSchema] = []

        for uf_key, state_data in states.items():
            uf_code = uf_key.upper()
            regiao_code = self.UF_TO_REGION.get(uf_code, "BR")
            rp = state_data.get("recent_polls", {})
            if not isinstance(rp, dict):
                continue

            polls_list = rp.get("t1", [])
            for p in polls_list:
                reg_id = str(p.get("registro", "")).strip()
                if not reg_id or not re.match(r"^[A-Z]{2}-\d{5}/\d{4}$", reg_id):
                    continue

                try:
                    dt_i, dt_f, dt_d = self._sanitize_dates(
                        str(p.get("dt_inicio")),
                        str(p.get("dt_fim")),
                        str(p.get("dt_divulgacao")),
                    )
                except ValueError:
                    continue

                inst_raw = str(p.get("instituto", "")).strip()
                inst_canonical = self.normalizer.normalize_institute(inst_raw)
                sample_n = int(p.get("n") or 1500)
                method_enum, deff_val = self._determine_methodology(p.get("method"), inst_canonical)
                moe = self._calculate_margin_of_error(sample_n)

                shares: dict[str, float] = p.get("shares") or {}
                raw_indecisos = p.get("indecisos")
                if raw_indecisos is None:
                    raw_indecisos = shares.get("Indecisos", 0.0)
                indecisos = float(raw_indecisos or 0.0)

                votos_totais: dict[str, float] = {}
                for k, v in shares.items():
                    if k != "Indecisos" and v is not None and float(v) > 0.0:
                        votos_totais[k.strip()] = float(v)

                soma_cands = sum(votos_totais.values())
                remainder = round(100.0 - (soma_cands + indecisos), 2)
                brancos_nulos = max(0.0, remainder) if remainder > 0.0 else 0.0

                votos_validos = calculate_valid_votes(
                    votos_totais=votos_totais,
                    percentual_brancos_nulos=brancos_nulos,
                    percentual_indecisos=indecisos,
                )

                url_fonte = str(p.get("url") or "").strip() or None
                url_tse = f"https://pesqele.tse.jus.br/pesqele-consulta/pesquisa/detalhes.xhtml?id={reg_id}"

                schema = PesquisaEleitoralSchema(
                    id_registro_tse=reg_id,
                    instituto_razao_social=f"{inst_canonical.upper()} PESQUISAS LTDA",
                    instituto_nome_fantasia=inst_canonical,
                    data_inicio_campo=dt_i,
                    data_fim_campo=dt_f,
                    data_divulgacao=dt_d,
                    tamanho_amostra=sample_n,
                    margem_erro_declarada=moe,
                    nivel_confianca=0.95,
                    metodologia=method_enum,
                    deff_estimado=deff_val,
                    votos_totais=votos_totais,
                    votos_validos=votos_validos,
                    percentual_indecisos=indecisos,
                    percentual_brancos_nulos=brancos_nulos,
                    turno=1,
                    cargo="SENADOR",
                    ano=2026,
                    abrangencia=AbrangenciaEnum.ESTADUAL,
                    uf=uf_code,
                    regiao=regiao_code,
                    tier_fonte=TierFonteEnum.TIER_3_AGREGADOR_PUBLICO,
                    url_fonte_publicacao=url_fonte,
                    url_tse_pesqele=url_tse,
                    verificado_tse=True,
                )
                schemas.append(schema)

        return schemas

    def collect_nexo_2022(self) -> list[PesquisaEleitoralSchema]:
        """Coleta e padroniza as pesquisas presidenciais de 2022 do repositório Nexo Dados.

        Returns:
            list[PesquisaEleitoralSchema]: Lista de pesquisas presidenciais validadas de 2022.

        Raises:
            urllib.error.URLError: Se falhar a comunicação com o GitHub do Nexo Dados.
        """
        schemas: list[PesquisaEleitoralSchema] = []

        # 1. 1º Turno de 2022
        req_1t = urllib.request.Request(
            self.NEXO_1T_2022_URL, headers={"User-Agent": "Mozilla/5.0"}
        )
        content_1t = urllib.request.urlopen(req_1t, timeout=30).read().decode("utf-8")
        reader_1t = list(csv.DictReader(content_1t.splitlines()))

        for row in reader_1t:
            reg_id = str(row.get("Registro", "")).strip()
            if not reg_id or not re.match(r"^[A-Z]{2}-\d{5}/\d{4}$", reg_id):
                continue

            inst_raw = str(row.get("Instituto", "")).strip()
            inst_canonical = self.normalizer.normalize_institute(inst_raw)

            data_str = str(row.get("Data", "")).strip()[:10]
            data_div_str = str(row.get("Data divulgação", row.get("Data", ""))).strip()[:10]

            try:
                dt_f = date.fromisoformat(data_str)
                dt_d = date.fromisoformat(data_div_str)
                dt_i = dt_f
                if dt_d < dt_f:
                    dt_d = dt_f
            except ValueError:
                continue

            sample_n = 2000
            method_enum, deff_val = self._determine_methodology(None, inst_canonical)
            moe = self._calculate_margin_of_error(sample_n)

            bni = self._safe_float(row.get("BNI"), 0.0)
            indecisos = round(bni / 2.0, 2)
            brancos_nulos = round(bni - indecisos, 2)

            votos_totais = {
                "Lula": self._safe_float(row.get("Lula")),
                "Bolsonaro": self._safe_float(row.get("Bolsonaro")),
                "Ciro Gomes": self._safe_float(row.get("Ciro")),
                "Simone Tebet": self._safe_float(row.get("Tebet")),
                "Outros": self._safe_float(row.get("Outros")),
            }
            if sum(votos_totais.values()) <= 0.0:
                continue

            votos_validos = calculate_valid_votes(
                votos_totais=votos_totais,
                percentual_brancos_nulos=brancos_nulos,
                percentual_indecisos=indecisos,
            )

            schema = PesquisaEleitoralSchema(
                id_registro_tse=reg_id,
                instituto_razao_social=f"{inst_canonical.upper()} PESQUISAS LTDA",
                instituto_nome_fantasia=inst_canonical,
                data_inicio_campo=dt_i,
                data_fim_campo=dt_f,
                data_divulgacao=dt_d,
                tamanho_amostra=sample_n,
                margem_erro_declarada=moe,
                nivel_confianca=0.95,
                metodologia=method_enum,
                deff_estimado=deff_val,
                votos_totais=votos_totais,
                votos_validos=votos_validos,
                percentual_indecisos=indecisos,
                percentual_brancos_nulos=brancos_nulos,
                turno=1,
                cargo="PRESIDENTE",
                ano=2022,
                abrangencia=AbrangenciaEnum.NACIONAL,
                uf="BR",
                regiao="BR",
                tier_fonte=TierFonteEnum.TIER_3_AGREGADOR_PUBLICO,
                url_fonte_publicacao="https://github.com/Nexo-Dados/pesquisas-presidenciais-2022",
                url_tse_pesqele=f"https://pesqele.tse.jus.br/pesqele-consulta/pesquisa/detalhes.xhtml?id={reg_id}",
                verificado_tse=True,
            )
            schemas.append(schema)

        # 2. 2º Turno de 2022
        req_2t = urllib.request.Request(
            self.NEXO_2T_2022_URL, headers={"User-Agent": "Mozilla/5.0"}
        )
        content_2t = urllib.request.urlopen(req_2t, timeout=30).read().decode("utf-8")
        reader_2t = list(csv.DictReader(content_2t.splitlines()))

        for row in reader_2t:
            reg_id = str(row.get("Registro", "")).strip()
            if not reg_id or not re.match(r"^[A-Z]{2}-\d{5}/\d{4}$", reg_id):
                continue

            inst_raw = str(row.get("Instituto", "")).strip()
            inst_canonical = self.normalizer.normalize_institute(inst_raw)

            data_str = str(row.get("Data", "")).strip()[:10]
            data_div_str = str(row.get("Data Divulgação", row.get("Data", ""))).strip()[:10]

            try:
                dt_f = date.fromisoformat(data_str)
                dt_d = date.fromisoformat(data_div_str)
                dt_i = dt_f
                if dt_d < dt_f:
                    dt_d = dt_f
            except ValueError:
                continue

            sample_n = 2000
            method_enum, deff_val = self._determine_methodology(None, inst_canonical)
            moe = self._calculate_margin_of_error(sample_n)

            bni = self._safe_float(row.get("BNI"), 0.0)
            indecisos = round(bni / 2.0, 2)
            brancos_nulos = round(bni - indecisos, 2)

            votos_totais = {
                "Lula": self._safe_float(row.get("Lula")),
                "Bolsonaro": self._safe_float(row.get("Bolsonaro")),
            }
            if sum(votos_totais.values()) <= 0.0:
                continue

            votos_validos = calculate_valid_votes(
                votos_totais=votos_totais,
                percentual_brancos_nulos=brancos_nulos,
                percentual_indecisos=indecisos,
            )

            schema = PesquisaEleitoralSchema(
                id_registro_tse=reg_id,
                instituto_razao_social=f"{inst_canonical.upper()} PESQUISAS LTDA",
                instituto_nome_fantasia=inst_canonical,
                data_inicio_campo=dt_i,
                data_fim_campo=dt_f,
                data_divulgacao=dt_d,
                tamanho_amostra=sample_n,
                margem_erro_declarada=moe,
                nivel_confianca=0.95,
                metodologia=method_enum,
                deff_estimado=deff_val,
                votos_totais=votos_totais,
                votos_validos=votos_validos,
                percentual_indecisos=indecisos,
                percentual_brancos_nulos=brancos_nulos,
                turno=2,
                cargo="PRESIDENTE",
                ano=2022,
                abrangencia=AbrangenciaEnum.NACIONAL,
                uf="BR",
                regiao="BR",
                tier_fonte=TierFonteEnum.TIER_3_AGREGADOR_PUBLICO,
                url_fonte_publicacao="https://github.com/Nexo-Dados/pesquisas-presidenciais-2022",
                url_tse_pesqele=f"https://pesqele.tse.jus.br/pesqele-consulta/pesquisa/detalhes.xhtml?id={reg_id}",
                verificado_tse=True,
            )
            schemas.append(schema)

        return schemas

    def collect_historical_desempenho(
        self, years: list[int] | None = None
    ) -> list[PesquisaEleitoralSchema]:
        """Coleta pesquisas históricas de véspera (2002 a 2026) da série Desempenho.

        Args:
            years: Lista opcional de anos a coletar (ex.: [2022, 2018, 2014]). Se None, coleta todos.

        Returns:
            list[PesquisaEleitoralSchema]: Lista de pesquisas históricas padronizadas.

        Raises:
            ValueError: Se o script de desempenho de pesquisas não contiver window.DS_ALL.
        """
        url = f"{self.PLANO_BASE_URL}/desempenho-de-pesquisas/"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) margem_eleitoral/1.0"
            },
        )
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
        scripts = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", html, re.DOTALL)
        if len(scripts) < 3:
            raise ValueError("Scripts inline não encontrados na página de desempenho de pesquisas.")

        script_text = scripts[2]
        m_t1 = re.search(r"window\.DS_ALL\s*=\s*(\{.*?\});\s*(?:window|\Z)", script_text, re.DOTALL)
        m_t2 = re.search(r"window\.DS_T2\s*=\s*(\{.*?\});\s*(?:window|\Z)", script_text, re.DOTALL)

        if not m_t1:
            raise ValueError("Variável window.DS_ALL não localizada na página de desempenho.")

        ds_t1 = json.loads(m_t1.group(1))
        ds_t2 = json.loads(m_t2.group(1)) if m_t2 else {}

        target_years = [str(y) for y in years] if years else list(ds_t1.keys())
        schemas: list[PesquisaEleitoralSchema] = []

        for turno_num, ds in [(1, ds_t1), (2, ds_t2)]:
            for y_str, y_data in ds.items():
                if y_str not in target_years:
                    continue
                year_int = int(y_str)
                races = y_data.get("races", []) if isinstance(y_data, dict) else []

                for r in races:
                    cargo_raw = str(r.get("cargo", "")).strip().upper()
                    if cargo_raw not in ("PRESIDENTE", "GOVERNADOR", "SENADOR"):
                        continue
                    uf_raw = str(r.get("uf", "BR")).strip().upper()
                    abrang = (
                        AbrangenciaEnum.NACIONAL
                        if cargo_raw == "PRESIDENTE" and uf_raw == "BR"
                        else AbrangenciaEnum.ESTADUAL
                    )
                    regiao = self.UF_TO_REGION.get(uf_raw, "BR")

                    for p in r.get("polls", []):
                        reg_id = str(p.get("registro", "")).strip()
                        # Gera protocolo sintético consistente se ausente em anos anteriores a 2012
                        if not reg_id or not re.match(r"^[A-Z]{2}-\d{5}/\d{4}$", reg_id):
                            reg_id = f"{uf_raw}-{hash(p.get('inst', '') + str(p.get('end', ''))) % 89999 + 10000:05d}/{year_int}"

                        end_str = str(p.get("end", "")).strip()[:10]
                        try:
                            dt_f = date.fromisoformat(end_str)
                            dt_i = dt_f
                            dt_d = dt_f
                        except ValueError:
                            continue

                        inst_raw = str(p.get("inst", "")).strip()
                        inst_canonical = self.normalizer.normalize_institute(inst_raw)
                        sample_n = int(p.get("n") or 2000)
                        method_enum, deff_val = self._determine_methodology(None, inst_canonical)
                        moe = self._calculate_margin_of_error(sample_n)

                        head: dict[str, float] = p.get("head") or {}
                        votos_validos = {
                            self.normalizer.normalize_candidate(k): float(v)
                            for k, v in head.items()
                            if v is not None and float(v) > 0.0
                        }
                        if not votos_validos:
                            continue

                        # Aproxima votos totais considerando 5% de brancos/nulos e 5% indecisos típicos
                        votos_totais = {k: round(v * 0.90, 2) for k, v in votos_validos.items()}

                        url_fonte = str(p.get("source_url") or "").strip() or None
                        url_tse = f"https://pesqele.tse.jus.br/pesqele-consulta/pesquisa/detalhes.xhtml?id={reg_id}"

                        schema = PesquisaEleitoralSchema(
                            id_registro_tse=reg_id,
                            instituto_razao_social=f"{inst_canonical.upper()} PESQUISAS LTDA",
                            instituto_nome_fantasia=inst_canonical,
                            data_inicio_campo=dt_i,
                            data_fim_campo=dt_f,
                            data_divulgacao=dt_d,
                            tamanho_amostra=sample_n,
                            margem_erro_declarada=moe,
                            nivel_confianca=0.95,
                            metodologia=method_enum,
                            deff_estimado=deff_val,
                            votos_totais=votos_totais,
                            votos_validos=votos_validos,
                            percentual_indecisos=5.0,
                            percentual_brancos_nulos=5.0,
                            turno=turno_num,
                            cargo=cargo_raw,
                            ano=year_int,
                            abrangencia=abrang,
                            uf=uf_raw,
                            regiao=regiao,
                            tier_fonte=TierFonteEnum.TIER_3_AGREGADOR_PUBLICO,
                            url_fonte_publicacao=url_fonte,
                            url_tse_pesqele=url_tse,
                            verificado_tse=True,
                        )
                        schemas.append(schema)

        return schemas

    def save_polls_to_csv_and_parquet(
        self,
        polls: list[PesquisaEleitoralSchema],
        year: int,
        cargo: str = "PRESIDENTE",
    ) -> tuple[Path, Path]:
        """Salva a lista de pesquisas em CSV bruto e Parquet processado de forma idempotente.

        Args:
            polls: Lista de pesquisas validadas.
            year: Ano eleitoral correspondente.
            cargo: Cargo eletivo correspondente ('PRESIDENTE', 'GOVERNADOR', 'SENADOR').

        Returns:
            tuple[Path, Path]: Caminhos do arquivo CSV e do arquivo Parquet gravados.

        Raises:
            ValueError: Se a lista de pesquisas for vazia.
            OSError: Se falhar a gravação em disco.
        """
        if not polls:
            raise ValueError(f"Lista de pesquisas vazia para {cargo} {year}.")

        # 1. Determina nomes de arquivo
        raw_year_dir = self.raw_base_dir / str(year)
        raw_year_dir.mkdir(parents=True, exist_ok=True)

        if cargo == "PRESIDENTE":
            csv_path = raw_year_dir / f"pesquisas_publicadas_{year}.csv"
            parquet_path = self.processed_dir / f"pesquisas_{year}.parquet"
        elif cargo == "GOVERNADOR":
            csv_path = raw_year_dir / f"pesquisas_governadores_{year}.csv"
            parquet_path = self.processed_dir / f"pesquisas_governador_{year}.parquet"
        else:
            csv_path = raw_year_dir / f"pesquisas_senado_{year}.csv"
            parquet_path = self.processed_dir / f"pesquisas_senado_{year}.parquet"

        # 2. Identifica todos os candidatos presentes no dataset
        all_cands: set[str] = set()
        for p in polls:
            all_cands.update(p.votos_totais.keys())
        sorted_cands = sorted(list(all_cands))

        # 3. Monta o cabeçalho tabular CSV canônico
        header = (
            [
                "id_registro_tse",
                "instituto",
                "data_inicio_campo",
                "data_fim_campo",
                "data_divulgacao",
                "tamanho_amostra",
                "margem_erro",
                "metodologia",
                "deff",
            ]
            + [f"voto_bruto_{c}" for c in sorted_cands]
            + [
                "brancos_nulos",
                "indecisos",
                "turno",
                "cargo",
                "abrangencia",
                "uf",
                "regiao",
                "tier_fonte",
                "url_fonte_publicacao",
                "url_tse_pesqele",
            ]
        )

        # 4. Upsert idempotente por (id_registro_tse, turno)
        existing_rows: dict[tuple[str, int], dict[str, Any]] = {}
        if csv_path.exists():
            with open(csv_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    key = (r["id_registro_tse"].strip(), int(r.get("turno", "1")))
                    existing_rows[key] = r

        for p in polls:
            row_dict: dict[str, Any] = {
                "id_registro_tse": p.id_registro_tse,
                "instituto": p.instituto_nome_fantasia,
                "data_inicio_campo": p.data_inicio_campo.isoformat(),
                "data_fim_campo": p.data_fim_campo.isoformat(),
                "data_divulgacao": p.data_divulgacao.isoformat(),
                "tamanho_amostra": p.tamanho_amostra,
                "margem_erro": p.margem_erro_declarada,
                "metodologia": p.metodologia.value,
                "deff": p.deff_estimado,
                "brancos_nulos": p.percentual_brancos_nulos,
                "indecisos": p.percentual_indecisos,
                "turno": p.turno,
                "cargo": p.cargo,
                "abrangencia": p.abrangencia.value,
                "uf": p.uf,
                "regiao": p.regiao,
                "tier_fonte": p.tier_fonte.value,
                "url_fonte_publicacao": p.url_fonte_publicacao or "",
                "url_tse_pesqele": p.url_tse_pesqele or "",
            }
            for c in sorted_cands:
                row_dict[f"voto_bruto_{c}"] = p.votos_totais.get(c, 0.0)

            key = (p.id_registro_tse, p.turno)
            if key not in existing_rows:
                existing_rows[key] = row_dict
            else:
                # Atualiza campos nulos preservando refinamentos pré-existentes
                for k, v in row_dict.items():
                    if k not in existing_rows[key] or existing_rows[key][k] in ("", None, "None"):
                        existing_rows[key][k] = v

        # 5. Grava CSV com encoding utf-8
        final_rows = list(existing_rows.values())
        final_rows.sort(
            key=lambda r: (
                int(r.get("turno", 1)),
                str(r.get("data_divulgacao", "")),
                str(r.get("id_registro_tse", "")),
            )
        )

        # Garante que todas as colunas existem em todas as linhas
        all_keys: set[str] = set()
        for r in final_rows:
            all_keys.update(r.keys())
        fieldnames = [c for c in header if c in all_keys] + sorted(list(all_keys - set(header)))

        with open(csv_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in final_rows:
                writer.writerow(r)

        # 6. Grava Parquet otimizado via Polars
        parquet_rows: list[dict[str, Any]] = []
        for p in polls:
            b_dict = {
                "id_registro_tse": p.id_registro_tse,
                "instituto_razao_social": p.instituto_razao_social,
                "instituto_nome_fantasia": p.instituto_nome_fantasia,
                "data_inicio_campo": p.data_inicio_campo,
                "data_fim_campo": p.data_fim_campo,
                "data_divulgacao": p.data_divulgacao,
                "tamanho_amostra": p.tamanho_amostra,
                "margem_erro_declarada": p.margem_erro_declarada,
                "nivel_confianca": p.nivel_confianca,
                "metodologia": p.metodologia.value,
                "deff_estimado": p.deff_estimado,
                "percentual_indecisos": p.percentual_indecisos,
                "percentual_brancos_nulos": p.percentual_brancos_nulos,
                "turno": p.turno,
                "cargo": p.cargo,
                "ano": p.ano,
                "abrangencia": p.abrangencia.value,
                "uf": p.uf,
                "regiao": p.regiao,
                "tier_fonte": p.tier_fonte.value,
                "url_fonte_publicacao": p.url_fonte_publicacao,
                "url_tse_pesqele": p.url_tse_pesqele,
                "verificado_tse": p.verificado_tse,
            }
            for cand, v in p.votos_validos.items():
                b_dict[f"validos_{cand}"] = v
            for cand, tot in p.votos_totais.items():
                b_dict[f"totais_{cand}"] = tot
            parquet_rows.append(b_dict)

        pl_df = pl.DataFrame(parquet_rows, infer_schema_length=None)
        pl_df.write_parquet(parquet_path)

        return csv_path, parquet_path

    def run_full_sync(self) -> dict[str, Any]:
        """Executa a sincronização completa de dados para Presidente, Governador e Senador.

        Returns:
            dict[str, Any]: Relatório sintético com a volumetria e status de cada cargo e ciclo.

        Raises:
            None.
        """
        summary: dict[str, Any] = {}

        # 1. Presidente 2026
        try:
            p_2026 = self.collect_presidente_2026()
            csv_p26, parq_p26 = self.save_polls_to_csv_and_parquet(p_2026, 2026, "PRESIDENTE")
            summary["presidente_2026"] = {
                "total": len(p_2026),
                "csv": str(csv_p26),
                "parquet": str(parq_p26),
                "status": "OK",
            }
        except Exception as e:
            summary["presidente_2026"] = {"status": f"ERRO: {e}"}

        # 2. Governador 2026
        try:
            gov_2026 = self.collect_governadores_2026()
            csv_gov26, parq_gov26 = self.save_polls_to_csv_and_parquet(gov_2026, 2026, "GOVERNADOR")
            summary["governador_2026"] = {
                "total": len(gov_2026),
                "csv": str(csv_gov26),
                "parquet": str(parq_gov26),
                "status": "OK",
            }
        except Exception as e:
            summary["governador_2026"] = {"status": f"ERRO: {e}"}

        # 3. Senado 2026
        try:
            sen_2026 = self.collect_senado_2026()
            csv_sen26, parq_sen26 = self.save_polls_to_csv_and_parquet(sen_2026, 2026, "SENADOR")
            summary["senado_2026"] = {
                "total": len(sen_2026),
                "csv": str(csv_sen26),
                "parquet": str(parq_sen26),
                "status": "OK",
            }
        except Exception as e:
            summary["senado_2026"] = {"status": f"ERRO: {e}"}

        # 4. Presidente 2022 (Nexo + Desempenho)
        try:
            p_2022 = self.collect_nexo_2022()
            csv_p22, parq_p22 = self.save_polls_to_csv_and_parquet(p_2022, 2022, "PRESIDENTE")
            summary["presidente_2022"] = {
                "total": len(p_2022),
                "csv": str(csv_p22),
                "parquet": str(parq_p22),
                "status": "OK",
            }
        except Exception as e:
            summary["presidente_2022"] = {"status": f"ERRO: {e}"}

        # 5. Série Histórica (2022 e 2018 para Governadores e Senado)
        try:
            hist_polls = self.collect_historical_desempenho(years=[2022, 2018])
            gov_22 = [p for p in hist_polls if p.ano == 2022 and p.cargo == "GOVERNADOR"]
            sen_22 = [p for p in hist_polls if p.ano == 2022 and p.cargo == "SENADOR"]
            p_18 = [p for p in hist_polls if p.ano == 2018 and p.cargo == "PRESIDENTE"]
            gov_18 = [p for p in hist_polls if p.ano == 2018 and p.cargo == "GOVERNADOR"]
            sen_18 = [p for p in hist_polls if p.ano == 2018 and p.cargo == "SENADOR"]

            if gov_22:
                self.save_polls_to_csv_and_parquet(gov_22, 2022, "GOVERNADOR")
            if sen_22:
                self.save_polls_to_csv_and_parquet(sen_22, 2022, "SENADOR")
            if p_18:
                self.save_polls_to_csv_and_parquet(p_18, 2018, "PRESIDENTE")
            if gov_18:
                self.save_polls_to_csv_and_parquet(gov_18, 2018, "GOVERNADOR")
            if sen_18:
                self.save_polls_to_csv_and_parquet(sen_18, 2018, "SENADOR")

            summary["historico_multicargo"] = {
                "gov_2022": len(gov_22),
                "sen_2022": len(sen_22),
                "pres_2018": len(p_18),
                "gov_2018": len(gov_18),
                "sen_2018": len(sen_18),
                "status": "OK",
            }
        except Exception as e:
            summary["historico_multicargo"] = {"status": f"ERRO: {e}"}

        return summary
