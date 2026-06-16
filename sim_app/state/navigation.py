"""Session-state navigation helpers."""

import streamlit as st

from sim_app.session.query_params import get_query_param


def clear_payment_values():
    for key in list(st.session_state.keys()):
        if key.startswith("payment_"):
            del st.session_state[key]


def resolve_session_id():
    session_id = st.session_state.get("session_id")
    if session_id:
        return session_id

    candidates = [
        get_query_param("sid"),
        (st.session_state.get("checkpoint_last_load") or {}).get("session_id"),
        (st.session_state.get("checkpoint_last_save") or {}).get("session_id"),
    ]
    for candidate in candidates:
        if candidate:
            st.session_state.session_id = candidate
            return candidate

    return None


__all__ = [
    "clear_payment_values",
    "resolve_session_id",
]
