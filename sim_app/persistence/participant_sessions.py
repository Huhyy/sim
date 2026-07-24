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
    if row.get("prolific_pid") and "prolific_pid" not in checkpoint:
        checkpoint["prolific_pid"] = row["prolific_pid"]
    if row.get("prolific_study_id") and "prolific_study_id" not in checkpoint:
        checkpoint["prolific_study_id"] = row["prolific_study_id"]
    if row.get("prolific_session_id") and "prolific_session_id" not in checkpoint:
        checkpoint["prolific_session_id"] = row["prolific_session_id"]
    if row.get("prolific_pid") and "prolific_mode" not in checkpoint:
        checkpoint["prolific_mode"] = True
    if row.get("experimental_condition") and "experimental_condition" not in checkpoint:
        checkpoint["experimental_condition"] = row["experimental_condition"]
    if row.get("score_frame") and "score_frame" not in checkpoint:
        checkpoint["score_frame"] = row["score_frame"]
    if row.get("monthly_score_feedback") and "monthly_score_feedback" not in checkpoint:
        checkpoint["monthly_score_feedback"] = row["monthly_score_feedback"]
    if row.get("status") == "completed":
        checkpoint["page"] = "done"
        checkpoint["submission_finalized"] = True
        summary_response = (
            _require_client()
            .table("session_summaries")
            .select("*")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        summaries = getattr(summary_response, "data", None) or []
        if summaries:
            summary = summaries[0]
            checkpoint["final_score"] = summary.get("final_score")
            checkpoint["final_score_breakdown"] = summary
            checkpoint["loan_balance"] = summary.get("remaining_credit", checkpoint.get("loan_balance", 7000.0))
            checkpoint["overdraft_balance"] = summary.get("remaining_overdraft", checkpoint.get("overdraft_balance", 0.0))

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
    if checkpoint.get("prolific_pid"):
        row["prolific_pid"] = checkpoint.get("prolific_pid")
    if checkpoint.get("prolific_study_id"):
        row["prolific_study_id"] = checkpoint.get("prolific_study_id")
    if checkpoint.get("prolific_session_id"):
        row["prolific_session_id"] = checkpoint.get("prolific_session_id")
    if checkpoint.get("prolific_mode"):
        row["missing_prolific_params"] = False
    if checkpoint.get("comprehension_attempts") is not None:
        row["comprehension_attempts"] = int(checkpoint.get("comprehension_attempts") or 0)
    if checkpoint.get("comprehension_passed") is not None:
        row["comprehension_passed"] = bool(checkpoint.get("comprehension_passed"))
    if checkpoint.get("attention_failed_count") is not None:
        row["attention_failed_count"] = int(checkpoint.get("attention_failed_count") or 0)
    if checkpoint.get("answers", {}).get("anti_ai_declaration") is True:
        row["anti_ai_declaration"] = True
        row["anti_ai_declared_at"] = _utcnow()
    if checkpoint.get("experimental_condition"):
        row["experimental_condition"] = checkpoint.get("experimental_condition")
    if checkpoint.get("score_frame"):
        row["score_frame"] = checkpoint.get("score_frame")
    if checkpoint.get("monthly_score_feedback"):
        row["monthly_score_feedback"] = checkpoint.get("monthly_score_feedback")
    if status == "completed":
        row["completed_at"] = _utcnow()

    client.table("participant_sessions").upsert(row).execute()


__all__ = [
    "load_session_checkpoint",
    "load_session_row",
    "save_session_checkpoint",
]
