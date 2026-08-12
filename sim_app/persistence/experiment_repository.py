"""Supabase/Postgres implementation of the atomic experiment repository."""

from __future__ import annotations

from sim_app.application.errors import (
    ConcurrencyConflict,
    IdempotencyConflict,
    PersistenceReadError,
    PersistenceWriteError,
    SessionNotFound,
    TreatmentConflict,
)
from sim_app.application.instrumentation import DEFAULT_METRICS
from sim_app.application.repositories import RepositoryCommit
from sim_app.application.state import ParticipantState
from sim_app.config import SCENARIO_VERSION
from sim_app.domain.scoring import get_bonus_max_session
from sim_app.infra.supabase import _require_client
from sim_app.persistence.mappers import (
    _demographic_answers,
    _month_result_from_row,
    _month_result_row,
    _psychometric_rows,
)


class SupabaseExperimentRepository:
    def __init__(self, client=None, *, metrics=None):
        self._client = client
        self.metrics = metrics or DEFAULT_METRICS

    @property
    def client(self):
        if self._client is None:
            # The synchronous Supabase/httpx client is not safe to share
            # concurrently across Streamlit or future transport worker threads.
            # Infrastructure returns one reusable client per worker thread.
            return _require_client()
        return self._client

    def load(self, session_id):
        return self._load(session_id, allow_legacy_backfill=True)

    def find_session_id_for_account(self, account_key):
        try:
            with self.metrics.measure("find_session_for_account", layer="database"):
                self.metrics.increment("database_request_count")
                response = (
                    self.client.table("resume_links")
                    .select("session_id")
                    .eq("account_key", account_key)
                    .limit(1)
                    .execute()
                )
            rows = getattr(response, "data", None) or []
            return str(rows[0]["session_id"]) if rows else None
        except Exception as exc:
            raise PersistenceReadError("Could not resolve participant session ownership") from exc

    def account_owns_session(self, account_key, session_id):
        linked = self.find_session_id_for_account(account_key)
        return linked == str(session_id)

    def creation_request_payload_hash(self, session_id, request_id):
        try:
            with self.metrics.measure("verify_creation_request", layer="database"):
                self.metrics.increment("database_request_count")
                response = (
                    self.client.table("experiment_idempotency")
                    .select("payload_hash")
                    .eq("session_id", session_id)
                    .eq("operation", "create_session")
                    .eq("request_id", request_id)
                    .limit(1)
                    .execute()
                )
            rows = getattr(response, "data", None) or []
            return str(rows[0]["payload_hash"]) if rows else None
        except Exception as exc:
            raise PersistenceReadError("Could not verify the session creation retry") from exc

    def finalization_request_matches(self, session_id, request_id):
        try:
            with self.metrics.measure("verify_finalization_request", layer="database"):
                self.metrics.increment("database_request_count")
                response = (
                    self.client.table("participant_sessions")
                    .select("finalization_request_id")
                    .eq("id", session_id)
                    .eq("finalization_request_id", request_id)
                    .limit(1)
                    .execute()
                )
            return bool(getattr(response, "data", None) or [])
        except Exception as exc:
            raise PersistenceReadError("Could not verify the finalization retry") from exc

    def load_study_session_by_code(self, session_code):
        try:
            with self.metrics.measure("load_study_session_by_code", layer="database"):
                self.metrics.increment("database_request_count")
                response = (
                    self.client.table("admin_study_sessions")
                    .select("*")
                    .eq("session_code", str(session_code).strip())
                    .eq("status", "active")
                    .limit(1)
                    .execute()
                )
            rows = getattr(response, "data", None) or []
            return dict(rows[0]) if rows else None
        except Exception as exc:
            raise PersistenceReadError("Could not resolve the study session code") from exc

    def _load(self, session_id, *, allow_legacy_backfill):
        try:
            with self.metrics.measure("load_participant", layer="database"):
                self.metrics.increment("database_request_count")
                self.metrics.increment("database.load_participant.request_count")
                response = (
                    self.client.table("participant_sessions")
                    .select("*")
                    .eq("id", session_id)
                    .limit(1)
                    .execute()
                )
            rows = getattr(response, "data", None) or []
            if not rows:
                return None
            row = rows[0]
            with self.metrics.measure("load_month_results", layer="database"):
                self.metrics.increment("database_request_count")
                self.metrics.increment("database.load_month_results.request_count")
                month_response = (
                    self.client.table("month_results")
                    .select("*")
                    .eq("session_id", session_id)
                    .order("month_number")
                    .execute()
                )
            month_rows = getattr(month_response, "data", None) or []
            checkpoint = dict(row.get("checkpoint") or {})
            legacy_results = checkpoint.get("monthly_results") or []
            legacy_checkpoint = "monthly_results" in checkpoint or "pending_month_result" in checkpoint
            if allow_legacy_backfill and legacy_checkpoint:
                self._backfill_legacy(session_id, checkpoint, legacy_results)
                return self._load(session_id, allow_legacy_backfill=False)

            summary = None
            if row.get("status") == "completed" or row.get("completion_status") not in (None, "not_started"):
                with self.metrics.measure("load_summary", layer="database"):
                    self.metrics.increment("database_request_count")
                    self.metrics.increment("database.load_summary.request_count")
                    summary_response = (
                        self.client.table("session_summaries")
                        .select("*")
                        .eq("session_id", session_id)
                        .limit(1)
                        .execute()
                    )
                summaries = getattr(summary_response, "data", None) or []
                summary = summaries[0] if summaries else None
            return _state_from_rows(row, checkpoint, month_rows, summary)
        except (ConcurrencyConflict, IdempotencyConflict, TreatmentConflict, PersistenceReadError):
            raise
        except Exception as exc:
            raise PersistenceReadError(f"Could not read participant session {session_id}: {exc}") from exc

    def create_session(self, state, *, account_key, request_id, payload_hash):
        data = self._rpc(
            "claim_participant_session_v3",
            {
                "p_session_id": state.session_id,
                "p_account_key": account_key,
                "p_request_id": request_id,
                "p_payload_hash": payload_hash,
                "p_state": _state_payload(state),
            },
        )
        session_id = data.get("session_id") or state.session_id
        return self._committed(session_id, data)

    def save_stage(self, proposed_state, *, expected_version, request_id, payload_hash):
        data = self._rpc(
            "commit_stage_transition_v3",
            {
                "p_session_id": proposed_state.session_id,
                "p_expected_version": expected_version,
                "p_request_id": request_id,
                "p_payload_hash": payload_hash,
                "p_state": _state_payload(proposed_state),
            },
        )
        return self._committed(proposed_state.session_id, data)

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
        result_row = _month_result_row(
            proposed_state.session_id,
            result,
            bonus_max_session=get_bonus_max_session(),
            metadata={
                "study_session_id": proposed_state.study_session_id,
                "study_session_code": proposed_state.study_session_code,
                "participant_code": proposed_state.participant_code,
            },
            decision_request_id=request_id,
            committed_state_version=expected_version + 1,
        )
        data = self._rpc(
            "commit_month_decision_v3",
            {
                "p_session_id": proposed_state.session_id,
                "p_expected_version": expected_version,
                "p_expected_month": expected_month,
                "p_request_id": request_id,
                "p_payload_hash": payload_hash,
                "p_state": _state_payload(proposed_state),
                "p_result": result_row,
            },
        )
        return self._committed(proposed_state.session_id, data, result=data.get("result") or result)

    def save_quality_transition(
        self,
        proposed_state,
        quality_events,
        *,
        expected_version,
        request_id,
        payload_hash,
    ):
        data = self._rpc(
            "commit_quality_transition_v3",
            {
                "p_session_id": proposed_state.session_id,
                "p_expected_version": expected_version,
                "p_request_id": request_id,
                "p_payload_hash": payload_hash,
                "p_state": _state_payload(proposed_state),
                "p_events": quality_events,
            },
        )
        return self._committed(proposed_state.session_id, data)

    def acknowledge_month_feedback(
        self,
        proposed_state,
        *,
        expected_version,
        expected_month,
        request_id,
        payload_hash,
    ):
        data = self._rpc(
            "acknowledge_month_feedback_v3",
            {
                "p_session_id": proposed_state.session_id,
                "p_expected_version": expected_version,
                "p_expected_month": expected_month,
                "p_request_id": request_id,
                "p_payload_hash": payload_hash,
                "p_state": _state_payload(proposed_state),
            },
        )
        return self._committed(proposed_state.session_id, data, result=data.get("result"))

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
        metadata = {
            "study_session_id": proposed_state.study_session_id,
            "study_session_code": proposed_state.study_session_code,
            "participant_code": proposed_state.participant_code,
        }
        data = self._rpc(
            "finalize_experiment_v3",
            {
                "p_session_id": proposed_state.session_id,
                "p_expected_version": expected_version,
                "p_account_key": account_key,
                "p_request_id": request_id,
                "p_payload_hash": payload_hash,
                "p_state": _state_payload(proposed_state),
                "p_summary": proposed_state.final_score_breakdown or {},
                "p_demographics": _demographic_answers(proposed_state.answers),
                "p_pre_answers": _psychometric_rows(
                    proposed_state.session_id,
                    proposed_state.answers,
                    pre_sections,
                    metadata=metadata,
                ),
                "p_post_answers": _psychometric_rows(
                    proposed_state.session_id,
                    proposed_state.answers,
                    post_sections,
                    metadata=metadata,
                ),
                "p_feedback": proposed_state.answers.get("feedback"),
            },
        )
        return self._committed(proposed_state.session_id, data)

    def _backfill_legacy(self, session_id, checkpoint, legacy_results):
        checkpoint = dict(checkpoint)
        legacy_results = list(legacy_results)
        pending = checkpoint.get("pending_month_result")
        if pending and not any(int(item.get("month", 0)) == int(pending.get("month", 0)) for item in legacy_results):
            legacy_results.append(pending)
            checkpoint["loan_balance"] = pending.get("credit_final", checkpoint.get("loan_balance"))
            checkpoint["overdraft_balance"] = pending.get("overdraft_final", checkpoint.get("overdraft_balance"))
            checkpoint["total_score"] = float(checkpoint.get("total_score") or 0) + float(pending.get("monthly_score") or 0)
            checkpoint["monthly_points"] = float(checkpoint.get("monthly_points") or 0) + float(pending.get("monthly_score") or 0)
            checkpoint["accumulated_costs"] = float(checkpoint.get("accumulated_costs") or 0) + float(pending.get("costs_this_month") or 0)
        rows = [
            _month_result_row(
                session_id,
                result,
                bonus_max_session=get_bonus_max_session(),
                metadata={
                    "study_session_id": checkpoint.get("study_session_id"),
                    "study_session_code": checkpoint.get("study_session_code"),
                    "participant_code": checkpoint.get("participant_code"),
                },
                decision_request_id=f"legacy-backfill:{session_id}:{int(result.get('month', 0))}",
            )
            for result in legacy_results
        ]
        self._rpc(
            "backfill_legacy_session_v3",
            {"p_session_id": session_id, "p_checkpoint": checkpoint, "p_results": rows},
        )

    def _committed(self, session_id, data, *, result=None):
        state = self._load(session_id, allow_legacy_backfill=False)
        if state is None:
            raise PersistenceReadError("Committed participant session could not be reloaded")
        return RepositoryCommit(
            state,
            result=result,
            idempotency_hit=bool(data.get("idempotency_hit")),
        )

    def _rpc(self, name, params):
        try:
            with self.metrics.measure(name, layer="database"):
                self.metrics.increment("database_request_count")
                self.metrics.increment(f"database.{name}.request_count")
                response = self.client.rpc(name, params).execute()
            data = getattr(response, "data", None)
            if isinstance(data, list):
                data = data[0] if data else {}
            return data or {}
        except Exception as exc:
            _raise_mapped_write_error(exc)


def _state_payload(state):
    return {
        "scenario_version": state.scenario_version,
        "page": state.page,
        "current_month": state.month,
        "loan_balance": state.loan.balance,
        "overdraft_balance": state.overdraft.balance,
        "total_score": state.total_score,
        "monthly_points": state.monthly_points,
        "accumulated_costs": state.accumulated_costs,
        "pending_month_number": (
            int(state.pending_month_result.get("month", 0))
            if state.pending_month_result
            else None
        ),
        "study_session_id": state.study_session_id,
        "study_session_code": state.study_session_code,
        "participant_code": state.participant_code,
        "prolific_pid": state.prolific_pid,
        "prolific_study_id": state.prolific_study_id,
        "prolific_session_id": state.prolific_session_id,
        "experimental_condition": state.experimental_condition,
        "score_frame": state.score_frame,
        "monthly_score_feedback": state.monthly_score_feedback,
        "treatment_bound": state.treatment_bound,
        "completion_status": state.completion_status,
        "resume_projection": state.to_resume_projection(),
    }


def _state_from_rows(row, checkpoint, month_rows, summary):
    state = ParticipantState.from_checkpoint(checkpoint, SCENARIO_VERSION)
    state.session_id = row.get("id")
    state.state_version = int(row.get("state_version") or 0)
    state.page = row.get("current_page") or checkpoint.get("page") or state.page
    state.month = int(row.get("current_month") or checkpoint.get("month") or state.month)
    state.loan.balance = float(row.get("loan_balance") if row.get("loan_balance") is not None else state.loan.balance)
    state.overdraft.balance = float(
        row.get("overdraft_balance") if row.get("overdraft_balance") is not None else state.overdraft.balance
    )
    state.total_score = float(row.get("total_score") if row.get("total_score") is not None else state.total_score)
    state.monthly_points = float(row.get("monthly_points") if row.get("monthly_points") is not None else state.monthly_points)
    state.accumulated_costs = float(
        row.get("accumulated_costs") if row.get("accumulated_costs") is not None else state.accumulated_costs
    )
    for field in (
        "study_session_id", "study_session_code", "participant_code", "prolific_pid",
        "prolific_study_id", "prolific_session_id", "experimental_condition",
        "score_frame", "monthly_score_feedback",
    ):
        if row.get(field) is not None:
            setattr(state, field, row.get(field))
    state.prolific_mode = bool(state.prolific_pid)
    state.treatment_bound = bool(row.get("treatment_bound"))
    state.comprehension_attempts = int(row.get("comprehension_attempts") or 0)
    state.comprehension_passed = bool(row.get("comprehension_passed"))
    state.attention_failed_count = int(row.get("attention_failed_count") or 0)
    state.completion_status = row.get("completion_status") or "not_started"
    state.monthly_results = [_month_result_from_row(item) for item in month_rows]
    pending_month = row.get("pending_month_number")
    state.pending_month_result = next(
        (result for result in state.monthly_results if int(result.get("month", 0)) == int(pending_month or 0)),
        None,
    )
    state.submission_finalized = row.get("status") == "completed" or state.completion_status != "not_started"
    state.saved = state.submission_finalized
    if summary:
        state.final_score = float(summary.get("final_score")) if summary.get("final_score") is not None else None
        state.final_score_breakdown = dict(summary)
        state.payment_status = summary.get("payment_status") or state.payment_status
    return state


def _raise_mapped_write_error(exc):
    message = str(exc)
    if "SIM_IDEMPOTENCY_CONFLICT" in message:
        raise IdempotencyConflict("Idempotency key was reused with a different payload") from exc
    if "SIM_TREATMENT_CONFLICT" in message:
        raise TreatmentConflict("Treatment is immutable after binding") from exc
    if "SIM_CONFLICT" in message or "SIM_MONTH_CONFLICT" in message:
        raise ConcurrencyConflict(message) from exc
    if "SIM_NOT_FOUND" in message:
        raise SessionNotFound(message) from exc
    if "23505" in message or "duplicate key" in message.lower():
        raise ConcurrencyConflict("A participant identity or request was claimed concurrently") from exc
    raise PersistenceWriteError(message) from exc


__all__ = ["SupabaseExperimentRepository"]
