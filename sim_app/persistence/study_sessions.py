"""Admin-created study session persistence."""

import secrets
import uuid

from sim_app.infra.supabase import _require_client
from sim_app.infra.time import _utcnow


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


__all__ = [
    "cancel_admin_study_session",
    "create_admin_study_session",
    "list_admin_study_sessions",
    "load_admin_study_session_by_code",
]
