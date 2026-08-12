"""Authoritative framework-neutral experiment use-case service."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any

from sim_app.application.commands import (
    accept_consent,
    acknowledge_month_feedback as acknowledge_feedback_command,
    assign_study_session,
    begin_comprehension_attempt,
    calculate_final_scores,
    clear_study_session_assignment,
    complete_comprehension_attempt,
    complete_final_score,
    complete_instructions,
    complete_post_question,
    complete_pre_question,
    complete_profile,
    decline_consent,
    go_to_page,
    prepare_completion,
    record_attention_result,
    submit_demographics as submit_demographics_command,
    submit_month_decision as submit_month_command,
)
from sim_app.application.errors import (
    AuthenticationRequired,
    ConcurrencyConflict,
    IdempotencyConflict,
    InputValidationError,
    InvalidTransition,
    ParticipationCompleted,
    ProlificLaunchError,
    SessionAccessDenied,
    SessionNotFound,
)
from sim_app.application.instrumentation import DEFAULT_METRICS
from sim_app.application.principal import ParticipantPrincipal
from sim_app.application.repositories import ExperimentRepository
from sim_app.application.state import ParticipantState
from sim_app.config import REPEAT_SCENARIO_DEV_MODE, SCENARIO_VERSION
from sim_app.content.questions import POST_SECTIONS, PRE_SECTIONS
from sim_app.content.tables import get_month
from sim_app.content.translations import get_display_post_sections, get_display_pre_sections, t
from sim_app.domain.experimental_conditions import assign_prolific_condition
from sim_app.infra.time import _utcnow
from sim_app.prolific.identity import completion_redirect_url, configured_completion_code


DEMOGRAPHIC_KEYS = (
    "demo_age",
    "demo_gender",
    "demo_education",
    "demo_field",
    "demo_occupation",
    "demo_income",
    "demo_financial_decisions",
    "demo_credit_experience",
    "demo_financial_familiarity",
    "demo_living_situation",
    "demo_recurring_responsibilities",
    "demo_country",
)

COMPREHENSION_QUESTIONS = (
    {"id": "who_completes", "correct": "A"},
    {"id": "monthly_task", "correct": "A"},
)


@dataclass(frozen=True)
class ServiceResult:
    state: ParticipantState
    result: dict[str, Any] | None = None
    idempotency_hit: bool = False


class ExperimentService:
    def __init__(self, repository: ExperimentRepository, *, month_loader=get_month, metrics=None, payment_processor=None):
        self.repository = repository
        self.month_loader = month_loader
        self.metrics = metrics or DEFAULT_METRICS
        self.payment_processor = payment_processor

    def find_session(self, session_id: str) -> ParticipantState | None:
        with self.metrics.measure("load_session"):
            return self.repository.load(session_id)

    def load_session(self, session_id: str) -> ParticipantState:
        state = self.find_session(session_id)
        if state is None:
            raise SessionNotFound(f"Participant session {session_id} was not found")
        return state

    def load_owned_session(self, session_id: str, principal: ParticipantPrincipal) -> ParticipantState:
        self._require_principal(principal)
        if self.repository.account_owns_session(principal.account_key, session_id):
            return self.load_session(session_id)
        if principal.bound_session_id == session_id:
            state = self.load_session(session_id)
            if state.submission_finalized:
                return state
        raise SessionAccessDenied("The authenticated participant does not own this session")

    def find_prolific_owned_session_id(self, principal: ParticipantPrincipal) -> str | None:
        self._require_principal(principal)
        if principal.identity_kind != "prolific":
            return None
        record = self.repository.find_prolific_session(principal.prolific_pid, principal.prolific_study_id)
        if not record or not record.get("id"):
            return None
        completed = record.get("status") == "completed"
        same_attempt = record.get("prolific_session_id") == principal.prolific_session_id
        if completed and not same_attempt:
            raise ProlificLaunchError("This Prolific study participation is already complete")
        # Active relaunches go through bootstrap so a new trusted SESSION_ID is
        # durably rebound with normal version/idempotency protection.
        return str(record["id"]) if completed and same_attempt else None

    def bootstrap_session(self, principal, *, expected_version, language, request_id):
        self._require_principal(principal)
        if expected_version != 0:
            raise InputValidationError("Session creation requires expected_version 0")
        language = _validate_language(language)
        state = ParticipantState.initial(SCENARIO_VERSION)
        state.session_id = str(uuid.uuid4())
        state.language = language
        if principal.identity_kind == "prolific":
            if not all((principal.prolific_pid, principal.prolific_study_id, principal.prolific_session_id)):
                raise AuthenticationRequired("A complete trusted Prolific identity is required")
            treatment = assign_prolific_condition(principal.prolific_pid, principal.prolific_study_id)
            state.prolific_mode = True
            state.prolific_pid = principal.prolific_pid
            state.prolific_study_id = principal.prolific_study_id
            state.prolific_session_id = principal.prolific_session_id
            state.prolific_completion_code = configured_completion_code()
            state.prolific_completion_url = completion_redirect_url(state.prolific_completion_code)
            state.experimental_condition = treatment["experimental_condition"]
            state.score_frame = treatment["score_frame"]
            state.monthly_score_feedback = treatment["monthly_score_feedback"]
            state.treatment_bound = True
            state.page = "consent"
        linked_session_id = self.repository.find_session_id_for_account(principal.account_key)
        if linked_session_id:
            stored_hash = self.repository.creation_request_payload_hash(linked_session_id, request_id)
            requested_hash = _payload_hash({
                "state": state.to_resume_projection(),
                "treatment": _treatment(state),
            })
            if stored_hash is not None and stored_hash != requested_hash:
                raise IdempotencyConflict("The creation request key has a different payload")
            linked_state = self.load_owned_session(linked_session_id, principal)
            if (
                principal.identity_kind == "prolific"
                and linked_state.prolific_session_id != principal.prolific_session_id
            ):
                proposed = linked_state.copy()
                proposed.prolific_session_id = principal.prolific_session_id
                return self.save_stage(
                    proposed,
                    expected_version=linked_state.state_version,
                    request_id=request_id,
                )
            return ServiceResult(linked_state, idempotency_hit=True)
        if principal.identity_kind == "prolific":
            existing = self.repository.find_prolific_session(
                principal.prolific_pid,
                principal.prolific_study_id,
            )
            if existing:
                same_attempt = existing.get("prolific_session_id") == principal.prolific_session_id
                completed = existing.get("status") == "completed"
                if completed and not same_attempt:
                    raise ProlificLaunchError("This Prolific study participation is already complete")
                existing_state = self.load_session(existing["id"])
                if (
                    existing_state.prolific_pid != principal.prolific_pid
                    or existing_state.prolific_study_id != principal.prolific_study_id
                ):
                    raise SessionAccessDenied("The Prolific identity does not own this session")
                if completed:
                    return ServiceResult(existing_state, idempotency_hit=True)
                if existing_state.prolific_session_id != principal.prolific_session_id:
                    proposed = existing_state.copy()
                    proposed.prolific_session_id = principal.prolific_session_id
                    return self.save_stage(
                        proposed,
                        expected_version=existing_state.state_version,
                        request_id=request_id,
                    )
                return ServiceResult(existing_state, idempotency_hit=True)
        if (
            principal.identity_kind != "prolific"
            and not REPEAT_SCENARIO_DEV_MODE
            and self.repository.account_has_completed(principal.account_key)
        ):
            raise ParticipationCompleted("This account has already completed the experiment")
        return self.create_session(
            state,
            account_key=principal.account_key,
            request_id=request_id,
        )

    def start_experiment(self, session_id, principal, *, expected_version, request_id):
        return self._stage_command(
            session_id,
            principal,
            expected_version=expected_version,
            request_id=request_id,
            expected_page="home",
            command=lambda state: go_to_page(state, "consent"),
        )

    def change_language(self, session_id, principal, *, expected_version, request_id, language):
        language = _validate_language(language)
        state = self.load_owned_session(session_id, principal)
        proposed = state.copy()
        proposed.language = language
        return self.save_stage(proposed, expected_version=expected_version, request_id=request_id)

    def reconsider_consent(self, session_id, principal, *, expected_version, request_id):
        return self._stage_command(
            session_id,
            principal,
            expected_version=expected_version,
            request_id=request_id,
            expected_page="consent_declined",
            command=lambda state: go_to_page(state, "consent"),
        )

    def bind_study_session(
        self,
        session_id,
        principal,
        *,
        expected_version,
        request_id,
        session_code,
        participant_code,
    ):
        # Authorize the participant session before resolving a potentially
        # sensitive active study-session code.
        self.load_owned_session(session_id, principal)
        normalized_session = re.sub(r"\D", "", str(session_code or ""))[:6]
        raw_participant = str(participant_code or "").strip().upper()
        participant_digits = re.sub(r"\D", "", raw_participant)
        normalized_participant = (
            f"P{participant_digits[:3].zfill(3)}"
            if participant_digits
            else re.sub(r"[^A-Z0-9]", "", raw_participant)[:4]
        )
        if len(normalized_session) != 6 or not re.fullmatch(r"P[0-9]{3}", normalized_participant):
            raise InputValidationError("A valid study-session and participant code are required")
        record = self.repository.load_study_session_by_code(normalized_session)
        if not record:
            raise InputValidationError("The study-session code is invalid or inactive")
        return self._stage_command(
            session_id,
            principal,
            expected_version=expected_version,
            request_id=request_id,
            expected_page=("home", "enter_session_code"),
            command=lambda state: assign_study_session(state, record, normalized_participant),
        )

    def skip_study_session(self, session_id, principal, *, expected_version, request_id):
        return self._stage_command(
            session_id,
            principal,
            expected_version=expected_version,
            request_id=request_id,
            expected_page=("home", "enter_session_code"),
            command=clear_study_session_assignment,
        )

    def submit_consent(
        self,
        session_id,
        principal,
        *,
        expected_version,
        request_id,
        accepted,
        anti_ai_declaration=False,
    ):
        def command(state):
            if accepted:
                if state.prolific_mode and not anti_ai_declaration:
                    raise InputValidationError("The participant declaration is required")
                return accept_consent(state, anti_ai_declaration=anti_ai_declaration)
            return decline_consent(state)

        return self._stage_command(
            session_id,
            principal,
            expected_version=expected_version,
            request_id=request_id,
            expected_page="consent",
            command=command,
        )

    def submit_demographics(
        self,
        session_id,
        principal,
        *,
        expected_version,
        request_id,
        values,
    ):
        state = self.load_owned_session(session_id, principal)
        values = dict(values or {})
        if set(values) != set(DEMOGRAPHIC_KEYS):
            raise InputValidationError("Every demographic field must be supplied exactly once")
        if not isinstance(values["demo_age"], int) or not 18 <= values["demo_age"] <= 75:
            raise InputValidationError("Age must be between 18 and 75")
        if any(value in (None, "") for value in values.values()):
            raise InputValidationError("Every demographic field is required")
        option_names = {
            "demo_gender": "gender",
            "demo_education": "education",
            "demo_field": "field",
            "demo_occupation": "occupation",
            "demo_income": "income",
            "demo_financial_decisions": "frequency",
            "demo_credit_experience": "credit",
            "demo_financial_familiarity": "familiarity",
            "demo_living_situation": "living",
            "demo_recurring_responsibilities": "yes_no",
        }
        for field, option_name in option_names.items():
            if values[field] not in t(f"demographics.options.{option_name}", language=state.language):
                raise InputValidationError(f"{field} is outside the allowed options")
        values["demo_country"] = str(values["demo_country"]).strip()
        return self._stage_command(
            session_id,
            principal,
            expected_version=expected_version,
            request_id=request_id,
            expected_page="demographics",
            command=lambda state: submit_demographics_command(state, values),
        )

    def submit_questionnaire_section(
        self,
        session_id,
        principal,
        *,
        phase,
        section_index,
        expected_version,
        request_id,
        answers,
        attention_response=None,
        feedback=None,
        strategy_feedback=None,
    ):
        if phase not in {"pre", "post"}:
            raise InputValidationError("Questionnaire phase must be pre or post")
        state = self.load_owned_session(session_id, principal)
        sections = _questionnaire_sections(phase, state.language)
        if section_index < 0 or section_index >= len(sections):
            raise InputValidationError("Questionnaire section is out of range")
        expected_page = f"{phase}_question_{section_index}"
        quality_required = state.prolific_mode and (
            (phase == "pre" and section_index == 0)
            or (phase == "post" and section_index + 1 == len(sections))
        )
        quality_event = None
        if state.state_version == expected_version:
            if not (
                phase == "post"
                and section_index == 0
                and state.page == "simulation"
                and state.month > 24
            ):
                legacy_page = f"{phase}_questions" if section_index == 0 else expected_page
                self._require_page(state, (expected_page, legacy_page))
            section = sections[section_index]
            supplied = dict(answers or {})
            expected_keys = {
                f"{section['key_prefix']}_{question_index}"
                for question_index in range(len(section["questions"]))
            }
            if set(supplied) != expected_keys:
                raise InputValidationError("Answers must match the current questionnaire section")
            if any(value not in section["scale"] for value in supplied.values()):
                raise InputValidationError("A questionnaire answer is outside the allowed scale")
            proposed = state.copy()
            proposed.answers.update(supplied)
            if phase == "post" and section_index + 1 == len(sections):
                proposed.answers["feedback"] = feedback or ""
                proposed.answers["strategy_feedback"] = strategy_feedback or ""
            if quality_required:
                if attention_response is None:
                    raise InputValidationError("The attention-check response is required")
                if attention_response not in t("prolific.attention_number_options", language=state.language):
                    raise InputValidationError("The attention-check response is invalid")
                passed = str(attention_response or "").startswith("3")
                proposed = record_attention_result(proposed, passed=passed)
                quality_event = {
                    "check_type": "attention",
                    "check_id": "attention_pre_1" if phase == "pre" else "attention_post_1",
                    "attempt_number": 1,
                    "passed": passed,
                    "response_value": attention_response,
                    "response_time_ms": None,
                    "page_id": expected_page,
                }
            command = (
                complete_pre_question(
                    proposed,
                    section_index=section_index,
                    section_count=len(sections),
                )
                if phase == "pre"
                else complete_post_question(
                    proposed,
                    section_index=section_index,
                    section_count=len(sections),
                )
            )
            proposed = command.state
        else:
            proposed = state.copy()
            section = sections[section_index]
            proposed.answers.update(dict(answers or {}))
            if phase == "post" and section_index + 1 == len(sections):
                proposed.answers["feedback"] = feedback or ""
                proposed.answers["strategy_feedback"] = strategy_feedback or ""
            proposed = (
                complete_pre_question(
                    proposed,
                    section_index=section_index,
                    section_count=len(sections),
                ).state
                if phase == "pre"
                else complete_post_question(
                    proposed,
                    section_index=section_index,
                    section_count=len(sections),
                ).state
            )
            if quality_required and attention_response is not None:
                passed = str(attention_response or "").startswith("3")
                quality_event = {
                    "check_type": "attention",
                    "check_id": "attention_pre_1" if phase == "pre" else "attention_post_1",
                    "attempt_number": 1,
                    "passed": passed,
                    "response_value": attention_response,
                    "response_time_ms": None,
                    "page_id": expected_page,
                }
        if quality_event:
            return self.save_quality_transition(
                proposed,
                [quality_event],
                expected_version=expected_version,
                request_id=request_id,
            )
        return self.save_stage(proposed, expected_version=expected_version, request_id=request_id)

    def acknowledge_instructions(self, session_id, principal, *, expected_version, request_id):
        return self._stage_command(
            session_id,
            principal,
            expected_version=expected_version,
            request_id=request_id,
            expected_page="instructions",
            command=complete_instructions,
        )

    def submit_comprehension(
        self,
        session_id,
        principal,
        *,
        expected_version,
        request_id,
        responses,
    ):
        state = self.load_owned_session(session_id, principal)
        responses = dict(responses or {})
        expected_ids = {question["id"] for question in COMPREHENSION_QUESTIONS}
        if set(responses) != expected_ids or any(value in (None, "") for value in responses.values()):
            raise InputValidationError("Every comprehension response is required")
        comprehension_option_keys = {
            "who_completes": "prolific.comprehension_q1_options",
            "monthly_task": "prolific.comprehension_q2_options",
        }
        for response_id, option_key in comprehension_option_keys.items():
            if responses[response_id] not in t(option_key, language=state.language):
                raise InputValidationError("A comprehension response is invalid")
        passed = all(
            str(responses[question["id"]] or "").startswith(question["correct"])
            for question in COMPREHENSION_QUESTIONS
        )
        if state.state_version == expected_version:
            self._require_page(state, "comprehension")
            attempted = begin_comprehension_attempt(state)
            attempt_number = attempted.comprehension_attempts
            proposed = complete_comprehension_attempt(
                attempted,
                passed=passed,
                passed_at=_utcnow() if passed else None,
            ).state
        else:
            proposed = state.copy()
            attempt_number = max(1, state.comprehension_attempts)
        events = [
            {
                "check_type": "comprehension",
                "check_id": question["id"],
                "attempt_number": attempt_number,
                "passed": passed and str(responses[question["id"]] or "").startswith(question["correct"]),
                "response_value": responses[question["id"]],
                "response_time_ms": None,
                "page_id": "comprehension",
            }
            for question in COMPREHENSION_QUESTIONS
        ]
        return self.save_quality_transition(
            proposed,
            events,
            expected_version=expected_version,
            request_id=request_id,
        )

    def acknowledge_profile(self, session_id, principal, *, expected_version, request_id):
        return self._stage_command(
            session_id,
            principal,
            expected_version=expected_version,
            request_id=request_id,
            expected_page="profile",
            command=complete_profile,
        )

    def submit_owned_month_decision(
        self,
        session_id,
        principal,
        *,
        expected_version,
        expected_month,
        payment,
        request_id,
    ):
        self.load_owned_session(session_id, principal)
        return self.submit_month_decision(
            session_id=session_id,
            expected_version=expected_version,
            expected_month=expected_month,
            payment=payment,
            request_id=request_id,
        )

    def acknowledge_owned_month_feedback(
        self,
        session_id,
        principal,
        *,
        expected_version,
        expected_month,
        request_id,
    ):
        self.load_owned_session(session_id, principal)
        return self.acknowledge_month_feedback(
            session_id=session_id,
            expected_version=expected_version,
            expected_month=expected_month,
            request_id=request_id,
        )

    def acknowledge_final_score(self, session_id, principal, *, expected_version, request_id):
        return self._stage_command(
            session_id,
            principal,
            expected_version=expected_version,
            request_id=request_id,
            expected_page="final_score",
            command=lambda state: complete_final_score(calculate_final_scores(state)),
        )

    def finalize_owned_session(self, session_id, principal, *, expected_version, request_id):
        self._require_principal(principal)
        try:
            self.load_owned_session(session_id, principal)
        except SessionAccessDenied:
            # Finalization removes the resume-link ownership row. Verify the
            # encrypted browser-session binding as well as the durable logical
            # request before loading the finalized state. A request ID alone is
            # never an ownership credential.
            if (
                principal.bound_session_id != session_id
                or not self.repository.finalization_request_matches(session_id, request_id)
            ):
                raise
            state = self.load_session(session_id)
            if not state.submission_finalized:
                raise SessionAccessDenied("The authenticated participant does not own this session")
        return self.finalize(
            session_id=session_id,
            expected_version=expected_version,
            request_id=request_id,
            account_key=principal.account_key,
            pre_sections=PRE_SECTIONS,
            post_sections=POST_SECTIONS,
        )

    def create_session(self, state, *, account_key, request_id):
        payload_hash = _payload_hash({"state": state.to_resume_projection(), "treatment": _treatment(state)})
        with self.metrics.measure("create_session"):
            committed = self.repository.create_session(
                state,
                account_key=account_key,
                request_id=request_id,
                payload_hash=payload_hash,
            )
        self._record_commit(committed)
        return ServiceResult(committed.state, committed.result, committed.idempotency_hit)

    def save_stage(self, proposed_state, *, expected_version, request_id):
        projection_json = json.dumps(
            proposed_state.to_resume_projection(),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        self.metrics.increment("checkpoint_payload_bytes_total", len(projection_json.encode("utf-8")))
        payload_hash = _payload_hash({
            "projection": proposed_state.to_resume_projection(),
            "treatment": _treatment(proposed_state),
            "treatment_bound": proposed_state.treatment_bound,
        })
        try:
            with self.metrics.measure("save_stage"):
                committed = self.repository.save_stage(
                    proposed_state,
                    expected_version=expected_version,
                    request_id=request_id,
                    payload_hash=payload_hash,
                )
        except ConcurrencyConflict:
            self.metrics.increment("conflict_count")
            raise
        self._record_commit(committed)
        return ServiceResult(committed.state, committed.result, committed.idempotency_hit)

    def submit_month_decision(
        self,
        *,
        session_id,
        expected_version,
        expected_month,
        payment,
        request_id,
        translate=None,
    ):
        state = self.load_session(session_id)
        payload_hash = _payload_hash({
            "session_id": session_id,
            "month": expected_month,
            "payment": payment,
            "scenario_version": state.scenario_version,
            "treatment": _treatment(state),
        })
        if state.state_version != expected_version or state.month != expected_month:
            # The repository checks idempotency before its version predicate,
            # allowing a response-lost retry to recover the original commit.
            try:
                committed = self.repository.commit_month_decision(
                    state,
                    {},
                    expected_version=expected_version,
                    expected_month=expected_month,
                    request_id=request_id,
                    payload_hash=payload_hash,
                )
            except ConcurrencyConflict:
                self.metrics.increment("conflict_count")
                raise
            self._record_commit(committed)
            return ServiceResult(committed.state, committed.result, committed.idempotency_hit)
        if state.page != "simulation" or state.submission_finalized or state.month > 24 or state.pending_month_result:
            raise InvalidTransition("A month decision cannot be submitted from the current stage")
        month_data = self.month_loader(state.month)
        command = submit_month_command(state, month_data=month_data, payment=payment, translate=translate)
        try:
            with self.metrics.measure("monthly_decision_commit"):
                committed = self.repository.commit_month_decision(
                    command.state,
                    command.feedback,
                    expected_version=expected_version,
                    expected_month=expected_month,
                    request_id=request_id,
                    payload_hash=payload_hash,
                )
        except ConcurrencyConflict:
            self.metrics.increment("conflict_count")
            raise
        self._record_commit(committed)
        return ServiceResult(committed.state, committed.result, committed.idempotency_hit)

    def save_quality_transition(
        self,
        proposed_state,
        quality_events,
        *,
        expected_version,
        request_id,
    ):
        payload_hash = _payload_hash({
            "projection": proposed_state.to_resume_projection(),
            "events": quality_events,
        })
        try:
            with self.metrics.measure("quality_transition"):
                committed = self.repository.save_quality_transition(
                    proposed_state,
                    quality_events,
                    expected_version=expected_version,
                    request_id=request_id,
                    payload_hash=payload_hash,
                )
        except ConcurrencyConflict:
            self.metrics.increment("conflict_count")
            raise
        self._record_commit(committed)
        return ServiceResult(committed.state, committed.result, committed.idempotency_hit)

    def acknowledge_month_feedback(
        self,
        *,
        session_id,
        expected_version,
        expected_month,
        request_id,
    ):
        state = self.load_session(session_id)
        # Let the repository return an earlier idempotent response even when
        # the authoritative state has already moved beyond this version.
        if state.state_version == expected_version and state.month == expected_month:
            command = acknowledge_feedback_command(state)
            proposed = command.state
        else:
            proposed = state.copy()
        payload_hash = _payload_hash({"session_id": session_id, "month": expected_month})
        try:
            with self.metrics.measure("acknowledge_month_feedback"):
                committed = self.repository.acknowledge_month_feedback(
                    proposed,
                    expected_version=expected_version,
                    expected_month=expected_month,
                    request_id=request_id,
                    payload_hash=payload_hash,
                )
        except ConcurrencyConflict:
            self.metrics.increment("conflict_count")
            raise
        self._record_commit(committed)
        return ServiceResult(committed.state, committed.result, committed.idempotency_hit)

    def finalize(
        self,
        *,
        session_id,
        expected_version,
        request_id,
        account_key,
        pre_sections,
        post_sections,
    ):
        state = self.load_session(session_id)
        if state.state_version == expected_version:
            if state.page != "done" or len(state.monthly_results) != 24:
                raise InvalidTransition("Finalization requires exactly 24 durable month results")
            proposed = prepare_completion(state)
            proposed.submission_finalized = True
            proposed.saved = True
            proposed.page = "done"
            proposed.completion_status = "payment_pending" if proposed.prolific_pid else "complete"
        else:
            proposed = state.copy()
        payload_hash = _payload_hash({
            "session_id": session_id,
            "account_key": account_key,
            "expected_version": expected_version,
            "answers": {key: value for key, value in state.answers.items() if key != "financial_summary"},
            "months": state.monthly_results,
            "treatment": _treatment(state),
            "completion_code": state.prolific_completion_code,
        })
        try:
            with self.metrics.measure("finalization"):
                committed = self.repository.finalize(
                    proposed,
                    expected_version=expected_version,
                    account_key=account_key,
                    request_id=request_id,
                    payload_hash=payload_hash,
                    pre_sections=pre_sections,
                    post_sections=post_sections,
                )
                self._record_commit(committed)
                final_state = committed.state
                if self.payment_processor is not None:
                    final_state = self.payment_processor.process(final_state, request_id=request_id)
        except ConcurrencyConflict:
            self.metrics.increment("conflict_count")
            raise
        return ServiceResult(final_state, committed.result, committed.idempotency_hit)

    def _record_commit(self, committed):
        if committed.idempotency_hit:
            self.metrics.increment("idempotency_hit_count")

    def _stage_command(
        self,
        session_id,
        principal,
        *,
        expected_version,
        request_id,
        expected_page,
        command,
    ):
        state = self.load_owned_session(session_id, principal)
        if state.state_version == expected_version:
            self._require_page(state, expected_page)
            proposed = command(state).state
        else:
            # Reusing the already committed projection preserves response-loss
            # idempotency before the repository evaluates the stale version.
            proposed = command(state).state
        return self.save_stage(
            proposed,
            expected_version=expected_version,
            request_id=request_id,
        )

    @staticmethod
    def _require_principal(principal):
        if not isinstance(principal, ParticipantPrincipal) or not principal.account_key:
            raise AuthenticationRequired("An authenticated participant identity is required")

    @staticmethod
    def _require_page(state, expected_page):
        expected_pages = (expected_page,) if isinstance(expected_page, str) else tuple(expected_page)
        if state.page not in expected_pages:
            raise InvalidTransition(f"This action requires stage {expected_page}")


def _treatment(state):
    return {
        "experimental_condition": state.experimental_condition,
        "score_frame": state.score_frame,
        "monthly_score_feedback": state.monthly_score_feedback,
    }


def _payload_hash(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_language(language):
    if language not in {"en", "ro"}:
        raise InputValidationError("Language must be en or ro")
    return language


def _questionnaire_sections(phase, language):
    return (
        get_display_pre_sections(language)
        if phase == "pre"
        else get_display_post_sections(language)
    )


__all__ = ["ExperimentService", "ServiceResult"]
