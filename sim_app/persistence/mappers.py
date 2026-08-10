"""Database row mapping helpers."""

from copy import deepcopy

from sim_app.infra.time import _utcnow


def _parse(value):
    if value is None:
        return None
    try:
        return int(str(value).split(" - ")[0].strip())
    except Exception:
        return None


def _float_or_none(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value):
    if value is None:
        return None
    return bool(value)


def _demographic_answers(answers: dict):
    return {
        key: value
        for key, value in answers.items()
        if key.startswith("demo_") or key == "consent_agreed"
    }


def _clean_metadata(metadata=None):
    metadata = metadata or {}
    return {
        key: value
        for key, value in {
            "study_session_id": metadata.get("study_session_id"),
            "study_session_code": metadata.get("study_session_code"),
            "participant_code": metadata.get("participant_code"),
        }.items()
        if value
    }


def _psychometric_rows(session_id: str, answers: dict, sections, metadata=None):
    rows = []
    question_number = 1
    now = _utcnow()
    metadata_columns = _clean_metadata(metadata)

    for section_number, section in enumerate(sections or [], start=1):
        prefix = section.get("key_prefix")
        for index, question_text in enumerate(section.get("questions", [])):
            key = f"{prefix}_{index}"
            answer = _parse(answers.get(key))
            if answer is None:
                question_number += 1
                continue

            rows.append(
                {
                    "session_id": session_id,
                    **metadata_columns,
                    "section_number": section_number,
                    "question_number": question_number,
                    "question_key": key,
                    "question_text": question_text,
                    "answer_value": answer,
                    "updated_at": now,
                }
            )
            question_number += 1

    return rows


def _month_result_row(
    session_id: str,
    result: dict,
    bonus_max_session: float = 12.0,
    metadata=None,
    *,
    decision_request_id=None,
    committed_state_version=None,
):
    monthly_score = _float_or_none(result.get("monthly_score")) or 0.0
    bonus_lunar = monthly_score / 100.0 * (float(bonus_max_session) / 24.0)

    return {
        "session_id": session_id,
        **_clean_metadata(metadata),
        "month_number": int(result.get("month", 0)),
        "opening_balance": _float_or_none(result.get("opening_balance")),
        "income_total": _float_or_none(result.get("income_total")),
        "expenses_total": _float_or_none(result.get("expenses_total")),
        "loan_balance_before_payment": _float_or_none(result.get("loan_balance_before_payment")),
        "loan_obligation": _float_or_none(result.get("loan_obligation")),
        "credit_interest": _float_or_none(result.get("credit_interest")),
        "overdraft_interest": _float_or_none(result.get("overdraft_interest")),
        "penalties": _float_or_none(result.get("penalties")),
        "available_total": _float_or_none(result.get("available_total")),
        "outflows_before_credit": _float_or_none(result.get("outflows_before_credit")),
        "deficit_before_credit": _float_or_none(result.get("deficit_before_credit")),
        "liquidity_before_payment": _float_or_none(result.get("liquidity_after_charges")),
        "overdraft_after_charges": _float_or_none(result.get("overdraft_after_charges")),
        "overdraft_remaining": _float_or_none(result.get("overdraft_remaining")),
        "max_payment": _float_or_none(result.get("max_payment")),
        "payment_input": _float_or_none(result.get("payment_input")),
        "accepted_payment": _float_or_none(result.get("accepted_payment")),
        "overdraft_from_payment": _float_or_none(result.get("overdraft_from_payment")),
        "overdraft_final": _float_or_none(result.get("overdraft_final")),
        "cash_final": _float_or_none(result.get("cash_final")),
        "credit_final": _float_or_none(result.get("credit_final")),
        "score_repayment": _float_or_none(result.get("score_repayment")),
        "score_liquidity": _float_or_none(result.get("score_liquidity")),
        "score_overdraft": _float_or_none(result.get("score_overdraft")),
        "monthly_score": monthly_score,
        "bonus_lunar": bonus_lunar,
        "costs_this_month": _float_or_none(result.get("costs_this_month")),
        "feedback_message": result.get("feedback_message"),
        "invalid_reason": result.get("invalid_reason"),
        "pre_credit_impossible": _bool_or_none(result.get("pre_credit_impossible")),
        "payment_valid": _bool_or_none(result.get("payment_valid")),
        "score_model": result.get("score_model"),
        "result_json": deepcopy(result),
        "decision_request_id": decision_request_id,
        "committed_state_version": committed_state_version,
        "updated_at": _utcnow(),
    }


def _month_result_from_row(row: dict):
    if row.get("result_json"):
        return deepcopy(row["result_json"])

    mapping = {
        "month": "month_number",
        "opening_balance": "opening_balance",
        "income_total": "income_total",
        "expenses_total": "expenses_total",
        "loan_balance_before_payment": "loan_balance_before_payment",
        "loan_obligation": "loan_obligation",
        "credit_interest": "credit_interest",
        "overdraft_interest": "overdraft_interest",
        "penalties": "penalties",
        "available_total": "available_total",
        "outflows_before_credit": "outflows_before_credit",
        "deficit_before_credit": "deficit_before_credit",
        "liquidity_after_charges": "liquidity_before_payment",
        "overdraft_after_charges": "overdraft_after_charges",
        "overdraft_remaining": "overdraft_remaining",
        "max_payment": "max_payment",
        "payment_input": "payment_input",
        "accepted_payment": "accepted_payment",
        "overdraft_from_payment": "overdraft_from_payment",
        "overdraft_final": "overdraft_final",
        "cash_final": "cash_final",
        "credit_final": "credit_final",
        "score_repayment": "score_repayment",
        "score_liquidity": "score_liquidity",
        "score_overdraft": "score_overdraft",
        "monthly_score": "monthly_score",
        "bonus_lunar": "bonus_lunar",
        "costs_this_month": "costs_this_month",
        "feedback_message": "feedback_message",
        "invalid_reason": "invalid_reason",
        "pre_credit_impossible": "pre_credit_impossible",
        "payment_valid": "payment_valid",
        "score_model": "score_model",
    }
    numeric = {
        key for key in mapping
        if key not in {"month", "feedback_message", "invalid_reason", "pre_credit_impossible", "payment_valid", "score_model"}
    }
    result = {}
    for result_key, row_key in mapping.items():
        value = row.get(row_key)
        if result_key == "month" and value is not None:
            value = int(value)
        elif result_key in numeric and value is not None:
            value = float(value)
        result[result_key] = value
    return result


__all__ = [
    "_bool_or_none",
    "_demographic_answers",
    "_float_or_none",
    "_clean_metadata",
    "_month_result_row",
    "_month_result_from_row",
    "_parse",
    "_psychometric_rows",
]
