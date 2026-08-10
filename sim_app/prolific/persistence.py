"""Supabase persistence helpers for Prolific sessions."""

from sim_app.infra.supabase import _require_client


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

__all__ = [
    "find_prolific_session",
    "has_completed_prolific_session",
]
