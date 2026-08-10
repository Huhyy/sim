"""Thin Streamlit transport adapter over ExperimentService."""

from __future__ import annotations

import hashlib
import json
import uuid

from sim_app.application.commands import go_to_page
from sim_app.application.errors import ConcurrencyConflict, ExperimentError
from sim_app.session.streamlit_state import apply_participant_state, read_participant_state


def retained_request_id(runtime_state, operation, payload):
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    storage_key = f"_request_id_{operation}_{digest[:20]}"
    existing = runtime_state.get(storage_key)
    if existing:
        return existing
    request_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"credit-simulator:{operation}:{digest}"))
    runtime_state[storage_key] = request_id
    return request_id


def commit_command(st, service, command, *, operation="stage_transition", rerun=True):
    return commit_state(st, service, command.state, operation=operation, rerun=rerun)


def commit_state(st, service, proposed_state, *, operation, rerun=True):
    current = read_participant_state(st.session_state)
    request_id = retained_request_id(
        st.session_state,
        operation,
        {
            "session_id": current.session_id,
            "expected_version": current.state_version,
            "page": proposed_state.page,
            "projection": proposed_state.to_resume_projection(),
            "treatment": proposed_state.experimental_condition,
        },
    )
    try:
        committed = service.save_stage(
            proposed_state,
            expected_version=current.state_version,
            request_id=request_id,
        )
    except ConcurrencyConflict:
        _restore_authoritative(st, service, current.session_id)
        st.warning("Your session changed in another tab. The latest committed state was restored.")
        st.stop()
    except ExperimentError as exc:
        st.error(f"The change was not saved. Please retry. ({exc})")
        st.stop()
    apply_participant_state(st.session_state, committed.state)
    if rerun:
        st.rerun()
    return committed.state


def commit_quality_state(st, service, proposed_state, quality_events, *, operation, rerun=True):
    current = read_participant_state(st.session_state)
    request_id = retained_request_id(
        st.session_state,
        operation,
        {
            "session_id": current.session_id,
            "expected_version": current.state_version,
            "events": quality_events,
            "projection": proposed_state.to_resume_projection(),
        },
    )
    try:
        committed = service.save_quality_transition(
            proposed_state,
            quality_events,
            expected_version=current.state_version,
            request_id=request_id,
        )
    except ConcurrencyConflict:
        _restore_authoritative(st, service, current.session_id)
        st.warning("Quality-check state changed in another tab. The latest committed state was restored.")
        st.stop()
    except ExperimentError as exc:
        st.error(f"The quality check was not saved, so progression was stopped. ({exc})")
        st.stop()
    apply_participant_state(st.session_state, committed.state)
    if rerun:
        st.rerun()
    return committed.state


def navigate_committed(st, service, page):
    command = go_to_page(read_participant_state(st.session_state), page)
    return commit_command(st, service, command, operation=f"navigate:{page}")


def submit_month_decision(st, service, *, payment, translate=None):
    current = read_participant_state(st.session_state)
    request_id = retained_request_id(
        st.session_state,
        f"month_decision:{current.month}",
        {
            "session_id": current.session_id,
            "expected_version": current.state_version,
            "month": current.month,
            "payment": payment,
        },
    )
    try:
        committed = service.submit_month_decision(
            session_id=current.session_id,
            expected_version=current.state_version,
            expected_month=current.month,
            payment=payment,
            request_id=request_id,
            translate=translate,
        )
    except ConcurrencyConflict:
        _restore_authoritative(st, service, current.session_id)
        st.warning("This decision was already handled or the session changed in another tab.")
        st.stop()
    except ExperimentError as exc:
        st.error(f"The decision was not committed. No progress was recorded. ({exc})")
        st.stop()
    apply_participant_state(st.session_state, committed.state)
    st.rerun()


def acknowledge_month_feedback(st, service):
    current = read_participant_state(st.session_state)
    request_id = retained_request_id(
        st.session_state,
        f"feedback_ack:{current.month}",
        {
            "session_id": current.session_id,
            "expected_version": current.state_version,
            "month": current.month,
        },
    )
    try:
        committed = service.acknowledge_month_feedback(
            session_id=current.session_id,
            expected_version=current.state_version,
            expected_month=current.month,
            request_id=request_id,
        )
    except ConcurrencyConflict:
        _restore_authoritative(st, service, current.session_id)
        st.warning("Feedback was already acknowledged in another tab. The latest state was restored.")
        st.stop()
    except ExperimentError as exc:
        st.error(f"Progress could not be saved. The month was not advanced. ({exc})")
        st.stop()
    apply_participant_state(st.session_state, committed.state)
    st.rerun()


def finalize_experiment(st, service, *, account_key, pre_sections, post_sections):
    current = read_participant_state(st.session_state)
    request_id = retained_request_id(
        st.session_state,
        "finalize",
        {
            "session_id": current.session_id,
            "expected_version": current.state_version,
            "months": len(current.monthly_results),
        },
    )
    try:
        committed = service.finalize(
            session_id=current.session_id,
            expected_version=current.state_version,
            request_id=request_id,
            account_key=account_key,
            pre_sections=pre_sections,
            post_sections=post_sections,
        )
    except ConcurrencyConflict:
        restored = _restore_authoritative(st, service, current.session_id)
        if restored.submission_finalized:
            return restored
        st.warning("Finalization changed in another tab. The latest state was restored.")
        st.stop()
    except ExperimentError as exc:
        st.error(f"Completion processing did not finish. It is safe to retry; committed progress will be restored. ({exc})")
        st.stop()
    apply_participant_state(st.session_state, committed.state)
    return committed.state


def _restore_authoritative(st, service, session_id):
    state = service.load_session(session_id)
    apply_participant_state(st.session_state, state)
    return state


__all__ = [
    "acknowledge_month_feedback",
    "commit_command",
    "commit_quality_state",
    "commit_state",
    "finalize_experiment",
    "navigate_committed",
    "retained_request_id",
    "submit_month_decision",
]
