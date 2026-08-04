"""Secret lookup helpers."""

import os

import streamlit as st


def _get_secret(name: str):
    try:
        value = st.secrets.get(name)
        if value:
            return value
        for section_name in ("prolific", "auth"):
            section = st.secrets.get(section_name)
            if section:
                value = section.get(name)
                if value:
                    return value
    except Exception:
        pass
    return os.getenv(name)


def _first_secret(*names):
    for name in names:
        value = _get_secret(name)
        if value:
            return value
    return None


__all__ = [
    "_first_secret",
    "_get_secret",
]
