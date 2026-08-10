"""Framework-neutral participant experiment commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sim_app.application.progression import (
    page_after_comprehension,
    page_after_consent,
    page_after_demographics,
    page_after_final_score,
    page_after_instructions,
    page_after_month_feedback,
    page_after_post_question,
    page_after_pre_question,
    page_after_profile,
)
from sim_app.application.state import ParticipantState
from sim_app.domain.experimental_conditions import condition_from_record
from sim_app.domain.scoring import (
    compute_final_score_from_results,
    get_final_score_breakdown_from_results,
    normalize_month_result_score,
)
from sim_app.domain.simulation import compute_month_result


@dataclass(frozen=True)
class CommandResult:
    state: ParticipantState
    next_page: str | None = None
    feedback: dict[str, Any] | None = None


def go_to_page(state: ParticipantState, page: str, *, scroll_to_top: bool = True) -> CommandResult:
    updated = state.copy()
    updated.page = page
    if scroll_to_top:
        updated.scroll_to_top = True
    return CommandResult(updated, page)


def accept_consent(state: ParticipantState, *, anti_ai_declaration: bool = False) -> CommandResult:
    updated = state.copy()
    updated.answers["consent_agreed"] = "1 - Da"
    if updated.prolific_mode:
        updated.answers["anti_ai_declaration"] = bool(anti_ai_declaration)
    updated.scroll_to_top = True
    updated.page = page_after_consent(True)
    return CommandResult(updated, updated.page)


def decline_consent(state: ParticipantState) -> CommandResult:
    updated = state.copy()
    updated.answers["consent_agreed"] = "0 - Nu"
    updated.scroll_to_top = True
    updated.page = page_after_consent(False)
    return CommandResult(updated, updated.page)


def submit_demographics(state: ParticipantState, values: dict[str, Any]) -> CommandResult:
    updated = state.copy()
    updated.answers.update(values)
    updated.scroll_to_top = True
    updated.page = page_after_demographics()
    return CommandResult(updated, updated.page)


def complete_pre_question(
    state: ParticipantState,
    *,
    section_index: int,
    section_count: int,
) -> CommandResult:
    updated = state.copy()
    updated.scroll_to_top = True
    updated.page = page_after_pre_question(section_index, section_count)
    return CommandResult(updated, updated.page)


def complete_instructions(state: ParticipantState) -> CommandResult:
    updated = state.copy()
    updated.scroll_to_top = True
    updated.page = page_after_instructions(updated.prolific_mode)
    return CommandResult(updated, updated.page)


def record_attention_result(state: ParticipantState, *, passed: bool) -> ParticipantState:
    updated = state.copy()
    if not passed:
        updated.attention_failed_count += 1
    return updated


def begin_comprehension_attempt(state: ParticipantState) -> ParticipantState:
    updated = state.copy()
    updated.comprehension_attempts += 1
    return updated


def complete_comprehension_attempt(
    state: ParticipantState,
    *,
    passed: bool,
    passed_at: str | None = None,
) -> CommandResult:
    updated = state.copy()
    if passed:
        updated.comprehension_passed = True
        updated.answers["comprehension_passed"] = True
        updated.answers["comprehension_passed_at"] = passed_at
    else:
        updated.comprehension_passed = False
    next_page = page_after_comprehension(
        passed=passed,
        attempts=updated.comprehension_attempts,
    )
    if next_page:
        updated.page = next_page
    return CommandResult(updated, next_page)


def submit_comprehension(
    state: ParticipantState,
    *,
    passed: bool,
    passed_at: str | None = None,
) -> CommandResult:
    attempted = begin_comprehension_attempt(state)
    return complete_comprehension_attempt(
        attempted,
        passed=passed,
        passed_at=passed_at,
    )


def complete_profile(state: ParticipantState) -> CommandResult:
    updated = state.copy()
    updated.scroll_to_top = True
    updated.page = page_after_profile()
    return CommandResult(updated, updated.page)


def assign_study_session(state: ParticipantState, record: dict[str, Any], participant_code: str) -> CommandResult:
    updated = state.copy()
    condition = condition_from_record(record)
    updated.study_session_id = record["id"]
    updated.study_session_code = record["session_code"]
    updated.participant_code = participant_code
    updated.experimental_condition = condition["experimental_condition"]
    updated.score_frame = condition["score_frame"]
    updated.monthly_score_feedback = condition["monthly_score_feedback"]
    updated.treatment_bound = True
    updated.scroll_to_top = True
    updated.page = "home"
    return CommandResult(updated, updated.page)


def clear_study_session_assignment(state: ParticipantState) -> CommandResult:
    updated = state.copy()
    condition = condition_from_record()
    updated.study_session_id = None
    updated.study_session_code = None
    updated.participant_code = None
    updated.experimental_condition = condition["experimental_condition"]
    updated.score_frame = condition["score_frame"]
    updated.monthly_score_feedback = condition["monthly_score_feedback"]
    updated.treatment_bound = True
    updated.scroll_to_top = True
    updated.page = "home"
    return CommandResult(updated, updated.page)


def submit_month_decision(
    state: ParticipantState,
    *,
    month_data: dict[str, Any],
    payment: float | None,
    translate: Callable[[str], str] | None = None,
) -> CommandResult:
    updated = state.copy()
    result = compute_month_result(
        updated.month,
        month_data,
        updated.loan,
        updated.overdraft,
        payment,
        monthly_results=updated.monthly_results,
        translate=translate,
    )
    result = normalize_month_result_score(result)
    updated.loan.balance = result["credit_final"]
    updated.overdraft.balance = result["overdraft_final"]
    updated.total_score += result["monthly_score"]
    updated.monthly_points += result["monthly_score"]
    updated.accumulated_costs += result["costs_this_month"]
    updated.monthly_results.append(result)
    updated.pending_month_result = result
    updated.page = "month_feedback"
    return CommandResult(updated, updated.page, feedback=result)


def normalize_pending_month_feedback(state: ParticipantState) -> ParticipantState:
    if not state.pending_month_result:
        return state.copy()
    updated = state.copy()
    updated.pending_month_result = normalize_month_result_score(updated.pending_month_result)
    return updated


def acknowledge_month_feedback(state: ParticipantState) -> CommandResult:
    if not state.pending_month_result:
        raise ValueError("Missing pending month result")
    updated = state.copy()
    result = normalize_month_result_score(updated.pending_month_result)
    # Legacy checkpoints may contain a pending result that predates the Phase
    # 3 durable-decision commit. Apply it once during compatibility recovery.
    if not any(int(item.get("month", 0)) == int(result.get("month", 0)) for item in updated.monthly_results):
        updated.loan.balance = result["credit_final"]
        updated.overdraft.balance = result["overdraft_final"]
        updated.total_score += result["monthly_score"]
        updated.monthly_points += result["monthly_score"]
        updated.accumulated_costs += result["costs_this_month"]
        updated.monthly_results.append(result)
    updated.pending_month_result = None
    updated.month += 1
    updated.page = page_after_month_feedback()
    return CommandResult(updated, updated.page, feedback=result)


def complete_post_question(
    state: ParticipantState,
    *,
    section_index: int,
    section_count: int,
) -> CommandResult:
    updated = state.copy()
    updated.scroll_to_top = True
    updated.page = page_after_post_question(section_index, section_count)
    return CommandResult(updated, updated.page)


def calculate_final_scores(state: ParticipantState) -> ParticipantState:
    updated = state.copy()
    updated.final_score = compute_final_score_from_results(updated.monthly_results)
    updated.final_score_breakdown = get_final_score_breakdown_from_results(
        updated.monthly_results,
        remaining_credit=updated.loan.balance,
        remaining_overdraft=updated.overdraft.balance,
        study_session_id=updated.study_session_id,
        study_session_code=updated.study_session_code,
        participant_code=updated.participant_code,
        experimental_condition=updated.experimental_condition,
        score_frame=updated.score_frame,
        monthly_score_feedback=updated.monthly_score_feedback,
        payment_status=updated.payment_status,
        prolific_pid=updated.prolific_pid,
        prolific_study_id=updated.prolific_study_id,
        prolific_session_id=updated.prolific_session_id,
        completion_code=updated.prolific_completion_code,
    )
    return updated


def prepare_completion(state: ParticipantState) -> ParticipantState:
    if state.submission_finalized and state.final_score_breakdown:
        updated = state.copy()
        updated.final_score = updated.final_score_breakdown.get("final_score")
    else:
        updated = calculate_final_scores(state)
    updated.answers["financial_summary"] = updated.final_score_breakdown
    return updated


def completion_month_results(state: ParticipantState) -> list[dict[str, Any]]:
    return [normalize_month_result_score(result) for result in state.monthly_results]


def mark_completion_saved(state: ParticipantState) -> ParticipantState:
    updated = state.copy()
    updated.saved = True
    updated.submission_finalized = True
    return updated


def complete_final_score(state: ParticipantState) -> CommandResult:
    updated = state.copy()
    updated.scroll_to_top = True
    updated.page = page_after_final_score()
    return CommandResult(updated, updated.page)


__all__ = [
    "CommandResult",
    "accept_consent",
    "acknowledge_month_feedback",
    "assign_study_session",
    "begin_comprehension_attempt",
    "calculate_final_scores",
    "clear_study_session_assignment",
    "completion_month_results",
    "complete_final_score",
    "complete_comprehension_attempt",
    "complete_instructions",
    "complete_post_question",
    "complete_pre_question",
    "complete_profile",
    "decline_consent",
    "go_to_page",
    "mark_completion_saved",
    "normalize_pending_month_feedback",
    "prepare_completion",
    "record_attention_result",
    "submit_comprehension",
    "submit_demographics",
    "submit_month_decision",
]
