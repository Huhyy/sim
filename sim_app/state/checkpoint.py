"""Checkpoint collection, hydration, and persistence."""

import streamlit as st

from sim_app.application.state import ParticipantState
from sim_app.config import SCENARIO_VERSION
from sim_app.session.query_params import set_query_param
from sim_app.session.service_provider import get_experiment_service
from sim_app.session.streamlit_service import retained_request_id
from sim_app.session.streamlit_state import apply_participant_state
from sim_app.state.defaults import runtime_defaults
from sim_app.state.navigation import clear_payment_values, resolve_session_id


def collect_checkpoint():
    """Collect the reduced, non-authoritative Phase 3 resume projection."""
    return ParticipantState.from_runtime_state(
        st.session_state,
        SCENARIO_VERSION,
    ).to_resume_projection()


def persist_checkpoint(status=None):
    if st.session_state.get("submission_finalized") or st.session_state.get("already_completed"):
        return True

    session_id = resolve_session_id()
    if not session_id:
        st.session_state.checkpoint_last_save = {
            "ok": False,
            "error": "Missing session_id",
        }
        raise RuntimeError("Missing session_id")

    if status == "completed":
        raise RuntimeError("Completion must use ExperimentService.finalize, not checkpoint persistence")

    state = ParticipantState.from_runtime_state(st.session_state, SCENARIO_VERSION)
    checkpoint = state.to_resume_projection()
    resolved_status = status or "in_progress"
    request_id = retained_request_id(
        st.session_state,
        "legacy_checkpoint_adapter",
        {
            "session_id": session_id,
            "expected_version": state.state_version,
            "projection": checkpoint,
        },
    )

    try:
        committed = get_experiment_service().save_stage(
            state,
            expected_version=state.state_version,
            request_id=request_id,
        )
        apply_participant_state(st.session_state, committed.state)
        st.session_state.checkpoint_last_save = {
            "ok": True,
            "session_id": session_id,
            "status": resolved_status,
            "page": checkpoint.get("page"),
            "month": committed.state.month,
            "state_version": committed.state.state_version,
        }
        st.session_state.checkpoint_last_error = None
        return True
    except Exception as e:
        st.session_state.checkpoint_last_save = {
            "ok": False,
            "session_id": session_id,
            "status": resolved_status,
            "page": checkpoint.get("page"),
            "month": checkpoint.get("month"),
            "error": str(e),
        }
        st.session_state.checkpoint_last_error = str(e)
        raise


def hydrate_from_checkpoint(checkpoint):
    defaults = runtime_defaults()
    clear_payment_values()
    for key, value in defaults.items():
        if key not in ("loan", "overdraft", "session_id"):
            st.session_state[key] = value

    state = ParticipantState.from_checkpoint(checkpoint, SCENARIO_VERSION)
    # Legacy hydration left the runtime default in place rather than copying a
    # checkpoint's scenario version into Streamlit session state.
    state.scenario_version = SCENARIO_VERSION
    state.apply_to_runtime_state(st.session_state, include_session_id=False)
    if st.session_state.prolific_mode:
        for parameter_name, parameter_value in {
            "PROLIFIC_PID": st.session_state.prolific_pid,
            "STUDY_ID": st.session_state.prolific_study_id,
            "SESSION_ID": st.session_state.prolific_session_id,
        }.items():
            if parameter_value:
                set_query_param(parameter_name, parameter_value)


__all__ = [
    "collect_checkpoint",
    "hydrate_from_checkpoint",
    "persist_checkpoint",
]
