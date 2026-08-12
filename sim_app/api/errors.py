"""Stable HTTP mappings for application and transport failures."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sim_app.application.errors import (
    AuthenticationRequired,
    ConcurrencyConflict,
    IdempotencyConflict,
    IdempotencyKeyRequired,
    InputValidationError,
    InvalidTransition,
    PersistenceReadError,
    PersistenceWriteError,
    ParticipationCompleted,
    ProlificLaunchError,
    SessionAccessDenied,
    SessionNotFound,
    TreatmentConflict,
)


LOGGER = logging.getLogger("sim_app.api")


def install_exception_handlers(app):
    app.add_exception_handler(RequestValidationError, _request_validation_error)
    app.add_exception_handler(AuthenticationRequired, _application_error)
    app.add_exception_handler(SessionAccessDenied, _application_error)
    app.add_exception_handler(SessionNotFound, _application_error)
    app.add_exception_handler(IdempotencyKeyRequired, _application_error)
    app.add_exception_handler(InputValidationError, _application_error)
    app.add_exception_handler(IdempotencyConflict, _application_error)
    app.add_exception_handler(TreatmentConflict, _application_error)
    app.add_exception_handler(ConcurrencyConflict, _application_error)
    app.add_exception_handler(InvalidTransition, _application_error)
    app.add_exception_handler(PersistenceReadError, _application_error)
    app.add_exception_handler(PersistenceWriteError, _application_error)
    app.add_exception_handler(ParticipationCompleted, _application_error)
    app.add_exception_handler(ProlificLaunchError, _application_error)
    app.add_exception_handler(Exception, _unexpected_error)


def _request_validation_error(request: Request, _exc):
    return _response(
        request,
        status=422,
        code="validation_error",
        message="The request payload is invalid.",
        retryable=False,
    )


def _application_error(request: Request, exc):
    status, code, message, retryable = _mapping(exc)
    request.state.error_category = code
    return _response(
        request,
        status=status,
        code=code,
        message=message,
        retryable=retryable,
        authoritative_version=getattr(exc, "current_version", None),
    )


def _unexpected_error(request: Request, exc):
    request.state.error_category = "internal_error"
    LOGGER.exception(
        "unhandled_api_error",
        extra={"request_id": _request_id(request), "path": request.url.path},
    )
    return _response(
        request,
        status=500,
        code="internal_error",
        message="An unexpected server error occurred.",
        retryable=True,
    )


def _mapping(exc):
    if isinstance(exc, AuthenticationRequired):
        return 401, "authentication_required", "Participant authentication is required.", False
    if isinstance(exc, SessionAccessDenied):
        return 403, "session_access_denied", "This participant cannot access the requested session.", False
    if isinstance(exc, SessionNotFound):
        return 404, "session_not_found", "The participant session was not found.", False
    if isinstance(exc, IdempotencyKeyRequired):
        return 400, "idempotency_key_required", str(exc), False
    if isinstance(exc, InputValidationError):
        return 422, "invalid_input", str(exc), False
    if isinstance(exc, IdempotencyConflict):
        return 409, "idempotency_conflict", "The idempotency key was already used for a different action.", False
    if isinstance(exc, TreatmentConflict):
        return 409, "treatment_conflict", "The durable treatment assignment cannot be changed.", False
    if isinstance(exc, ConcurrencyConflict):
        return 409, "concurrency_conflict", "The participant state changed in another client.", False
    if isinstance(exc, InvalidTransition):
        return 409, "invalid_transition", "This action is not valid for the current participant stage.", False
    if isinstance(exc, PersistenceReadError):
        return 503, "persistence_read_failed", "Participant state could not be read safely.", True
    if isinstance(exc, PersistenceWriteError):
        return 503, "persistence_write_failed", "The action was not committed. Retry with the same idempotency key.", True
    if isinstance(exc, ParticipationCompleted):
        return 409, "participation_completed", str(exc), False
    if isinstance(exc, ProlificLaunchError):
        return 400, "prolific_launch_error", str(exc), False
    return 500, "internal_error", "An unexpected server error occurred.", True


def _response(request, *, status, code, message, retryable, authoritative_version=None):
    detail = {
        "code": code,
        "message": message,
        "retryable": retryable,
        "request_id": _request_id(request),
    }
    if authoritative_version is not None:
        detail["authoritative_version"] = authoritative_version
    return JSONResponse(status_code=status, content={"error": detail})


def _request_id(request):
    return str(getattr(request.state, "request_id", "unavailable"))


__all__ = ["install_exception_handlers"]
