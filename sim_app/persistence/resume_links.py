"""Mapping between authenticated accounts and active simulation sessions."""

from sim_app.infra.supabase import _require_client


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

__all__ = [
    "load_linked_session_id",
]
