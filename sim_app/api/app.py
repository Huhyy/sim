"""FastAPI application factory for the second simulator transport."""

from __future__ import annotations

import logging
import os
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from sim_app.api.errors import install_exception_handlers
from sim_app.api.routes import router
from sim_app.api.auth_routes import router as auth_router
from sim_app.api.admin_routes import router as admin_router
from sim_app.api.frontend_routes import FRONTEND_ROOT, router as frontend_router
from sim_app.application.instrumentation import DEFAULT_METRICS


LOGGER = logging.getLogger("sim_app.api.requests")


def create_app(*, service=None, principal_provider=None, browser_session_manager=None, oidc_client=None, admin_service=None, docs_enabled=None):
    if docs_enabled is None:
        docs_enabled = str(os.getenv("API_DOCS_ENABLED", "true")).lower() not in {"0", "false", "no", "off"}
    application = FastAPI(
        title="Behavioral Credit Simulator API",
        version="1.0.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    application.state.experiment_service = service
    application.state.principal_provider = principal_provider
    application.state.browser_session_manager = browser_session_manager
    application.state.oidc_client = oidc_client
    application.state.admin_service = admin_service
    install_exception_handlers(application)

    @application.middleware("http")
    async def request_observability(request: Request, call_next):
        request_id = str(request.headers.get("X-Request-ID") or uuid.uuid4())[:200]
        request.state.request_id = request_id
        started = time.perf_counter()
        status = 500
        idempotency_replayed = False
        try:
            response = await call_next(request)
            status = response.status_code
            idempotency_replayed = response.headers.get("Idempotency-Replayed") == "true"
            if idempotency_replayed:
                DEFAULT_METRICS.increment("http.idempotency_replay_count")
            response.headers["X-Request-ID"] = request_id
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("Referrer-Policy", "same-origin")
            response.headers.setdefault("X-Frame-Options", "DENY")
            if request.url.path.startswith(("/api/", "/auth/")):
                response.headers["Cache-Control"] = "no-store"
            if request.url.path in {"/", "/admin"} or request.url.path.startswith("/static/"):
                response.headers.setdefault(
                    "Content-Security-Policy",
                    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data:; connect-src 'self'; base-uri 'none'; "
                    "form-action 'self'; frame-ancestors 'none'",
                )
            return response
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            route = getattr(request.scope.get("route"), "path", request.url.path)
            DEFAULT_METRICS.increment("http.request_count")
            DEFAULT_METRICS.increment(f"http.status.{status}")
            category = getattr(request.state, "error_category", None)
            if category:
                DEFAULT_METRICS.increment(f"http.error.{category}")
            LOGGER.info(
                "http_request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "route": route,
                    "status": status,
                    "latency_ms": round(elapsed_ms, 3),
                    "error_category": category,
                    "idempotency_replayed": idempotency_replayed,
                },
            )

    application.include_router(auth_router)
    application.include_router(router)
    application.include_router(admin_router)
    application.mount("/static", StaticFiles(directory=FRONTEND_ROOT / "static"), name="static")
    application.include_router(frontend_router)
    return application


app = create_app()


__all__ = ["app", "create_app"]
