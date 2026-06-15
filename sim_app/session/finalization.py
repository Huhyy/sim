"""Participant finalization service."""

import streamlit as st

from sim_app.auth.identity import current_account_key
from sim_app.config import REPEAT_SCENARIO_DEV_MODE
from sim_app.persistence.participation import finalize_participation as db_finalize_participation
from sim_app.session.query_params import clear_query_param
from sim_app.state.navigation import resolve_session_id


def finalize_participant(
    session_id,
    answers,
    final_score,
    monthly_results=None,
    summary=None,
    pre_sections=None,
    post_sections=None,
):
    resolved_session_id = session_id or resolve_session_id()
    if not resolved_session_id:
        raise ValueError("Missing session_id")

    account_key = current_account_key()
    if not account_key:
        raise ValueError("Missing authenticated account")

    try:
        response = db_finalize_participation(
            account_key,
            resolved_session_id,
            answers,
            final_score,
            allow_repeat=REPEAT_SCENARIO_DEV_MODE,
            monthly_results=monthly_results,
            summary=summary,
            pre_sections=pre_sections,
            post_sections=post_sections,
        )
    except TypeError as e:
        if "unexpected keyword argument" not in str(e):
            raise
        response = db_finalize_participation(
            account_key,
            resolved_session_id,
            answers,
            final_score,
            allow_repeat=REPEAT_SCENARIO_DEV_MODE,
        )
    st.session_state.submission_finalized = True
    clear_query_param("sid")
    return response


__all__ = [
    "finalize_participant",
]
