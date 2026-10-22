"""Testes unitários para o componente visual de Storytelling Executivo."""

from datetime import date

import pytest

from src.ingestion.data_loader import get_election_dataset, get_election_date
from src.presentation.components.executive_story_cards import (
    compute_executive_snapshot,
    get_candidate_metadata,
    render_avatar_svg,
    render_candidate_avatar,
    render_executive_story_cards,
    render_gauge_svg,
)


def test_get_candidate_metadata_known() -> None:
    """Valida a recuperação de metadados para candidatos conhecidos do catálogo."""
    meta_lula = get_candidate_metadata("Lula")
    assert meta_lula["name"] == "Lula"
    assert meta_lula["party"] == "PT"
    assert meta_lula["color"] == "#EF4444"
    assert meta_lula["initials"] == "LU"
    assert "divulgacandcontas.tse.jus.br" in str(meta_lula.get("foto_url"))

    meta_flavio = get_candidate_metadata("Flávio Bolsonaro")
    assert meta_flavio["name"] == "Flávio Bolsonaro"
    assert meta_flavio["party"] == "PL"
    assert meta_flavio["color"] == "#3B82F6"
    assert meta_flavio["initials"] == "FB"
    assert "divulgacandcontas.tse.jus.br" in str(meta_flavio.get("foto_url"))


def test_get_candidate_metadata_unknown() -> None:
    """Valida a geração de metadados de contingência para candidatos não mapeados."""
    meta_custom = get_candidate_metadata("Candidato Independente")
    assert meta_custom["name"] == "Candidato Independente"
    assert meta_custom["party"] == "IND"
    assert meta_custom["color"] == "#38BDF8"
    assert meta_custom["initials"] == "CI"
    assert meta_custom.get("foto_url") is None


def test_render_candidate_avatar_with_photo() -> None:
    """Verifica a renderização do avatar híbrido com a foto oficial do DivulgaCand e fallback."""
    meta = get_candidate_metadata("Lula")
    avatar_html = render_candidate_avatar(meta, size=46)

    assert "<img" in avatar_html
    assert 'src="https://divulgacandcontas.tse.jus.br' in avatar_html
    assert "onerror=" in avatar_html
    assert "border-radius: 50%" in avatar_html
    assert meta["color"] in avatar_html
    assert "<svg" in avatar_html  # Fallback embutido no span


def test_render_candidate_avatar_without_photo() -> None:
    """Verifica que candidatos sem foto registrada renderizam diretamente o avatar vetorial."""
    meta = get_candidate_metadata("Candidato Independente")
    avatar_html = render_candidate_avatar(meta, size=46)

    assert "<img" not in avatar_html
    assert "<svg" in avatar_html
    assert "CI" in avatar_html


def test_render_avatar_svg() -> None:
    """Verifica a renderização do SVG de avatar estilizado."""
    meta = get_candidate_metadata("Lula")
    svg = render_avatar_svg(meta, size=44)

    assert "<svg" in svg
    assert 'viewBox="0 0 44 44"' in svg
    assert meta["color"] in svg
    assert "LU" in svg


def test_render_gauge_svg() -> None:
    """Verifica a renderização do arco semicircular (gauge) do modelo preditivo."""
    meta1 = get_candidate_metadata("Lula")
    meta2 = get_candidate_metadata("Flávio Bolsonaro")
    gauge_svg = render_gauge_svg(
        p_c1=42.2,
        p_c2=57.8,
        meta_c1=meta1,
        meta_c2=meta2,
        leader_prob=58.0,
    )

    assert "<svg" in gauge_svg
    assert 'viewBox="0 0 160 92"' in gauge_svg
    assert "58%" in gauge_svg
    assert meta1["color"] in gauge_svg
    assert meta2["color"] in gauge_svg


def test_compute_executive_snapshot_empty() -> None:
    """Verifica que lista vazia de pesquisas retorna snapshot vazio com segurança."""
    res = compute_executive_snapshot(
        polls=[],
        multiscope_polls=[],
        election_date=date(2026, 10, 25),
        turno_num=1,
        ano_eleicao=2026,
    )
    assert res == {}


def test_compute_executive_snapshot_2026_t1() -> None:
    """Valida o cálculo do snapshot executivo para o 1º Turno de 2026."""
    tse_res, _, all_polls = get_election_dataset(year=2026, turno=1)
    _, _, multiscope = get_election_dataset(year=2026, turno=1, include_subnational=True)
    dt = get_election_date(year=2026, turno=1)

    snapshot = compute_executive_snapshot(
        polls=all_polls,
        multiscope_polls=multiscope,
        election_date=dt,
        turno_num=1,
        ano_eleicao=2026,
        use_valid_votes=True,
    )

    assert snapshot != {}
    assert "headline" in snapshot
    assert "subheadline" in snapshot
    assert snapshot["v1"] > 0.0
    assert snapshot["v2"] > 0.0
    assert snapshot["diff_pp"] >= 0.0
    assert isinstance(snapshot["is_empate"], bool)
    assert snapshot["total_polls"] == len(all_polls)
    assert snapshot["p_win_1"] + snapshot["p_win_2"] > 50.0
    assert snapshot["n_simulations"] == 10000


def test_compute_executive_snapshot_2026_t2_with_calibration() -> None:
    """Valida o cálculo do snapshot executivo no 2º Turno com calibração pós-1º Turno."""
    tse_res, _, all_polls = get_election_dataset(year=2026, turno=2)
    _, _, multiscope = get_election_dataset(year=2026, turno=2, include_subnational=True)
    dt = get_election_date(year=2026, turno=2)

    t1_tse, _, t1_p = get_election_dataset(year=2026, turno=1, include_subnational=True)
    t1_dt = get_election_date(year=2026, turno=1)

    snapshot = compute_executive_snapshot(
        polls=all_polls,
        multiscope_polls=multiscope,
        election_date=dt,
        turno_num=2,
        ano_eleicao=2026,
        use_valid_votes=True,
        t1_polls=t1_p,
        t1_tse_result=t1_tse,
        t1_election_date=t1_dt,
    )

    assert snapshot != {}
    assert snapshot["calibrado_t1"] is True
    assert "1º turno:" in snapshot["t1_info"]
    assert snapshot["leader_pred_prob"] >= snapshot["runner_pred_prob"]


def test_compute_executive_snapshot_total_votes_mode() -> None:
    """Valida o cálculo do snapshot executivo com base em votos totais (com indecisos)."""
    _, _, all_polls = get_election_dataset(year=2026, turno=2)
    _, _, multiscope = get_election_dataset(year=2026, turno=2, include_subnational=True)
    dt = get_election_date(year=2026, turno=2)

    snap_valid = compute_executive_snapshot(
        polls=all_polls,
        multiscope_polls=multiscope,
        election_date=dt,
        turno_num=2,
        ano_eleicao=2026,
        use_valid_votes=True,
    )
    snap_total = compute_executive_snapshot(
        polls=all_polls,
        multiscope_polls=multiscope,
        election_date=dt,
        turno_num=2,
        ano_eleicao=2026,
        use_valid_votes=False,
    )

    assert snap_valid["v1"] != snap_total["v1"]
    assert snap_total["use_valid_votes"] is False


def test_render_executive_story_cards_renders_without_error(mocker: pytest.MonkeyPatch) -> None:
    """Verifica que a função de renderização executa os comandos do Streamlit sem erro."""
    tse_res, _, all_polls = get_election_dataset(year=2026, turno=1)
    _, _, multiscope = get_election_dataset(year=2026, turno=1, include_subnational=True)
    dt = get_election_date(year=2026, turno=1)

    # Executa sem exceções
    render_executive_story_cards(
        polls=all_polls,
        multiscope_polls=multiscope,
        election_date=dt,
        turno_num=1,
        ano_eleicao=2026,
        tse_result=tse_res,
    )
