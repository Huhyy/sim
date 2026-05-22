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
    key = _first_secret("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY", "SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    return _build_client(url, key)



def _require_client():
    client = get_client()
    if client is None:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY / SUPABASE_ANON_KEY)."
        )
    return client



def _parse(value):
    if value is None:
        return None
    try:
        return int(str(value).split(" - ")[0].strip())
    except Exception:
        return None



def save_participant(session_id: str, answers: dict, final_score: float):
    client = _require_client()

    row = {
        "id": session_id,
        "completed": True,
        "final_score": float(final_score),
        "feedback": answers.get("feedback") or None,
    }
    for key, value in answers.items():
        if key == "feedback":
            continue
        row[key] = _parse(value)

    client.table("participants").upsert(row).execute()



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
