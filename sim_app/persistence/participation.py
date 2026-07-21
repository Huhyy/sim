"""Final participation persistence workflow."""

from sim_app.infra.supabase import _require_client
from sim_app.infra.time import _utcnow
from sim_app.persistence.completed_accounts import account_has_completed
from sim_app.persistence.mappers import _demographic_answers, _float_or_none
from sim_app.persistence.results import save_month_results, save_psychometric_answers, save_session_summary
from sim_app.prolific.bonuses import process_prolific_bonus


def _active_resume_link_exists(client, account_key: str, session_id: str):
    response = (
        client
        .table("resume_links")
        .select("account_key")
        .eq("account_key", account_key)
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    return bool(getattr(response, "data", None) or [])


def _session_exists_for_finalization(client, session_id: str):
    response = (
        client
        .table("participant_sessions")
        .select("id,status")
        .eq("id", session_id)
        .limit(1)
        .execute()
    )
    data = getattr(response, "data", None) or []
    if not data:
        return False
    return data[0].get("status") != "completed"


def _repair_missing_resume_link(client, account_key: str, session_id: str):
    if not _session_exists_for_finalization(client, session_id):
        return False

    client.table("resume_links").upsert(
        {
            "account_key": account_key,
            "session_id": session_id,
            "updated_at": _utcnow(),
        }
    ).execute()
    return True


def finalize_participation(
    account_key: str,
    session_id: str,
    answers: dict,
    final_score: float,
    allow_repeat: bool = False,
    monthly_results=None,
    summary=None,
    pre_sections=None,
    post_sections=None,
):
    client = _require_client()
    if allow_repeat:
        client.table("completed_accounts").delete().eq("account_key", account_key).execute()

    summary = summary or {}
    prolific_mode = bool(summary.get("prolific_pid"))

    if not allow_repeat and not prolific_mode and account_has_completed(account_key):
        raise RuntimeError("This participant has already completed the study.")

    if not _active_resume_link_exists(client, account_key, session_id) and not _repair_missing_resume_link(client, account_key, session_id):
        raise RuntimeError("No active session is associated with this participant.")

    bonus_max_session = _float_or_none(summary.get("bonus_max_session")) or 12.0
    feedback = answers.get("feedback") or None
    metadata = {
        "study_session_id": summary.get("study_session_id"),
        "study_session_code": summary.get("study_session_code"),
        "participant_code": summary.get("participant_code"),
    }

    save_psychometric_answers(session_id, answers, pre_sections=pre_sections, post_sections=post_sections, metadata=metadata)
    save_month_results(session_id, monthly_results or [], bonus_max_session=bonus_max_session, metadata=metadata)
    response = save_session_summary(session_id, summary, feedback=feedback)

    client.table("participant_sessions").update(
        {
            "status": "completed",
            "current_page": "done",
            "completed_at": _utcnow(),
            "updated_at": _utcnow(),
            "checkpoint": {
                "page": "done",
                "scenario_version": summary.get("scenario_version"),
                "months_completed": summary.get("months_completed"),
                "final_score": summary.get("final_score"),
            },
            "demographics": _demographic_answers(answers),
            "participant_code": summary.get("participant_code"),
            "prolific_pid": summary.get("prolific_pid"),
            "prolific_study_id": summary.get("prolific_study_id"),
            "prolific_session_id": summary.get("prolific_session_id"),
            "prolific_finished_at": _utcnow() if summary.get("prolific_pid") else None,
            "prolific_completion_redirected_at": _utcnow() if summary.get("prolific_pid") else None,
            "completion_code": summary.get("completion_code"),
            "experimental_condition": summary.get("experimental_condition"),
            "score_frame": summary.get("score_frame"),
            "monthly_score_feedback": summary.get("monthly_score_feedback"),
        }
    ).eq("id", session_id).execute()

    client.table("completed_accounts").upsert(
        {
            "account_key": account_key,
            "completed_at": _utcnow(),
        }
    ).execute()

    client.table("resume_links").delete().eq("account_key", account_key).eq("session_id", session_id).execute()

    process_prolific_bonus(client, session_id, summary)

    return response


__all__ = [
    "_active_resume_link_exists",
    "_repair_missing_resume_link",
    "_session_exists_for_finalization",
    "finalize_participation",
]
