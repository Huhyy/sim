"""Read-only compatibility access to legacy participant checkpoints."""

from sim_app.infra.supabase import _require_client


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
    final_page_saved = row.get("status") == "completed" or row.get("current_page") == "done" or checkpoint.get("page") == "done"
    if final_page_saved:
        checkpoint["page"] = "done"
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
            checkpoint["submission_finalized"] = True
            checkpoint["final_score"] = summary.get("final_score")
            checkpoint["final_score_breakdown"] = summary
            checkpoint["loan_balance"] = summary.get("remaining_credit", checkpoint.get("loan_balance", 7000.0))
            checkpoint["overdraft_balance"] = summary.get("remaining_overdraft", checkpoint.get("overdraft_balance", 0.0))

    return checkpoint

__all__ = [
    "load_session_checkpoint",
    "load_session_row",
]
