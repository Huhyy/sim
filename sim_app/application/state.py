"""Framework-neutral participant experiment state.

The model intentionally mirrors the existing Streamlit/checkpoint shape.  It is
not a new persistence contract: ``to_checkpoint`` emits the same fields that
the legacy checkpoint collector emitted, and runtime-only fields remain
runtime-only.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping

from sim_app.domain.experimental_conditions import (
    DEFAULT_EXPERIMENTAL_CONDITION,
    DEFAULT_PAYMENT_STATUS,
)
from sim_app.domain.loan import Loan
from sim_app.domain.overdraft import Overdraft


def _new_loan() -> Loan:
    return Loan(balance=7000.0, annual_interest=0.0835, months=24)


def _new_overdraft() -> Overdraft:
    return Overdraft(limit=3000.0, annual_interest=0.18)


@dataclass
class ParticipantState:
    """All research-relevant and progression-relevant participant state."""

    scenario_version: str
    state_version: int = 0
    page: str = "home"
    session_id: str | None = None
    admin_return_page: str | None = None
    language: str = "en"
    month: int = 1
    study_session_id: str | None = None
    study_session_code: str | None = None
    participant_code: str | None = None
    prolific_pid: str | None = None
    prolific_study_id: str | None = None
    prolific_session_id: str | None = None
    prolific_mode: bool = False
    prolific_access_error: str | None = None
    prolific_completion_url: str | None = None
    prolific_completion_code: str | None = None
    prolific_redirected: bool = False
    experimental_condition: str = DEFAULT_EXPERIMENTAL_CONDITION
    score_frame: str = "gain_frame"
    monthly_score_feedback: str = "displayed"
    treatment_bound: bool = False
    loan: Loan = field(default_factory=_new_loan)
    overdraft: Overdraft = field(default_factory=_new_overdraft)
    savings: Any = None
    total_score: float = 0
    monthly_points: float = 0.0
    accumulated_costs: float = 0.0
    monthly_results: list[dict[str, Any]] = field(default_factory=list)
    pending_month_result: dict[str, Any] | None = None
    final_score: float | None = None
    final_score_breakdown: dict[str, Any] | None = None
    answers: dict[str, Any] = field(default_factory=dict)
    scroll_to_top: bool = False
    submission_finalized: bool = False
    completion_status: str = "not_started"
    comprehension_attempts: int = 0
    comprehension_passed: bool = False
    attention_failed_count: int = 0
    already_completed: bool = False
    saved: bool = False
    payment_status: str = DEFAULT_PAYMENT_STATUS
    payment_values: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def initial(cls, scenario_version: str) -> "ParticipantState":
        return cls(scenario_version=scenario_version)

    @classmethod
    def from_runtime_state(
        cls,
        runtime_state: Mapping[str, Any],
        scenario_version: str,
    ) -> "ParticipantState":
        defaults = cls.initial(scenario_version)
        get = runtime_state.get if hasattr(runtime_state, "get") else lambda key, default=None: getattr(runtime_state, key, default)
        items = runtime_state.items() if hasattr(runtime_state, "items") else vars(runtime_state).items()
        payment_values = {
            key: value
            for key, value in items
            if str(key).startswith("payment_")
        }
        return cls(
            # Checkpoint collection historically always stamped the running
            # scenario version rather than trusting session state.
            scenario_version=scenario_version,
            state_version=int(get("state_version", defaults.state_version) or 0),
            page=get("page", defaults.page),
            session_id=get("session_id"),
            admin_return_page=get("admin_return_page"),
            language=get("language", defaults.language),
            month=int(get("month", defaults.month)),
            study_session_id=get("study_session_id"),
            study_session_code=get("study_session_code"),
            participant_code=get("participant_code"),
            prolific_pid=get("prolific_pid"),
            prolific_study_id=get("prolific_study_id"),
            prolific_session_id=get("prolific_session_id"),
            prolific_mode=bool(get("prolific_mode", defaults.prolific_mode)),
            prolific_access_error=get("prolific_access_error"),
            prolific_completion_url=get("prolific_completion_url"),
            prolific_completion_code=get("prolific_completion_code"),
            prolific_redirected=bool(get("prolific_redirected", defaults.prolific_redirected)),
            experimental_condition=get("experimental_condition", defaults.experimental_condition),
            score_frame=get("score_frame", defaults.score_frame),
            monthly_score_feedback=get("monthly_score_feedback", defaults.monthly_score_feedback),
            treatment_bound=bool(get("treatment_bound", defaults.treatment_bound)),
            loan=get("loan", defaults.loan),
            overdraft=get("overdraft", defaults.overdraft),
            savings=get("savings"),
            total_score=get("total_score", defaults.total_score),
            monthly_points=get("monthly_points", defaults.monthly_points),
            accumulated_costs=get("accumulated_costs", defaults.accumulated_costs),
            monthly_results=get("monthly_results", defaults.monthly_results),
            pending_month_result=get("pending_month_result"),
            final_score=get("final_score"),
            final_score_breakdown=get("final_score_breakdown"),
            answers=get("answers", defaults.answers),
            scroll_to_top=bool(get("scroll_to_top", defaults.scroll_to_top)),
            submission_finalized=bool(get("submission_finalized", defaults.submission_finalized)),
            completion_status=get("completion_status", defaults.completion_status),
            comprehension_attempts=int(get("comprehension_attempts", defaults.comprehension_attempts) or 0),
            comprehension_passed=bool(get("comprehension_passed", defaults.comprehension_passed)),
            attention_failed_count=int(get("attention_failed_count", defaults.attention_failed_count) or 0),
            already_completed=bool(get("already_completed", defaults.already_completed)),
            saved=bool(get("saved", defaults.saved)),
            payment_status=get("payment_status", DEFAULT_PAYMENT_STATUS),
            payment_values=payment_values,
        )

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint: Mapping[str, Any],
        scenario_version: str,
    ) -> "ParticipantState":
        defaults = cls.initial(scenario_version)
        page = checkpoint.get("page", defaults.page)
        if page == "pre_questions":
            page = "pre_question_0"
        elif page == "post_questions":
            page = "post_question_0"
        elif page == "month_feedback" and not checkpoint.get("pending_month_result"):
            page = "simulation"

        loan = Loan(
            balance=float(checkpoint.get("loan_balance", 7000.0)),
            annual_interest=0.0835,
            months=24,
        )
        overdraft = Overdraft(limit=3000.0, annual_interest=0.18)
        overdraft.balance = round(float(checkpoint.get("overdraft_balance", 0.0)), 2)

        monthly_results = checkpoint.get("monthly_results", [])
        return cls(
            scenario_version=checkpoint.get("scenario_version", scenario_version),
            state_version=int(checkpoint.get("state_version", 0) or 0),
            page=page,
            admin_return_page=checkpoint.get("admin_return_page"),
            language=checkpoint.get("language", defaults.language),
            month=int(checkpoint.get("month", defaults.month)),
            study_session_id=checkpoint.get("study_session_id"),
            study_session_code=checkpoint.get("study_session_code"),
            participant_code=checkpoint.get("participant_code"),
            prolific_pid=checkpoint.get("prolific_pid"),
            prolific_study_id=checkpoint.get("prolific_study_id"),
            prolific_session_id=checkpoint.get("prolific_session_id"),
            prolific_mode=bool(checkpoint.get("prolific_mode", defaults.prolific_mode)),
            prolific_completion_url=checkpoint.get("prolific_completion_url"),
            prolific_completion_code=checkpoint.get("prolific_completion_code"),
            prolific_redirected=bool(checkpoint.get("prolific_redirected", defaults.prolific_redirected)),
            experimental_condition=checkpoint.get("experimental_condition", defaults.experimental_condition),
            score_frame=checkpoint.get("score_frame", defaults.score_frame),
            monthly_score_feedback=checkpoint.get("monthly_score_feedback", defaults.monthly_score_feedback),
            treatment_bound=bool(
                checkpoint.get("treatment_bound")
                or checkpoint.get("prolific_pid")
                or checkpoint.get("study_session_id")
                or monthly_results
                or checkpoint.get("pending_month_result")
                or int(checkpoint.get("month", 1) or 1) > 1
            ),
            loan=loan,
            overdraft=overdraft,
            savings=checkpoint.get("savings"),
            total_score=checkpoint.get("total_score", defaults.total_score),
            monthly_points=checkpoint.get("monthly_points", defaults.monthly_points),
            accumulated_costs=checkpoint.get("accumulated_costs", defaults.accumulated_costs),
            monthly_results=monthly_results,
            pending_month_result=checkpoint.get("pending_month_result"),
            final_score=checkpoint.get("final_score"),
            final_score_breakdown=checkpoint.get("final_score_breakdown"),
            answers=checkpoint.get("answers", {}),
            scroll_to_top=bool(checkpoint.get("scroll_to_top", False)),
            submission_finalized=bool(checkpoint.get("submission_finalized", False)),
            completion_status=(
                checkpoint.get("completion_status")
                or ("complete" if checkpoint.get("submission_finalized") else "not_started")
            ),
            comprehension_attempts=int(checkpoint.get("comprehension_attempts", 0) or 0),
            comprehension_passed=bool(checkpoint.get("comprehension_passed", False)),
            attention_failed_count=int(checkpoint.get("attention_failed_count", 0) or 0),
            saved=bool(checkpoint.get("submission_finalized", False)),
            payment_values=dict(checkpoint.get("payment_values") or {}),
        )

    def copy(self) -> "ParticipantState":
        return deepcopy(self)

    def to_checkpoint(self) -> dict[str, Any]:
        """Return the unchanged legacy checkpoint persistence contract."""
        return {
            "scenario_version": self.scenario_version,
            "page": self.page,
            "admin_return_page": self.admin_return_page,
            "language": self.language,
            "month": self.month,
            "study_session_id": self.study_session_id,
            "study_session_code": self.study_session_code,
            "participant_code": self.participant_code,
            "prolific_pid": self.prolific_pid,
            "prolific_study_id": self.prolific_study_id,
            "prolific_session_id": self.prolific_session_id,
            "prolific_mode": self.prolific_mode,
            "prolific_completion_url": self.prolific_completion_url,
            "prolific_completion_code": self.prolific_completion_code,
            "prolific_redirected": self.prolific_redirected,
            "experimental_condition": self.experimental_condition,
            "score_frame": self.score_frame,
            "monthly_score_feedback": self.monthly_score_feedback,
            "loan_balance": self.loan.balance,
            "overdraft_balance": self.overdraft.balance,
            "savings": self.savings,
            "total_score": self.total_score,
            "monthly_points": self.monthly_points,
            "accumulated_costs": self.accumulated_costs,
            "monthly_results": self.monthly_results,
            "pending_month_result": self.pending_month_result,
            "final_score": self.final_score,
            "final_score_breakdown": self.final_score_breakdown,
            "answers": self.answers,
            "comprehension_attempts": self.comprehension_attempts,
            "comprehension_passed": self.comprehension_passed,
            "attention_failed_count": self.attention_failed_count,
            "payment_values": self.payment_values,
        }

    def to_resume_projection(self) -> dict[str, Any]:
        """Return non-authoritative UI/resume state for Phase 3 persistence.

        Economic history, balances, treatment, completion, and scores are
        deliberately excluded because their structured database columns and
        ledgers are authoritative.
        """
        return {
            "scenario_version": self.scenario_version,
            "page": self.page,
            "admin_return_page": self.admin_return_page,
            "language": self.language,
            "scroll_to_top": self.scroll_to_top,
            "answers": self.answers,
            "comprehension_attempts": self.comprehension_attempts,
            "comprehension_passed": self.comprehension_passed,
            "attention_failed_count": self.attention_failed_count,
            "payment_values": self.payment_values,
            "prolific_completion_url": self.prolific_completion_url,
            "prolific_completion_code": self.prolific_completion_code,
            "prolific_redirected": self.prolific_redirected,
        }

    def to_runtime_defaults(self) -> dict[str, Any]:
        """Return the exact legacy default key set used by Streamlit."""
        return {
            "page": self.page,
            "session_id": self.session_id,
            "state_version": self.state_version,
            "language": self.language,
            "month": self.month,
            "study_session_id": self.study_session_id,
            "study_session_code": self.study_session_code,
            "participant_code": self.participant_code,
            "prolific_pid": self.prolific_pid,
            "prolific_study_id": self.prolific_study_id,
            "prolific_session_id": self.prolific_session_id,
            "prolific_mode": self.prolific_mode,
            "prolific_access_error": self.prolific_access_error,
            "prolific_completion_url": self.prolific_completion_url,
            "prolific_completion_code": self.prolific_completion_code,
            "prolific_redirected": self.prolific_redirected,
            "experimental_condition": self.experimental_condition,
            "score_frame": self.score_frame,
            "monthly_score_feedback": self.monthly_score_feedback,
            "treatment_bound": self.treatment_bound,
            "loan": self.loan,
            "overdraft": self.overdraft,
            "savings": self.savings,
            "total_score": self.total_score,
            "monthly_points": self.monthly_points,
            "accumulated_costs": self.accumulated_costs,
            "monthly_results": self.monthly_results,
            "pending_month_result": self.pending_month_result,
            "final_score": self.final_score,
            "final_score_breakdown": self.final_score_breakdown,
            "answers": self.answers,
            "scroll_to_top": self.scroll_to_top,
            "submission_finalized": self.submission_finalized,
            "completion_status": self.completion_status,
            "comprehension_attempts": self.comprehension_attempts,
            "comprehension_passed": self.comprehension_passed,
            "attention_failed_count": self.attention_failed_count,
            "already_completed": self.already_completed,
            "saved": self.saved,
            "scenario_version": self.scenario_version,
        }

    def apply_to_runtime_state(
        self,
        runtime_state: MutableMapping[str, Any],
        *,
        include_session_id: bool = True,
    ) -> None:
        values = self.to_runtime_defaults()
        if not include_session_id:
            values.pop("session_id", None)
        values["admin_return_page"] = self.admin_return_page
        for key, value in values.items():
            runtime_state[key] = value
        for key, value in self.payment_values.items():
            runtime_state[key] = value


__all__ = ["ParticipantState"]
