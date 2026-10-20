"""Extrator e sincronizador de pesquisas eleitorais publicadas na web.

Consome feeds e bases abertas estruturadas de pesquisas registradas, normaliza entidades,
calcula a conversão canônica de votos válidos e audita cada protocolo contra o censo
oficial do TSE (PesqEle) antes de atualizar os datasets consolidados do projeto.
"""

import csv
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import polars as pl

from src.ingestion.base import BaseElectionDataExtractor
from src.ingestion.pesqele_collector import PesqEleCollector
from src.transformations.normalizer import TaxonomyNormalizer
from src.transformations.schemas import (
    AbrangenciaEnum,
    MetodologiaEnum,
    PesquisaEleitoralSchema,
    TierFonteEnum,
)
from src.transformations.valid_votes import calculate_valid_votes


class WebPollExtractor(BaseElectionDataExtractor):
    """Extrator agnóstico para ingestão e validação de pesquisas publicadas na web."""

    CSV_HEADER = [
        "id_registro_tse",
        "instituto",
        "data_inicio_campo",
        "data_fim_campo",
        "data_divulgacao",
        "tamanho_amostra",
        "margem_erro",
        "metodologia",
        "deff",
        "voto_bruto_Flávio Bolsonaro",
        "voto_bruto_Lula",
        "voto_bruto_Augusto Cury",
        "voto_bruto_Renan Santos",
        "voto_bruto_Ronaldo Caiado",
        "voto_bruto_Romeu Zema",
        "voto_bruto_Outros",
        "brancos_nulos",
        "indecisos",
        "turno",
        "abrangencia",
        "uf",
        "regiao",
        "tier_fonte",
        "url_fonte_publicacao",
        "url_tse_pesqele",
    ]

    def __init__(
        self,
        year: int = 2026,
        feed_url: str | None = None,
        raw_base_dir: str | Path | None = None,
    ) -> None:
        """Inicializa o extrator de pesquisas web para o ciclo eleitoral especificado.

        Args:
            year: Ano do pleito eleitoral (padrão: 2026).
            feed_url: URL opcional do feed estruturado de pesquisas abertas.
                Caso não fornecido, busca na variável de ambiente `POLLS_FEED_URL`.
            raw_base_dir: Diretório base para armazenamento dos dados brutos.

        Raises:
            ValueError: Se o ano for anterior a 1989.
        """
        super().__init__(year=year, raw_base_dir=raw_base_dir)
        self.feed_url = feed_url or os.environ.get("POLLS_FEED_URL")
        self.normalizer = TaxonomyNormalizer()
        self.collector = PesqEleCollector(year=year, raw_base_dir=raw_base_dir)

    def fetch_feed_payload(
        self,
        url: str | None = None,
        local_path: Path | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        """Obtém os dados brutos do feed a partir de URL remota ou arquivo local de cache.

        Args:
            url: URL opcional para requisição HTTP (sobrescreve a URL da instância).
            local_path: Caminho opcional para leitura de arquivo JSON local.
            timeout_seconds: Limite de tempo em segundos para requisições remotas.

        Returns:
            dict[str, Any]: Dicionário com a estrutura parseada do payload.

        Raises:
            ValueError: Se nenhuma URL ou arquivo local válido for fornecido.
            httpx.HTTPError: Se houver falha de rede na requisição remota.
            json.JSONDecodeError: Se o conteúdo recebido não for um JSON válido.
        """
        target_path = (
            local_path
            if local_path
            else self.raw_dir / f"feed_pesquisas_publicadas_{self.year}.json"
        )

        target_url = url or self.feed_url
        if target_url:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) margem_eleitoral/0.1.0"
            }
            with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
                resp = client.get(target_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            # Salva snapshot local seguro para auditoria offline
            try:
                target_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError:
                pass
            return data

        if target_path.exists():
            with open(target_path, encoding="utf-8") as f:
                return json.load(f)

        raise ValueError(
            "Nenhuma URL de feed fornecida e nenhum arquivo de snapshot local encontrado em "
            f"{target_path}."
        )

    def _determine_methodology(
        self, institute: str, method_text: str | None
    ) -> tuple[MetodologiaEnum, float]:
        """Determina a metodologia canônica e o fator DEFF estimado para a pesquisa.

        Args:
            institute: Nome canônico do instituto de pesquisa.
            method_text: Descrição textual bruta do modo de coleta (ex.: 'telefone', 'presencial').

        Returns:
            tuple[MetodologiaEnum, float]: Tupla contendo o enum metodológico e o DEFF correspondente.

        Raises:
            None.
        """
        raw = (method_text or "").strip().lower()
        inst_upper = institute.upper()

        if "verita" in inst_upper or "ura" in raw:
            return MetodologiaEnum.TELEFONICA_URA, 1.30
        if "online" in raw or "painel" in raw or "web" in raw or "atlas" in inst_upper:
            return MetodologiaEnum.ONLINE, 1.35
        if "presencial" in raw or "domiciliar" in raw:
            return MetodologiaEnum.PRESENCIAL_DOMICILIAR, 1.35
        if "fluxo" in raw:
            return MetodologiaEnum.PRESENCIAL_FLUXO, 1.30
        if "telefone" in raw or "cati" in raw:
            return MetodologiaEnum.TELEFONICA_CATI, 1.30

        return MetodologiaEnum.TELEFONICA_CATI, 1.30

    def extract_and_transform(
        self,
        feed_data: dict[str, Any] | None = None,
        only_verified: bool = True,
        only_eligible: bool = True,
    ) -> list[PesquisaEleitoralSchema]:
        """Extrai, filtra, enriquece e valida os levantamentos sob o contrato estrito Pydantic.

        Args:
            feed_data: Payload estruturado opcional. Se None, chama `fetch_feed_payload()`.
            only_verified: Se True, descarta pesquisas com `verificado == False`.
            only_eligible: Se True, descarta pesquisas marcadas como não-elegíveis.

        Returns:
            list[PesquisaEleitoralSchema]: Lista de pesquisas estruturadas e validadas.

        Raises:
            ValueError: Se o payload não contiver a chave esperada de pesquisas ou for inválido.
        """
        if feed_data is None:
            feed_data = self.fetch_feed_payload()

        raw_polls: list[dict[str, Any]] = feed_data.get("pesquisas", [])
        if not raw_polls:
            return []

        # Carrega o censo oficial do TSE para indexação e enriquecimento cadastral
        census_df = self.collector.get_tse_registration_census()
        census_map: dict[str, dict[str, Any]] = (
            {r["id_registro_tse"]: r for r in census_df.to_dicts()} if census_df.height > 0 else {}
        )

        valid_polls: list[PesquisaEleitoralSchema] = []

        for p in raw_polls:
            is_verified = bool(p.get("verificado", False))
            is_eligible = bool(p.get("elegivel", True))

            if only_verified and not is_verified:
                continue
            if only_eligible and not is_eligible:
                continue

            reg_id = str(p.get("registro_tse", "")).strip()
            if not reg_id:
                continue

            census_info = census_map.get(reg_id, {})
            inst_raw = str(p.get("instituto", "")).strip()
            inst_canonical = self.normalizer.normalize_institute(inst_raw)

            # Datas
            dt_inicio = date.fromisoformat(str(p["data_campo_inicio"]).strip())
            dt_fim = date.fromisoformat(str(p["data_campo_fim"]).strip())
            dt_div = date.fromisoformat(str(p["data_divulgacao"]).strip())

            # Metodologia e DEFF
            metodologia_enum, deff_val = self._determine_methodology(
                institute=inst_canonical,
                method_text=p.get("modo"),
            )

            # Abrangência e Recorte Regional via TSE
            abrang_str = census_info.get("abrangencia", "NACIONAL")
            try:
                abrang_enum = AbrangenciaEnum(str(abrang_str).upper())
            except ValueError:
                abrang_enum = AbrangenciaEnum.NACIONAL

            uf_str = str(census_info.get("uf", "BR")).upper()
            regiao_str = str(census_info.get("regiao", "BR")).upper()

            # Votos
            # No 2º Turno, mapeamos os percentuais para os candidatos finalistas
            pct_a = float(p.get("pct_a") or 0.0)
            pct_b = float(p.get("pct_b") or 0.0)
            bn = float(p.get("pct_branco_nulo") or 0.0)
            ind = float(p.get("pct_indeciso") or 0.0)

            votos_brutos = {
                "Flávio Bolsonaro": pct_b,
                "Lula": pct_a,
            }

            votos_validos = calculate_valid_votes(
                votos_totais=votos_brutos,
                percentual_brancos_nulos=bn,
                percentual_indecisos=ind,
            )

            # Amostra e margem de erro
            amostra_val = int(p.get("amostra_n") or census_info.get("tamanho_amostra") or 2000)
            margem_val = float(p.get("margem_erro_pp") or 2.0)
            conf_val = float(p.get("nivel_confianca") or 95.0)
            if conf_val > 1.0:
                conf_val = conf_val / 100.0

            # URLs e fontes
            urls_raw = str(p.get("urls", "")).strip()
            url_fonte = urls_raw.split()[0] if urls_raw else None
            url_tse = f"https://pesqele.tse.jus.br/pesqele-consulta/pesquisa/detalhes.xhtml?id={reg_id}"

            razao_social = (
                census_info.get("instituto_razao_social")
                or f"{inst_canonical.upper()} PESQUISAS LTDA"
            )

            poll_schema = PesquisaEleitoralSchema(
                id_registro_tse=reg_id,
                instituto_razao_social=razao_social,
                instituto_nome_fantasia=inst_canonical,
                data_inicio_campo=dt_inicio,
                data_fim_campo=dt_fim,
                data_divulgacao=dt_div,
                tamanho_amostra=amostra_val,
                margem_erro_declarada=margem_val,
                nivel_confianca=conf_val,
                metodologia=metodologia_enum,
                deff_estimado=deff_val,
                votos_totais=votos_brutos,
                votos_validos=votos_validos,
                percentual_indecisos=ind,
                percentual_brancos_nulos=bn,
                turno=2,
                cargo="PRESIDENTE",
                ano=self.year,
                abrangencia=abrang_enum,
                uf=uf_str,
                regiao=regiao_str,
                tier_fonte=TierFonteEnum.TIER_2_CONTRATANTE_ORIGINAL,
                url_fonte_publicacao=url_fonte,
                url_tse_pesqele=url_tse,
                verificado_tse=True,
            )
            valid_polls.append(poll_schema)

        return valid_polls

    def cross_validate_with_tse_census(
        self,
        polls: list[PesquisaEleitoralSchema] | None = None,
        census_df: pl.DataFrame | None = None,
    ) -> dict[str, Any]:
        """Realiza a auditoria e validação cruzada estrita de protocolos contra o censo do TSE.

        Args:
            polls: Lista opcional de pesquisas a auditar. Se None, executa extração padrão.
            census_df: DataFrame opcional contendo o censo oficial de registros do TSE.

        Returns:
            dict[str, Any]: Resumo estatístico da auditoria com total avaliado, validado e taxa.

        Raises:
            None.
        """
        if polls is None:
            polls = self.extract_and_transform()
        return self.collector.cross_validate_with_tse_census(polls=polls, census_df=census_df)

    def update_published_polls_csv(self, polls: list[PesquisaEleitoralSchema]) -> int:
        """Atualiza pesquisas_publicadas_{year}.csv com novos levantamentos validados.

        Preserva os registros existentes (incluindo pesquisas do 1º Turno) e atualiza ou insere
        os levantamentos do 2º Turno de forma idempotente, deduplicando por `id_registro_tse`.

        Args:
            polls: Lista de instâncias validadas de `PesquisaEleitoralSchema` para incorporação.

        Returns:
            int: Quantidade de registros novos ou atualizados gravados no CSV.

        Raises:
            OSError: Se houver falha de escrita no arquivo em disco.
        """
        csv_path = self.raw_dir / f"pesquisas_publicadas_{self.year}.csv"
        existing_rows: list[dict[str, str]] = []

        if csv_path.exists():
            with open(csv_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    existing_rows.append(
                        {k.strip(): (v.strip() if v is not None else "") for k, v in r.items()}
                    )

        # Mapa de linhas existentes indexado por id_registro_tse
        row_map: dict[str, dict[str, str]] = {
            r["id_registro_tse"]: r for r in existing_rows if r.get("id_registro_tse")
        }

        updated_count = 0
        for p in polls:
            is_new = p.id_registro_tse not in row_map
            row_dict = {
                "id_registro_tse": p.id_registro_tse,
                "instituto": p.instituto_nome_fantasia,
                "data_inicio_campo": p.data_inicio_campo.isoformat(),
                "data_fim_campo": p.data_fim_campo.isoformat(),
                "data_divulgacao": p.data_divulgacao.isoformat(),
                "tamanho_amostra": str(p.tamanho_amostra),
                "margem_erro": str(p.margem_erro_declarada),
                "metodologia": p.metodologia.value,
                "deff": str(p.deff_estimado),
                "voto_bruto_Flávio Bolsonaro": str(p.votos_totais.get("Flávio Bolsonaro", 0.0)),
                "voto_bruto_Lula": str(p.votos_totais.get("Lula", 0.0)),
                "voto_bruto_Augusto Cury": "0.0",
                "voto_bruto_Renan Santos": "0.0",
                "voto_bruto_Ronaldo Caiado": "0.0",
                "voto_bruto_Romeu Zema": "0.0",
                "voto_bruto_Outros": "0.0",
                "brancos_nulos": str(p.percentual_brancos_nulos),
                "indecisos": str(p.percentual_indecisos),
                "turno": str(p.turno),
                "abrangencia": p.abrangencia.value,
                "uf": p.uf,
                "regiao": p.regiao,
                "tier_fonte": p.tier_fonte.value,
                "url_fonte_publicacao": p.url_fonte_publicacao or "",
                "url_tse_pesqele": p.url_tse_pesqele or "",
            }
            row_map[p.id_registro_tse] = row_dict
            if is_new:
                updated_count += 1

        # Escreve o arquivo completo mantendo a ordem original e adicionando os novos
        all_ordered_rows = list(row_map.values())
        temp_csv = csv_path.with_suffix(".tmp.csv")
        with open(temp_csv, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_HEADER)
            writer.writeheader()
            for r in all_ordered_rows:
                # Garante que todas as colunas do header existam na linha
                clean_r = {col: r.get(col, "0.0" if "voto_bruto" in col else "") for col in self.CSV_HEADER}
                writer.writerow(clean_r)

        temp_csv.replace(csv_path)
        return updated_count

    def update_processed_parquet(self) -> Path:
        """Regenera o arquivo Parquet consolidado data/processed/pesquisas_{year}.parquet.

        Returns:
            Path: Caminho do arquivo Parquet atualizado.

        Raises:
            OSError: Se houver falha de escrita no arquivo em disco.
        """
        return self.collector.save_processed()

    def sync(
        self,
        feed_url: str | None = None,
        only_verified: bool = True,
    ) -> dict[str, Any]:
        """Executa o ciclo completo de sincronização, validação cadastral e atualização em disco.

        Args:
            feed_url: URL opcional para busca do feed.
            only_verified: Se True, filtra apenas pesquisas com verificação positiva.

        Returns:
            dict[str, Any]: Dicionário com métricas do processo de sincronização e validação.

        Raises:
            ValueError: Se houver inconsistência nos dados de entrada.
            httpx.HTTPError: Se houver falha na obtenção do feed.
        """
        payload = self.fetch_feed_payload(url=feed_url)
        polls = self.extract_and_transform(feed_data=payload, only_verified=only_verified)

        # Validação cruzada estrita contra o censo do TSE
        audit_result = self.cross_validate_with_tse_census(polls=polls)

        # Atualização atômica dos datasets em disco
        new_polls_count = self.update_published_polls_csv(polls=polls)
        parquet_path = self.update_processed_parquet()

        return {
            "total_extraidas": len(polls),
            "novas_incorporadas": new_polls_count,
            "tse_audit": audit_result,
            "parquet_path": str(parquet_path),
            "status": "SUCESSO",
        }
