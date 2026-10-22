"""Componentes visuais reutilizáveis em Plotly e diálogos de interface."""

from src.presentation.components.documentation_modal import render_documentation_modal
from src.presentation.components.executive_story_cards import (
    render_candidate_avatar,
    render_executive_story_cards,
)
from src.presentation.components.institute_temporal_chart import create_institute_temporal_chart
from src.presentation.components.phase_story_chart import create_phases_comparison_chart
from src.presentation.components.polls_list_modal import (
    render_polls_list_content,
    render_polls_modal,
)

__all__ = [
    "create_institute_temporal_chart",
    "create_phases_comparison_chart",
    "render_candidate_avatar",
    "render_documentation_modal",
    "render_executive_story_cards",
    "render_polls_list_content",
    "render_polls_modal",
]
