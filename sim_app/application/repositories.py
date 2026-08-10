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
