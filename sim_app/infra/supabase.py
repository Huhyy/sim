"""Supabase client construction."""

from supabase import create_client

from .secrets import _first_secret


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


__all__ = [
    "_build_client",
    "_require_client",
    "get_client",
]
