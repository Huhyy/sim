"""Framework-neutral experiment progression rules."""

from __future__ import annotations

from typing import Any

from sim_app.content.questions import question_key


def page_after_consent(accepted: bool) -> str:
    return "demographics" if accepted else "consent_declined"


def page_after_demographics() -> str:
    return "pre_question_0"


def required_page_before_demographics(state: Any) -> str | None:
    answers = _state_get(state, "answers", {})
    return None if answers.get("consent_agreed") == "1 - Da" else "consent"


def required_page_before_pre_questions(state: Any) -> str | None:
    answers = _state_get(state, "answers", {})
    if answers.get("consent_agreed") != "1 - Da":
        return "consent"
    if not _demographics_complete(answers):
        return "demographics"
    return None


def page_after_pre_question(section_index: int, section_count: int) -> str:
    if section_index + 1 >= section_count:
        return "instructions"
    return f"pre_question_{section_index + 1}"


def page_after_instructions(prolific_mode: bool) -> str:
    return "comprehension" if prolific_mode else "profile"


def page_after_comprehension(*, passed: bool, attempts: int) -> str | None:
    if passed:
        return "profile"
    if attempts >= 2:
        return "prolific_return"
    return None


def page_after_profile() -> str:
    return "simulation"


def redirect_before_simulation(month: int) -> str | None:
    return "post_question_0" if month > 24 else None


def redirect_before_month_feedback(has_pending_result: bool) -> str | None:
    return None if has_pending_result else "simulation"


def redirect_for_pre_question_index(section_index: int, section_count: int) -> str | None:
    return "instructions" if section_index >= section_count else None


def redirect_for_post_question_index(section_index: int, section_count: int) -> str | None:
    return "final_score" if section_index >= section_count else None


def page_after_month_feedback() -> str:
    # Preserve the legacy intermediate checkpoint at page=simulation, month=25.
    # The next safe-view render then applies redirect_before_simulation.
    return "simulation"


def page_after_post_question(section_index: int, section_count: int) -> str:
    if section_index + 1 >= section_count:
        return "final_score"
    return f"post_question_{section_index + 1}"


def page_after_final_score() -> str:
    return "done"


def required_page_before(
    page: str,
    state: Any,
    *,
    pre_sections=None,
    post_sections=None,
) -> str | None:
    """Preserve the existing Prolific-only route guard."""
    pre_sections = pre_sections or []
    post_sections = post_sections or []
    if not _state_get(state, "prolific_mode"):
        return None
    if _state_get(state, "submission_finalized"):
        return None
    if page in {"prolific_error", "prolific_return", "already_completed"}:
        return None
    answers = _state_get(state, "answers", {})
    if answers.get("consent_agreed") != "1 - Da" or answers.get("anti_ai_declaration") is not True:
        return None if page == "consent" else "consent"
    if not _demographics_complete(answers):
        return None if page == "demographics" else "demographics"
    first_pre_gap = _first_section_gap(answers, pre_sections)
    if first_pre_gap is not None:
        required = f"pre_question_{first_pre_gap}"
        return None if page == required else required
    if not _state_get(state, "comprehension_passed"):
        if page in {"instructions", "comprehension"}:
            return None
        return "instructions" if int(_state_get(state, "comprehension_attempts") or 0) <= 0 else "comprehension"
    completed_months = len(_state_get(state, "monthly_results", []) or [])
    if _is_after_simulation_page(page) and completed_months < 24:
        return "simulation"
    first_post_gap = _first_section_gap(answers, post_sections)
    if page.startswith("post_question_") and first_post_gap is not None:
        try:
            requested_post_index = int(page.rsplit("_", 1)[1])
        except (IndexError, TypeError, ValueError):
            requested_post_index = 0
        if first_post_gap < requested_post_index:
            return f"post_question_{first_post_gap}"
    if _is_final_page(page) and first_post_gap is not None:
        return f"post_question_{first_post_gap}"
    return None


def _first_section_gap(answers, sections):
    for section_index, section in enumerate(sections):
        for question_index in range(len(section.get("questions", []))):
            if answers.get(question_key(section, question_index)) is None:
                return section_index
    return None


def _demographics_complete(answers):
    keys = [
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
    ]
    return all(answers.get(key) not in (None, "") for key in keys)


def _is_after_simulation_page(page):
    return page.startswith("post_question_") or page in {"final_score", "done"}


def _is_final_page(page):
    return page in {"final_score", "done"}


def _state_get(state, key, default=None):
    if hasattr(state, "get"):
        return state.get(key, default)
    return getattr(state, key, default)


__all__ = [
    "page_after_comprehension",
    "page_after_consent",
    "page_after_demographics",
    "page_after_final_score",
    "page_after_instructions",
    "page_after_month_feedback",
    "page_after_post_question",
    "page_after_pre_question",
    "page_after_profile",
    "redirect_before_simulation",
    "redirect_before_month_feedback",
    "redirect_for_post_question_index",
    "redirect_for_pre_question_index",
    "required_page_before_demographics",
    "required_page_before_pre_questions",
    "required_page_before",
]
