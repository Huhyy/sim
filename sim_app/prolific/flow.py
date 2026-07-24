"""Prolific page-flow validation."""


def prolific_required_page_before(page, state, pre_sections=None, post_sections=None):
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
    if page in {"home", "consent", "demographics", "instructions", "comprehension"} or page.startswith("pre_question_"):
        return None
    return None


def _first_section_gap(answers, sections):
    for section_index, section in enumerate(sections):
        prefix = section.get("key_prefix")
        for question_index in range(len(section.get("questions", []))):
            if answers.get(f"{prefix}_{question_index}") is None:
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
