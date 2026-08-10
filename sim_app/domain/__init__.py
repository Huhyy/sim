"""Domain model and simulation logic."""

from .loan import Loan
from .overdraft import Overdraft
from .scoring import (
    compute_final_score_from_results,
    compute_monthly_score,
    get_bonus_max_session,
    get_final_score_breakdown_from_results,
    normalize_month_result_score,
)
from .simulation import compute_month_preview, compute_month_result, get_opening_balance, month_sum
from .experimental_conditions import (
    CONDITIONS,
    DEFAULT_EXPERIMENTAL_CONDITION,
    DEFAULT_PAYMENT_STATUS,
    MAX_PERFORMANCE_BONUS_GBP,
    PROLIFIC_BASE_REWARD_GBP,
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
    "compute_month_preview",
    "compute_monthly_score",
    "get_bonus_max_session",
    "get_final_score_breakdown_from_results",
    "get_opening_balance",
    "month_sum",
    "normalize_month_result_score",
    "Loan",
    "Overdraft",
    "CONDITIONS",
    "DEFAULT_EXPERIMENTAL_CONDITION",
    "DEFAULT_PAYMENT_STATUS",
    "MAX_PERFORMANCE_BONUS_GBP",
    "PROLIFIC_BASE_REWARD_GBP",
    "condition_config",
    "condition_from_record",
    "condition_options",
    "monthly_score_is_displayed",
    "normalize_experimental_condition",
    "performance_bonus",
    "score_frame",
]
