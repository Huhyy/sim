"""Supabase client construction with thread-local resource reuse."""

from threading import RLock, local

from supabase import create_client

from .secrets import _first_secret


def _build_client(url: str, key: str):
    return create_client(url, key)


_client_lock = RLock()
_thread_clients = local()
_client_generation = 0


def get_client():
    url = _first_secret("SUPABASE_URL", "SUPABASE_PROJECT_URL")
    key = _first_secret("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY")
    if not url or not key:
        return None
    if str(key).startswith("sb_publishable_"):
        raise RuntimeError("Use a Supabase secret key for server-side study storage, not a publishable key.")
    credentials = (str(url), str(key))
    cached = getattr(_thread_clients, "resource", None)
    if cached is not None and cached[0] == credentials and cached[1] == _client_generation:
        return cached[2]
    with _client_lock:
        cached = getattr(_thread_clients, "resource", None)
        if cached is None or cached[0] != credentials or cached[1] != _client_generation:
            client = _build_client(*credentials)
            _thread_clients.resource = (credentials, _client_generation, client)
        return _thread_clients.resource[2]


def reset_shared_client():
    """Invalidate all thread-local resources after configuration changes/tests."""
    global _client_generation
    with _client_lock:
        _client_generation += 1
        if hasattr(_thread_clients, "resource"):
            del _thread_clients.resource


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
    "reset_shared_client",
]
