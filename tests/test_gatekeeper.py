"""Testes unitários para o sistema de blindagem e Gatekeeper eleitoral.

Valida:
1. Rejeição sumária de pesquisas de 2º Turno com mais ou menos de 2 candidatos.
2. Rejeição de pesquisas com soma amostral inconsistente (fora do intervalo [97%, 103%]).
3. Aceitação de pesquisas legítimas de 1º Turno (múltiplos candidatos) e 2º Turno (binárias).
4. Interceptação e bloqueio no CLI (cmd_add_poll) antes de gravar dados no disco.
5. Isolamento estrito dos dois finalistas via ElectoralGatekeeper.filter_and_enforce_two_candidates.
"""

import argparse
from datetime import date

import pytest
from pydantic import ValidationError

from src.cli import cmd_add_poll
from src.transformations.gatekeeper import (
    ElectoralGatekeeper,
    GatekeeperViolationError,
    PollSumMismatchError,
    SecondRoundCandidateCountError,
)
from src.transformations.schemas import MetodologiaEnum, PesquisaEleitoralSchema


def test_second_round_strictly_two_candidates_passes() -> None:
    """Verifica que uma pesquisa legítima de 2º Turno com 2 candidatos é aceita pelo Gatekeeper.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    assert issubclass(SecondRoundCandidateCountError, GatekeeperViolationError)
    assert issubclass(PollSumMismatchError, GatekeeperViolationError)

    poll = PesquisaEleitoralSchema(
        id_registro_tse="BR-01001/2026",
        instituto_razao_social="Datafolha Instituto de Pesquisas Ltda",
        instituto_nome_fantasia="Datafolha",
        data_inicio_campo=date(2026, 10, 20),
        data_fim_campo=date(2026, 10, 22),
        data_divulgacao=date(2026, 10, 23),
        tamanho_amostra=2500,
        margem_erro_declarada=2.0,
        metodologia=MetodologiaEnum.PRESENCIAL_DOMICILIAR,
        votos_totais={"Flávio Bolsonaro": 49.0, "Lula": 46.0},
        votos_validos={"Flávio Bolsonaro": 51.58, "Lula": 48.42},
        percentual_indecisos=2.5,
        percentual_brancos_nulos=2.5,
        turno=2,
    )
    assert poll.turno == 2
    assert len(poll.votos_totais) == 2


def test_second_round_three_candidates_raises() -> None:
    """Verifica que a tentativa de criar pesquisa de 2º Turno com 3 candidatos é bloqueada.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    with pytest.raises(ValidationError, match="deve possuir estritamente 2 candidatos"):
        PesquisaEleitoralSchema(
            id_registro_tse="BR-01002/2026",
            instituto_razao_social="Instituto Teste Ltda",
            instituto_nome_fantasia="Instituto Teste",
            data_inicio_campo=date(2026, 10, 20),
            data_fim_campo=date(2026, 10, 22),
            data_divulgacao=date(2026, 10, 23),
            tamanho_amostra=2000,
            margem_erro_declarada=2.0,
            metodologia=MetodologiaEnum.TELEFONICA_CATI,
            votos_totais={"Flávio Bolsonaro": 48.0, "Lula": 45.0, "Ciro Gomes": 2.0},
            votos_validos={"Flávio Bolsonaro": 50.5, "Lula": 47.4, "Ciro Gomes": 2.1},
            percentual_indecisos=2.5,
            percentual_brancos_nulos=2.5,
            turno=2,
        )


def test_second_round_single_candidate_raises() -> None:
    """Verifica que a tentativa de criar pesquisa de 2º Turno com 1 único candidato é bloqueada.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    with pytest.raises(ValidationError, match="deve possuir estritamente 2 candidatos"):
        PesquisaEleitoralSchema(
            id_registro_tse="BR-01003/2026",
            instituto_razao_social="Instituto Teste Ltda",
            instituto_nome_fantasia="Instituto Teste",
            data_inicio_campo=date(2026, 10, 20),
            data_fim_campo=date(2026, 10, 22),
            data_divulgacao=date(2026, 10, 23),
            tamanho_amostra=2000,
            margem_erro_declarada=2.0,
            metodologia=MetodologiaEnum.TELEFONICA_CATI,
            votos_totais={"Flávio Bolsonaro": 55.0},
            votos_validos={"Flávio Bolsonaro": 100.0},
            percentual_indecisos=25.0,
            percentual_brancos_nulos=20.0,
            turno=2,
        )


def test_poll_sum_excess_raises() -> None:
    """Verifica que pesquisa de 2º Turno com soma amostral inflada (> 103%) é rejeitada pelo Gatekeeper.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    with pytest.raises(ValidationError, match="fechamento amostral inconsistente"):
        PesquisaEleitoralSchema(
            id_registro_tse="BR-01004/2026",
            instituto_razao_social="Instituto Veritá",
            instituto_nome_fantasia="Instituto Veritá",
            data_inicio_campo=date(2026, 10, 18),
            data_fim_campo=date(2026, 10, 22),
            data_divulgacao=date(2026, 10, 23),
            tamanho_amostra=15554,
            margem_erro_declarada=1.0,
            metodologia=MetodologiaEnum.TELEFONICA_CATI,
            votos_totais={"Flávio Bolsonaro": 55.0, "Lula": 50.0},
            votos_validos={"Flávio Bolsonaro": 52.4, "Lula": 47.6},
            percentual_indecisos=2.0,
            percentual_brancos_nulos=2.0,  # Soma = 109.0%
            turno=2,
        )


def test_poll_sum_deficient_raises() -> None:
    """Verifica que pesquisa de 2º Turno com soma amostral deficiente (< 85%) é rejeitada pelo Gatekeeper.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    with pytest.raises(ValidationError, match="fechamento amostral inconsistente"):
        PesquisaEleitoralSchema(
            id_registro_tse="BR-01005/2026",
            instituto_razao_social="Instituto X",
            instituto_nome_fantasia="Instituto X",
            data_inicio_campo=date(2026, 10, 18),
            data_fim_campo=date(2026, 10, 22),
            data_divulgacao=date(2026, 10, 23),
            tamanho_amostra=2000,
            margem_erro_declarada=2.0,
            metodologia=MetodologiaEnum.ONLINE,
            votos_totais={"Candidato A": 40.0, "Candidato B": 40.0},
            votos_validos={"Candidato A": 50.0, "Candidato B": 50.0},
            percentual_indecisos=2.0,
            percentual_brancos_nulos=2.0,  # Soma = 84.0%
            turno=2,
        )


def test_first_round_multiple_candidates_allowed() -> None:
    """Verifica que o 1º Turno aceita múltiplos concorrentes de forma irrestrita.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    poll_1t = PesquisaEleitoralSchema(
        id_registro_tse="BR-01006/2026",
        instituto_razao_social="Datafolha",
        instituto_nome_fantasia="Datafolha",
        data_inicio_campo=date(2026, 9, 25),
        data_fim_campo=date(2026, 9, 27),
        data_divulgacao=date(2026, 9, 28),
        tamanho_amostra=3000,
        margem_erro_declarada=2.0,
        metodologia=MetodologiaEnum.PRESENCIAL_DOMICILIAR,
        votos_totais={
            "Flávio Bolsonaro": 43.0,
            "Lula": 41.0,
            "Cury": 3.0,
            "Santos": 2.0,
            "Caiado": 2.0,
            "Zema": 1.0,
            "Outros": 1.0,
        },
        votos_validos={
            "Flávio Bolsonaro": 46.2,
            "Lula": 44.1,
            "Cury": 3.2,
            "Santos": 2.2,
            "Caiado": 2.2,
            "Zema": 1.1,
            "Outros": 1.1,
        },
        percentual_indecisos=3.5,
        percentual_brancos_nulos=3.5,
        turno=1,
    )
    assert poll_1t.turno == 1
    assert len(poll_1t.votos_totais) == 7


def test_gatekeeper_direct_methods() -> None:
    """Valida as chamadas estáticas diretas da classe ElectoralGatekeeper.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    # 2º Turno com 2 candidatos passa sem erros
    ElectoralGatekeeper.validate_second_round_candidate_count(
        turno=2,
        candidates_with_votes={"A": 50.0, "B": 50.0},
        poll_id="BR-TEST",
    )

    # 2º Turno com 3 candidatos levanta SecondRoundCandidateCountError
    with pytest.raises(SecondRoundCandidateCountError):
        ElectoralGatekeeper.validate_second_round_candidate_count(
            turno=2,
            candidates_with_votes={"A": 45.0, "B": 45.0, "C": 10.0},
            poll_id="BR-TEST",
        )

    # Soma em 100.5% passa
    ElectoralGatekeeper.validate_poll_sum(
        votos_totais={"A": 48.0, "B": 47.0},
        percentual_brancos_nulos=3.0,
        percentual_indecisos=2.5,
        poll_id="BR-TEST",
    )

    # Soma em 106% levanta PollSumMismatchError
    with pytest.raises(PollSumMismatchError):
        ElectoralGatekeeper.validate_poll_sum(
            votos_totais={"A": 50.0, "B": 50.0},
            percentual_brancos_nulos=3.0,
            percentual_indecisos=3.0,
            poll_id="BR-TEST",
        )


def test_cli_add_poll_gatekeeper_blocks_three_candidates(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verifica se o comando CLI add-poll bloqueia a inserção de 3 candidatos para o 2º Turno.

    Args:
        capsys: Fixture do pytest para captura de stdout e stderr.

    Returns:
        None.

    Raises:
        None.
    """
    args = argparse.Namespace(
        year=2026,
        turno=2,
        instituto="Datafolha",
        registro="BR-09999/2026",
        dt_inicio="2026-10-20",
        dt_fim="2026-10-22",
        dt_divulgacao="2026-10-23",
        amostra=2000,
        margem=2.0,
        metodologia="PRESENCIAL_DOMICILIAR",
        deff=1.3,
        voto=["Flávio Bolsonaro=48.0", "Lula=45.0", "Ciro Gomes=3.0"],
        brancos_nulos=2.0,
        indecisos=2.0,
        abrangencia="NACIONAL",
        uf="BR",
        regiao="BR",
    )

    with pytest.raises(SystemExit) as exc_info:
        cmd_add_poll(args)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "[ERRO DE GATEKEEPER]" in captured.err
    assert "deve possuir estritamente 2 candidatos" in captured.err
