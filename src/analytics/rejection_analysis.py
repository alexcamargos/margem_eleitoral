"""Motor de cálculo estatístico e modelagem analítica de rejeição eleitoral.

Fornece funções para agregação de taxas de rejeição ("não votaria de jeito nenhum"),
classificação de vereditos por instituto, apuração de placar competitivo, cálculo de teto
eleitoral e estruturação de dados para visualização em halteres (Dumbbell Plot).
"""

from typing import Any, Sequence


def calculate_rejection_averages(
    polls: Sequence[dict[str, Any]],
    candidates: Sequence[str],
) -> dict[str, float]:
    """Calcula a média aritmética simples das taxas de rejeição declaradas pelos institutos.

    Args:
        polls: Sequência de dicionários com registros de pesquisas e suas taxas de rejeição.
        candidates: Lista de candidatos avaliados.

    Returns:
        dict[str, float]: Mapeamento de cada candidato para sua taxa média de rejeição (arredondada a 1 casa decimal).

    Raises:
        ValueError: Se a lista de pesquisas ou de candidatos estiver vazia.
    """
    if not polls:
        raise ValueError("A lista de pesquisas não pode estar vazia.")
    if not candidates:
        raise ValueError("A lista de candidatos não pode estar vazia.")

    totals: dict[str, float] = {c: 0.0 for c in candidates}
    counts: dict[str, int] = {c: 0 for c in candidates}

    for poll in polls:
        rejeicao = poll.get("rejeicao", {})
        for cand in candidates:
            if cand in rejeicao:
                totals[cand] += float(rejeicao[cand])
                counts[cand] += 1

    averages: dict[str, float] = {}
    for cand in candidates:
        if counts[cand] > 0:
            averages[cand] = round(totals[cand] / counts[cand], 1)
        else:
            averages[cand] = 0.0

    return averages


def classify_institute_rejection(
    rejection_nominal: dict[str, float],
    candidate_1: str,
    candidate_2: str,
    tie_threshold: float = 1.0,
) -> tuple[str, float]:
    """Classifica o posicionamento relativo de dois candidatos na taxa de rejeição de um instituto.

    Quanto menor a rejeição, mais vantajosa é a posição do candidato. Diferenças dentro
    do limiar de tolerância `tie_threshold` são classificadas como empate técnico.

    Args:
        rejection_nominal: Mapeamento de candidato para seu percentual de rejeição.
        candidate_1: Nome do primeiro candidato.
        candidate_2: Nome do segundo candidato.
        tie_threshold: Diferença máxima em pontos percentuais para considerar empate (padrão: 1.0).

    Returns:
        tuple[str, float]: Veredito ('<C1> menos', '<C2> menos' ou 'empate') e a diferença absoluta em pontos.

    Raises:
        KeyError: Se algum dos candidatos não constar no dicionário de rejeição.
        ValueError: Se tie_threshold for negativo.
    """
    if tie_threshold < 0.0:
        raise ValueError("O limiar de empate (tie_threshold) não pode ser negativo.")
    if candidate_1 not in rejection_nominal or candidate_2 not in rejection_nominal:
        raise KeyError(
            f"Ambos os candidatos ({candidate_1}, {candidate_2}) devem estar presentes em rejection_nominal."
        )

    val_1 = float(rejection_nominal[candidate_1])
    val_2 = float(rejection_nominal[candidate_2])
    diff = abs(val_1 - val_2)

    if diff <= tie_threshold:
        return "empate", round(diff, 1)

    if val_1 < val_2:
        return f"{candidate_1} menos", round(diff, 1)

    return f"{candidate_2} menos", round(diff, 1)


def compute_rejection_scoreboard(
    polls: Sequence[dict[str, Any]],
    candidate_1: str,
    candidate_2: str,
    tie_threshold: float = 1.0,
) -> dict[str, int]:
    """Computa o placar consolidado de institutos em que cada candidato é menos rejeitado.

    Prioriza o campo 'veredito' declarado se presente no registro; caso contrário,
    aplica a classificação algorítmica por limiar de empate.

    Args:
        polls: Sequência de levantamentos contendo rejeição por instituto.
        candidate_1: Primeiro candidato.
        candidate_2: Segundo candidato.
        tie_threshold: Limiar de pontos para empate técnico.

    Returns:
        dict[str, int]: Dicionário com contagens para 'candidato_1_menos', 'candidato_2_menos' e 'empate'.

    Raises:
        ValueError: Se a sequência de pesquisas estiver vazia.
    """
    if not polls:
        raise ValueError("A sequência de pesquisas não pode estar vazia.")

    scoreboard = {
        "candidato_1_menos": 0,
        "candidato_2_menos": 0,
        "empate": 0,
    }

    c1_lower = candidate_1.lower()
    c2_lower = candidate_2.lower()

    for poll in polls:
        verdict = poll.get("veredito")
        if verdict:
            verdict_lower = str(verdict).lower()
            if "empate" in verdict_lower:
                scoreboard["empate"] += 1
            elif c1_lower in verdict_lower or c1_lower.split()[0] in verdict_lower:
                scoreboard["candidato_1_menos"] += 1
            elif c2_lower in verdict_lower or c2_lower.split()[0] in verdict_lower:
                scoreboard["candidato_2_menos"] += 1
            continue

        rejeicao = poll.get("rejeicao", {})
        if candidate_1 in rejeicao and candidate_2 in rejeicao:
            v, _ = classify_institute_rejection(
                rejection_nominal=rejeicao,
                candidate_1=candidate_1,
                candidate_2=candidate_2,
                tie_threshold=tie_threshold,
            )
            if v == "empate":
                scoreboard["empate"] += 1
            elif candidate_1 in v:
                scoreboard["candidato_1_menos"] += 1
            else:
                scoreboard["candidato_2_menos"] += 1

    return scoreboard


def calculate_electoral_ceiling(rejection_pct: float) -> float:
    """Calcula o teto eleitoral teórico de um candidato a partir de sua rejeição.

    Em eleições majoritárias, o eleitor que rejeita categoricamente o candidato não
    constitui voto potencial, estabelecendo um teto: Teto = 100% - Rejeição.

    Args:
        rejection_pct: Percentual de rejeição do candidato (entre 0.0 e 100.0).

    Returns:
        float: Percentual máximo teórico de voto potencial (entre 0.0 e 100.0).

    Raises:
        ValueError: Se rejection_pct estiver fora do intervalo [0.0, 100.0].
    """
    if not (0.0 <= rejection_pct <= 100.0):
        raise ValueError(
            f"Taxa de rejeição deve estar entre 0.0 e 100.0, recebido: {rejection_pct}"
        )
    return round(100.0 - rejection_pct, 1)


def structure_rejection_metrics(dataset: dict[str, Any]) -> dict[str, Any]:
    """Estrutura e valida as métricas consolidadas do módulo de rejeição a partir do dataset.

    Args:
        dataset: Dicionário carregado do JSON de rejeição do ciclo eleitoral correspondente.

    Returns:
        dict[str, Any]: Pacote estruturado contendo dados do 1º turno, médias, placar e feed do 2º turno.

    Raises:
        KeyError: Se chaves fundamentais estiverem ausentes no dataset.
    """
    if "candidatos" not in dataset or "primeiro_turno" not in dataset:
        raise KeyError("Dataset de rejeição inválido: ausência de 'candidatos' ou 'primeiro_turno'.")

    c1, c2 = dataset["candidatos"][0], dataset["candidatos"][1]
    c1_display = dataset.get("candidatos_nomes_exibicao", {}).get(c1, c1)
    c2_display = dataset.get("candidatos_nomes_exibicao", {}).get(c2, c2)

    t1_data = dataset["primeiro_turno"]
    polls = t1_data.get("pesquisas_instituto", [])

    calc_averages = calculate_rejection_averages(polls=polls, candidates=[c1, c2])
    averages = t1_data.get("media_rejeicao", calc_averages)

    scoreboard = compute_rejection_scoreboard(
        polls=polls,
        candidate_1=c1,
        candidate_2=c2,
        tie_threshold=1.0,
    )

    teto_c1 = calculate_electoral_ceiling(averages.get(c1, 50.0))
    teto_c2 = calculate_electoral_ceiling(averages.get(c2, 50.0))

    return {
        "ano": dataset.get("ano", 2026),
        "cargo": dataset.get("cargo", "PRESIDENTE"),
        "candidatos": [c1, c2],
        "display_names": {c1: c1_display, c2: c2_display},
        "cores": dataset.get("cores_candidatos", {c1: "#EF4444", c2: "#3B82F6"}),
        "titulo_card": t1_data.get("titulo_card", "Quem é menos rejeitado?"),
        "subtitulo_resumo": t1_data.get("subtitulo_resumo", ""),
        "conceito_pedagogico": t1_data.get("conceito_pedagogico", ""),
        "texto_diagnostico": t1_data.get("texto_diagnostico", ""),
        "media_rejeicao": averages,
        "total_institutos": len(polls),
        "placar": scoreboard,
        "texto_placar": t1_data.get("texto_placar", ""),
        "pesquisas_instituto": polls,
        "notas_metodologicas": t1_data.get("notas_metodologicas", []),
        "segundo_turno": dataset.get("segundo_turno", {}),
        "tetos_eleitorais": {c1: teto_c1, c2: teto_c2},
    }
