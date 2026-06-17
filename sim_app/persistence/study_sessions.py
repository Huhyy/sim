"""Admin-created study session persistence."""

import secrets
import uuid

from sim_app.domain.experimental_conditions import condition_config, normalize_experimental_condition
from sim_app.infra.supabase import _require_client
from sim_app.infra.time import _utcnow


def create_admin_study_session(created_by_email: str, experimental_condition: str = None):
    client = _require_client()
    email = str(created_by_email).strip().lower()
    condition = condition_config(normalize_experimental_condition(experimental_condition))

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
            **condition,
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


def list_participant_sessions_for_study_session(study_session_id: str = None, study_session_code: str = None):
    client = _require_client()
    select_columns = "id,participant_code,current_page,status,checkpoint,updated_at,completed_at"

    if study_session_id:
        response = (
            client
            .table("participant_sessions")
            .select(select_columns)
            .eq("study_session_id", str(study_session_id))
            .order("participant_code")
            .execute()
        )
        data = _with_participant_codes(getattr(response, "data", None) or [])
        if data:
            return _with_session_summaries(client, data)

    if not study_session_code:
        return []

    response = (
        client
        .table("participant_sessions")
        .select(select_columns)
        .eq("study_session_code", str(study_session_code).strip())
        .order("participant_code")
        .execute()
    )
    return _with_session_summaries(client, _with_participant_codes(getattr(response, "data", None) or []))


def _with_participant_codes(rows):
    return [row for row in rows if row.get("participant_code")]


def _with_session_summaries(client, rows):
    session_ids = [row.get("id") for row in rows if row.get("id")]
    if not session_ids:
        return rows

    response = (
        client
        .table("session_summaries")
        .select("session_id,final_score,performance_bonus_czk,loss_amount_czk,payment_status,completion_timestamp")
        .in_("session_id", session_ids)
        .execute()
    )
    summaries_by_session_id = {
        row.get("session_id"): row
        for row in (getattr(response, "data", None) or [])
        if row.get("session_id")
    }
    for row in rows:
        row["summary"] = summaries_by_session_id.get(row.get("id"))
    return rows


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
    "list_participant_sessions_for_study_session",
    "load_admin_study_session_by_code",
]
