"""Runtime default state values."""

from sim_app.config import SCENARIO_VERSION
from sim_app.domain.experimental_conditions import DEFAULT_EXPERIMENTAL_CONDITION
from sim_app.domain.loan import Loan
from sim_app.domain.overdraft import Overdraft


def runtime_defaults():
    return {
        "page": "home",
        "session_id": None,
        "language": "en",
        "month": 1,
        "study_session_id": None,
        "study_session_code": None,
        "participant_code": None,
        "prolific_pid": None,
        "prolific_study_id": None,
        "prolific_session_id": None,
        "prolific_mode": False,
        "prolific_access_error": None,
        "prolific_completion_url": None,
        "prolific_completion_code": None,
        "prolific_redirected": False,
        "experimental_condition": DEFAULT_EXPERIMENTAL_CONDITION,
        "score_frame": "gain_frame",
        "monthly_score_feedback": "displayed",
        "loan": Loan(balance=7000.0, annual_interest=0.0835, months=24),
        "overdraft": Overdraft(limit=3000.0, annual_interest=0.18),
        "savings": None,
        "total_score": 0,
        "monthly_points": 0.0,
        "accumulated_costs": 0.0,
        "monthly_results": [],
        "pending_month_result": None,
        "final_score": None,
        "final_score_breakdown": None,
        "answers": {},
        "scroll_to_top": False,
        "submission_finalized": False,
        "comprehension_attempts": 0,
        "comprehension_passed": False,
        "attention_failed_count": 0,
        "already_completed": False,
        "saved": False,
        "scenario_version": SCENARIO_VERSION,
    }


__all__ = [
    "runtime_defaults",
]
