"""Framework-neutral repository contracts used by ExperimentService."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from sim_app.application.state import ParticipantState


@dataclass(frozen=True)
class RepositoryCommit:
    state: ParticipantState
    result: dict[str, Any] | None = None
    idempotency_hit: bool = False


class ExperimentRepository(Protocol):
    def load(self, session_id: str) -> ParticipantState | None: ...

    def find_session_id_for_account(self, account_key: str) -> str | None: ...

    def account_owns_session(self, account_key: str, session_id: str) -> bool: ...

    def creation_request_payload_hash(self, session_id: str, request_id: str) -> str | None: ...

    def finalization_request_matches(self, session_id: str, request_id: str) -> bool: ...

    def load_study_session_by_code(self, session_code: str) -> dict[str, Any] | None: ...

    def create_session(
        self,
        state: ParticipantState,
        *,
        account_key: str,
        request_id: str,
        payload_hash: str,
    ) -> RepositoryCommit: ...

    def save_stage(
        self,
        proposed_state: ParticipantState,
        *,
        expected_version: int,
        request_id: str,
        payload_hash: str,
    ) -> RepositoryCommit: ...

    def commit_month_decision(
        self,
        proposed_state: ParticipantState,
        result: dict[str, Any],
        *,
        expected_version: int,
        expected_month: int,
        request_id: str,
        payload_hash: str,
    ) -> RepositoryCommit: ...

    def save_quality_transition(
        self,
        proposed_state: ParticipantState,
        quality_events: list[dict[str, Any]],
        *,
        expected_version: int,
        request_id: str,
        payload_hash: str,
    ) -> RepositoryCommit: ...

    def acknowledge_month_feedback(
        self,
        proposed_state: ParticipantState,
        *,
        expected_version: int,
        expected_month: int,
        request_id: str,
        payload_hash: str,
    ) -> RepositoryCommit: ...

    def finalize(
        self,
        proposed_state: ParticipantState,
        *,
        expected_version: int,
        account_key: str,
        request_id: str,
        payload_hash: str,
        pre_sections: list[dict[str, Any]],
        post_sections: list[dict[str, Any]],
    ) -> RepositoryCommit: ...


__all__ = ["ExperimentRepository", "RepositoryCommit"]
