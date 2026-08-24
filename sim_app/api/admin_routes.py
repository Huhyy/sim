"""Authenticated admin HTTP transport over AdminService."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from sim_app.api.dependencies import get_admin_application_service, get_principal, require_csrf
from sim_app.api.schemas import AdminCreateSessionRequest, AdminParticipantResultView, AdminStudySessionView
from sim_app.application.principal import ParticipantPrincipal


router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_csrf)])
AdminDependency = Annotated[object, Depends(get_admin_application_service)]
PrincipalDependency = Annotated[ParticipantPrincipal, Depends(get_principal)]


@router.get("/sessions", response_model=list[AdminStudySessionView], response_model_exclude_none=True)
def list_sessions(service: AdminDependency, principal: PrincipalDependency):
    return service.list_sessions(principal)


@router.get("/participants", response_model=list[AdminParticipantResultView], response_model_exclude_none=True)
def list_participant_results(service: AdminDependency, principal: PrincipalDependency):
    return service.list_participant_results(principal)


@router.get("/content/{language}")
def localized_content(language: str, service: AdminDependency, principal: PrincipalDependency):
    return service.localized_content(principal, language=language)


@router.post("/sessions", response_model=AdminStudySessionView, response_model_exclude_none=True, status_code=201)
def create_session(payload: AdminCreateSessionRequest, service: AdminDependency, principal: PrincipalDependency):
    return service.create_session(principal, experimental_condition=payload.experimental_condition)


@router.post("/sessions/{session_id}/cancel")
def cancel_session(session_id: str, service: AdminDependency, principal: PrincipalDependency):
    return service.cancel_session(principal, session_id=session_id)


__all__ = ["router"]
