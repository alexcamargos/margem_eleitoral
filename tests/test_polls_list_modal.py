"""Testes unitários para o componente de modal e listagem de pesquisas eleitorais."""

from datetime import date

from pytest_mock import MockerFixture

from src.presentation.components.polls_list_modal import (
    _build_poll_card_html,
    _compute_poll_weights,
    _format_field_period_pt,
    _format_site_since,
    _load_extra_feed_metadata,
    render_polls_list_content,
    render_polls_modal,
)
from src.transformations.schemas import MetodologiaEnum, PesquisaEleitoralSchema


def create_sample_poll_t2() -> PesquisaEleitoralSchema:
    """Cria uma instância de exemplo de pesquisa para o 2º Turno.

    Args:
        None.

    Returns:
        PesquisaEleitoralSchema: Instância válida de pesquisa.

    Raises:
        None.
    """
    return PesquisaEleitoralSchema(
        id_registro_tse="BR-04612/2026",
        instituto_razao_social="PALVER PESQUISAS LTDA",
        instituto_nome_fantasia="Palver",
        data_inicio_campo=date(2026, 10, 16),
        data_fim_campo=date(2026, 10, 20),
        data_divulgacao=date(2026, 10, 21),
        tamanho_amostra=5000,
        margem_erro_declarada=2.4,
        nivel_confianca=0.95,
        metodologia=MetodologiaEnum.ONLINE,
        deff_estimado=1.35,
        votos_totais={"Lula": 48.0, "Flávio Bolsonaro": 50.0},
        votos_validos={"Lula": 48.98, "Flávio Bolsonaro": 51.02},
        percentual_indecisos=0.0,
        percentual_brancos_nulos=1.0,
        rejeicao=None,
        turno=2,
        cargo="PRESIDENTE",
        ano=2026,
        url_fonte_publicacao="https://exame.com/palver",
        url_tse_pesqele="https://pesqele.tse.jus.br/detalhes",
    )


def create_sample_poll_t1() -> PesquisaEleitoralSchema:
    """Cria uma instância de exemplo de pesquisa para o 1º Turno com múltiplos candidatos.

    Args:
        None.

    Returns:
        PesquisaEleitoralSchema: Instância válida de pesquisa.

    Raises:
        None.
    """
    return PesquisaEleitoralSchema(
        id_registro_tse="BR-01234/2026",
        instituto_razao_social="DATAFOLHA INSTITUTO LTDA",
        instituto_nome_fantasia="Datafolha",
        data_inicio_campo=date(2026, 9, 28),
        data_fim_campo=date(2026, 10, 1),
        data_divulgacao=date(2026, 10, 2),
        tamanho_amostra=2500,
        margem_erro_declarada=2.0,
        nivel_confianca=0.95,
        metodologia=MetodologiaEnum.PRESENCIAL_DOMICILIAR,
        deff_estimado=1.3,
        votos_totais={"Lula": 44.0, "Bolsonaro": 40.0, "Simone Tebet": 4.0, "Ciro Gomes": 3.0},
        votos_validos={"Lula": 48.4, "Bolsonaro": 43.2, "Simone Tebet": 4.4, "Ciro Gomes": 3.3},
        percentual_indecisos=5.0,
        percentual_brancos_nulos=4.0,
        rejeicao={"Lula": 45.0, "Bolsonaro": 48.0},
        turno=1,
        cargo="PRESIDENTE",
        ano=2026,
        url_fonte_publicacao="https://folha.uol.com.br/datafolha",
        url_tse_pesqele="https://pesqele.tse.jus.br/detalhes-t1",
    )


def test_format_field_period_pt() -> None:
    """Testa a formatação em português do intervalo de datas de campo.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    # Mesmo mês
    s1 = _format_field_period_pt(date(2026, 10, 16), date(2026, 10, 20))
    assert s1 == "campo de 16 a 20 de outubro"

    # Meses diferentes
    s2 = _format_field_period_pt(date(2026, 9, 29), date(2026, 10, 3))
    assert s2 == "campo de 29 de setembro a 3 de outubro"

    # Mesmo dia
    s3 = _format_field_period_pt(date(2026, 10, 20), date(2026, 10, 20))
    assert s3 == "campo em 20 de outubro"


def test_format_site_since() -> None:
    """Testa a formatação da data/hora de publicação ou inclusão no agregador.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    # Com ISO contendo timezone
    s1 = _format_site_since("2026-10-21T07:00:35-03:00", date(2026, 10, 21))
    assert s1 == "No site desde 21/10 às 07h00"

    # Sem ISO (fallback para data_divulgacao)
    s2 = _format_site_since(None, date(2026, 10, 21))
    assert s2 == "Divulgada em 21/10"


def test_load_extra_feed_metadata() -> None:
    """Verifica o carregamento seguro dos metadados extras do feed.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    data = _load_extra_feed_metadata(2026)
    assert isinstance(data, dict)
    assert "pesquisas_by_tse" in data
    assert "vies_by_inst" in data
    assert "fator_vies" in data


def test_compute_poll_weights_normalization() -> None:
    """Verifica se os pesos relativos das pesquisas somam 100%.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    p1 = create_sample_poll_t2()
    p2 = create_sample_poll_t1()

    weights = _compute_poll_weights([p1, p2])
    assert len(weights) == 2
    assert abs(sum(weights.values()) - 100.0) < 1e-4
    assert weights[p1.id_registro_tse] > 0.0
    assert weights[p2.id_registro_tse] > 0.0


def test_compute_poll_weights_empty() -> None:
    """Verifica comportamento com lista vazia de pesquisas.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    weights = _compute_poll_weights([])
    assert weights == {}


def test_build_poll_card_html_t2() -> None:
    """Valida a estrutura HTML do cartão para pesquisa de 2º Turno.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    p = create_sample_poll_t2()
    extra_feed = {
        "pesquisas_by_tse": {
            "BR-04612/2026": {
                "adicionada_em": "2026-10-21T07:00:35-03:00",
                "urls": "https://exame.com/palver",
            }
        },
        "vies_by_inst": {"Palver": -0.012107},
        "fator_vies": 0.5,
    }

    html = _build_poll_card_html(poll=p, weight_pct=7.0, extra_feed_data=extra_feed, turno_num=2)

    assert "Palver" in html
    assert "campo de 16 a 20 de outubro" in html
    assert "No site desde 21/10 às 07h00" in html
    assert "5.000" in html
    assert "BR-04612/2026" in html
    assert "48.98" in html or "49.0%" in html
    assert "51.02" in html or "51.0%" in html
    assert "Peso" in html
    assert "7%" in html
    assert "<details" in html
    assert "<summary" in html
    assert "Todos os detalhes" in html
    assert "Correção de viés" in html
    assert "+0.6 p.p." in html
    assert "online" in html


def test_build_poll_card_html_t1() -> None:
    """Valida a estrutura HTML do cartão para pesquisa de 1º Turno (múltiplos candidatos).

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    p = create_sample_poll_t1()
    html = _build_poll_card_html(poll=p, weight_pct=10.0, extra_feed_data={}, turno_num=1)

    assert "Datafolha" in html
    assert "2.500" in html
    assert "BR-01234/2026" in html
    assert "Lula" in html
    assert "Bolsonaro" in html
    assert "<details" in html
    assert "presencial domiciliar" in html


def test_render_polls_list_content(mocker: MockerFixture) -> None:
    """Verifica a renderização da lista completa via Streamlit.

    Args:
        mocker: Fixture do pytest-mock.

    Returns:
        None.

    Raises:
        None.
    """
    mock_md = mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.text_input", return_value="")
    mocker.patch("streamlit.selectbox", return_value="Mais recentes (fim de campo)")

    polls = [create_sample_poll_t2(), create_sample_poll_t1()]
    render_polls_list_content(polls=polls, ano_eleicao=2026, turno_num=2)

    assert mock_md.called
    all_texts = " ".join([call[0][0] for call in mock_md.call_args_list if call[0]])
    assert "Só entram pesquisas nacionais" in all_texts
    assert "Palver" in all_texts


def test_render_polls_list_content_empty(mocker: MockerFixture) -> None:
    """Verifica aviso de nenhuma pesquisa quando lista estiver vazia.

    Args:
        mocker: Fixture do pytest-mock.

    Returns:
        None.

    Raises:
        None.
    """
    mocker.patch("streamlit.markdown")
    mock_info = mocker.patch("streamlit.info")

    render_polls_list_content(polls=[], ano_eleicao=2026, turno_num=2)

    assert mock_info.called


def test_render_polls_modal(mocker: MockerFixture) -> None:
    """Verifica a invocação da função interna do modal de pesquisas.

    Args:
        mocker: Fixture do pytest-mock.

    Returns:
        None.

    Raises:
        None.
    """
    mock_content = mocker.patch(
        "src.presentation.components.polls_list_modal.render_polls_list_content"
    )
    polls = [create_sample_poll_t2()]

    # Invoca a função desempacotada do decorator st.dialog para teste fora de runtime Streamlit
    func = getattr(render_polls_modal, "__wrapped__", render_polls_modal)
    func(polls=polls, ano_eleicao=2026, turno_num=2)

    mock_content.assert_called_once_with(
        polls=polls,
        ano_eleicao=2026,
        turno_num=2,
        cargo="Presidente da República",
    )
