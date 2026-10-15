"""Algoritmo e regras de conversão de intenções de voto brutas em votos válidos.

Este módulo implementa a conversão canônica exigida pelo Tribunal Superior Eleitoral (TSE),
onde brancos, nulos e indecisos são expurgados do denominador antes de qualquer
comparação com os resultados oficiais das urnas.
"""


class InvalidVoteCalculationError(ValueError):
    """Exceção levantada quando os parâmetros de cálculo de votos válidos são inconsistentes."""


def calculate_valid_votes(
    votos_totais: dict[str, float],
    percentual_brancos_nulos: float,
    percentual_indecisos: float,
) -> dict[str, float]:
    """Converte intenções de voto brutas (cenário estimulado) em percentuais de votos válidos.

    Aplica a fórmula oficial do TSE:
    p_v,i = p_i / (1 - (p_brancos_nulos + p_indecisos))

    Todos os percentuais devem ser informados na escala de 0 a 100. O resultado retornado
    é um dicionário de percentuais de votos válidos normalizados para somar 100.0%.

    Args:
        votos_totais: Dicionário mapeando nome do candidato ao seu percentual bruto.
        percentual_brancos_nulos: Percentual acumulado de votos em branco e nulos (0 a 100).
        percentual_indecisos: Percentual de eleitores indecisos ou sem resposta (0 a 100).

    Returns:
        dict[str, float]: Dicionário mapeando cada candidato ao seu percentual de votos válidos,
            arredondado para duas casas decimais e normalizado.

    Raises:
        InvalidVoteCalculationError: Se os percentuais forem negativos, se a soma de
            não-válidos for >= 100%, se os votos totais forem vazios ou se a soma
            dos votos brutos de candidatos for <= 0.
    """
    if percentual_brancos_nulos < 0.0 or percentual_indecisos < 0.0:
        raise InvalidVoteCalculationError(
            "Percentuais de brancos/nulos ou indecisos não podem ser negativos."
        )

    soma_nao_validos = percentual_brancos_nulos + percentual_indecisos
    if soma_nao_validos >= 100.0:
        raise InvalidVoteCalculationError(
            f"A soma de brancos, nulos e indecisos ({soma_nao_validos:.2f}%) "
            "deve ser estritamente menor que 100%."
        )

    if not votos_totais:
        raise InvalidVoteCalculationError("O dicionário de votos totais não pode ser vazio.")

    for cand, pct in votos_totais.items():
        if pct < 0.0:
            raise InvalidVoteCalculationError(
                f"O percentual do candidato '{cand}' não pode ser negativo ({pct}%)."
            )

    soma_bruta_candidatos = sum(votos_totais.values())
    if soma_bruta_candidatos <= 0.0:
        raise InvalidVoteCalculationError(
            "A soma dos percentuais brutos dos candidatos deve ser estritamente positiva."
        )

    # Denominador de válidos: proporção disponível para candidatos
    # Ex: se não válidos somam 10%, o denominador é 0.90 (ou 90%)
    denominador = (100.0 - soma_nao_validos) / 100.0

    # Cálculo inicial dos válidos
    votos_validos_brutos: dict[str, float] = {
        cand: pct / denominador for cand, pct in votos_totais.items()
    }

    # Normalização final para garantir fechamento exato em 100.0%
    soma_calculada = sum(votos_validos_brutos.values())
    if soma_calculada <= 0.0:
        raise InvalidVoteCalculationError(
            "Falha numérica: soma dos votos válidos calculados resultou em zero."
        )

    fator_normalizacao = 100.0 / soma_calculada
    return {cand: round(pct * fator_normalizacao, 2) for cand, pct in votos_validos_brutos.items()}
