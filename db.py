import os
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



def _parsed_answers(answers: dict):
    return {
        key: _parse(value)
        for key, value in answers.items()
        if key != "feedback"
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


def finalize_participation(
    account_key: str,
    session_id: str,
    answers: dict,
    final_score: float,
    allow_repeat: bool = False,
):
    client = _require_client()
    if allow_repeat:
        client.table("completed_accounts").delete().eq("account_key", account_key).execute()

    payload = {
        "p_account_key": account_key,
        "p_session_id": session_id,
        "p_final_score": float(final_score),
        "p_feedback": answers.get("feedback") or None,
        "p_answers": _parsed_answers(answers),
    }
    return client.rpc("finalize_study_response", payload).execute()
