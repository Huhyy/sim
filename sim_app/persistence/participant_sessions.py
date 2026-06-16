"""Participant session checkpoint reads and writes."""

from sim_app.infra.supabase import _require_client
from sim_app.infra.time import _utcnow


def load_session_row(session_id: str):
    client = _require_client()

    response = (
        client
        .table("participant_sessions")
        .select("*")
        .eq("id", session_id)
        .limit(1)
        .execute()
    )
    data = getattr(response, "data", None) or []
    return data[0] if data else None


def load_session_checkpoint(session_id: str):
    row = load_session_row(session_id)
    if not row:
        return None

    checkpoint = row.get("checkpoint") or {}
    if row.get("current_page") and "page" not in checkpoint:
        checkpoint["page"] = row["current_page"]
    if row.get("study_session_id") and "study_session_id" not in checkpoint:
        checkpoint["study_session_id"] = row["study_session_id"]
    if row.get("study_session_code") and "study_session_code" not in checkpoint:
        checkpoint["study_session_code"] = row["study_session_code"]
    if row.get("participant_code") and "participant_code" not in checkpoint:
        checkpoint["participant_code"] = row["participant_code"]
    if row.get("experimental_condition") and "experimental_condition" not in checkpoint:
        checkpoint["experimental_condition"] = row["experimental_condition"]
    if row.get("score_frame") and "score_frame" not in checkpoint:
        checkpoint["score_frame"] = row["score_frame"]
    if row.get("monthly_score_feedback") and "monthly_score_feedback" not in checkpoint:
        checkpoint["monthly_score_feedback"] = row["monthly_score_feedback"]

    return checkpoint


def save_session_checkpoint(session_id: str, checkpoint: dict, status: str = "in_progress"):
    client = _require_client()

    row = {
        "id": session_id,
        "status": status,
        "current_page": checkpoint.get("page") or "home",
        "checkpoint": checkpoint,
        "updated_at": _utcnow(),
    }

    if checkpoint.get("study_session_id"):
        row["study_session_id"] = checkpoint.get("study_session_id")
    if checkpoint.get("study_session_code"):
        row["study_session_code"] = checkpoint.get("study_session_code")
    if checkpoint.get("participant_code"):
        row["participant_code"] = checkpoint.get("participant_code")
    if status == "completed":
        row["completed_at"] = _utcnow()

    client.table("participant_sessions").upsert(row).execute()


__all__ = [
    "load_session_checkpoint",
    "load_session_row",
    "save_session_checkpoint",
]
