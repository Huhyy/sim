"""Authoritative framework-neutral experiment use-case service."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sim_app.application.commands import (
    acknowledge_month_feedback as acknowledge_feedback_command,
    prepare_completion,
    submit_month_decision as submit_month_command,
)
from sim_app.application.errors import ConcurrencyConflict, InvalidTransition, SessionNotFound
from sim_app.application.instrumentation import DEFAULT_METRICS
from sim_app.application.repositories import ExperimentRepository
from sim_app.application.state import ParticipantState
from sim_app.content.tables import get_month


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


def _treatment(state):
    return {
        "experimental_condition": state.experimental_condition,
        "score_frame": state.score_frame,
        "monthly_score_feedback": state.monthly_score_feedback,
    }


def _payload_hash(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = ["ExperimentService", "ServiceResult"]
