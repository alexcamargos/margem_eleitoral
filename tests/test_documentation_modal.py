"""Testes unitários para o componente de modal de documentação e metodologia."""

from pytest_mock import MockerFixture

from src.presentation.components.documentation_modal import render_documentation_content


def test_render_documentation_content(mocker: MockerFixture) -> None:
    """Verifica se a função do modal renderiza as duas abas e o conteúdo markdown/latex.

    Args:
        mocker: Fixture do pytest-mock.

    Returns:
        None.

    Raises:
        None.
    """
    mock_tab1 = mocker.MagicMock()
    mock_tab2 = mocker.MagicMock()
    mocker.patch("streamlit.tabs", return_value=[mock_tab1, mock_tab2])
    mock_md = mocker.patch("streamlit.markdown")
    mock_latex = mocker.patch("streamlit.latex")

    render_documentation_content()

    assert mock_md.called
    assert mock_latex.called

    # Verifica se os termos principais estão presentes nas chamadas de markdown
    all_markdown_texts = [call[0][0] for call in mock_md.call_args_list if call[0]]
    combined_md = " ".join(all_markdown_texts)

    assert "Propósito e Missão do Projeto" in combined_md
    assert "Pesquisa é Fotografia, Não Previsão do Futuro" in combined_md
    assert "A Regra de Ouro dos Votos Válidos" in combined_md
    assert "Fundamentação Estatística e Modelagem Matemática" in combined_md
    assert "Efeito de Delineamento" in combined_md
    assert "Mosteller" in combined_md
    assert "Erro Ponderado" in combined_md
