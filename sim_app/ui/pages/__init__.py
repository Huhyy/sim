"""Streamlit page renderers."""

from .router import STATIC_PAGE_RENDERERS, get_page_renderer, render_current_page


__all__ = [
    "STATIC_PAGE_RENDERERS",
    "get_page_renderer",
    "render_current_page",
]
