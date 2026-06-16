"""Runtime default state values."""

from sim_app.config import SCENARIO_VERSION
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
        "loan": Loan(balance=7000.0, annual_interest=0.0835, months=24),
        "overdraft": Overdraft(limit=3000.0, annual_interest=0.18),
        "savings": None,
        "total_score": 0,
        "monthly_points": 0.0,
        "accumulated_costs": 0.0,
        "monthly_results": [],
        "pending_month_result": None,
        "final_score": None,
        "answers": {},
        "scroll_to_top": False,
        "submission_finalized": False,
        "already_completed": False,
        "saved": False,
        "scenario_version": SCENARIO_VERSION,
    }


__all__ = [
    "runtime_defaults",
]
