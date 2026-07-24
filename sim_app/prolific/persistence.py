"""Supabase persistence helpers for Prolific sessions."""

from sim_app.infra.supabase import _require_client
from sim_app.infra.time import _utcnow


def find_prolific_session(prolific_pid, study_id):
    client = _require_client()
    response = (
        client
        .table("participant_sessions")
        .select("*")
        .eq("prolific_pid", str(prolific_pid))
        .eq("prolific_study_id", str(study_id))
        .limit(1)
        .execute()
    )
    data = getattr(response, "data", None) or []
    return data[0] if data else None


def has_completed_prolific_session(prolific_pid, study_id):
    row = find_prolific_session(prolific_pid, study_id)
    # A completed status without a completion code is recoverable. This can
    # happen when the final database write succeeds only partially or the
    # browser is refreshed before the Prolific completion step finishes.
    return bool(row and row.get("status") == "completed" and row.get("completion_code"))


def reopen_unconfirmed_prolific_session(session_id):
    client = _require_client()
    row = {
        "status": "in_progress",
        "completed_at": None,
        "updated_at": _utcnow(),
    }
    client.table("participant_sessions").update(row).eq("id", session_id).execute()
    return row


def bind_prolific_session(session_id, params, condition, account_key=None):
    client = _require_client()
    existing = find_prolific_session(params["PROLIFIC_PID"], params["STUDY_ID"])
    duplicate_entry = bool(existing and existing.get("id") != session_id and existing.get("status") != "completed")
    row = {
        "id": session_id,
        "prolific_pid": params["PROLIFIC_PID"],
        "prolific_study_id": params["STUDY_ID"],
        "prolific_session_id": params["SESSION_ID"],
        "prolific_account_key": account_key,
        "duplicate_entry": duplicate_entry,
        "missing_prolific_params": False,
        "experimental_condition": condition["experimental_condition"],
        "score_frame": condition["score_frame"],
        "monthly_score_feedback": condition["monthly_score_feedback"],
        "updated_at": _utcnow(),
    }
    client.table("participant_sessions").upsert(row).execute()
    return {**row, "existing": existing}


def mark_prolific_completed(session_id, completion_code=None):
    client = _require_client()
    row = {
        "prolific_finished_at": _utcnow(),
        "completion_code": completion_code,
        "updated_at": _utcnow(),
    }
    client.table("participant_sessions").update(row).eq("id", session_id).execute()
    return row


__all__ = [
    "bind_prolific_session",
    "find_prolific_session",
    "has_completed_prolific_session",
    "mark_prolific_completed",
    "reopen_unconfirmed_prolific_session",
]
