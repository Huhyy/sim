"""Domain model and simulation logic."""

from .loan import Loan
from .overdraft import Overdraft
from .scoring import compute_final_score_from_results, compute_monthly_score, get_final_score_breakdown_from_results
from .simulation import compute_month_result
from .experimental_conditions import (
    CONDITIONS,
    DEFAULT_EXPERIMENTAL_CONDITION,
    DEFAULT_PAYMENT_STATUS,
    MAX_PERFORMANCE_BONUS_EUR,
    condition_config,
    condition_from_record,
    condition_options,
    monthly_score_is_displayed,
    normalize_experimental_condition,
    performance_bonus,
    score_frame,
)


__all__ = [
    "compute_final_score_from_results",
    "compute_month_result",
    "compute_monthly_score",
    "get_final_score_breakdown_from_results",
    "Loan",
    "Overdraft",
    "CONDITIONS",
    "DEFAULT_EXPERIMENTAL_CONDITION",
    "DEFAULT_PAYMENT_STATUS",
    "MAX_PERFORMANCE_BONUS_EUR",
    "condition_config",
    "condition_from_record",
    "condition_options",
    "monthly_score_is_displayed",
    "normalize_experimental_condition",
    "performance_bonus",
    "score_frame",
]
