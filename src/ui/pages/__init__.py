"""
UI Pages module for Streamlit multi-page navigation.

Provides page components for:
- Graph Explorer: Interactive knowledge graph visualization
"""

from src.ui.pages.graph_explorer import (
    PAGE_ICON,
    PAGE_TITLE,
)
from src.ui.pages.graph_explorer import (
    main as graph_explorer_main,
)
from src.ui.pages.graph_explorer import (
    render_page as render_graph_explorer,
)

__all__ = [
    "PAGE_ICON",
    "PAGE_TITLE",
    "graph_explorer_main",
    "render_graph_explorer",
]
