"""Domain model and simulation logic."""

from .loan import Loan
from .overdraft import Overdraft
from .scoring import compute_final_score_from_results, compute_monthly_score, get_final_score_breakdown_from_results
from .simulation import compute_month_result


__all__ = [
    "compute_final_score_from_results",
    "compute_month_result",
    "compute_monthly_score",
    "get_final_score_breakdown_from_results",
    "Loan",
    "Overdraft",
]
