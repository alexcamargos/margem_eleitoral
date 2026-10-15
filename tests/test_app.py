"""Testes unitários para o módulo principal da aplicação Streamlit (app.py)."""

from pytest_mock import MockerFixture

from src.presentation.app import apply_custom_css, init_session_state, main, run


def test_init_session_state(mocker: MockerFixture) -> None:
    """Verifica se o estado de sessão é inicializado corretamente.

    Args:
        mocker: Fixture do pytest-mock.

    Returns:
        None.

    Raises:
        None.
    """
    mock_state = {}
    mocker.patch("streamlit.session_state", mock_state)
    init_session_state()
    assert "polls_synced_r2" in mock_state
    assert mock_state["polls_synced_r2"] is False


def test_apply_custom_css(mocker: MockerFixture) -> None:
    """Verifica a aplicação de estilos CSS no Streamlit.

    Args:
        mocker: Fixture do pytest-mock.

    Returns:
        None.

    Raises:
        None.
    """
    mock_md = mocker.patch("streamlit.markdown")
    apply_custom_css()
    assert mock_md.called
    assert "stApp" in mock_md.call_args[0][0]


def test_main_render_flow(mocker: MockerFixture) -> None:
    """Verifica o fluxo completo de renderização da aplicação principal.

    Args:
        mocker: Fixture do pytest-mock.

    Returns:
        None.

    Raises:
        None.
    """
    mocker.patch("streamlit.set_page_config")
    mocker.patch("streamlit.session_state", {"polls_synced_r2": True})
    mocker.patch("streamlit.sidebar.markdown")
    mocker.patch("streamlit.sidebar.selectbox", return_value=2026)
    mocker.patch("streamlit.sidebar.radio", return_value="1º Turno (Consolidado)")
    mocker.patch("streamlit.sidebar.button", return_value=False)
    mocker.patch("streamlit.button", return_value=False)
    mocker.patch("streamlit.markdown")
    mocker.patch("src.presentation.app.render_documentation_modal")
    mock_tabs = [mocker.MagicMock() for _ in range(5)]
    mocker.patch("streamlit.tabs", return_value=mock_tabs)

    mocker.patch("src.presentation.app.render_act1")
    mocker.patch("src.presentation.app.render_act2")
    mocker.patch("src.presentation.app.render_act3")
    mocker.patch("src.presentation.app.render_act4")
    mocker.patch("src.presentation.app.render_act5")

    main()


def test_main_sync_button_clicked(mocker: MockerFixture) -> None:
    """Verifica a reação ao clique no botão de sincronização oficial do TSE.

    Args:
        mocker: Fixture do pytest-mock.

    Returns:
        None.

    Raises:
        None.
    """
    mocker.patch("streamlit.set_page_config")
    mocker.patch("streamlit.session_state", {})
    mocker.patch("streamlit.sidebar.markdown")
    mocker.patch("streamlit.sidebar.selectbox", return_value=2026)
    mocker.patch("streamlit.sidebar.radio", return_value="2º Turno (Contínuo)")
    mocker.patch(
        "streamlit.sidebar.button",
        side_effect=lambda label, **kwargs: "Sincronizar" in label,
    )
    mocker.patch("streamlit.button", return_value=False)
    mocker.patch("streamlit.markdown")
    mocker.patch("src.presentation.app.render_documentation_modal")
    mocker.patch(
        "streamlit.tabs",
        side_effect=lambda tabs_list: [mocker.MagicMock() for _ in tabs_list],
    )
    mocker.patch("streamlit.spinner")
    mocker.patch("streamlit.success")
    mocker.patch("streamlit.rerun")

    mocker.patch("src.presentation.app.render_act1")
    mocker.patch("src.presentation.app.render_act2")
    mocker.patch("src.presentation.app.render_act3")
    mocker.patch("src.presentation.app.render_act4")
    mocker.patch("src.presentation.app.render_act5")

    mock_sync = mocker.patch(
        "src.ingestion.pesqele_collector.PesqEleCollector.sync_official_second_round_polls",
        return_value=[],
    )

    main()
    assert mock_sync.called


def test_run(mocker: MockerFixture) -> None:
    """Verifica se a função run configura os argumentos e invoca a CLI do Streamlit.

    Args:
        mocker: Fixture do pytest-mock.

    Returns:
        None.

    Raises:
        None.
    """
    mock_exit = mocker.patch("sys.exit")
    mock_stcli = mocker.patch("streamlit.web.cli.main", return_value=0)
    mocker.patch("sys.argv", ["app", "--server.port", "8502"])

    run()

    mock_stcli.assert_called_once()
    call_args = mock_stcli.call_args[1].get("args")
    assert call_args[0] == "run"
    assert "app.py" in call_args[1]
    assert call_args[2:] == ["--server.port", "8502"]
    mock_exit.assert_called_once_with(0)


def test_root_main_script(mocker: MockerFixture) -> None:
    """Verifica se o ponto de entrada principal main.py invoca run.

    Args:
        mocker: Fixture do pytest-mock.

    Returns:
        None.

    Raises:
        None.
    """
    mock_run = mocker.patch("src.presentation.app.run")
    import main as root_main

    root_main.main()
    mock_run.assert_called_once()
