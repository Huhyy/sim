"""FastAPI dependency adapters for application services and identity."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, Request

from sim_app.application.errors import AuthenticationRequired, IdempotencyKeyRequired
from sim_app.application.principal import ParticipantPrincipal
from sim_app.composition import get_experiment_service
from sim_app.infra.secrets import _first_secret


def get_service(request: Request):
    return getattr(request.app.state, "experiment_service", None) or get_experiment_service()


def get_ready_service(request: Request):
    explicit = getattr(request.app.state, "experiment_service", None)
    if explicit is not None:
        return explicit
    url = _first_secret("SUPABASE_URL", "SUPABASE_PROJECT_URL")
    key = _first_secret("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY")
    if not url or not key or str(key).startswith("sb_publishable_"):
        from sim_app.application.errors import PersistenceReadError

        raise PersistenceReadError("Required server persistence configuration is unavailable")
    return get_experiment_service()


def get_principal(request: Request) -> ParticipantPrincipal:
    provider = getattr(request.app.state, "principal_provider", None)
    if provider is None:
        raise AuthenticationRequired("No participant authentication adapter is configured")
    principal = provider(request)
    if not isinstance(principal, ParticipantPrincipal) or not principal.account_key:
        raise AuthenticationRequired("A valid participant identity is required")
    return principal


def require_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    value = str(idempotency_key or "")
    if not value.strip():
        raise IdempotencyKeyRequired("Idempotency-Key is required for state-changing requests")
    if len(value) > 200:
        raise IdempotencyKeyRequired("Idempotency-Key is too long")
    return value


__all__ = ["get_principal", "get_ready_service", "get_service", "require_idempotency_key"]
