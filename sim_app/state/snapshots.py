"""Incremental persistence snapshots."""

import streamlit as st

from sim_app.persistence.results import save_month_result, save_psychometric_answers, save_session_summary
from sim_app.state.navigation import resolve_session_id


def persist_month_result_snapshot(result, bonus_max_session=12.0):
    session_id = resolve_session_id()
    if not session_id:
        return False

    try:
        save_month_result(session_id, result, bonus_max_session=bonus_max_session)
        st.session_state.month_snapshot_last_save = {
            "ok": True,
            "session_id": session_id,
            "month": result.get("month"),
        }
        return True
    except Exception as e:
        st.session_state.month_snapshot_last_save = {
            "ok": False,
            "session_id": session_id,
            "month": result.get("month"),
            "error": str(e),
        }
        return False


def persist_psychometric_answers_snapshot(answers, pre_sections=None, post_sections=None):
    session_id = resolve_session_id()
    if not session_id:
        return False

    try:
        save_psychometric_answers(
            session_id,
            answers,
            pre_sections=pre_sections,
            post_sections=post_sections,
        )
        st.session_state.psychometric_snapshot_last_save = {
            "ok": True,
            "session_id": session_id,
        }
        return True
    except Exception as e:
        st.session_state.psychometric_snapshot_last_save = {
            "ok": False,
            "session_id": session_id,
            "error": str(e),
        }
        return False


def persist_session_summary_snapshot(summary, feedback=None):
    session_id = resolve_session_id()
    if not session_id:
        return False

    try:
        save_session_summary(session_id, summary, feedback=feedback)
        st.session_state.summary_snapshot_last_save = {
            "ok": True,
            "session_id": session_id,
        }
        return True
    except Exception as e:
        st.session_state.summary_snapshot_last_save = {
            "ok": False,
            "session_id": session_id,
            "error": str(e),
        }
        return False


__all__ = [
    "persist_month_result_snapshot",
    "persist_psychometric_answers_snapshot",
    "persist_session_summary_snapshot",
]
