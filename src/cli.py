"""Interface de Linha de Comando (CLI) para consulta, processamento e modelagem eleitoral.

Permite consultar o status das pesquisas, sincronizar o censo oficial do TSE,
adicionar novos levantamentos manualmente ou em lote, reprocessar datasets e
executar/ajustar os modelos agregador e preditivo diretamente pelo terminal.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import httpx
import polars as pl

from src.analytics.aggregator_model import compute_poll_aggregation_series
from src.analytics.predictive_model import (
    PredictiveModelConfig,
    compute_first_round_institute_calibration,
    predict_election_outcome,
)
from src.ingestion.data_loader import (
    get_election_dataset,
    get_election_date,
    get_second_round_sync_summary,
    get_tse_registration_census,
)
from src.ingestion.pesqele_collector import PesqEleCollector
from src.ingestion.pipeline import run_etl_for_year
from src.ingestion.web_poll_extractor import WebPollExtractor
from src.transformations.normalizer import TaxonomyNormalizer
from src.transformations.valid_votes import calculate_valid_votes


def format_header(title: str) -> None:
    """Imprime um cabeçalho formatado no terminal.

    Args:
        title: Título do bloco informativo.

    Returns:
        None.

    Raises:
        None.
    """
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def cmd_status(args: argparse.Namespace) -> None:
    """Consulta o status atual dos dados eleitorais e pesquisas registradas.

    Args:
        args: Argumentos parseados do terminal (ano, turno).

    Returns:
        None.

    Raises:
        None.
    """
    year = int(args.year)
    turno = int(args.turno)
    format_header(f"Status do Ciclo Eleitoral: {year} (Turno {turno})")

    election_date = get_election_date(year=year, turno=turno)
    print(f"-> Data oficial da eleição: {election_date.strftime('%d/%m/%Y')}")

    try:
        tse_result, eve_polls, all_polls = get_election_dataset(
            year=year, turno=turno, include_subnational=True
        )
        if tse_result is not None and getattr(tse_result, "apuracao_concluida", True):
            print(f"-> Apuração oficial do TSE: {len(tse_result.resultado_nominal)} candidatos")
            for cand, pct in sorted(
                tse_result.resultado_nominal.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"   * {cand}: {pct:.2f}%")
        else:
            print(
                f"-> Apuração oficial do TSE: [AGUARDANDO TOTALIZAÇÃO DAS URNAS (Votação em {election_date.strftime('%d/%m/%Y')})]"
            )

        print(f"\n-> Pesquisas disponíveis: {len(all_polls)} levantamentos totais")
        print(f"   * Pesquisas de véspera (<= 72h): {len(eve_polls)}")

        institutos = sorted({p.instituto_nome_fantasia for p in all_polls})
        print(f"   * Institutos monitorados ({len(institutos)}): {', '.join(institutos)}")

        if all_polls:
            latest_poll = max(all_polls, key=lambda p: p.data_fim_campo)
            print(
                f"   * Levantamento mais recente: {latest_poll.instituto_nome_fantasia} (Fim: {latest_poll.data_fim_campo.strftime('%d/%m/%Y')})"
            )
    except (FileNotFoundError, OSError, ValueError, KeyError) as e:
        print(f"[!] Alerta ao carregar dataset: {e}")

    if turno == 2:
        sync_sum = get_second_round_sync_summary(year=year)
        status_txt = "SINCRONIZADO" if sync_sum["is_synced"] else "PENDENTE"
        print(f"\n-> Sincronização 2º Turno: [{status_txt}]")
        print(f"   * Total pesquisas 2T: {sync_sum['total_polls']}")
        print(f"   * Pesquisas véspera 2T: {sync_sum['eve_polls_count']}")

    census_df = get_tse_registration_census(year=year)
    if census_df.height > 0:
        print(f"\n-> Censo Oficial TSE (PesqEle): {census_df.height} registros brutos catalogados.")
    print("=" * 70 + "\n")


def cmd_audit(args: argparse.Namespace) -> None:
    """Audita a integridade e conformidade de 100% das pesquisas com o censo do TSE.

    Args:
        args: Argumentos parseados do terminal (ano).

    Returns:
        None.

    Raises:
        None.
    """
    year = int(args.year)
    format_header(f"Auditoria Técnica e Validação Cruzada TSE ({year})")
    try:
        collector = PesqEleCollector(year=year)
        census_df = get_tse_registration_census(year=year)
        res = collector.cross_validate_with_tse_census(census_df=census_df)
        print(f"-> Total de pesquisas analisadas: {res['total_avaliadas']}")
        print(f"-> Pesquisas validadas no censo TSE: {res['total_validadas']}")
        print(f"-> Pesquisas divergentes/fictícias: {res['total_divergentes']}")
        print(f"-> Taxa de autenticidade comprovada: {res['taxa_conformidade'] * 100:.1f}%")
        if res["detalhes_divergencias"]:
            print(
                f"   [!] Protocolos não encontrados no TSE: {', '.join(res['detalhes_divergencias'])}"
            )
        else:
            print("   [OK] 100% dos levantamentos coincidem com registros oficiais do TSE.")
    except (FileNotFoundError, OSError, ValueError, KeyError) as e:
        print(f"[ERRO] Falha durante a auditoria: {e}", file=sys.stderr)
        sys.exit(1)
    print("=" * 70 + "\n")


def cmd_sync(args: argparse.Namespace) -> None:
    """Dispara a sincronização automática de pesquisas do 2º Turno junto ao TSE ou feed web.

    Args:
        args: Argumentos parseados do terminal (ano, force, feed_url).

    Returns:
        None.

    Raises:
        None.
    """
    year = int(args.year)
    feed_url = getattr(args, "feed_url", None)
    if feed_url:
        format_header(f"Sincronizando Pesquisas via Feed Web ({year})")
        try:
            extractor = WebPollExtractor(year=year, feed_url=feed_url)
            res = extractor.sync(feed_url=feed_url)
            print("[OK] Sincronização via feed web concluída com sucesso!")
            print(f"-> Total de pesquisas verificadas no feed: {res['total_extraidas']}")
            print(f"-> Novos levantamentos incorporados ao dataset: {res['novas_incorporadas']}")
            audit = res.get("tse_audit", {})
            print(
                f"-> Auditoria cadastral TSE: {audit.get('total_validadas', 0)}/{audit.get('total_avaliadas', 0)} "
                f"validadas ({audit.get('taxa_conformidade', 0.0) * 100:.1f}%)"
            )
            print(f"-> Dataset Parquet atualizado: {res.get('parquet_path')}")
        except (httpx.HTTPError, OSError, ValueError) as e:
            print(f"[ERRO] Falha ao sincronizar via feed web: {e}", file=sys.stderr)
            sys.exit(1)
        print("=" * 70 + "\n")
        return

    format_header(f"Sincronizando Pesquisas Oficiais do TSE ({year})")
    try:
        collector = PesqEleCollector(year=year)
        synced = collector.sync_official_second_round_polls(force_download=args.force)
        print("[OK] Sincronização concluída com sucesso!")
        print(f"-> Foram integradas e validadas {len(synced)} pesquisas de 2º Turno.")
    except (httpx.HTTPError, OSError, ValueError) as e:
        print(f"[ERRO] Falha ao sincronizar com o TSE: {e}", file=sys.stderr)
        sys.exit(1)
    print("=" * 70 + "\n")


def cmd_add_poll(args: argparse.Namespace) -> None:
    """Adiciona uma nova pesquisa divulgada e atualiza os arquivos do projeto.

    Args:
        args: Argumentos parseados com os dados da pesquisa (registro, instituto, datas, votos, etc).

    Returns:
        None.

    Raises:
        None.
    """
    year = int(args.year)
    turno = int(args.turno)
    format_header(f"Inserindo Nova Pesquisa Divulgada ({year} - Turno {turno})")

    normalizer = TaxonomyNormalizer()
    inst_canonical = normalizer.normalize_institute(args.instituto)
    method_canonical = normalizer.normalize_methodology(args.metodologia).value

    # Parseia votos brutos passados como lista cand=pct
    votos_brutos: dict[str, float] = {}
    for item in args.voto:
        if "=" not in item:
            print(
                f"[ERRO] Formato de voto inválido: '{item}'. Use formato 'Candidato=Percentual' (ex: 'Lula=47.5')",
                file=sys.stderr,
            )
            sys.exit(1)
        c_raw, val_str = item.split("=", 1)
        c_norm = normalizer.normalize_candidate(c_raw.strip())
        try:
            votos_brutos[c_norm] = float(val_str.strip())
        except ValueError:
            print(
                f"[ERRO] Valor numérico inválido para o candidato '{c_raw}': '{val_str}'",
                file=sys.stderr,
            )
            sys.exit(1)

    brancos_nulos = float(args.brancos_nulos)
    indecisos = float(args.indecisos)

    validos = calculate_valid_votes(
        votos_totais=votos_brutos,
        percentual_brancos_nulos=brancos_nulos,
        percentual_indecisos=indecisos,
    )

    print(f"-> Instituto: {inst_canonical}")
    print(f"-> Registro TSE: {args.registro}")
    print(
        f"-> Período de Campo: {args.dt_inicio} a {args.dt_fim} (Divulgação: {args.dt_divulgacao})"
    )
    print(f"-> Amostra: {args.amostra} entrevistados | Margem: ±{args.margem}% | Deff: {args.deff}")
    print(f"-> Metodologia: {method_canonical}")
    print(f"-> Abrangência: {args.abrangencia.upper()} ({args.uf}/{args.regiao})")
    print(f"-> Votos Brutos: {votos_brutos} | BN: {brancos_nulos}% | Indecisos: {indecisos}%")
    print(f"-> Votos Válidos Calculados: {validos}")

    # Monta linha CSV para data/raw/{year}/pesquisas_publicadas_{year}.csv
    repo_root = Path(__file__).resolve().parent.parent
    raw_csv = repo_root / "data" / "raw" / str(year) / f"pesquisas_publicadas_{year}.csv"

    if not raw_csv.exists():
        print(f"[ERRO] Arquivo de dados brutos não encontrado: {raw_csv}", file=sys.stderr)
        sys.exit(1)

    # Verifica colunas existentes no cabeçalho
    with open(raw_csv, mode="r", encoding="utf-8-sig") as f:
        header_line = f.readline().strip()
    headers = [h.strip() for h in header_line.split(",")]

    row_dict: dict[str, str] = {h: "0.0" for h in headers}
    row_dict["id_registro_tse"] = args.registro
    row_dict["instituto"] = inst_canonical
    row_dict["data_inicio_campo"] = args.dt_inicio
    row_dict["data_fim_campo"] = args.dt_fim
    row_dict["data_divulgacao"] = args.dt_divulgacao
    row_dict["tamanho_amostra"] = str(args.amostra)
    row_dict["margem_erro"] = str(args.margem)
    row_dict["metodologia"] = method_canonical
    row_dict["deff"] = str(args.deff)
    row_dict["brancos_nulos"] = str(brancos_nulos)
    row_dict["indecisos"] = str(indecisos)
    row_dict["turno"] = str(turno)
    row_dict["abrangencia"] = args.abrangencia.upper()
    row_dict["uf"] = args.uf.upper()
    row_dict["regiao"] = args.regiao.upper()

    for cand, pct in votos_brutos.items():
        col_name = f"voto_bruto_{cand}"
        if col_name in row_dict:
            row_dict[col_name] = str(pct)

    if "tier_fonte" in headers:
        row_dict["tier_fonte"] = getattr(args, "tier", None) or "TIER_3_AGREGADOR_PUBLICO"
    if "url_fonte_publicacao" in headers:
        row_dict["url_fonte_publicacao"] = getattr(args, "url_fonte", None) or ""
    if "url_tse_pesqele" in headers:
        digits = "".join(c for c in args.registro if c.isdigit())
        row_dict["url_tse_pesqele"] = (
            getattr(args, "url_tse", None)
            or f"https://pesqele-divulgacao.tse.jus.br/app/pesquisa/detalhar.xhtml?p={digits}"
        )

    # Escreve linha formatada no CSV
    line_to_write = ",".join(row_dict[h] for h in headers) + "\n"
    with open(raw_csv, mode="a", encoding="utf-8") as f:
        f.write(line_to_write)
    print(f"-> Pesquisa gravada em: {raw_csv}")

    # Reprocessa ETL
    print("-> Atualizando dataset e persistindo formato colunar Parquet...")
    collector = PesqEleCollector(year=year)
    collector.save_processed()
    print("[OK] Dataset atualizado e validado com sucesso!")


def cmd_process(args: argparse.Namespace) -> None:
    """Executa o pipeline completo de ETL e validação de contratos.

    Args:
        args: Argumentos parseados do terminal (ano, turno).

    Returns:
        None.

    Raises:
        None.
    """
    year = int(args.year)
    turno = int(args.turno)
    format_header(f"Processando Pipeline de Dados ({year} - Turno {turno})")
    try:
        run_etl_for_year(year=year, turno=turno)
        print("[OK] Processamento concluído com sucesso!")
    except (FileNotFoundError, OSError, ValueError, KeyError) as e:
        print(f"[ERRO] Falha no processamento: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_predict(args: argparse.Namespace) -> None:
    """Ajusta e executa os modelos agregador e preditivo para os dados atuais.

    Args:
        args: Argumentos com ano, turno, data de corte e opções de simulação.

    Returns:
        None.

    Raises:
        None.
    """
    year = int(args.year)
    turno = int(args.turno)
    format_header(f"Ajuste e Execução dos Modelos Preditivos ({year} - Turno {turno})")

    election_date = get_election_date(year=year, turno=turno)
    today = date.today()
    default_cutoff = min(today, election_date) if year == 2026 and turno == 2 else election_date
    cutoff_date = date.fromisoformat(args.cutoff) if args.cutoff else default_cutoff

    tse_result, eve_polls, all_polls = get_election_dataset(
        year=year, turno=turno, include_subnational=True
    )

    if not all_polls:
        print("[ERRO] Nenhuma pesquisa encontrada para os parâmetros informados.", file=sys.stderr)
        sys.exit(1)

    print(f"-> Base de dados: {len(all_polls)} pesquisas ({len(eve_polls)} de véspera)")
    print(f"-> Data de corte da projeção: {cutoff_date.strftime('%d/%m/%Y')}")

    # 1. Agregador Dinâmico Contínuo
    print("\n--- [1] Agregador Dinâmico com Decaimento Temporal ---")
    candidatos = sorted({c for p in all_polls for c in p.votos_validos.keys() if c != "Outros"})
    df_agg = compute_poll_aggregation_series(
        polls=all_polls,
        candidates=candidatos,
        half_life_days=args.tau,
        deff=1.3,
        use_valid_votes=True,
    )
    if df_agg.height > 0:
        latest_agg = df_agg.filter(pl.col("data") == df_agg["data"].max())
        for row in latest_agg.iter_rows(named=True):
            cand = row["candidato"]
            med = row["media_ponderada"]
            p025 = row.get("ci_95_inf", 0.0)
            p975 = row.get("ci_95_sup", 0.0)
            print(f"   * {cand}: {med:.2f}% (IC 95%: [{p025:.2f}%; {p975:.2f}%])")

    # 2. Modelo Preditivo Hierárquico Calibrado (Ato 6)
    print("\n--- [2] Modelo Estado-Espaço Hierárquico Calibrado ---")
    cfg = PredictiveModelConfig.load_from_settings()
    if args.tau != 7.0:
        cfg = PredictiveModelConfig(
            tau_days=args.tau,
            momentum_window_days=cfg.momentum_window_days,
            audit_lambda=cfg.audit_lambda,
            shrinkage_alpha=cfg.shrinkage_alpha,
            unobserved_error_sigma=cfg.unobserved_error_sigma,
            student_t_df=cfg.student_t_df,
            n_simulations=args.simulations,
            random_seed=cfg.random_seed,
            scope_weights=cfg.scope_weights,
            macro_region_weights=cfg.macro_region_weights,
            regional_differentials=cfg.regional_differentials,
            promotion_gates=cfg.promotion_gates,
        )

    calib_t1 = None
    if turno == 2:
        try:
            t1_res, t1_eve, t1_all = get_election_dataset(
                year=year, turno=1, include_subnational=True
            )
            t1_date = get_election_date(year=year, turno=1)
            calib_t1 = compute_first_round_institute_calibration(
                t1_polls=t1_all,
                t1_official_result=t1_res,
                election_date_t1=t1_date,
                audit_lambda=cfg.audit_lambda,
                config=cfg,
            )
            print(
                f"   -> Calibração empírica do 1º Turno ativa: {len(calib_t1)} institutos calibrados."
            )
        except (FileNotFoundError, OSError, ValueError, KeyError) as e:
            print(f"   -> Aviso: Não foi possível carregar calibração do 1º Turno: {e}")

    try:
        forecast = predict_election_outcome(
            polls=all_polls,
            election_date=election_date,
            cutoff_date=cutoff_date,
            turno=turno,
            calibration_t1=calib_t1,
            config=cfg,
        )

        print("\nResultado da Projeção Probabilística:")
        for pred in forecast.candidatos:
            print(f"   [*] {pred.candidato}:")
            print(f"      - Probabilidade de Vitória: {pred.probabilidade_vitoria:.1f}%")
            print(
                f"      - Votação Esperada: {pred.voto_esperado:.2f}% (Envelope 95%: [{pred.ic_95_inferior:.2f}%; {pred.ic_95_superior:.2f}%])"
            )
            print(f"      - Momentum / Tendência Diária: {pred.tendencia_diaria_pp:+.2f} pp/dia")

        print(
            f"\n   -> Decomposição Subnacional e Regional ({len(forecast.agregacao_regional)} fatias):"
        )
        for s in forecast.agregacao_regional:
            if s.regiao == "BR":
                continue
            print(
                f"      * {s.nome_regiao} (Peso: {s.peso_eleitorado * 100:.1f}%, Pesquisas: {s.n_pesquisas}): {s.votos_projetados} | Margem Líder: {s.margem_lider:+.2f} pp"
            )

    except (ValueError, KeyError, RuntimeError, TypeError) as e:
        print(f"[ERRO] Falha ao ajustar modelo preditivo: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 70 + "\n")


def build_parser() -> argparse.ArgumentParser:
    """Constrói a árvore de subcomandos do utilitário CLI.

    Args:
        None.

    Returns:
        argparse.ArgumentParser: Parser configurado com os subcomandos.

    Raises:
        None.
    """
    parser = argparse.ArgumentParser(
        prog="margem",
        description="Margem Eleitoral CLI: Auditoria, Ingestão e Ajuste de Modelos de Pesquisas Eleitorais",
    )
    subparsers = parser.add_subparsers(
        dest="subcommand", required=True, help="Subcomando a executar"
    )

    # 1. status
    p_status = subparsers.add_parser("status", help="Consulta o status atual dos dados e pesquisas")
    p_status.add_argument("--year", type=int, default=2026, help="Ano eleitoral (default: 2026)")
    p_status.add_argument(
        "--turno", type=int, default=2, choices=[1, 2], help="Turno eleitoral (default: 2)"
    )
    p_status.set_defaults(func=cmd_status)

    # 2. sync
    p_sync = subparsers.add_parser(
        "sync", help="Sincroniza as pesquisas eleitorais junto ao TSE ou feed web"
    )
    p_sync.add_argument("--year", type=int, default=2026, help="Ano eleitoral (default: 2026)")
    p_sync.add_argument("--force", action="store_true", help="Força novo download do CDN do TSE")
    p_sync.add_argument(
        "--feed-url",
        type=str,
        default=None,
        help="URL opcional do feed de pesquisas abertas para sincronização direta",
    )
    p_sync.set_defaults(func=cmd_sync)

    # 3. add-poll
    p_add = subparsers.add_parser(
        "add-poll", help="Adiciona uma nova pesquisa divulgada e atualiza os datasets"
    )
    p_add.add_argument("--year", type=int, default=2026, help="Ano eleitoral (default: 2026)")
    p_add.add_argument(
        "--turno", type=int, default=2, choices=[1, 2], help="Turno eleitoral (default: 2)"
    )
    p_add.add_argument(
        "--registro", type=str, required=True, help="Número de registro TSE (ex: BR-01115/2026)"
    )
    p_add.add_argument(
        "--instituto", type=str, required=True, help="Nome do instituto (ex: Datafolha, Quaest)"
    )
    p_add.add_argument(
        "--dt-inicio", type=str, required=True, help="Data de início de campo (AAAA-MM-DD)"
    )
    p_add.add_argument(
        "--dt-fim", type=str, required=True, help="Data de fim de campo (AAAA-MM-DD)"
    )
    p_add.add_argument(
        "--dt-divulgacao", type=str, required=True, help="Data de divulgação oficial (AAAA-MM-DD)"
    )
    p_add.add_argument("--amostra", type=int, required=True, help="Tamanho da amostra (ex: 2000)")
    p_add.add_argument(
        "--margem", type=float, default=2.0, help="Margem de erro declarada (default: 2.0)"
    )
    p_add.add_argument(
        "--metodologia",
        type=str,
        default="PRESENCIAL_DOMICILIAR",
        help="Metodologia (ex: PRESENCIAL_DOMICILIAR, TELEFONICA_CATI, ONLINE)",
    )
    p_add.add_argument(
        "--deff", type=float, default=1.35, help="Efeito de delineamento / deff (default: 1.35)"
    )
    p_add.add_argument(
        "--voto",
        action="append",
        required=True,
        help="Intenção de voto bruta (ex: --voto 'Lula=47.5' --voto 'Flávio Bolsonaro=48.0')",
    )
    p_add.add_argument(
        "--brancos-nulos",
        type=float,
        default=3.5,
        help="Percentual de brancos/nulos (default: 3.5)",
    )
    p_add.add_argument(
        "--indecisos", type=float, default=2.0, help="Percentual de indecisos (default: 2.0)"
    )
    p_add.add_argument(
        "--abrangencia",
        type=str,
        default="NACIONAL",
        choices=["NACIONAL", "ESTADUAL", "REGIONAL"],
        help="Abrangência geográfica",
    )
    p_add.add_argument("--uf", type=str, default="BR", help="Sigla da UF (default: BR)")
    p_add.add_argument(
        "--regiao",
        type=str,
        default="BR",
        choices=["BR", "SE", "NE", "S", "N", "CO"],
        help="Sigla da Região (default: BR)",
    )
    p_add.add_argument(
        "--tier",
        type=str,
        default="TIER_3_AGREGADOR_PUBLICO",
        help="Classificação na hierarquia de fontes (ex: TIER_1_RELATORIO_INSTITUTO, TIER_2_CONTRATANTE_ORIGINAL)",
    )
    p_add.add_argument(
        "--url-fonte",
        type=str,
        default="",
        help="URL pública da divulgação/laudo técnico",
    )
    p_add.add_argument(
        "--url-tse",
        type=str,
        default="",
        help="URL oficial de detalhamento no PesqEle do TSE",
    )
    p_add.set_defaults(func=cmd_add_poll)

    # 4. audit
    p_audit = subparsers.add_parser(
        "audit", help="Audita a autenticidade cruzando pesquisas publicadas com o censo do TSE"
    )
    p_audit.add_argument("--year", type=int, default=2026, help="Ano eleitoral (default: 2026)")
    p_audit.set_defaults(func=cmd_audit)

    # 4. process
    p_process = subparsers.add_parser(
        "process", help="Executa o pipeline completo de processamento (ETL)"
    )
    p_process.add_argument("--year", type=int, default=2026, help="Ano eleitoral (default: 2026)")
    p_process.add_argument(
        "--turno", type=int, default=2, choices=[1, 2], help="Turno eleitoral (default: 2)"
    )
    p_process.set_defaults(func=cmd_process)

    # 5. predict
    p_predict = subparsers.add_parser(
        "predict", help="Ajusta e recalcula os modelos agregador e preditivo"
    )
    p_predict.add_argument("--year", type=int, default=2026, help="Ano eleitoral (default: 2026)")
    p_predict.add_argument(
        "--turno", type=int, default=2, choices=[1, 2], help="Turno eleitoral (default: 2)"
    )
    p_predict.add_argument(
        "--cutoff", type=str, default=None, help="Data limite de corte (AAAA-MM-DD)"
    )
    p_predict.add_argument(
        "--tau", type=float, default=7.0, help="Meia-vida exponencial em dias (default: 7.0)"
    )
    p_predict.add_argument(
        "--simulations",
        type=int,
        default=10000,
        help="Número de simulações Monte Carlo (default: 10000)",
    )
    p_predict.set_defaults(func=cmd_predict)

    return parser


def main() -> None:
    """Função principal de despacho CLI do terminal.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: Em caso de argumentos inválidos ou falhas de execução.
    """
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
