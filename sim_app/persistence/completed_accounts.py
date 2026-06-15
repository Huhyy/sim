"""Completed account lockout checks."""

from sim_app.infra.supabase import _require_client


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


__all__ = [
    "account_has_completed",
]
