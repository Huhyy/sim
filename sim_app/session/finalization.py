"""Legacy Streamlit entry point over the authoritative ExperimentService."""

import hashlib
import json
import uuid
import streamlit as st

from sim_app.auth.identity import current_account_key
from sim_app.session.query_params import clear_query_param
from sim_app.session.service_provider import get_experiment_service
from sim_app.session.streamlit_state import apply_participant_state
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

    service = get_experiment_service()
    state = service.load_session(resolved_session_id)
    if monthly_results is not None and list(monthly_results) != state.monthly_results:
        raise ValueError("Finalization month history must match the durable structured ledger")
    if final_score is not None and state.final_score is not None and round(float(final_score), 2) != round(float(state.final_score), 2):
        raise ValueError("Finalization score must match the durable participant state")

    if dict(answers or {}) != state.answers:
        proposed = state.copy()
        proposed.answers = dict(answers or {})
        saved = service.save_stage(
            proposed,
            expected_version=state.state_version,
            request_id=_request_id("legacy-finalization-state", resolved_session_id, state.state_version, proposed.answers),
        )
        state = saved.state

    result = service.finalize(
        session_id=resolved_session_id,
        expected_version=state.state_version,
        request_id=_request_id("legacy-finalization", resolved_session_id, state.state_version, summary or {}),
        account_key=account_key,
        pre_sections=pre_sections or [],
        post_sections=post_sections or [],
    )
    apply_participant_state(st.session_state, result.state)
    clear_query_param("sid")
    return result


def _request_id(operation, session_id, version, payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"credit-simulator:{operation}:{session_id}:{version}:{digest}"))


__all__ = [
    "finalize_participant",
]
