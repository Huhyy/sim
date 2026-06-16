"""Mapping between authenticated accounts and active simulation sessions."""

from sim_app.infra.supabase import _require_client
from sim_app.infra.time import _utcnow


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


__all__ = [
    "load_linked_session_id",
    "save_resume_link",
]
