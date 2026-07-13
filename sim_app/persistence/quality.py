"""Quality-check persistence."""

import streamlit as st

from sim_app.infra.supabase import _require_client
from sim_app.infra.time import _utcnow
from sim_app.state.navigation import resolve_session_id


def save_quality_check(check_type, check_id, attempt_number=1, passed=False, response_value=None, response_time_ms=None, page_id=None):
    session_id = resolve_session_id()
    if not session_id:
        return False
    row = {
        "app_session_id": session_id,
        "prolific_pid": st.session_state.get("prolific_pid"),
        "study_id": st.session_state.get("prolific_study_id"),
        "session_id": st.session_state.get("prolific_session_id"),
        "check_type": check_type,
        "check_id": check_id,
        "attempt_number": int(attempt_number or 1),
        "passed": bool(passed),
        "response_value": None if response_value is None else str(response_value),
        "response_time_ms": response_time_ms,
        "page_id": page_id,
        "created_at": _utcnow(),
    }
    try:
        _require_client().table("quality_checks").insert(row).execute()
        return True
    except Exception as e:
        st.session_state.quality_check_last_error = str(e)
        return False


__all__ = [
    "save_quality_check",
]
