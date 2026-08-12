"""Synchronous HTTP transport over narrow ExperimentService use cases."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from sim_app.api.dependencies import get_browser_session_manager, get_principal, get_ready_service, get_service, require_csrf, require_idempotency_key
from sim_app.api.presentation import present_result, present_state
from sim_app.api.schemas import (
    ConsentRequest,
    CreateSessionRequest,
    DemographicsRequest,
    FeedbackAcknowledgementRequest,
    FinalizeRequest,
    MonthDecisionRequest,
    LanguageRequest,
    ParticipantSessionResponse,
    QuestionnaireSectionRequest,
    StudySessionBindingRequest,
    VersionedCommandRequest,
    ComprehensionRequest,
)
from sim_app.application.principal import ParticipantPrincipal


router = APIRouter()
participant_router = APIRouter(prefix="/api/v1", tags=["participant"], dependencies=[Depends(require_csrf)])


@router.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@router.get("/ready", tags=["health"])
def ready(service=Depends(get_ready_service)):
    del service
    return {"status": "ready"}


ServiceDependency = Annotated[object, Depends(get_service)]
PrincipalDependency = Annotated[ParticipantPrincipal, Depends(get_principal)]
IdempotencyDependency = Annotated[str, Depends(require_idempotency_key)]


def _present(response: Response, result):
    if result.idempotency_hit:
        response.headers["Idempotency-Replayed"] = "true"
    return present_result(result)


@participant_router.post("/sessions", response_model=ParticipantSessionResponse, response_model_exclude_none=True, status_code=201)
def create_session(
    request: Request,
    payload: CreateSessionRequest,
    response: Response,
    service: ServiceDependency,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyDependency,
):
    result = service.bootstrap_session(
        principal,
        expected_version=payload.expected_version,
        language=payload.language,
        request_id=idempotency_key,
    )
    presented = _present(response, result)
    if getattr(request.app.state, "principal_provider", None) is None:
        from dataclasses import replace
        manager = get_browser_session_manager(request)
        _current, csrf_token = manager.decode_principal(request.cookies.get("sim_browser_session"))
        manager.set_principal_cookie(
            response,
            replace(principal, bound_session_id=result.state.session_id),
            csrf_token=csrf_token,
        )
    return presented


@participant_router.get("/sessions/{session_id}", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def get_session(session_id: str, service: ServiceDependency, principal: PrincipalDependency):
    return present_state(service.load_owned_session(session_id, principal))


@participant_router.post("/sessions/{session_id}/start", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def start_session(session_id: str, payload: VersionedCommandRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.start_experiment(session_id, principal, expected_version=payload.expected_version, request_id=idempotency_key))


@participant_router.post("/sessions/{session_id}/study-session", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def bind_study_session(session_id: str, payload: StudySessionBindingRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.bind_study_session(
        session_id, principal, expected_version=payload.expected_version,
        request_id=idempotency_key, session_code=payload.session_code,
        participant_code=payload.participant_code,
    ))


@participant_router.post("/sessions/{session_id}/study-session/skip", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def skip_study_session(session_id: str, payload: VersionedCommandRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.skip_study_session(session_id, principal, expected_version=payload.expected_version, request_id=idempotency_key))


@participant_router.post("/sessions/{session_id}/consent", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def submit_consent(session_id: str, payload: ConsentRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.submit_consent(
        session_id, principal, expected_version=payload.expected_version,
        request_id=idempotency_key, accepted=payload.accepted,
        anti_ai_declaration=payload.anti_ai_declaration,
    ))


@participant_router.post("/sessions/{session_id}/consent/reconsider", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def reconsider_consent(session_id: str, payload: VersionedCommandRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.reconsider_consent(
        session_id, principal, expected_version=payload.expected_version, request_id=idempotency_key,
    ))


@participant_router.post("/sessions/{session_id}/language", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def change_language(session_id: str, payload: LanguageRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.change_language(
        session_id, principal, expected_version=payload.expected_version,
        request_id=idempotency_key, language=payload.language,
    ))


@participant_router.post("/sessions/{session_id}/demographics", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def submit_demographics(session_id: str, payload: DemographicsRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    values = payload.model_dump(exclude={"expected_version"})
    return _present(response, service.submit_demographics(
        session_id, principal, expected_version=payload.expected_version,
        request_id=idempotency_key, values=values,
    ))


@participant_router.post("/sessions/{session_id}/questionnaires/{phase}/sections/{section_index}", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def submit_questionnaire_section(session_id: str, phase: str, section_index: int, payload: QuestionnaireSectionRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.submit_questionnaire_section(
        session_id, principal, phase=phase, section_index=section_index,
        expected_version=payload.expected_version, request_id=idempotency_key,
        answers=payload.answers, attention_response=payload.attention_response,
        feedback=payload.feedback, strategy_feedback=payload.strategy_feedback,
    ))


@participant_router.post("/sessions/{session_id}/instructions/acknowledge", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def acknowledge_instructions(session_id: str, payload: VersionedCommandRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.acknowledge_instructions(session_id, principal, expected_version=payload.expected_version, request_id=idempotency_key))


@participant_router.post("/sessions/{session_id}/comprehension", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def submit_comprehension(session_id: str, payload: ComprehensionRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.submit_comprehension(
        session_id, principal, expected_version=payload.expected_version,
        request_id=idempotency_key, responses=payload.responses,
    ))


@participant_router.post("/sessions/{session_id}/profile/acknowledge", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def acknowledge_profile(session_id: str, payload: VersionedCommandRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.acknowledge_profile(session_id, principal, expected_version=payload.expected_version, request_id=idempotency_key))


@participant_router.post("/sessions/{session_id}/months/{month}/decision", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def submit_month_decision(session_id: str, month: int, payload: MonthDecisionRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.submit_owned_month_decision(
        session_id, principal, expected_version=payload.expected_version,
        expected_month=month, payment=payload.payment, request_id=idempotency_key,
    ))


@participant_router.post("/sessions/{session_id}/months/{month}/feedback/acknowledge", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def acknowledge_feedback(session_id: str, month: int, payload: FeedbackAcknowledgementRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.acknowledge_owned_month_feedback(
        session_id, principal, expected_version=payload.expected_version,
        expected_month=month, request_id=idempotency_key,
    ))


@participant_router.post("/sessions/{session_id}/final-score/acknowledge", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def acknowledge_final_score(session_id: str, payload: VersionedCommandRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.acknowledge_final_score(session_id, principal, expected_version=payload.expected_version, request_id=idempotency_key))


@participant_router.post("/sessions/{session_id}/finalize", response_model=ParticipantSessionResponse, response_model_exclude_none=True)
def finalize_session(session_id: str, payload: FinalizeRequest, response: Response, service: ServiceDependency, principal: PrincipalDependency, idempotency_key: IdempotencyDependency):
    return _present(response, service.finalize_owned_session(
        session_id, principal, expected_version=payload.expected_version,
        request_id=idempotency_key,
    ))


router.include_router(participant_router)


__all__ = ["router"]
