import streamlit as st
from supabase import create_client
from datetime import datetime, timezone
import os


def _get_secret(name: str):
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name)

def _build_client(url: str, key: str):
    try:
        return create_client(url, key)
    except Exception:
        return None


def get_client():
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_KEY")
    if not url or not key:
        return None

    return _build_client(url, key)


def _parse(value):
    if value is None:
        return None
    try:
        return int(str(value).split(" - ")[0].strip())
    except Exception:
        return None


def save_participant(session_id: str, answers: dict, final_score: float):
    client = get_client()
    if client is None:
        return

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
    client = get_client()
    if client is None:
        return None

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
    client = get_client()
    if client is None:
        return

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
