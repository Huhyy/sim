import os
import secrets
import uuid
from datetime import datetime, timezone

import streamlit as st
from supabase import create_client



def _get_secret(name: str):
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name)



def _first_secret(*names):
    for name in names:
        value = _get_secret(name)
        if value:
            return value
    return None



def _build_client(url: str, key: str):
    return create_client(url, key)



def get_client():
    url = _first_secret("SUPABASE_URL", "SUPABASE_PROJECT_URL")
    key = _first_secret("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY")
    if not url or not key:
        return None
    if str(key).startswith("sb_publishable_"):
        raise RuntimeError("Use a Supabase secret key for server-side study storage, not a publishable key.")
    return _build_client(url, key)



def _require_client():
    client = get_client()
    if client is None:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SECRET_KEY (or SUPABASE_SERVICE_ROLE_KEY / SUPABASE_KEY)."
        )
    return client



def _parse(value):
    if value is None:
        return None
    try:
        return int(str(value).split(" - ")[0].strip())
    except Exception:
        return None



def _float_or_none(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value):
    if value is None:
        return None
    return bool(value)


def _demographic_answers(answers: dict):
    return {
        key: value
        for key, value in answers.items()
        if key.startswith("demo_") or key == "consent_agreed"
    }



def _utcnow():
    return datetime.now(timezone.utc).isoformat()



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

    if status == "completed":
        row["completed_at"] = _utcnow()

    client.table("participant_sessions").upsert(row).execute()


def account_has_completed(account_key: str):
    client = _require_client()
    response = (
        client
        .table("completed_accounts")
        .select("account_key")
        .eq("account_key", account_key)
        .limit(1)
        .execute()
    )
    return bool(getattr(response, "data", None) or [])


def load_linked_session_id(account_key: str):
    client = _require_client()
    response = (
        client
        .table("resume_links")
        .select("session_id")
        .eq("account_key", account_key)
        .limit(1)
        .execute()
    )
    data = getattr(response, "data", None) or []
    return data[0]["session_id"] if data else None


def save_resume_link(account_key: str, session_id: str):
    client = _require_client()
    row = {
        "account_key": account_key,
        "session_id": session_id,
        "updated_at": _utcnow(),
    }
    client.table("resume_links").upsert(row).execute()


def create_admin_study_session(created_by_email: str):
    client = _require_client()
    email = str(created_by_email).strip().lower()

    for _ in range(25):
        session_code = f"{secrets.randbelow(1_000_000):06d}"
        existing = load_admin_study_session_by_code(session_code, require_active=False)
        if existing:
            continue

        row = {
            "id": str(uuid.uuid4()),
            "session_code": session_code,
            "created_by_email": email,
            "status": "active",
            "created_at": _utcnow(),
            "updated_at": _utcnow(),
        }
        client.table("admin_study_sessions").insert(row).execute()
        return row

    raise RuntimeError("Could not generate a unique 6-digit session code. Please try again.")


def load_admin_study_session_by_code(session_code: str, require_active: bool = True):
    client = _require_client()
    query = (
        client
        .table("admin_study_sessions")
        .select("*")
        .eq("session_code", str(session_code).strip())
        .limit(1)
    )
    if require_active:
        query = query.eq("status", "active")
    response = query.execute()
    data = getattr(response, "data", None) or []
    return data[0] if data else None


def list_admin_study_sessions(created_by_email: str, only_active: bool = True, limit: int = 10):
    client = _require_client()
    query = (
        client
        .table("admin_study_sessions")
        .select("*")
        .eq("created_by_email", str(created_by_email).strip().lower())
        .limit(limit)
        .order("created_at", desc=True)
    )
    if only_active:
        query = query.eq("status", "active")
    response = query.execute()
    return getattr(response, "data", None) or []


def cancel_admin_study_session(session_id: str, created_by_email: str):
    client = _require_client()
    email = str(created_by_email).strip().lower()
    response = (
        client
        .table("admin_study_sessions")
        .update(
            {
                "status": "cancelled",
                "updated_at": _utcnow(),
            }
        )
        .eq("id", str(session_id))
        .eq("created_by_email", email)
        .eq("status", "active")
        .execute()
    )
    data = getattr(response, "data", None) or []
    return data[0] if data else None


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


def _psychometric_rows(session_id: str, answers: dict, sections):
    rows = []
    question_number = 1
    now = _utcnow()

    for section_number, section in enumerate(sections or [], start=1):
        prefix = section.get("key_prefix")
        for index, question_text in enumerate(section.get("questions", [])):
            key = f"{prefix}_{index}"
            answer = _parse(answers.get(key))
            if answer is None:
                question_number += 1
                continue

            rows.append(
                {
                    "session_id": session_id,
                    "section_number": section_number,
                    "question_number": question_number,
                    "question_key": key,
                    "question_text": question_text,
                    "answer_value": answer,
                    "updated_at": now,
                }
            )
            question_number += 1

    return rows


def save_psychometric_answers(session_id: str, answers: dict, pre_sections=None, post_sections=None):
    client = _require_client()
    pre_rows = _psychometric_rows(session_id, answers, pre_sections)
    post_rows = _psychometric_rows(session_id, answers, post_sections)

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


def _month_result_row(session_id: str, result: dict, bonus_max_session: float = 12.0):
    monthly_score = _float_or_none(result.get("monthly_score")) or 0.0
    bonus_lunar = monthly_score / 100.0 * (float(bonus_max_session) / 24.0)

    return {
        "session_id": session_id,
        "month_number": int(result.get("month", 0)),
        "opening_balance": _float_or_none(result.get("opening_balance")),
        "income_total": _float_or_none(result.get("income_total")),
        "expenses_total": _float_or_none(result.get("expenses_total")),
        "loan_obligation": _float_or_none(result.get("loan_obligation")),
        "credit_interest": _float_or_none(result.get("credit_interest")),
        "overdraft_interest": _float_or_none(result.get("overdraft_interest")),
        "penalties": _float_or_none(result.get("penalties")),
        "available_total": _float_or_none(result.get("available_total")),
        "outflows_before_credit": _float_or_none(result.get("outflows_before_credit")),
        "deficit_before_credit": _float_or_none(result.get("deficit_before_credit")),
        "liquidity_before_payment": _float_or_none(result.get("liquidity_after_charges")),
        "overdraft_after_charges": _float_or_none(result.get("overdraft_after_charges")),
        "overdraft_remaining": _float_or_none(result.get("overdraft_remaining")),
        "max_payment": _float_or_none(result.get("max_payment")),
        "payment_input": _float_or_none(result.get("payment_input")),
        "accepted_payment": _float_or_none(result.get("accepted_payment")),
        "overdraft_from_payment": _float_or_none(result.get("overdraft_from_payment")),
        "overdraft_final": _float_or_none(result.get("overdraft_final")),
        "cash_final": _float_or_none(result.get("cash_final")),
        "credit_final": _float_or_none(result.get("credit_final")),
        "score_repayment": _float_or_none(result.get("score_repayment")),
        "score_liquidity": _float_or_none(result.get("score_liquidity")),
        "score_overdraft": _float_or_none(result.get("score_overdraft")),
        "monthly_score": monthly_score,
        "bonus_lunar": bonus_lunar,
        "costs_this_month": _float_or_none(result.get("costs_this_month")),
        "feedback_message": result.get("feedback_message"),
        "invalid_reason": result.get("invalid_reason"),
        "pre_credit_impossible": _bool_or_none(result.get("pre_credit_impossible")),
        "payment_valid": _bool_or_none(result.get("payment_valid")),
        "score_model": result.get("score_model"),
        "updated_at": _utcnow(),
    }


def save_month_result(session_id: str, result: dict, bonus_max_session: float = 12.0):
    client = _require_client()
    row = _month_result_row(session_id, result, bonus_max_session=bonus_max_session)
    client.table("month_results").upsert(
        row,
        on_conflict="session_id,month_number",
    ).execute()


def save_month_results(session_id: str, monthly_results, bonus_max_session: float = 12.0):
    client = _require_client()
    rows = [
        _month_result_row(session_id, result, bonus_max_session=bonus_max_session)
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
    return client.table("session_summaries").upsert(row, on_conflict="session_id").execute()


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

    if not allow_repeat and account_has_completed(account_key):
        raise RuntimeError("This participant has already completed the study.")

    if not _active_resume_link_exists(client, account_key, session_id) and not _repair_missing_resume_link(client, account_key, session_id):
        raise RuntimeError("No active session is associated with this participant.")

    summary = summary or {}
    bonus_max_session = _float_or_none(summary.get("bonus_max_session")) or 12.0
    feedback = answers.get("feedback") or None

    save_psychometric_answers(session_id, answers, pre_sections=pre_sections, post_sections=post_sections)
    save_month_results(session_id, monthly_results or [], bonus_max_session=bonus_max_session)
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
        }
    ).eq("id", session_id).execute()

    client.table("completed_accounts").upsert(
        {
            "account_key": account_key,
            "completed_at": _utcnow(),
        }
    ).execute()

    client.table("resume_links").delete().eq("account_key", account_key).eq("session_id", session_id).execute()

    return response
