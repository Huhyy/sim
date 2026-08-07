"""Experimental condition helpers for the 2 x 2 study design."""

DEFAULT_EXPERIMENTAL_CONDITION = "C1"
DEFAULT_PAYMENT_STATUS = "unpaid"
MAX_PERFORMANCE_BONUS_GBP = 3
PROLIFIC_BASE_REWARD_GBP = 5

CONDITIONS = {
    "C1": {
        "experimental_condition": "C1",
        "score_frame": "gain_frame",
        "monthly_score_feedback": "displayed",
    },
    "C2": {
        "experimental_condition": "C2",
        "score_frame": "gain_frame",
        "monthly_score_feedback": "hidden",
    },
    "C3": {
        "experimental_condition": "C3",
        "score_frame": "loss_frame",
        "monthly_score_feedback": "displayed",
    },
    "C4": {
        "experimental_condition": "C4",
        "score_frame": "loss_frame",
        "monthly_score_feedback": "hidden",
    },
}


def normalize_experimental_condition(value):
    key = str(value or DEFAULT_EXPERIMENTAL_CONDITION).strip().upper()
    return key if key in CONDITIONS else DEFAULT_EXPERIMENTAL_CONDITION


def condition_config(value=None):
    return dict(CONDITIONS[normalize_experimental_condition(value)])


def condition_from_record(record=None):
    record = record or {}
    config = condition_config(record.get("experimental_condition"))
    if record.get("score_frame"):
        config["score_frame"] = record.get("score_frame")
    if record.get("monthly_score_feedback"):
        config["monthly_score_feedback"] = record.get("monthly_score_feedback")
    return config


def monthly_score_is_displayed(value=None):
    return condition_config(value).get("monthly_score_feedback") == "displayed"


def score_frame(value=None):
    return condition_config(value).get("score_frame", "gain_frame")


def performance_bonus(final_score):
    score = float(final_score or 0.0)
    if score < 75:
        return {
            "performance_bonus_gbp": 0,
            "loss_amount_gbp": 3,
        }
    if score < 80:
        return {
            "performance_bonus_gbp": 1,
            "loss_amount_gbp": 2,
        }
    if score < 90:
        return {
            "performance_bonus_gbp": 2,
            "loss_amount_gbp": 1,
        }
    return {
        "performance_bonus_gbp": 3,
        "loss_amount_gbp": 0,
    }


def condition_options():
    return list(CONDITIONS.keys())


__all__ = [
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
