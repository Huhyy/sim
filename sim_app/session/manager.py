"""Authenticated participant session management."""

import streamlit as st

from sim_app.auth.identity import current_account_key
from sim_app.config import REPEAT_SCENARIO_DEV_MODE, SCENARIO_VERSION
from sim_app.persistence.completed_accounts import account_has_completed
from sim_app.persistence.participant_sessions import load_session_checkpoint
from sim_app.persistence.resume_links import load_linked_session_id, save_resume_link
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

    if not REPEAT_SCENARIO_DEV_MODE and account_has_completed(account_key):
        defaults = runtime_defaults()
        for key, value in defaults.items():
            st.session_state[key] = value
        st.session_state.page = "already_completed"
        st.session_state.already_completed = True
        clear_query_param("sid")
        return

    linked_session_id = load_linked_session_id(account_key)
    url_session_id = get_query_param("sid")
    unsafe_url_session_id = bool(url_session_id and not linked_session_id)
    is_new_session = not linked_session_id

    if linked_session_id:
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


def start_new_scenario():
    if not REPEAT_SCENARIO_DEV_MODE:
        raise RuntimeError("Repeat participation is disabled.")

    account_key = current_account_key()
    if not account_key:
        raise RuntimeError("Authentication is required before starting a new experiment.")

    current_study_session_id = st.session_state.get("study_session_id")
    current_study_session_code = st.session_state.get("study_session_code")
    current_participant_code = st.session_state.get("participant_code")
    defaults = runtime_defaults()
    clear_payment_values()
    for key, value in defaults.items():
        st.session_state[key] = value
    st.session_state.study_session_id = current_study_session_id
    st.session_state.study_session_code = current_study_session_code
    st.session_state.participant_code = current_participant_code

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
