"""Authenticated participant session management."""

import streamlit as st

from sim_app.auth.identity import current_account_key
from sim_app.config import PROLIFIC_MODE_ENABLED, REPEAT_SCENARIO_DEV_MODE, SCENARIO_VERSION
from sim_app.persistence.completed_accounts import account_has_completed
from sim_app.persistence.participant_sessions import load_session_checkpoint
from sim_app.persistence.resume_links import load_linked_session_id, save_resume_link
from sim_app.prolific import (
    assign_prolific_condition,
    configured_completion_code,
    bind_prolific_session,
    completion_redirect_url,
    find_prolific_session,
    has_any_prolific_param,
    has_completed_prolific_session,
    load_prolific_params,
    prolific_params_complete,
)
from sim_app.prolific.identity import prolific_study_allowed
from sim_app.session.ids import new_session_id
from sim_app.session.query_params import clear_query_param, get_query_param, set_query_param
from sim_app.state.checkpoint import hydrate_from_checkpoint, persist_checkpoint
from sim_app.state.defaults import runtime_defaults
from sim_app.state.navigation import clear_payment_values, resolve_session_id


def reset_current_session_for_scenario_version():
    session_id = resolve_session_id()
    clear_payment_values()
    defaults = runtime_defaults()
    for key, value in defaults.items():
        if key not in ("session_id",):
            st.session_state[key] = value
    st.session_state.session_id = session_id
    persist_checkpoint()
    st.session_state.checkpoint_last_load = {
        "ok": False,
        "source": "supabase",
        "session_id": session_id,
        "reset_reason": "Experiment data changed; old checkpoint was reset.",
        "scenario_version": SCENARIO_VERSION,
    }


def ensure_current_scenario_version():
    current_version = st.session_state.get("scenario_version")
    if current_version == SCENARIO_VERSION:
        return
    reset_current_session_for_scenario_version()


def bootstrap_authenticated_session():
    account_key = current_account_key()
    if not account_key:
        raise RuntimeError("Authentication is required before starting the experiment.")

    prolific_params = load_prolific_params()
    prolific_mode = PROLIFIC_MODE_ENABLED and has_any_prolific_param(prolific_params)
    if prolific_mode and not prolific_params_complete(prolific_params):
        _prolific_access_error("prolific.error_missing_params")
        return
    if prolific_mode and not prolific_study_allowed(prolific_params["STUDY_ID"]):
        _prolific_access_error("prolific.error_invalid_study")
        return
    if prolific_mode and has_completed_prolific_session(prolific_params["PROLIFIC_PID"], prolific_params["STUDY_ID"]):
        _prolific_access_error("prolific.error_already_completed")
        return

    if not REPEAT_SCENARIO_DEV_MODE and not prolific_mode and account_has_completed(account_key):
        defaults = runtime_defaults()
        for key, value in defaults.items():
            st.session_state[key] = value
        st.session_state.page = "already_completed"
        st.session_state.already_completed = True
        clear_query_param("sid")
        return

    linked_session_id = load_linked_session_id(account_key)
    prolific_existing_session = (
        find_prolific_session(prolific_params["PROLIFIC_PID"], prolific_params["STUDY_ID"])
        if prolific_mode
        else None
    )
    url_session_id = get_query_param("sid")
    unsafe_url_session_id = bool(url_session_id and not linked_session_id)
    is_new_session = not linked_session_id and not prolific_existing_session

    if prolific_existing_session and prolific_existing_session.get("id"):
        session_id = prolific_existing_session["id"]
    elif linked_session_id:
        session_id = linked_session_id
    else:
        session_id = new_session_id()

    if get_query_param("sid") != session_id:
        set_query_param("sid", session_id)

    st.session_state.session_id = session_id
    st.session_state.checkpoint_last_load = {"ok": False, "source": "supabase", "session_id": session_id}

    try:
        checkpoint = load_session_checkpoint(session_id)
    except Exception as e:
        st.session_state.checkpoint_last_load = {
            "ok": False,
            "source": "supabase",
            "session_id": session_id,
            "error": str(e),
        }
        checkpoint = None

    checkpoint_reset = False
    if checkpoint and checkpoint.get("scenario_version") and checkpoint.get("scenario_version") != SCENARIO_VERSION:
        checkpoint = None
        checkpoint_reset = True

    if checkpoint:
        hydrate_from_checkpoint(checkpoint)
        st.session_state.session_id = session_id
        st.session_state.checkpoint_last_load = {
            "ok": True,
            "source": "supabase",
            "session_id": session_id,
            "page": checkpoint.get("page"),
            "month": checkpoint.get("month"),
        }
    else:
        defaults = runtime_defaults()
        clear_payment_values()
        for key, value in defaults.items():
            if key not in ("loan", "overdraft", "session_id"):
                st.session_state[key] = value
        st.session_state.session_id = session_id
        st.session_state.loan = defaults["loan"]
        st.session_state.overdraft = defaults["overdraft"]
        persist_checkpoint()
        if checkpoint_reset:
            st.session_state.checkpoint_last_load = {
                "ok": False,
                "source": "supabase",
                "session_id": session_id,
                "reset_reason": "Experiment data changed; old checkpoint was reset.",
                "scenario_version": SCENARIO_VERSION,
            }

    if prolific_mode:
        condition = assign_prolific_condition(prolific_params["PROLIFIC_PID"], prolific_params["STUDY_ID"])
        st.session_state.prolific_mode = True
        st.session_state.prolific_pid = prolific_params["PROLIFIC_PID"]
        st.session_state.prolific_study_id = prolific_params["STUDY_ID"]
        st.session_state.prolific_session_id = prolific_params["SESSION_ID"]
        st.session_state.prolific_completion_code = configured_completion_code()
        st.session_state.prolific_completion_url = completion_redirect_url(st.session_state.prolific_completion_code)
        st.session_state.experimental_condition = condition["experimental_condition"]
        st.session_state.score_frame = condition["score_frame"]
        st.session_state.monthly_score_feedback = condition["monthly_score_feedback"]
        if not checkpoint and st.session_state.get("page") == "home":
            st.session_state.page = "consent"
        bind_prolific_session(session_id, prolific_params, condition, account_key=account_key)
        persist_checkpoint()
        if not linked_session_id:
            save_resume_link(account_key, session_id)

    if is_new_session:
        save_resume_link(account_key, session_id)
        if unsafe_url_session_id:
            st.session_state.checkpoint_last_load = {
                "ok": False,
                "source": "supabase",
                "session_id": session_id,
                "ignored_url_session_id": url_session_id,
                "reset_reason": "URL session id was not linked to this account, so a fresh session was created.",
            }


def _prolific_access_error(message_key):
    defaults = runtime_defaults()
    for key, value in defaults.items():
        st.session_state[key] = value
    st.session_state.prolific_mode = True
    st.session_state.prolific_access_error = message_key
    st.session_state.page = "prolific_error"
    clear_query_param("sid")


def start_new_scenario():
    if not REPEAT_SCENARIO_DEV_MODE:
        raise RuntimeError("Repeat participation is disabled.")

    account_key = current_account_key()
    if not account_key:
        raise RuntimeError("Authentication is required before starting a new experiment.")

    current_study_session_id = st.session_state.get("study_session_id")
    current_study_session_code = st.session_state.get("study_session_code")
    current_participant_code = st.session_state.get("participant_code")
    current_experimental_condition = st.session_state.get("experimental_condition")
    current_score_frame = st.session_state.get("score_frame")
    current_monthly_score_feedback = st.session_state.get("monthly_score_feedback")
    defaults = runtime_defaults()
    clear_payment_values()
    for key, value in defaults.items():
        st.session_state[key] = value
    st.session_state.study_session_id = current_study_session_id
    st.session_state.study_session_code = current_study_session_code
    st.session_state.participant_code = current_participant_code
    st.session_state.experimental_condition = current_experimental_condition
    st.session_state.score_frame = current_score_frame
    st.session_state.monthly_score_feedback = current_monthly_score_feedback

    session_id = new_session_id()
    st.session_state.session_id = session_id
    set_query_param("sid", session_id)
    persist_checkpoint()
    save_resume_link(account_key, session_id)


__all__ = [
    "bootstrap_authenticated_session",
    "ensure_current_scenario_version",
    "reset_current_session_for_scenario_version",
    "start_new_scenario",
]
