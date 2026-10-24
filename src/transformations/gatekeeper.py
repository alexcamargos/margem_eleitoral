"""Sistema de blindagem e Gatekeeper de integridade eleitoral.

Implementa os portões de segurança e validações estritas para garantir que:
1. No 2º Turno, qualquer levantamento eleitoral possua estritamente 2 candidatos
   com votos nominais registrados (regra constitucional e matemática absoluta).
2. A partição da intenção de votos (soma dos votos totais brutos + brancos/nulos +
   indecisos) respeite o invariante estocástico fechando em ~100% (com margem de tolerância).
3. Qualquer tentativa de inserção ou processamento com dados espúrios, corruptos ou
   multi-candidato no 2º Turno seja sumariamente barrada pelo sistema.
"""

from collections.abc import Sequence
from typing import Any


class GatekeeperViolationError(ValueError):
    """Exceção base para violações dos portões de integridade eleitoral."""


class SecondRoundCandidateCountError(GatekeeperViolationError):
    """Exceção levantada quando um levantamento do 2º Turno não possui exatamente dois candidatos."""


class PollSumMismatchError(GatekeeperViolationError):
    """Exceção levantada quando a soma de votos totais, brancos/nulos e indecisos não fecha em ~100%."""


class ElectoralGatekeeper:
    """Guardião de regras de integridade e contratos para pesquisas e modelos eleitorais.

    Garante conformidade com o art. 77 da Constituição Federal (segundo turno estritamente binário)
    e com os invariantes matemáticos de partição e cálculo de votos válidos.
    """

    MIN_TOTAL_SUM: float = 85.0
    MAX_TOTAL_SUM: float = 103.0

    @classmethod
    def validate_second_round_candidate_count(
        cls,
        turno: int,
        candidates_with_votes: Sequence[str] | dict[str, float],
        poll_id: str = "",
    ) -> None:
        """Garante que pesquisas de 2º Turno possuam estritamente dois candidatos concorrentes.

        No sistema eleitoral brasileiro (CF/88, art. 77), o 2º Turno é estritamente uma disputa
        entre os dois candidatos mais votados no 1º Turno. A presença de 1 ou mais de 2 candidatos
        com intenção de voto registrada é terminantemente proibida e invalida a pesquisa.

        Args:
            turno: Turno da eleição avaliada (1 ou 2).
            candidates_with_votes: Lista ou dicionário contendo os candidatos com votos apurados.
            poll_id: Identificador opcional do registro no TSE para rastreabilidade.

        Returns:
            None.

        Raises:
            SecondRoundCandidateCountError: Se o turno for 2 e a contagem de candidatos ativos for diferente de 2.
        """
        if turno != 2:
            return

        if isinstance(candidates_with_votes, dict):
            active_cands = [c for c, v in candidates_with_votes.items() if float(v) > 0.0]
        else:
            active_cands = list(candidates_with_votes)

        n_cands = len(active_cands)
        if n_cands != 2:
            id_info = f" ({poll_id})" if poll_id else ""
            raise SecondRoundCandidateCountError(
                f"[GATEKEEPER 2º TURNO] Pesquisa{id_info} inválida para o 2º Turno: "
                f"deve possuir estritamente 2 candidatos com votos registrados. "
                f"Encontrados {n_cands} candidatos: {active_cands}."
            )

    @classmethod
    def validate_poll_sum(
        cls,
        votos_totais: dict[str, float],
        percentual_brancos_nulos: float,
        percentual_indecisos: float,
        poll_id: str = "",
        turno: int = 2,
        min_sum: float | None = None,
        max_sum: float | None = None,
    ) -> None:
        """Valida se a soma das intenções brutas, brancos/nulos e indecisos fecha em aproximadamente 100%.

        No 2º Turno, detecta contaminações no dataset bruto, como duplicação de colunas de candidatos ou dados corrompidos.

        Args:
            votos_totais: Mapeamento de candidato para intenção de voto total bruta (%).
            percentual_brancos_nulos: Percentual declarado de brancos e nulos somados.
            percentual_indecisos: Percentual declarado de eleitores indecisos ou sem resposta.
            poll_id: Identificador opcional do registro no TSE para rastreabilidade.
            turno: Turno da pesquisa (validação estrita aplicada ao 2º Turno).
            min_sum: Limite inferior aceitável em percentual (padrão: 85.0%).
            max_sum: Limite superior aceitável em percentual (padrão: 103.0%).

        Returns:
            None.

        Raises:
            PollSumMismatchError: Se a soma estiver fora do intervalo de tolerância estocástica.
        """
        if turno != 2:
            return

        low = min_sum if min_sum is not None else cls.MIN_TOTAL_SUM
        high = max_sum if max_sum is not None else cls.MAX_TOTAL_SUM

        total_sum = (
            sum(float(v) for v in votos_totais.values())
            + float(percentual_brancos_nulos)
            + float(percentual_indecisos)
        )
        if not (low <= total_sum <= high):
            id_info = f" ({poll_id})" if poll_id else ""
            raise PollSumMismatchError(
                f"[GATEKEEPER SOMA TOTAL] Pesquisa{id_info} com fechamento amostral inconsistente: "
                f"a soma de votos totais + brancos/nulos + indecisos resultou em {total_sum:.2f}%. "
                f"No 2º Turno, o intervalo permitido é [{low:.1f}%, {high:.1f}%]."
            )

    @classmethod
    def validate_raw_poll_entry(
        cls,
        turno: int,
        votos_brutos: dict[str, float],
        brancos_nulos: float,
        indecisos: float,
        poll_id: str = "",
    ) -> None:
        """Aplica a blindagem completa de integridade sobre uma entrada bruta de pesquisa.

        Args:
            turno: Turno da eleição (1 ou 2).
            votos_brutos: Dicionário candidato -> percentual bruto.
            brancos_nulos: Percentual de brancos/nulos.
            indecisos: Percentual de indecisos.
            poll_id: Identificador do registro TSE.

        Returns:
            None.

        Raises:
            GatekeeperViolationError: Se qualquer regra de integridade for violada.
        """
        cls.validate_second_round_candidate_count(turno, votos_brutos, poll_id)
        cls.validate_poll_sum(votos_brutos, brancos_nulos, indecisos, poll_id, turno=turno)

    @classmethod
    def filter_and_enforce_two_candidates(
        cls,
        candidates: Sequence[str],
        polls: Sequence[Any],
        turno: int,
    ) -> list[str]:
        """Garante que a lista de candidatos avaliados seja estritamente os dois finalistas no 2º Turno.

        Caso um conjunto de pesquisas contenha ruído ou dados legados de 1º turno, isola
        os dois candidatos com maior massa agregada de intenção de voto no 2º Turno.

        Args:
            candidates: Lista de candidatos identificados.
            polls: Sequência de pesquisas eleitorais.
            turno: Turno eleitoral (1 ou 2).

        Returns:
            list[str]: Lista ordenada com os candidatos válidos (estritamente 2 se turno == 2).

        Raises:
            None.
        """
        if turno != 2 or len(candidates) <= 2:
            return sorted(candidates)

        cand_mass: dict[str, float] = {}
        for c in candidates:
            mass = sum(
                float(getattr(p, "votos_validos", {}).get(c, 0.0))
                for p in polls
                if hasattr(p, "votos_validos")
            )
            cand_mass[c] = mass

        top_2 = sorted(candidates, key=lambda c: cand_mass.get(c, 0.0), reverse=True)[:2]
        return sorted(top_2)
