"""Participant-safe, framework-neutral projections of authoritative state."""

from __future__ import annotations

from sim_app.application.commands import calculate_final_scores
from sim_app.application.state import ParticipantState
from sim_app.content.tables import get_month
from sim_app.content.translations import (
    get_category_label,
    get_display_post_sections,
    get_display_pre_sections,
    get_localized_narrative,
    get_ui_section,
    t,
)
from sim_app.domain.simulation import compute_month_preview


def participant_session_view(state: ParticipantState, *, idempotency_replayed=False):
    """Return only data that the current participant page already reveals."""
    stage = _effective_stage(state)
    language = state.language if state.language in {"en", "ro"} else "en"
    return {
        "session_id": state.session_id,
        "state_version": state.state_version,
        "stage": stage,
        "month": state.month,
        "language": language,
        "labels": _stage_labels(stage, state, language),
        "view": _stage_view(state, stage, language),
        "idempotency_replayed": bool(idempotency_replayed),
    }


def _effective_stage(state):
    if state.page == "simulation" and state.month > 24:
        return "post_question_0"
    if state.page == "pre_questions":
        return "pre_question_0"
    if state.page == "post_questions":
        return "post_question_0"
    return state.page or "home"


def _stage_view(state, stage, language):
    if stage == "home":
        return {
            "type": "home",
            "title": t("home.title", language=language),
            "body": t("home.body", language=language),
            "info": t("home.info", language=language),
            "framing_notice": t(
                "home.loss_frame_notice" if state.score_frame == "loss_frame" else "home.gain_frame_notice",
                language=language,
            ),
            "study_session_available": True,
        }
    if stage == "enter_session_code":
        return {
            "type": "study_session",
            "title": t("study_session.title", language=language),
            "body": t("study_session.body", language=language),
        }
    if stage == "consent":
        return {
            "type": "consent",
            "content": t("consent.markdown", language=language),
            "items": t("consent.items", language=language),
            "anti_ai_declaration_required": bool(state.prolific_mode),
            "framing_notice": t(
                "home.loss_frame_notice" if state.score_frame == "loss_frame" else "home.gain_frame_notice",
                language=language,
            ),
        }
    if stage == "consent_declined":
        return {
            "type": "consent_declined",
            "title": t("consent_declined.title", language=language),
            "body": t("consent_declined.body", language=language),
        }
    if stage == "demographics":
        return _demographics_view(state, language)
    if stage.startswith("pre_question_"):
        return _questionnaire_view(state, "pre", stage, language)
    if stage.startswith("post_question_"):
        return _questionnaire_view(state, "post", stage, language)
    if stage == "instructions":
        return {"type": "instructions", "content": t("instructions.body", language=language)}
    if stage == "comprehension":
        return {
            "type": "comprehension",
            "title": t("prolific.comprehension_title", language=language),
            "intro": t("prolific.comprehension_intro", language=language),
            "attempts": state.comprehension_attempts,
            "questions": [
                {
                    "id": "who_completes",
                    "prompt": t("prolific.comprehension_q1", language=language),
                    "options": t("prolific.comprehension_q1_options", language=language),
                },
                {
                    "id": "monthly_task",
                    "prompt": t("prolific.comprehension_q2", language=language),
                    "options": t("prolific.comprehension_q2_options", language=language),
                },
            ],
        }
    if stage == "profile":
        return {
            "type": "profile",
            "title": t("profile.title", language=language),
            "intro": t("profile.intro", language=language),
            "sections": t("profile.sections", language=language),
        }
    if stage == "simulation":
        return _simulation_view(state, language)
    if stage == "month_feedback":
        return _feedback_view(state, language)
    if stage == "final_score":
        return _final_score_view(state, language)
    if stage == "done":
        return _completion_view(state, language)
    if stage == "already_completed":
        return {
            "type": "already_completed",
            "title": t("already_completed.title", language=language),
            "body": t("already_completed.body", language=language),
        }
    if stage in {"prolific_error", "prolific_return"}:
        key = "prolific.return_message" if stage == "prolific_return" else "prolific.error_missing_params"
        return {"type": stage, "message": t(key, language=language)}
    return {"type": "unavailable"}


def _stage_labels(stage, state, language):
    if stage in {"home", "enter_session_code"}:
        sections = ("home", "study_session")
    elif stage in {"consent", "consent_declined"}:
        sections = ("consent", "consent_declined", "prolific")
    elif stage == "demographics":
        sections = ("demographics",)
    elif stage.startswith(("pre_question_", "post_question_")):
        sections = ("quiz", "prolific")
    elif stage == "instructions":
        sections = ("instructions",)
    elif stage == "comprehension":
        sections = ("prolific",)
    elif stage == "profile":
        sections = ("profile",)
    elif stage in {"simulation", "month_feedback"}:
        sections = ("simulation", "table")
    elif stage == "final_score":
        sections = ("final_score",)
    elif stage == "done":
        sections = ("done", "prolific")
    else:
        sections = ("auth", "already_completed", "prolific")
    labels = {section: get_ui_section(section, language) for section in sections}
    if stage in {"simulation", "month_feedback"} and state.monthly_score_feedback != "displayed":
        simulation_labels = labels.get("simulation", {})
        for key in tuple(simulation_labels):
            if key.startswith("score_") or key.startswith("monthly_score"):
                simulation_labels.pop(key, None)
    return labels


def _demographics_view(state, language):
    keys = (
        "demo_age", "demo_gender", "demo_education", "demo_field", "demo_occupation",
        "demo_income", "demo_financial_decisions", "demo_credit_experience",
        "demo_financial_familiarity", "demo_living_situation",
        "demo_recurring_responsibilities", "demo_country",
    )
    option_keys = {
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
    return {
        "type": "demographics",
        "title": t("demographics.title", language=language),
        "intro": t("demographics.intro", language=language),
        "values": {key: state.answers.get(key) for key in keys if state.answers.get(key) is not None},
        "options": {
            key: t(f"demographics.options.{option_key}", language=language)
            for key, option_key in option_keys.items()
        },
        "age_range": {"minimum": 18, "maximum": 75},
    }


def _questionnaire_view(state, phase, stage, language):
    sections = get_display_pre_sections(language) if phase == "pre" else get_display_post_sections(language)
    try:
        index = int(stage.rsplit("_", 1)[1])
    except (TypeError, ValueError):
        index = 0
    if index < 0 or index >= len(sections):
        return {"type": "questionnaire_unavailable", "phase": phase}
    section = sections[index]
    question_offset = sum(len(previous["questions"]) for previous in sections[:index])
    questions = []
    values = {}
    for question_index, prompt in enumerate(section["questions"]):
        key = f"{section['key_prefix']}_{question_index}"
        questions.append({
            "key": key,
            "number": question_offset + question_index + 1,
            "prompt": prompt,
            "options": list(section["scale"]),
        })
        if state.answers.get(key) is not None:
            values[key] = state.answers[key]
    attention_required = state.prolific_mode and (
        (phase == "pre" and index == 0)
        or (phase == "post" and index + 1 == len(sections))
    )
    view = {
        "type": "questionnaire_section",
        "phase": phase,
        "section_index": index,
        "section_count": len(sections),
        "instruction": section.get("instruction"),
        "questions": questions,
        "values": values,
        "attention_check": None,
    }
    if attention_required:
        view["attention_check"] = {
            "prompt": t(
                "prolific.attention_1" if phase == "pre" else "prolific.attention_2",
                language=language,
            ),
            "options": t("prolific.attention_number_options", language=language),
        }
    if phase == "post" and index + 1 == len(sections):
        view["optional_feedback"] = {
            "feedback": state.answers.get("feedback", ""),
            "strategy_feedback": state.answers.get("strategy_feedback", ""),
        }
    return view


def _simulation_view(state, language):
    data = get_month(state.month)
    preview = compute_month_preview(
        state.month,
        data,
        state.loan,
        state.overdraft,
        monthly_results=state.monthly_results,
    )
    return {
        "type": "simulation",
        "month": state.month,
        "narrative": get_localized_narrative(state.month, language),
        "income": [
            {"category": get_category_label(key, language), "value": value}
            for key, value in data["income"].items()
        ],
        "expenses": [
            {"category": get_category_label(key, language), "value": value}
            for key, value in data["expenses"].items()
        ],
        "summary": {
            "opening_balance": preview["opening_balance"] if state.month == 1 else None,
            "income_total": preview["income_total"],
            "expenses_total": preview["expenses_total"],
            "credit_interest": preview["credit_interest"],
            "overdraft_interest": preview["overdraft_interest"],
            "remaining_credit": state.loan.balance,
            "used_overdraft": state.overdraft.balance,
            "available_before_payment": preview["liquidity_after_charges"],
            "contract_payment": preview["loan_obligation"],
        },
        "payment": {
            "required": not preview["no_loan_due"],
            "blocked": preview["blocked"],
            "minimum": 0,
        },
    }


def _feedback_view(state, language):
    result = dict(state.pending_month_result or {})
    if not result:
        return {"type": "feedback_unavailable"}
    if result.get("pre_credit_impossible"):
        message_key = "simulation.feedback_pre_credit"
        tone = "error"
    elif result.get("payment_valid"):
        message_key = (
            "simulation.feedback_no_payment_due"
            if float(result.get("loan_balance_before_payment") or 0) <= 0
            else "simulation.feedback_success"
        )
        tone = "success"
    else:
        message_key = "simulation.feedback_invalid"
        tone = "warning"
    view = {
        "type": "month_feedback",
        "month": result.get("month"),
        "financial_result": {
            "payment_input": result.get("payment_input"),
            "accepted_payment": result.get("accepted_payment"),
            "cash_final": result.get("cash_final"),
            "credit_final": result.get("credit_final"),
            "overdraft_final": result.get("overdraft_final"),
            "credit_interest": result.get("credit_interest"),
            "overdraft_interest": result.get("overdraft_interest"),
            "penalties": result.get("penalties"),
        },
        "feedback": {"tone": tone, "message": t(message_key, language=language)},
    }
    if state.monthly_score_feedback == "displayed":
        score = {
            "repayment": result.get("score_repayment"),
            "liquidity": result.get("score_liquidity"),
            "overdraft": result.get("score_overdraft"),
        }
        if state.score_frame == "loss_frame":
            score["monthly_loss"] = max(0.0, 100.0 - float(result.get("monthly_score") or 0))
        else:
            score["monthly_score"] = result.get("monthly_score")
        view["score"] = score
    return view


def _final_score_view(state, language):
    calculated = calculate_final_scores(state)
    breakdown = calculated.final_score_breakdown or {}
    bonus = {"performance_bonus_gbp": breakdown.get("performance_bonus_gbp")}
    if state.score_frame == "loss_frame":
        bonus.update({
            "initial_bonus_gbp": 3,
            "loss_amount_gbp": breakdown.get("loss_amount_gbp"),
        })
    return {
        "type": "final_score",
        "final_score": breakdown.get("final_score"),
        "bonus": bonus,
        "summary": {
            "total_repaid": breakdown.get("total_repaid"),
            "remaining_credit": breakdown.get("remaining_credit"),
            "remaining_overdraft": breakdown.get("remaining_overdraft"),
            "interest_total": breakdown.get("interest_total"),
        },
        "info": t("final_score.info", language=language),
    }


def _completion_view(state, language):
    breakdown = state.final_score_breakdown or calculate_final_scores(state).final_score_breakdown or {}
    bonus = {"performance_bonus_gbp": breakdown.get("performance_bonus_gbp")}
    if state.score_frame == "loss_frame":
        bonus.update({
            "initial_bonus_gbp": 3,
            "loss_amount_gbp": breakdown.get("loss_amount_gbp"),
        })
    view = {
        "type": "completion",
        "saved": bool(state.saved),
        "final_score": breakdown.get("final_score"),
        "participant_code": state.participant_code,
        "bonus": bonus,
        "remaining_credit": state.loan.balance,
        "remaining_overdraft": state.overdraft.balance,
    }
    if state.saved and state.prolific_completion_url:
        view["prolific_completion"] = {
            "code": state.prolific_completion_code,
            "url": state.prolific_completion_url,
        }
    return view


__all__ = ["participant_session_view"]
