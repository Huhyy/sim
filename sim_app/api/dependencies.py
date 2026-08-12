"""FastAPI dependency adapters for application services and identity."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Header, Request

from sim_app.application.errors import AuthenticationRequired, IdempotencyKeyRequired
from sim_app.application.principal import ParticipantPrincipal
from sim_app.composition import get_experiment_service
from sim_app.composition import get_admin_service
from sim_app.infra.secrets import _first_secret
from sim_app.auth.browser_session import BrowserSessionManager, SESSION_COOKIE
from sim_app.config import PROLIFIC_MODE_ENABLED


def get_service(request: Request):
    return getattr(request.app.state, "experiment_service", None) or get_experiment_service()


def get_ready_service(request: Request):
    explicit = getattr(request.app.state, "experiment_service", None)
    if explicit is not None and getattr(request.app.state, "principal_provider", None) is not None:
        return explicit
    url = _first_secret("SUPABASE_URL", "SUPABASE_PROJECT_URL")
    key = _first_secret("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY")
    browser_secret = _first_secret("BROWSER_SESSION_SECRET")
    account_pepper = _first_secret("ACCOUNT_KEY_PEPPER")
    public_origin = _first_secret("PUBLIC_ORIGIN")
    prolific_allowlist = _first_secret("PROLIFIC_ALLOWED_STUDY_IDS")
    google_config = all(_first_secret(name) for name in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"))
    if (
        not url
        or not key
        or str(key).startswith("sb_publishable_")
        or not browser_secret
        or not account_pepper
        or not public_origin
        or not google_config
        or (PROLIFIC_MODE_ENABLED and not prolific_allowlist)
    ):
        from sim_app.application.errors import PersistenceReadError

        raise PersistenceReadError("Required server persistence configuration is unavailable")
    return explicit or get_experiment_service()


def get_admin_application_service(request: Request):
    return getattr(request.app.state, "admin_service", None) or get_admin_service()


def get_principal(request: Request) -> ParticipantPrincipal:
    provider = getattr(request.app.state, "principal_provider", None)
    if provider is not None:
        principal = provider(request)
    else:
        if not request.cookies.get(SESSION_COOKIE):
            raise AuthenticationRequired("No browser authentication session is present")
        manager = get_browser_session_manager(request)
        principal, csrf_token = manager.decode_principal(request.cookies.get(SESSION_COOKIE))
        request.state.csrf_token = csrf_token
    if not isinstance(principal, ParticipantPrincipal) or not principal.account_key:
        raise AuthenticationRequired("A valid participant identity is required")
    return principal


def get_browser_session_manager(request: Request):
    manager = getattr(request.app.state, "browser_session_manager", None)
    if manager is None:
        manager = BrowserSessionManager()
        request.app.state.browser_session_manager = manager
    return manager


def require_csrf(request: Request):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    # Explicit principal providers are a controlled testing/embedding boundary;
    # production browser authentication always uses the encrypted cookie path.
    if getattr(request.app.state, "principal_provider", None) is not None:
        return
    manager = get_browser_session_manager(request)
    _principal, expected = manager.decode_principal(request.cookies.get(SESSION_COOKIE))
    supplied = request.headers.get("X-CSRF-Token")
    import secrets
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise AuthenticationRequired("CSRF validation failed")
    content_type = request.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise AuthenticationRequired("JSON content type is required for state-changing requests")

    configured_origin = _first_secret("PUBLIC_ORIGIN")
    expected_origin = (configured_origin or f"{request.url.scheme}://{request.url.netloc}").rstrip("/")
    actual_origin = request.headers.get("Origin")
    if not actual_origin:
        referer = request.headers.get("Referer")
        if referer:
            parsed = urlsplit(referer)
            actual_origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else None
    if not actual_origin or actual_origin.rstrip("/") != expected_origin:
        raise AuthenticationRequired("Request origin validation failed")


def require_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    value = str(idempotency_key or "")
    if not value.strip():
        raise IdempotencyKeyRequired("Idempotency-Key is required for state-changing requests")
    if len(value) > 200:
        raise IdempotencyKeyRequired("Idempotency-Key is too long")
    return value


__all__ = [
    "get_browser_session_manager",
    "get_admin_application_service",
    "get_principal",
    "get_ready_service",
    "get_service",
    "require_csrf",
    "require_idempotency_key",
]
