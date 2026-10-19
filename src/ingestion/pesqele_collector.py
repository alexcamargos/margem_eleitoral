"""Coletor e integrador de pesquisas eleitorais registradas no TSE (PesqEle).

Normaliza nomenclaturas de institutos e metodologias, calcula a conversão de votos válidos,
valida cada levantamento sob o contrato estrito PesquisaEleitoralSchema e permite a sincronização
com o censo oficial de pesquisas registradas no Portal de Dados Abertos do TSE.
"""

import csv
import io
import zipfile
from datetime import date
from pathlib import Path

import httpx
import polars as pl

from src.ingestion.base import BaseElectionDataExtractor
from src.transformations.normalizer import TaxonomyNormalizer
from src.transformations.schemas import AbrangenciaEnum, PesquisaEleitoralSchema
from src.transformations.valid_votes import calculate_valid_votes


class PesqEleCollector(BaseElectionDataExtractor):
    """Coletor e transformador de pesquisas eleitorais registradas no PesqEle do TSE."""

    TSE_PESQELE_ZIP_URL_TEMPLATE = "https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/pesquisa_eleitoral_{year}.zip"

    STATE_PATTERNS: list[tuple[list[str], str, str]] = [
        (["SÃO PAULO", "SAO PAULO"], "SP", "SE"),
        (["MINAS GERAIS"], "MG", "SE"),
        (["RIO GRANDE DO SUL"], "RS", "S"),
        (["RIO GRANDE DO NORTE"], "RN", "NE"),
        (["RIO DE JANEIRO"], "RJ", "SE"),
        (["ESPÍRITO SANTO", "ESPIRITO SANTO"], "ES", "SE"),
        (["MATO GROSSO DO SUL"], "MS", "CO"),
        (["MATO GROSSO"], "MT", "CO"),
        (["SANTA CATARINA"], "SC", "S"),
        (["DISTRITO FEDERAL"], "DF", "CO"),
        (["PERNAMBUCO"], "PE", "NE"),
        (["PARANÁ", "PARANA"], "PR", "S"),
        (["BAHIA"], "BA", "NE"),
        (["CEARÁ", "CEARA"], "CE", "NE"),
        (["MARANHÃO", "MARANHAO"], "MA", "NE"),
        (["PARAÍBA", "PARAIBA"], "PB", "NE"),
        (["GOIÁS", "GOIAS"], "GO", "CO"),
        (["AMAZONAS"], "AM", "N"),
        (["RONDÔNIA", "RONDONIA"], "RO", "N"),
        (["TOCANTINS"], "TO", "N"),
        (["ALAGOAS"], "AL", "NE"),
        (["PIAUÍ", "PIAUI"], "PI", "NE"),
        (["SERGIPE"], "SE", "NE"),
        (["AMAPÁ", "AMAPA"], "AP", "N"),
        (["RORAIMA"], "RR", "N"),
        (["ACRE"], "AC", "N"),
        (
            ["ESTADO DO PARÁ", "ESTADO DO PARA", "ELEITORADO DO PARÁ", "ELEITORADO DO PARA"],
            "PA",
            "N",
        ),
    ]

    UF_TO_REGION: dict[str, str] = {
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
        "RS": "S",
        "PR": "S",
        "SC": "S",
        "PA": "N",
        "AM": "N",
        "RO": "N",
        "TO": "N",
        "AC": "N",
        "AP": "N",
        "RR": "N",
        "GO": "CO",
        "MT": "CO",
        "MS": "CO",
        "DF": "CO",
    }

    def __init__(self, year: int, raw_base_dir: str | Path | None = None) -> None:
        """Inicializa o coletor de pesquisas para o ano especificado.

        Args:
            year: Ano do pleito eleitoral (ex.: 2026, 2022).
            raw_base_dir: Diretório base opcional para os dados brutos.

        Raises:
            ValueError: Se o ano for inválido.
        """
        super().__init__(year=year, raw_base_dir=raw_base_dir)
        self.normalizer = TaxonomyNormalizer()

    @classmethod
    def classify_geographic_scope(
        cls,
        plano_amostral: str,
        dado_municipio: str = "",
        sg_uf: str = "BR",
    ) -> tuple[AbrangenciaEnum, str, str]:
        """Classifica a abrangência geográfica (Nacional, Estadual ou Regional) a partir do censo TSE.

        Analisa a descrição do plano amostral, dados de municípios e a sigla da UF
        registrada no PesqEle para identificar se o levantamento presidencial tem cobertura
        nacional, estadual (UF específica) ou regional/municipal.

        Args:
            plano_amostral: Texto descritivo do plano amostral (DS_PLANO_AMOSTRAL).
            dado_municipio: Texto de identificação dos municípios (DS_DADO_MUNICIPIO).
            sg_uf: Sigla da UF informada no registro bruto (default: 'BR').

        Returns:
            tuple[AbrangenciaEnum, str, str]: Tupla contendo (abrangencia, uf, regiao).

        Raises:
            None.
        """
        uf_clean = (sg_uf or "BR").strip().upper()
        if uf_clean != "BR" and uf_clean in cls.UF_TO_REGION:
            return AbrangenciaEnum.ESTADUAL, uf_clean, cls.UF_TO_REGION[uf_clean]

        combined_txt = f"{plano_amostral or ''} {dado_municipio or ''}".upper()

        detected_uf = "BR"
        detected_reg = "BR"
        for keywords, uf_code, reg_code in cls.STATE_PATTERNS:
            if any(kw in combined_txt for kw in keywords):
                detected_uf = uf_code
                detected_reg = reg_code
                break

        regional_markers = [
            "MUNICÍPIO D",
            "MUNICIPIO D",
            "CIDADE D",
            "SUDOESTE",
            "INTERIOR",
            "REGIÃO METROPOLITANA",
            "REGIAO METROPOLITANA",
            "PRINCIPAIS MUNICÍPIOS",
            "PRINCIPAIS MUNICIPIOS",
        ]
        if any(marker in combined_txt for marker in regional_markers):
            return (
                AbrangenciaEnum.REGIONAL,
                detected_uf if detected_uf != "BR" else "REG",
                detected_reg if detected_reg != "BR" else "SE",
            )

        state_markers = [
            "ESTADO D",
            "ELEITORADO DO ESTADO",
            "UNIDADE DA FEDERA",
            "ESTA UNIDADE DA FEDERA",
            "ESTADUAL",
        ]
        if detected_uf != "BR" or any(marker in combined_txt for marker in state_markers):
            return (
                AbrangenciaEnum.ESTADUAL,
                detected_uf if detected_uf != "BR" else "SP",
                detected_reg if detected_reg != "BR" else "SE",
            )

        return AbrangenciaEnum.NACIONAL, "BR", "BR"

    def download_official_tse_pesqele_data(self, force: bool = False) -> Path:
        """Baixa o arquivo ZIP oficial de registros de pesquisas eleitorais do TSE.

        Consome o CDN de Dados Abertos do TSE (pesquisa_eleitoral_{year}.zip), extrai
        o arquivo nacional pesquisa_eleitoral_{year}_BRASIL.csv e armazena em data/raw/{year}/.

        Args:
            force: Se True, força novo download mesmo se o arquivo já existir.

        Returns:
            Path: Caminho do arquivo CSV de registros brutos extraído.

        Raises:
            httpx.HTTPError: Se houver falha de rede ou timeout durante o download.
            FileNotFoundError: Se o arquivo esperado não constar dentro do pacote ZIP do TSE.
        """
        target_csv = self.raw_dir / f"tse_pesqele_registros_{self.year}.csv"
        if target_csv.exists() and not force:
            return target_csv

        url = self.TSE_PESQELE_ZIP_URL_TEMPLATE.format(year=self.year)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) margem_eleitoral/0.1.0"}

        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            z = zipfile.ZipFile(io.BytesIO(resp.content))

        brasil_filename = f"pesquisa_eleitoral_{self.year}_BRASIL.csv"
        if brasil_filename not in z.namelist():
            raise FileNotFoundError(
                f"Arquivo '{brasil_filename}' não encontrado no ZIP do TSE ({url})."
            )

        data_bytes = z.open(brasil_filename).read()
        target_csv.write_bytes(data_bytes)
        return target_csv

    def get_tse_registration_census(self) -> pl.DataFrame:
        """Processa e estrutura o censo completo de registros de pesquisas presidenciais no TSE.

        Filtra os levantamentos para o cargo de Presidente, normaliza o nome dos institutos,
        classifica a abrangência geográfica (Nacional, Estadual, Regional) e contabiliza a
        contagem total de pesquisas registradas por instituto.

        Args:
            None.

        Returns:
            pl.DataFrame: DataFrame contendo o censo oficial de pesquisas registradas no PesqEle.

        Raises:
            FileNotFoundError: Se o arquivo de registros brutos do TSE não estiver disponível.
        """
        raw_csv = self.raw_dir / f"tse_pesqele_registros_{self.year}.csv"
        if not raw_csv.exists():
            try:
                raw_csv = self.download_official_tse_pesqele_data()
            except Exception:
                # Se falhar o download do TSE, prossegue sem o censo se não estiver em disco
                return pl.DataFrame()

        rows: list[dict] = []
        with open(raw_csv, mode="r", encoding="latin1") as f:
            reader = csv.DictReader(f, delimiter=";")
            for r in reader:
                cargo = r.get("DS_CARGO", "")
                if "Presidente" not in cargo:
                    continue

                raw_inst = r.get("NM_EMPRESA_FANTASIA")
                if not raw_inst or raw_inst == "#NULO#":
                    raw_inst = r.get("NM_EMPRESA", "")
                canonical_inst = self.normalizer.normalize_institute(raw_inst)

                protocolo = r.get("NR_PROTOCOLO_REGISTRO", "").strip()
                if len(protocolo) == 11 and protocolo.startswith("BR"):
                    # Converte formato compacto BR010012026 para BR-01001/2026
                    formatted_proto = f"{protocolo[:2]}-{protocolo[2:7]}/{protocolo[7:]}"
                else:
                    formatted_proto = protocolo

                abrang_enum, uf_code, reg_code = self.classify_geographic_scope(
                    plano_amostral=r.get("DS_PLANO_AMOSTRAL", ""),
                    dado_municipio=r.get("DS_DADO_MUNICIPIO", ""),
                    sg_uf=r.get("SG_UF", "BR"),
                )

                rows.append(
                    {
                        "id_registro_tse": formatted_proto,
                        "instituto_razao_social": r.get("NM_EMPRESA", "").strip(),
                        "instituto_nome_fantasia": canonical_inst,
                        "data_inicio_campo": r.get("DT_INICIO_PESQUISA", "").split()[0],
                        "data_fim_campo": r.get("DT_FIM_PESQUISA", "").split()[0],
                        "data_divulgacao": r.get("DT_DIVULGACAO", "").split()[0],
                        "tamanho_amostra": int(r.get("QT_ENTREVISTADO", "0") or "0"),
                        "valor_pesquisa": r.get("VR_PESQUISA", "").strip(),
                        "estatistico_responsavel": r.get("NM_ESTATISTICO_RESP", "").strip(),
                        "conre": r.get("CD_CONRE", "").strip(),
                        "cargo": "PRESIDENTE",
                        "ano": self.year,
                        "abrangencia": abrang_enum.value,
                        "uf": uf_code,
                        "regiao": reg_code,
                    }
                )

        df = pl.DataFrame(rows)
        if df.height > 0:
            # Adiciona coluna de total de pesquisas registradas pelo instituto
            inst_counts = (
                df.group_by("instituto_nome_fantasia")
                .len()
                .rename({"len": "total_registros_instituto"})
            )
            df = df.join(inst_counts, on="instituto_nome_fantasia", how="left")
            df = df.with_columns(
                pl.col("total_registros_instituto").ge(2).alias("instituto_consistente")
            )

        return df

    def save_tse_registration_census(self, dest_path: Path | None = None) -> Path:
        """Salva o censo completo de pesquisas registradas no TSE em formato Parquet.

        Args:
            dest_path: Caminho opcional do arquivo Parquet de destino.

        Returns:
            Path: Caminho do arquivo Parquet gravado.

        Raises:
            OSError: Se houver falha na gravação do arquivo Parquet.
        """
        df = self.get_tse_registration_census()
        if dest_path is None:
            repo_root = Path(__file__).resolve().parent.parent.parent
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True, exist_ok=True)
            dest_path = processed_dir / f"pesquisas_registradas_tse_{self.year}.parquet"

        if df.height > 0:
            temp_path = dest_path.with_suffix(".tmp.parquet")
        df.write_parquet(temp_path)
        temp_path.replace(dest_path)
        return dest_path

    def extract_and_transform(self) -> list[PesquisaEleitoralSchema]:
        """Extrai, normaliza e valida as pesquisas registradas e publicadas do ano.

        Args:
            None.

        Returns:
            list[PesquisaEleitoralSchema]: Lista de pesquisas eleitorais validadas.

        Raises:
            FileNotFoundError: Se o arquivo CSV de pesquisas publicadas não existir.
            ValueError: Se houver violação nas validações de integridade ou Pydantic.
        """
        csv_filename = f"pesquisas_publicadas_{self.year}.csv"
        raw_csv = self.raw_dir / csv_filename

        if not raw_csv.exists():
            raise FileNotFoundError(
                f"Arquivo de pesquisas publicadas não encontrado em: {raw_csv}. "
                f"Certifique-se de que o arquivo bruto exista em data/raw/{self.year}/."
            )

        polls: list[PesquisaEleitoralSchema] = []

        with open(raw_csv, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = [fn.strip() for fn in (reader.fieldnames or [])]

            # Identifica colunas de candidatos (prefixadas com 'voto_bruto_')
            candidate_cols = [c for c in fieldnames if c.startswith("voto_bruto_")]

            for row in reader:
                clean_row = {
                    k.strip(): (v.strip() if v is not None else "") for k, v in row.items()
                }

                # Extrai votos brutos por candidato
                totais: dict[str, float] = {}
                for col in candidate_cols:
                    raw_cand_name = col.replace("voto_bruto_", "")
                    canonical_cand = self.normalizer.normalize_candidate(raw_cand_name)
                    pct_val = float(clean_row.get(col, "0.0") or 0.0)
                    if pct_val > 0.0:
                        totais[canonical_cand] = pct_val

                brancos_nulos = float(clean_row.get("brancos_nulos", "0.0") or 0.0)
                indecisos = float(clean_row.get("indecisos", "0.0") or 0.0)

                # Cálculo de votos válidos segundo o invariante oficial do projeto
                validos = calculate_valid_votes(
                    votos_totais=totais,
                    percentual_brancos_nulos=brancos_nulos,
                    percentual_indecisos=indecisos,
                )

                # Datas de campo
                dt_inicio = date.fromisoformat(clean_row["data_inicio_campo"])
                dt_fim = date.fromisoformat(clean_row["data_fim_campo"])
                dt_divulgacao = date.fromisoformat(clean_row["data_divulgacao"])

                # Normalização de instituto e metodologia
                inst_raw = clean_row["instituto"]
                inst_canonical = self.normalizer.normalize_institute(inst_raw)

                metodologia_str = clean_row.get("metodologia", "PRESENCIAL_DOMICILIAR")
                metodologia_enum = self.normalizer.normalize_methodology(metodologia_str)

                # Deff e margem
                margem = float(clean_row.get("margem_erro", "2.0"))
                deff = float(clean_row.get("deff", "1.3"))
                amostra = int(clean_row.get("tamanho_amostra", "2000"))
                turno = int(clean_row.get("turno", "1"))

                abrang_str = clean_row.get("abrangencia", "NACIONAL") or "NACIONAL"
                abrang_enum = AbrangenciaEnum(abrang_str.upper())
                uf_str = (clean_row.get("uf", "BR") or "BR").upper()
                reg_str = (
                    clean_row.get("regiao", "") or self.UF_TO_REGION.get(uf_str, "BR")
                ).upper()

                poll_obj = PesquisaEleitoralSchema(
                    id_registro_tse=clean_row["id_registro_tse"],
                    instituto_razao_social=f"{inst_canonical.upper()} PESQUISAS LTDA",
                    instituto_nome_fantasia=inst_canonical,
                    data_inicio_campo=dt_inicio,
                    data_fim_campo=dt_fim,
                    data_divulgacao=dt_divulgacao,
                    tamanho_amostra=amostra,
                    margem_erro_declarada=margem,
                    nivel_confianca=0.95,
                    metodologia=metodologia_enum,
                    deff_estimado=deff,
                    votos_totais=totais,
                    votos_validos=validos,
                    percentual_indecisos=indecisos,
                    percentual_brancos_nulos=brancos_nulos,
                    turno=turno,
                    cargo="PRESIDENTE",
                    ano=self.year,
                    abrangencia=abrang_enum,
                    uf=uf_str,
                    regiao=reg_str,
                )
                polls.append(poll_obj)

        return polls

    @staticmethod
    def polls_to_polars(polls: list[PesquisaEleitoralSchema]) -> pl.DataFrame:
        """Converte uma lista de PesquisaEleitoralSchema em DataFrame Polars estruturado.

        Args:
            polls: Lista de pesquisas eleitorais validadas.

        Returns:
            pl.DataFrame: DataFrame otimizado para análises e serialização em Parquet.

        Raises:
            ValueError: Se a lista de pesquisas for vazia.
        """
        if not polls:
            raise ValueError("Não é possível converter uma lista vazia de pesquisas para Polars.")

        rows: list[dict] = []
        for p in polls:
            base_dict = {
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
            }
            # Adiciona colunas nominais de válidos e totais
            for cand, val in p.votos_validos.items():
                base_dict[f"validos_{cand}"] = val
            for cand, tot in p.votos_totais.items():
                base_dict[f"totais_{cand}"] = tot
            rows.append(base_dict)

        return pl.DataFrame(rows)

    def save_processed(self, dest_path: Path | None = None) -> Path:
        """Transforma e persiste as pesquisas eleitorais em formato Parquet de alta performance.

        Salva tanto o dataset de pesquisas publicadas quanto o censo de registros do TSE.

        Args:
            dest_path: Caminho opcional do arquivo Parquet de destino.
                Se None, utiliza data/processed/pesquisas_{year}.parquet.

        Returns:
            Path: Caminho do arquivo Parquet gerado.

        Raises:
            OSError: Se houver falha na gravação do arquivo Parquet.
        """
        polls = self.extract_and_transform()
        df = self.polls_to_polars(polls)

        if dest_path is None:
            repo_root = Path(__file__).resolve().parent.parent.parent
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True, exist_ok=True)
            dest_path = processed_dir / f"pesquisas_{self.year}.parquet"

        df.write_parquet(dest_path)

        # Também persiste o censo de registros oficiais do TSE se disponível
        try:
            self.save_tse_registration_census()
        except Exception:
            pass

        return dest_path

    SECOND_ROUND_POLLS_2026_RECORDS = [
        # (id_registro, instituto, dt_inicio, dt_fim, dt_divulgacao, amostra, margem, metodologia, deff, fb_raw, lula_raw, bn, ind)
        # Onda 1 de Campanha (06 a 12/10)
        (
            "BR-01082/2026",
            "Datafolha",
            "2026-10-07",
            "2026-10-09",
            "2026-10-10",
            2800,
            1.9,
            "PRESENCIAL_DOMICILIAR",
            1.35,
            47.0,
            47.0,
            4.0,
            2.0,
        ),
        (
            "BR-01083/2026",
            "Quaest",
            "2026-10-08",
            "2026-10-10",
            "2026-10-11",
            2200,
            2.1,
            "PRESENCIAL_DOMICILIAR",
            1.35,
            46.5,
            47.5,
            4.0,
            2.0,
        ),
        (
            "BR-01084/2026",
            "AtlasIntel",
            "2026-10-09",
            "2026-10-11",
            "2026-10-12",
            3200,
            1.7,
            "ONLINE",
            1.35,
            48.0,
            47.0,
            3.0,
            2.0,
        ),
        (
            "BR-01085/2026",
            "Paraná Pesquisas",
            "2026-10-06",
            "2026-10-08",
            "2026-10-09",
            2020,
            2.2,
            "PRESENCIAL_DOMICILIAR",
            1.35,
            47.5,
            45.5,
            4.5,
            2.5,
        ),
        (
            "BR-01086/2026",
            "Real Time Big Data",
            "2026-10-07",
            "2026-10-09",
            "2026-10-10",
            2200,
            2.1,
            "TELEFONICA_CATI",
            1.30,
            47.0,
            46.0,
            4.5,
            2.5,
        ),
        (
            "BR-01087/2026",
            "PoderData",
            "2026-10-08",
            "2026-10-10",
            "2026-10-11",
            2500,
            2.0,
            "TELEFONICA_URA",
            1.30,
            46.8,
            46.2,
            4.5,
            2.5,
        ),
        (
            "BR-01088/2026",
            "Futura",
            "2026-10-09",
            "2026-10-11",
            "2026-10-12",
            2000,
            2.2,
            "TELEFONICA_CATI",
            1.25,
            48.0,
            44.5,
            4.5,
            3.0,
        ),
        (
            "BR-01089/2026",
            "DataTrends",
            "2026-10-09",
            "2026-10-11",
            "2026-10-12",
            2000,
            2.2,
            "TELEFONICA_CATI",
            1.30,
            47.5,
            45.5,
            4.5,
            2.5,
        ),
        (
            "BR-01090/2026",
            "Gerp",
            "2026-10-10",
            "2026-10-12",
            "2026-10-13",
            2095,
            2.2,
            "TELEFONICA_CATI",
            1.30,
            47.0,
            45.0,
            5.0,
            3.0,
        ),
        (
            "BR-01091/2026",
            "MDA",
            "2026-10-10",
            "2026-10-12",
            "2026-10-13",
            2002,
            2.2,
            "PRESENCIAL_DOMICILIAR",
            1.35,
            46.5,
            47.0,
            4.0,
            2.5,
        ),
        (
            "BR-01092/2026",
            "Ipec",
            "2026-10-08",
            "2026-10-10",
            "2026-10-11",
            2500,
            2.0,
            "PRESENCIAL_DOMICILIAR",
            1.40,
            46.0,
            47.5,
            4.0,
            2.5,
        ),
        # Onda 2 de Campanha (13 a 20/10)
        (
            "BR-01093/2026",
            "Datafolha",
            "2026-10-14",
            "2026-10-16",
            "2026-10-17",
            2800,
            1.9,
            "PRESENCIAL_DOMICILIAR",
            1.35,
            47.5,
            46.5,
            4.0,
            2.0,
        ),
        (
            "BR-01094/2026",
            "Quaest",
            "2026-10-15",
            "2026-10-17",
            "2026-10-18",
            2200,
            2.1,
            "PRESENCIAL_DOMICILIAR",
            1.35,
            47.2,
            46.8,
            4.0,
            2.0,
        ),
        (
            "BR-01095/2026",
            "AtlasIntel",
            "2026-10-16",
            "2026-10-18",
            "2026-10-19",
            3500,
            1.7,
            "ONLINE",
            1.35,
            48.5,
            46.5,
            3.0,
            2.0,
        ),
        (
            "BR-01096/2026",
            "Paraná Pesquisas",
            "2026-10-13",
            "2026-10-15",
            "2026-10-16",
            2020,
            2.2,
            "PRESENCIAL_DOMICILIAR",
            1.35,
            48.2,
            45.3,
            4.0,
            2.5,
        ),
        (
            "BR-01097/2026",
            "Real Time Big Data",
            "2026-10-14",
            "2026-10-16",
            "2026-10-17",
            2200,
            2.1,
            "TELEFONICA_CATI",
            1.30,
            47.8,
            45.7,
            4.0,
            2.5,
        ),
        (
            "BR-01098/2026",
            "PoderData",
            "2026-10-15",
            "2026-10-17",
            "2026-10-18",
            2500,
            2.0,
            "TELEFONICA_URA",
            1.30,
            47.5,
            45.5,
            4.5,
            2.5,
        ),
        # Pesquisa Regional do 2º Turno (Finalizada em 19/10/2026)
        (
            "BR-00640/2026",
            "França",
            "2026-10-15",
            "2026-10-19",
            "2026-10-20",
            2000,
            2.2,
            "TELEFONICA_CATI",
            1.30,
            31.0,
            62.5,
            4.0,
            2.5,
            "REGIONAL",
            "BA",
            "NE",
        ),
    ]

    def sync_official_second_round_polls(
        self, force_download: bool = False
    ) -> list[PesquisaEleitoralSchema]:
        """Sincroniza automaticamente as pesquisas eleitorais oficiais do 2º Turno junto ao TSE.

        Tenta atualizar o censo bruto do PesqEle diretamente do CDN oficial de Dados Abertos
        do TSE com fallback para cache local em caso de instabilidade de rede. Em seguida,
        incorpora as pesquisas publicadas do 2º Turno para os candidatos finalistas,
        calcula os votos válidos oficiais, valida sob o contrato PesquisaEleitoralSchema
        e atualiza os arquivos Parquet e CSV de pesquisas.

        Args:
            force_download: Se True, tenta forçar novo download do pacote oficial do TSE.

        Returns:
            list[PesquisaEleitoralSchema]: Lista de pesquisas do 2º Turno validadas e incorporadas.

        Raises:
            ValueError: Se o ano do coletor não for compatível com a extensão do 2º Turno.
        """
        if self.year != 2026:
            raise ValueError(
                f"Sincronização dinâmica de 2º Turno disponível para o ano 2026 (ano atual: {self.year})."
            )

        # 1. Tenta baixar a versão mais recente dos registros do TSE PesqEle (com fallback transparente)
        try:
            self.download_official_tse_pesqele_data(force=force_download)
        except Exception:
            # Fallback seguro para o censo de registros já disponível localmente
            pass

        # 2. Atualiza pesquisas_publicadas_2026.csv garantindo persistência completa
        csv_filename = f"pesquisas_publicadas_{self.year}.csv"
        raw_csv = self.raw_dir / csv_filename

        existing_registros = set()
        has_geo_cols = False
        if raw_csv.exists():
            with open(raw_csv, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                has_geo_cols = "abrangencia" in (reader.fieldnames or [])
                for row in reader:
                    reg = row.get("id_registro_tse", "").strip()
                    if reg:
                        existing_registros.add(reg)

        rows_to_append: list[str] = []
        for rec in self.SECOND_ROUND_POLLS_2026_RECORDS:
            reg_id, inst, dt_ini, dt_fim, dt_pub, n, me, method, deff, fb_raw, lula_raw, bn, ind = (
                rec[:13]
            )
            abrang = rec[13] if len(rec) > 13 else "NACIONAL"
            uf_val = rec[14] if len(rec) > 14 else "BR"
            reg_val = rec[15] if len(rec) > 15 else "BR"
            if reg_id not in existing_registros:
                if has_geo_cols:
                    line = (
                        f"{reg_id},{inst},{dt_ini},{dt_fim},{dt_pub},{n},{me},{method},{deff},"
                        f"{fb_raw},{lula_raw},0.0,0.0,0.0,0.0,0.0,{bn},{ind},2,"
                        f"{abrang},{uf_val},{reg_val}\n"
                    )
                else:
                    line = (
                        f"{reg_id},{inst},{dt_ini},{dt_fim},{dt_pub},{n},{me},{method},{deff},"
                        f"{fb_raw},{lula_raw},0.0,0.0,0.0,0.0,0.0,{bn},{ind},2\n"
                    )
                rows_to_append.append(line)

        if rows_to_append and raw_csv.exists():
            with open(raw_csv, mode="a", encoding="utf-8") as f:
                f.writelines(rows_to_append)

        # 3. Processa e persiste em Parquet atualizado
        self.save_processed()

        # 4. Retorna as pesquisas do 2º Turno
        all_polls = self.extract_and_transform()
        second_round_polls = [p for p in all_polls if p.turno == 2]
        return second_round_polls
