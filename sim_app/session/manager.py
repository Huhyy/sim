"""Authenticated Streamlit bootstrap over authoritative ExperimentService."""

import uuid

import streamlit as st

from sim_app.application.errors import PersistenceReadError, SessionNotFound, TreatmentConflict
from sim_app.application.state import ParticipantState
from sim_app.auth.identity import current_account_key
from sim_app.config import PROLIFIC_MODE_ENABLED, REPEAT_SCENARIO_DEV_MODE, SCENARIO_VERSION
from sim_app.persistence.completed_accounts import account_has_completed
from sim_app.persistence.resume_links import load_linked_session_id
from sim_app.prolific import (
    assign_prolific_condition,
    completion_redirect_url,
    configured_completion_code,
    find_prolific_session,
    has_any_prolific_param,
    load_prolific_params,
    prolific_params_complete,
)
from sim_app.prolific.identity import prolific_study_allowed
from sim_app.session.ids import new_session_id
from sim_app.session.query_params import clear_query_param, get_query_param, set_query_param
from sim_app.session.service_provider import get_experiment_service
from sim_app.session.streamlit_state import apply_participant_state, read_participant_state
from sim_app.state.defaults import runtime_defaults
from sim_app.state.navigation import clear_payment_values, resolve_session_id


def reset_current_session_for_scenario_version():
    # A changed economic scenario must never overwrite an existing durable
    # ledger. A fresh attempt is the only safe reset path.
    if not REPEAT_SCENARIO_DEV_MODE:
        raise RuntimeError("The experiment scenario changed; this session requires controlled migration.")
    start_new_scenario()


def ensure_current_scenario_version():
    current_version = st.session_state.get("scenario_version")
    if current_version != SCENARIO_VERSION:
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

    # These reads deliberately propagate failures. Uncertain database state is
    # never converted into a new/default participant.
    prolific_existing_session = _safe_read(
        "Prolific participant lookup",
        lambda: find_prolific_session(prolific_params["PROLIFIC_PID"], prolific_params["STUDY_ID"]),
    ) if prolific_mode else None
    same_prolific_attempt = bool(
        prolific_existing_session
        and prolific_existing_session.get("prolific_session_id") == prolific_params["SESSION_ID"]
    )
    if (
        prolific_mode
        and prolific_existing_session
        and prolific_existing_session.get("status") == "completed"
        and not same_prolific_attempt
    ):
        _prolific_access_error("prolific.error_already_completed")
        return

    completed = (
        _safe_read("completed-account lookup", lambda: account_has_completed(account_key))
        if not REPEAT_SCENARIO_DEV_MODE and not prolific_mode
        else False
    )
    if completed:
        defaults = runtime_defaults()
        for key, value in defaults.items():
            st.session_state[key] = value
        st.session_state.page = "already_completed"
        st.session_state.already_completed = True
        clear_query_param("sid")
        return

    linked_session_id = _safe_read("resume-link lookup", lambda: load_linked_session_id(account_key))
    url_session_id = get_query_param("sid")
    unsafe_url_session_id = bool(url_session_id and not linked_session_id)
    if prolific_existing_session and prolific_existing_session.get("id"):
        session_id = prolific_existing_session["id"]
    elif linked_session_id:
        session_id = linked_session_id
    else:
        session_id = new_session_id()

    service = get_experiment_service()
    st.session_state.checkpoint_last_load = {"ok": False, "source": "supabase", "session_id": session_id}
    try:
        state = service.find_session(session_id)
    except Exception as exc:
        st.session_state.checkpoint_last_load = {
            "ok": False,
            "source": "supabase",
            "session_id": session_id,
            "error": str(exc),
        }
        if isinstance(exc, PersistenceReadError):
            raise
        raise PersistenceReadError(f"Participant bootstrap read failed: {exc}") from exc

    known_session = bool(linked_session_id or prolific_existing_session)
    if state is None and known_session:
        raise SessionNotFound("A linked participant session is missing; bootstrap was stopped without creating defaults.")

    if state is None:
        state = ParticipantState.initial(SCENARIO_VERSION)
        state.session_id = session_id
        if prolific_mode:
            _apply_prolific_launch(state, prolific_params)
        created = service.create_session(
            state,
            account_key=account_key,
            request_id=_bootstrap_request_id(account_key, session_id),
        )
        state = created.state
    elif state.scenario_version != SCENARIO_VERSION:
        raise RuntimeError("The durable session uses a different scenario version and requires controlled migration.")

    if prolific_mode:
        expected = assign_prolific_condition(prolific_params["PROLIFIC_PID"], prolific_params["STUDY_ID"])
        if state.treatment_bound and (
            state.experimental_condition != expected["experimental_condition"]
            or state.score_frame != expected["score_frame"]
            or state.monthly_score_feedback != expected["monthly_score_feedback"]
        ):
            raise TreatmentConflict("Durable Prolific treatment does not match deterministic assignment")
        if not state.submission_finalized:
            proposed = state.copy()
            _apply_prolific_launch(proposed, prolific_params)
            committed = service.save_stage(
                proposed,
                expected_version=state.state_version,
                request_id=_bootstrap_request_id(account_key, session_id, suffix="prolific-bind"),
            )
            state = committed.state
        for parameter_name, parameter_value in prolific_params.items():
            if parameter_value and get_query_param(parameter_name) != parameter_value:
                set_query_param(parameter_name, parameter_value)

    clear_payment_values()
    apply_participant_state(st.session_state, state)
    st.session_state.session_id = state.session_id
    st.session_state.checkpoint_last_load = {
        "ok": True,
        "source": "supabase",
        "session_id": state.session_id,
        "page": state.page,
        "month": state.month,
        "state_version": state.state_version,
    }
    if get_query_param("sid") != state.session_id:
        set_query_param("sid", state.session_id)
    if unsafe_url_session_id:
        st.session_state.checkpoint_last_load["ignored_url_session_id"] = url_session_id


def _apply_prolific_launch(state, params):
    condition = assign_prolific_condition(params["PROLIFIC_PID"], params["STUDY_ID"])
    state.prolific_mode = True
    state.prolific_pid = params["PROLIFIC_PID"]
    state.prolific_study_id = params["STUDY_ID"]
    state.prolific_session_id = params["SESSION_ID"]
    state.prolific_completion_code = configured_completion_code()
    state.prolific_completion_url = completion_redirect_url(state.prolific_completion_code)
    state.experimental_condition = condition["experimental_condition"]
    state.score_frame = condition["score_frame"]
    state.monthly_score_feedback = condition["monthly_score_feedback"]
    state.treatment_bound = True
    if state.page == "home":
        state.page = "consent"


def _bootstrap_request_id(account_key, session_id, suffix="create"):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"credit-simulator:{suffix}:{account_key}:{session_id}"))


def _safe_read(label, operation):
    try:
        return operation()
    except Exception as exc:
        raise PersistenceReadError(f"{label} failed; no participant state was initialized: {exc}") from exc


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

    current = read_participant_state(st.session_state)
    state = ParticipantState.initial(SCENARIO_VERSION)
    state.session_id = new_session_id()
    state.study_session_id = current.study_session_id
    state.study_session_code = current.study_session_code
    state.participant_code = current.participant_code
    state.experimental_condition = current.experimental_condition
    state.score_frame = current.score_frame
    state.monthly_score_feedback = current.monthly_score_feedback
    state.treatment_bound = current.treatment_bound
    created = get_experiment_service().create_session(
        state,
        account_key=account_key,
        request_id=_bootstrap_request_id(account_key, state.session_id, suffix="repeat"),
    )
    clear_payment_values()
    apply_participant_state(st.session_state, created.state)
    set_query_param("sid", created.state.session_id)


__all__ = [
    "bootstrap_authenticated_session",
    "ensure_current_scenario_version",
    "reset_current_session_for_scenario_version",
    "start_new_scenario",
]
