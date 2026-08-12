"""FastAPI application factory for the second simulator transport."""

from __future__ import annotations

import logging
import os
import time
import uuid

from fastapi import FastAPI, Request

from sim_app.api.errors import install_exception_handlers
from sim_app.api.routes import router
from sim_app.application.instrumentation import DEFAULT_METRICS


LOGGER = logging.getLogger("sim_app.api.requests")


def create_app(*, service=None, principal_provider=None, docs_enabled=None):
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

    application.include_router(router)
    return application


app = create_app()


__all__ = ["app", "create_app"]
