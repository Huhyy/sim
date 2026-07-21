"""Result and answer persistence."""

from sim_app.infra.supabase import _require_client
from sim_app.infra.time import _utcnow
from sim_app.persistence.mappers import _float_or_none, _month_result_row, _psychometric_rows


def save_psychometric_answers(session_id: str, answers: dict, pre_sections=None, post_sections=None, metadata=None):
    client = _require_client()
    pre_rows = _psychometric_rows(session_id, answers, pre_sections, metadata=metadata)
    post_rows = _psychometric_rows(session_id, answers, post_sections, metadata=metadata)

    if pre_rows:
        client.table("psychometric_pre_answers").upsert(
            pre_rows,
            on_conflict="session_id,question_key",
        ).execute()

    if post_rows:
        client.table("psychometric_post_answers").upsert(
            post_rows,
            on_conflict="session_id,question_key",
        ).execute()


def save_month_result(session_id: str, result: dict, bonus_max_session: float = 12.0, metadata=None):
    client = _require_client()
    row = _month_result_row(session_id, result, bonus_max_session=bonus_max_session, metadata=metadata)
    client.table("month_results").upsert(
        row,
        on_conflict="session_id,month_number",
    ).execute()


def save_month_results(session_id: str, monthly_results, bonus_max_session: float = 12.0, metadata=None):
    client = _require_client()
    rows = [
        _month_result_row(session_id, result, bonus_max_session=bonus_max_session, metadata=metadata)
        for result in (monthly_results or [])
        if result.get("month")
    ]
    if rows:
        client.table("month_results").upsert(
            rows,
            on_conflict="session_id,month_number",
        ).execute()


def save_session_summary(session_id: str, summary: dict, feedback=None):
    client = _require_client()
    row = {
        "session_id": session_id,
        "months_completed": int(summary.get("months_completed", 0)),
        "monthly_score_sum": _float_or_none(summary.get("monthly_score_sum")),
        "final_score": _float_or_none(summary.get("final_score")),
        "bonus_max_session": _float_or_none(summary.get("bonus_max_session")),
        "bonus_final": _float_or_none(summary.get("bonus_final")),
        "experimental_condition": summary.get("experimental_condition"),
        "score_frame": summary.get("score_frame"),
        "monthly_score_feedback": summary.get("monthly_score_feedback"),
        "performance_bonus_gbp": float(summary.get("performance_bonus_gbp", 0)),
        "loss_amount_gbp": float(summary.get("loss_amount_gbp", 0)),
        "prolific_base_reward_gbp": float(summary.get("prolific_base_reward_gbp", 5)),
        "total_payout_gbp": float(summary.get("total_payout_gbp", 5) or 5),
        "prolific_bonus_status": summary.get("prolific_bonus_status") or (
            "pending" if summary.get("prolific_pid") and summary.get("prolific_session_id") else "not_applicable"
        ),
        "prolific_bonus_payment_id": summary.get("prolific_bonus_payment_id"),
        "prolific_bonus_created_at": summary.get("prolific_bonus_created_at"),
        "prolific_bonus_paid_at": summary.get("prolific_bonus_paid_at"),
        "prolific_bonus_error": summary.get("prolific_bonus_error"),
        "completion_timestamp": summary.get("completion_timestamp") or _utcnow(),
        "payment_status": summary.get("payment_status") or "unpaid",
        "total_repaid": _float_or_none(summary.get("total_repaid")),
        "remaining_credit": _float_or_none(summary.get("remaining_credit")),
        "remaining_overdraft": _float_or_none(summary.get("remaining_overdraft")),
        "credit_interest_total": _float_or_none(summary.get("credit_interest_total")),
        "overdraft_interest_total": _float_or_none(summary.get("overdraft_interest_total")),
        "interest_total": _float_or_none(summary.get("interest_total")),
        "feedback": feedback,
        "updated_at": _utcnow(),
    }
    if summary.get("study_session_id"):
        row["study_session_id"] = summary.get("study_session_id")
    if summary.get("study_session_code"):
        row["study_session_code"] = summary.get("study_session_code")
    if summary.get("participant_code"):
        row["participant_code"] = summary.get("participant_code")
    if summary.get("prolific_pid"):
        row["prolific_pid"] = summary.get("prolific_pid")
    if summary.get("prolific_study_id"):
        row["prolific_study_id"] = summary.get("prolific_study_id")
    if summary.get("prolific_session_id"):
        row["prolific_session_id"] = summary.get("prolific_session_id")
    if summary.get("completion_code"):
        row["completion_code"] = summary.get("completion_code")
    return client.table("session_summaries").upsert(row, on_conflict="session_id").execute()


__all__ = [
    "save_month_result",
    "save_month_results",
    "save_psychometric_answers",
    "save_session_summary",
]
