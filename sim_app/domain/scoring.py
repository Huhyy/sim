"""Scoring helpers for the financial simulation."""

from sim_app.domain.experimental_conditions import (
    DEFAULT_PAYMENT_STATUS,
    PROLIFIC_BASE_REWARD_GBP,
    performance_bonus,
)

RECOMMENDED_BUFFER = 5.0
SESSION_MONTHS = 24
EURO_PER_MONTHLY_POINT = 0.005
MAX_MONTHLY_SCORE = 100.0
DEFAULT_BONUS_MAX_SESSION = SESSION_MONTHS * MAX_MONTHLY_SCORE * EURO_PER_MONTHLY_POINT


def money(value):
    return round(float(value), 2)


def get_bonus_max_session():
    return money(DEFAULT_BONUS_MAX_SESSION)


def zero_score_data():
    return {
        "score_model": "behavioral_v1",
        "score_repayment": 0.0,
        "score_liquidity": 0.0,
        "score_overdraft": 0.0,
        "monthly_score": 0.0,
        "bonus_lunar": 0.0,
    }


def compute_monthly_score(
    accepted_payment,
    cash_final,
    overdraft_final,
    overdraft_limit,
    loan_obligation,
    loan_balance_before_payment=None,
    loan_closed_by_payment=False,
):
    reference_payment = money(loan_obligation)
    remaining_balance = reference_payment if loan_balance_before_payment is None else money(loan_balance_before_payment)
    expected_repayment = money(
        min(reference_payment, remaining_balance)
        if loan_closed_by_payment
        else reference_payment
    )

    if expected_repayment <= 0:
        repayment_score = 40.0
    else:
        repayment_score = min(accepted_payment / expected_repayment, 1.0) * 40.0

    liquidity_score = min(cash_final / RECOMMENDED_BUFFER, 1.0) * 30.0
    overdraft_score = 30.0 if overdraft_limit <= 0 else max(0.0, 30.0 * (1.0 - overdraft_final / overdraft_limit))
    monthly_score = min(100.0, max(0.0, repayment_score + liquidity_score + overdraft_score))

    return {
        "score_model": "behavioral_v1",
        "score_repayment": money(repayment_score),
        "score_liquidity": money(liquidity_score),
        "score_overdraft": money(overdraft_score),
        "monthly_score": money(monthly_score),
        "bonus_lunar": money(monthly_score * EURO_PER_MONTHLY_POINT),
    }


def normalize_month_result_score(result):
    if result.get("score_model") == "behavioral_v1":
        return result

    if not result.get("payment_valid") or result.get("pre_credit_impossible"):
        result.update(zero_score_data())
        return result

    result.update(
        compute_monthly_score(
            money(result.get("accepted_payment", 0.0)),
            money(result.get("cash_final", 0.0)),
            money(result.get("overdraft_final", 0.0)),
            3000.0,
            money(result.get("loan_obligation", 317.71)),
            money(result.get("loan_balance_before_payment", result.get("loan_obligation", 317.71))),
            money(result.get("credit_final", 0.0)) <= 0 and money(result.get("loan_balance_before_payment", 0.0)) > 0,
        )
    )
    return result


def compute_final_score_from_results(monthly_results):
    normalized = [normalize_month_result_score(result) for result in monthly_results or []]
    score_sum = sum(float(result.get("monthly_score", 0.0)) for result in normalized)
    return money(min(100.0, max(0.0, score_sum / SESSION_MONTHS)))


def get_final_score_breakdown_from_results(
    monthly_results,
    remaining_credit,
    remaining_overdraft,
    study_session_id=None,
    study_session_code=None,
    participant_code=None,
    experimental_condition=None,
    score_frame=None,
    monthly_score_feedback=None,
    payment_status=DEFAULT_PAYMENT_STATUS,
    prolific_pid=None,
    prolific_study_id=None,
    prolific_session_id=None,
    completion_code=None,
    bonus_max_session=None,
):
    normalized = [normalize_month_result_score(result) for result in monthly_results or []]
    monthly_score_sum = money(sum(float(result.get("monthly_score", 0.0)) for result in normalized))
    final_score = money(min(MAX_MONTHLY_SCORE, max(0.0, monthly_score_sum / SESSION_MONTHS)))
    resolved_bonus_max_session = get_bonus_max_session() if bonus_max_session is None else money(bonus_max_session)
    bonus_final = money(monthly_score_sum * EURO_PER_MONTHLY_POINT)
    bonus = performance_bonus(final_score)
    total_repaid = money(sum(float(result.get("accepted_payment", 0.0)) for result in normalized))
    credit_interest_total = money(sum(float(result.get("credit_interest", 0.0)) for result in normalized))
    overdraft_interest_total = money(sum(float(result.get("overdraft_interest", 0.0)) for result in normalized))
    return {
        "months_completed": len(normalized),
        "monthly_score_sum": monthly_score_sum,
        "final_score": final_score,
        "bonus_max_session": resolved_bonus_max_session,
        "bonus_final": bonus_final,
        "performance_bonus_gbp": bonus["performance_bonus_gbp"],
        "loss_amount_gbp": bonus["loss_amount_gbp"],
        "prolific_base_reward_gbp": PROLIFIC_BASE_REWARD_GBP,
        "total_payout_gbp": PROLIFIC_BASE_REWARD_GBP + bonus["performance_bonus_gbp"],
        "experimental_condition": experimental_condition,
        "score_frame": score_frame,
        "monthly_score_feedback": monthly_score_feedback,
        "payment_status": payment_status,
        "study_session_id": study_session_id,
        "study_session_code": study_session_code,
        "participant_code": participant_code,
        "prolific_pid": prolific_pid,
        "prolific_study_id": prolific_study_id,
        "prolific_session_id": prolific_session_id,
        "completion_code": completion_code,
        "total_repaid": total_repaid,
        "remaining_credit": money(remaining_credit),
        "remaining_overdraft": money(remaining_overdraft),
        "credit_interest_total": credit_interest_total,
        "overdraft_interest_total": overdraft_interest_total,
        "interest_total": money(credit_interest_total + overdraft_interest_total),
    }

