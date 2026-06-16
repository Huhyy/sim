"""UI context object for legacy-compatible page rendering."""

from types import SimpleNamespace


def make_ui_context(**kwargs):
    return SimpleNamespace(**kwargs)


__all__ = [
    "make_ui_context",
]

