"""Componentes visuais reutilizáveis em Plotly e diálogos de interface."""

from src.presentation.components.documentation_modal import render_documentation_modal
from src.presentation.components.institute_temporal_chart import create_institute_temporal_chart
from src.presentation.components.phase_story_chart import create_phases_comparison_chart

__all__ = [
    "create_institute_temporal_chart",
    "create_phases_comparison_chart",
    "render_documentation_modal",
]
