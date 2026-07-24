"""Checkpoint collection, hydration, and persistence."""

import streamlit as st

from sim_app.config import SCENARIO_VERSION
from sim_app.domain.loan import Loan
from sim_app.domain.overdraft import Overdraft
from sim_app.persistence.participant_sessions import save_session_checkpoint
from sim_app.state.defaults import runtime_defaults
from sim_app.state.navigation import clear_payment_values, resolve_session_id


def collect_checkpoint():
    payment_values = {
        key: value
        for key, value in st.session_state.items()
        if key.startswith("payment_")
    }

    return {
        "scenario_version": SCENARIO_VERSION,
        "page": st.session_state.get("page", "home"),
        "admin_return_page": st.session_state.get("admin_return_page"),
        "language": st.session_state.get("language", "en"),
        "month": st.session_state.get("month", 1),
        "study_session_id": st.session_state.get("study_session_id"),
        "study_session_code": st.session_state.get("study_session_code"),
        "participant_code": st.session_state.get("participant_code"),
        "prolific_pid": st.session_state.get("prolific_pid"),
        "prolific_study_id": st.session_state.get("prolific_study_id"),
        "prolific_session_id": st.session_state.get("prolific_session_id"),
        "prolific_mode": st.session_state.get("prolific_mode", False),
        "prolific_completion_url": st.session_state.get("prolific_completion_url"),
        "prolific_completion_code": st.session_state.get("prolific_completion_code"),
        "prolific_redirected": st.session_state.get("prolific_redirected", False),
        "experimental_condition": st.session_state.get("experimental_condition"),
        "score_frame": st.session_state.get("score_frame"),
        "monthly_score_feedback": st.session_state.get("monthly_score_feedback"),
        "loan_balance": st.session_state.loan.balance,
        "overdraft_balance": st.session_state.overdraft.balance,
        "savings": st.session_state.get("savings"),
        "total_score": st.session_state.get("total_score", 0),
        "monthly_points": st.session_state.get("monthly_points", 0.0),
        "accumulated_costs": st.session_state.get("accumulated_costs", 0.0),
        "monthly_results": st.session_state.get("monthly_results", []),
        "pending_month_result": st.session_state.get("pending_month_result"),
        "final_score": st.session_state.get("final_score"),
        "final_score_breakdown": st.session_state.get("final_score_breakdown"),
        "answers": st.session_state.get("answers", {}),
        "comprehension_attempts": st.session_state.get("comprehension_attempts", 0),
        "comprehension_passed": st.session_state.get("comprehension_passed", False),
        "attention_failed_count": st.session_state.get("attention_failed_count", 0),
        "payment_values": payment_values,
    }


def persist_checkpoint(status=None):
    if st.session_state.get("submission_finalized") or st.session_state.get("already_completed"):
        return True

    session_id = resolve_session_id()
    if not session_id:
        st.session_state.checkpoint_last_save = {
            "ok": False,
            "error": "Missing session_id",
        }
        return False

    checkpoint = collect_checkpoint()
    resolved_status = status or ("completed" if checkpoint.get("page") == "done" else "in_progress")

    try:
        save_session_checkpoint(session_id, checkpoint, status=resolved_status)
        st.session_state.checkpoint_last_save = {
            "ok": True,
            "session_id": session_id,
            "status": resolved_status,
            "page": checkpoint.get("page"),
            "month": checkpoint.get("month"),
        }
        st.session_state.checkpoint_last_error = None
        return True
    except Exception as e:
        st.session_state.checkpoint_last_save = {
            "ok": False,
            "session_id": session_id,
            "status": resolved_status,
            "page": checkpoint.get("page"),
            "month": checkpoint.get("month"),
            "error": str(e),
        }
        st.session_state.checkpoint_last_error = str(e)
        return False


def hydrate_from_checkpoint(checkpoint):
    defaults = runtime_defaults()
    clear_payment_values()
    for key, value in defaults.items():
        if key not in ("loan", "overdraft", "session_id"):
            st.session_state[key] = value

    page = checkpoint.get("page", "home")
    if page == "pre_questions":
        page = "pre_question_0"
    elif page == "post_questions":
        page = "post_question_0"
    elif page == "month_feedback" and not checkpoint.get("pending_month_result"):
        page = "simulation"

    st.session_state.page = page
    st.session_state.submission_finalized = checkpoint.get("submission_finalized", False)
    st.session_state.saved = checkpoint.get("submission_finalized", False)
    st.session_state.admin_return_page = checkpoint.get("admin_return_page")
    st.session_state.language = checkpoint.get("language", "en")
    st.session_state.month = int(checkpoint.get("month", 1))
    st.session_state.study_session_id = checkpoint.get("study_session_id")
    st.session_state.study_session_code = checkpoint.get("study_session_code")
    st.session_state.participant_code = checkpoint.get("participant_code")
    st.session_state.prolific_pid = checkpoint.get("prolific_pid")
    st.session_state.prolific_study_id = checkpoint.get("prolific_study_id")
    st.session_state.prolific_session_id = checkpoint.get("prolific_session_id")
    st.session_state.prolific_mode = checkpoint.get("prolific_mode", False)
    st.session_state.prolific_completion_url = checkpoint.get("prolific_completion_url")
    st.session_state.prolific_completion_code = checkpoint.get("prolific_completion_code")
    st.session_state.prolific_redirected = checkpoint.get("prolific_redirected", False)
    st.session_state.experimental_condition = checkpoint.get("experimental_condition", defaults["experimental_condition"])
    st.session_state.score_frame = checkpoint.get("score_frame", defaults["score_frame"])
    st.session_state.monthly_score_feedback = checkpoint.get("monthly_score_feedback", defaults["monthly_score_feedback"])
    st.session_state.loan = Loan(
        balance=float(checkpoint.get("loan_balance", 7000.0)),
        annual_interest=0.0835,
        months=24,
    )
    st.session_state.overdraft = Overdraft(
        limit=3000.0,
        annual_interest=0.18,
    )
    st.session_state.overdraft.balance = round(float(checkpoint.get("overdraft_balance", 0.0)), 2)
    st.session_state.savings = checkpoint.get("savings")
    st.session_state.total_score = checkpoint.get("total_score", 0)
    st.session_state.monthly_points = checkpoint.get("monthly_points", 0.0)
    st.session_state.accumulated_costs = checkpoint.get("accumulated_costs", 0.0)
    st.session_state.monthly_results = checkpoint.get("monthly_results", [])
    st.session_state.pending_month_result = checkpoint.get("pending_month_result")
    st.session_state.final_score = checkpoint.get("final_score")
    st.session_state.final_score_breakdown = checkpoint.get("final_score_breakdown")
    st.session_state.answers = checkpoint.get("answers", {})
    st.session_state.comprehension_attempts = checkpoint.get("comprehension_attempts", 0)
    st.session_state.comprehension_passed = checkpoint.get("comprehension_passed", False)
    st.session_state.attention_failed_count = checkpoint.get("attention_failed_count", 0)

    for key, value in (checkpoint.get("payment_values") or {}).items():
        st.session_state[key] = value


__all__ = [
    "collect_checkpoint",
    "hydrate_from_checkpoint",
    "persist_checkpoint",
]
