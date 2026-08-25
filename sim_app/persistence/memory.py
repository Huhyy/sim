"""Transactional in-memory ExperimentRepository used for invariant tests."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock

from sim_app.application.errors import (
    ConcurrencyConflict,
    IdempotencyConflict,
    PersistenceReadError,
    PersistenceWriteError,
    TreatmentConflict,
)
from sim_app.application.repositories import RepositoryCommit


class InMemoryExperimentRepository:
    def __init__(self):
        self._sessions = {}
        self._ledgers = {}
        self._idempotency = {}
        self._accounts = {}
        self._completed_accounts = set()
        self._finalizations = {}
        self._quality = {}
        self._legacy = set()
        self._failure = None
        self._lock = RLock()

    def fail_next(self, operation, *, phase="before"):
        self._failure = (operation, phase)

    def load(self, session_id):
        with self._lock:
            self._raise_failure("load", "before", read=True)
            state = self._sessions.get(session_id)
            if state is None:
                return None
            if session_id in self._legacy:
                self._backfill_legacy_locked(session_id)
                state = self._sessions[session_id]
            loaded = deepcopy(state)
            loaded.monthly_results = self.month_results(session_id)
            pending_month = (
                int(loaded.pending_month_result.get("month", 0))
                if loaded.pending_month_result
                else None
            )
            if pending_month:
                loaded.pending_month_result = deepcopy(self._ledgers[session_id].get(pending_month))
            return loaded

    def find_session_id_for_account(self, account_key):
        with self._lock:
            self._raise_failure("find_session_for_account", "before", read=True)
            return self._accounts.get(account_key)

    def account_has_completed(self, account_key):
        with self._lock:
            return account_key in self._completed_accounts

    def release_account_session(self, account_key, session_id):
        with self._lock:
            if self._accounts.get(account_key) == session_id:
                self._accounts.pop(account_key, None)

    def find_prolific_session(self, prolific_pid, study_id):
        with self._lock:
            for state in self._sessions.values():
                if state.prolific_pid == prolific_pid and state.prolific_study_id == study_id:
                    return {
                        "id": state.session_id,
                        "status": "completed" if state.submission_finalized else "in_progress",
                        "prolific_session_id": state.prolific_session_id,
                        "completion_code": state.prolific_completion_code,
                    }
            return None

    def account_owns_session(self, account_key, session_id):
        return self.find_session_id_for_account(account_key) == session_id

    def creation_request_payload_hash(self, session_id, request_id):
        with self._lock:
            stored = self._idempotency.get((session_id, "create_session", request_id))
            return stored["payload_hash"] if stored else None

    def finalization_request_matches(self, session_id, request_id):
        with self._lock:
            return (session_id, "finalize", request_id) in self._idempotency

    def load_study_session_by_code(self, session_code):
        with self._lock:
            records = getattr(self, "_study_sessions", {})
            record = records.get(str(session_code))
            return deepcopy(record) if record else None

    def add_study_session(self, record):
        with self._lock:
            if not hasattr(self, "_study_sessions"):
                self._study_sessions = {}
            self._study_sessions[str(record["session_code"])] = deepcopy(record)

    def create_session(self, state, *, account_key, request_id, payload_hash):
        with self._lock:
            hit = self._idempotent(state.session_id, "create_session", request_id, payload_hash)
            if hit:
                return hit
            self._raise_failure("create_session", "before")
            linked = self._accounts.get(account_key)
            if linked and linked != state.session_id:
                existing = deepcopy(self._sessions[linked])
                return RepositoryCommit(existing, idempotency_hit=True)
            if state.session_id in self._sessions:
                existing = deepcopy(self._sessions[state.session_id])
                return RepositoryCommit(existing, idempotency_hit=True)
            created = deepcopy(state)
            created.state_version = 0
            self._raise_failure("create_session", "during")
            self._sessions[state.session_id] = created
            self._ledgers[state.session_id] = {}
            self._quality[state.session_id] = []
            self._accounts[account_key] = state.session_id
            return self._remember(state.session_id, "create_session", request_id, payload_hash, created)

    def save_stage(
        self,
        proposed_state,
        *,
        expected_version,
        request_id,
        payload_hash,
        psychometric_phase=None,
    ):
        with self._lock:
            session_id = proposed_state.session_id
            hit = self._idempotent(session_id, "save_stage", request_id, payload_hash)
            if hit:
                return hit
            self._raise_failure("save_stage", "before")
            current = self._required(session_id)
            if current.submission_finalized:
                raise ConcurrencyConflict("Completed participant state is immutable", current_version=current.state_version)
            self._expected(current, expected_version)
            self._validate_treatment(current, proposed_state)
            updated = deepcopy(current)
            for field in (
                "page", "admin_return_page", "language", "study_session_id",
                "study_session_code", "participant_code", "prolific_pid",
                "prolific_study_id", "prolific_session_id", "prolific_mode",
                "prolific_completion_url", "prolific_completion_code",
                "prolific_redirected", "answers", "comprehension_attempts",
                "comprehension_passed", "attention_failed_count", "payment_values",
                "scroll_to_top",
            ):
                setattr(updated, field, deepcopy(getattr(proposed_state, field)))
            if not current.treatment_bound and proposed_state.treatment_bound:
                updated.experimental_condition = proposed_state.experimental_condition
                updated.score_frame = proposed_state.score_frame
                updated.monthly_score_feedback = proposed_state.monthly_score_feedback
                updated.treatment_bound = True
            updated.state_version = current.state_version + 1
            self._raise_failure("save_stage", "during")
            self._sessions[session_id] = updated
            return self._remember(session_id, "save_stage", request_id, payload_hash, updated)

    def save_quality_transition(
        self,
        proposed_state,
        quality_events,
        *,
        expected_version,
        request_id,
        payload_hash,
        psychometric_phase=None,
    ):
        with self._lock:
            session_id = proposed_state.session_id
            hit = self._idempotent(session_id, "quality_transition", request_id, payload_hash)
            if hit:
                return hit
            self._raise_failure("save_quality_transition", "before")
            current = self._required(session_id)
            self._expected(current, expected_version)
            updated = deepcopy(current)
            for field in (
                "page", "answers", "comprehension_attempts", "comprehension_passed",
                "attention_failed_count",
            ):
                setattr(updated, field, deepcopy(getattr(proposed_state, field)))
            updated.state_version = current.state_version + 1
            next_quality = deepcopy(self._quality.get(session_id, [])) + deepcopy(quality_events)
            self._raise_failure("save_quality_transition", "during")
            self._sessions[session_id] = updated
            self._quality[session_id] = next_quality
            return self._remember(session_id, "quality_transition", request_id, payload_hash, updated)

    def commit_month_decision(
        self,
        proposed_state,
        result,
        *,
        expected_version,
        expected_month,
        request_id,
        payload_hash,
    ):
        with self._lock:
            session_id = proposed_state.session_id
            hit = self._idempotent(session_id, "month_decision", request_id, payload_hash)
            if hit:
                return hit
            self._raise_failure("commit_month_decision", "before")
            current = self._required(session_id)
            self._expected(current, expected_version)
            if current.month != expected_month:
                raise ConcurrencyConflict("Month is no longer current", current_version=current.state_version)
            if current.pending_month_result or expected_month in self._ledgers[session_id]:
                raise ConcurrencyConflict("Month already has a committed decision", current_version=current.state_version)
            self._validate_treatment(current, proposed_state)
            updated = deepcopy(proposed_state)
            updated.treatment_bound = True
            updated.state_version = current.state_version + 1
            next_ledger = deepcopy(self._ledgers[session_id])
            next_ledger[expected_month] = deepcopy(result)
            self._raise_failure("commit_month_decision", "during")
            self._sessions[session_id] = updated
            self._ledgers[session_id] = next_ledger
            return self._remember(
                session_id,
                "month_decision",
                request_id,
                payload_hash,
                updated,
                result=result,
            )

    def acknowledge_month_feedback(
        self,
        proposed_state,
        *,
        expected_version,
        expected_month,
        request_id,
        payload_hash,
    ):
        with self._lock:
            session_id = proposed_state.session_id
            hit = self._idempotent(session_id, "feedback_ack", request_id, payload_hash)
            if hit:
                return hit
            self._raise_failure("acknowledge_month_feedback", "before")
            current = self._required(session_id)
            self._expected(current, expected_version)
            if current.month != expected_month or not current.pending_month_result:
                raise ConcurrencyConflict("Feedback is no longer pending", current_version=current.state_version)
            if expected_month not in self._ledgers[session_id]:
                raise PersistenceWriteError("Cannot acknowledge feedback without its durable month result")
            updated = deepcopy(proposed_state)
            updated.state_version = current.state_version + 1
            self._raise_failure("acknowledge_month_feedback", "during")
            self._sessions[session_id] = updated
            return self._remember(
                session_id,
                "feedback_ack",
                request_id,
                payload_hash,
                updated,
                result=self._ledgers[session_id][expected_month],
            )

    def finalize(
        self,
        proposed_state,
        *,
        expected_version,
        account_key,
        request_id,
        payload_hash,
        pre_sections,
        post_sections,
    ):
        del pre_sections, post_sections
        with self._lock:
            session_id = proposed_state.session_id
            hit = self._idempotent(session_id, "finalize", request_id, payload_hash)
            if hit:
                return hit
            self._raise_failure("finalize", "before")
            current = self._required(session_id)
            if current.submission_finalized:
                return RepositoryCommit(deepcopy(current), idempotency_hit=True)
            self._expected(current, expected_version)
            if len(self._ledgers[session_id]) != 24:
                raise PersistenceWriteError("Finalization requires 24 structured month results")
            if self._accounts.get(account_key) not in (None, session_id):
                raise ConcurrencyConflict("Account is linked to another active session")
            updated = deepcopy(proposed_state)
            updated.state_version = current.state_version + 1
            self._raise_failure("finalize", "during")
            self._sessions[session_id] = updated
            self._finalizations[session_id] = self._finalizations.get(session_id, 0) + 1
            self._accounts.pop(account_key, None)
            self._completed_accounts.add(account_key)
            return self._remember(session_id, "finalize", request_id, payload_hash, updated)

    def seed_legacy(self, state, *, account_key):
        with self._lock:
            self._sessions[state.session_id] = deepcopy(state)
            self._ledgers[state.session_id] = {}
            self._quality[state.session_id] = []
            self._accounts[account_key] = state.session_id
            self._legacy.add(state.session_id)

    def raw_state(self, session_id):
        with self._lock:
            return deepcopy(self._required(session_id))

    def replace_state_and_ledger(self, state):
        with self._lock:
            self._sessions[state.session_id] = deepcopy(state)
            self._ledgers[state.session_id] = {
                int(result["month"]): deepcopy(result)
                for result in state.monthly_results
            }
            self._legacy.discard(state.session_id)

    def month_results(self, session_id):
        with self._lock:
            return [deepcopy(self._ledgers.get(session_id, {})[month]) for month in sorted(self._ledgers.get(session_id, {}))]

    def month_result_count(self, session_id):
        with self._lock:
            return len(self._ledgers.get(session_id, {}))

    def quality_checks(self, session_id):
        with self._lock:
            return deepcopy(self._quality.get(session_id, []))

    def finalization_count(self, session_id):
        with self._lock:
            return self._finalizations.get(session_id, 0)

    def _backfill_legacy_locked(self, session_id):
        state = self._sessions[session_id]
        results = deepcopy(state.monthly_results)
        months = [int(result.get("month", 0)) for result in results]
        if months != list(range(1, len(months) + 1)):
            raise PersistenceReadError("Legacy month results are not consecutive")
        for result in results:
            self._ledgers[session_id].setdefault(int(result["month"]), result)
        if results:
            state.treatment_bound = True
            state.state_version += 1
        self._legacy.discard(session_id)

    def _required(self, session_id):
        state = self._sessions.get(session_id)
        if state is None:
            raise PersistenceWriteError(f"Unknown participant session {session_id}")
        return state

    @staticmethod
    def _expected(current, expected_version):
        if current.state_version != expected_version:
            raise ConcurrencyConflict("State version is stale", current_version=current.state_version)

    @staticmethod
    def _validate_treatment(current, proposed):
        if not current.treatment_bound:
            return
        current_treatment = (
            current.experimental_condition,
            current.score_frame,
            current.monthly_score_feedback,
        )
        proposed_treatment = (
            proposed.experimental_condition,
            proposed.score_frame,
            proposed.monthly_score_feedback,
        )
        if current_treatment != proposed_treatment:
            raise TreatmentConflict("Treatment is immutable after binding", current_version=current.state_version)

    def _idempotent(self, session_id, operation, request_id, payload_hash):
        stored = self._idempotency.get((session_id, operation, request_id))
        if not stored:
            return None
        if stored["payload_hash"] != payload_hash:
            raise IdempotencyConflict("Idempotency key was reused with a different payload")
        current = self._sessions.get(session_id) or stored["state"]
        return RepositoryCommit(
            deepcopy(current),
            deepcopy(stored["result"]),
            idempotency_hit=True,
        )

    def _remember(self, session_id, operation, request_id, payload_hash, state, result=None):
        commit = RepositoryCommit(deepcopy(state), deepcopy(result), idempotency_hit=False)
        self._idempotency[(session_id, operation, request_id)] = {
            "payload_hash": payload_hash,
            "state": deepcopy(state),
            "result": deepcopy(result),
        }
        return commit

    def _raise_failure(self, operation, phase, *, read=False):
        if self._failure != (operation, phase):
            return
        self._failure = None
        error = PersistenceReadError if read else PersistenceWriteError
        raise error(f"Injected {operation} failure at {phase}")


__all__ = ["InMemoryExperimentRepository"]
