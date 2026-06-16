"""Month-level financial simulation helpers."""

from sim_app.domain.scoring import compute_monthly_score, money, zero_score_data


def month_sum(values):
    return money(sum(values.values()))


def get_opening_balance(month, data, monthly_results=None):
    if month <= 1:
        return money(data["position"]["initial"])

    for result in reversed(monthly_results or []):
        if int(result.get("month", 0)) == month - 1:
            return money(result.get("cash_final", 0.0))

    return money(data["position"].get("initial", 0.0))


def compute_month_result(month, data, loan, overdraft, payment, monthly_results=None, translate=None):
    t = translate or (lambda key: key)
    income_total = month_sum(data["income"])
    expenses_total = month_sum(data["expenses"])
    obligations = data.get("obligations", {})
    loan_balance_before_payment = money(loan.balance)
    loan_obligation = money(loan.get_required_payment())
    credit_interest = money(loan.apply_interest())
    overdraft_interest = money(overdraft.apply_interest())
    penalties = money(obligations.get("penalties", 0))
    opening_balance = get_opening_balance(month, data, monthly_results=monthly_results)

    available_total = money(opening_balance + income_total)
    outflows_before_credit = money(expenses_total + overdraft_interest + credit_interest + penalties)
    deficit_before_credit = money(max(0.0, outflows_before_credit - available_total))
    liquidity_after_charges = money(max(0.0, available_total - outflows_before_credit))
    overdraft_after_charges = money(overdraft.balance + deficit_before_credit)
    overdraft_remaining = money(max(0.0, overdraft.limit - min(overdraft_after_charges, overdraft.limit)))
    max_payment = money(liquidity_after_charges + overdraft_remaining)

    pre_credit_impossible = overdraft_after_charges > overdraft.limit
    no_loan_due = loan_balance_before_payment <= 0 and loan_obligation <= 0
    payment_value = None if payment is None else money(payment)
    capped_payment = None if payment_value is None else money(min(payment_value, loan.balance))
    payment_valid = (
        not pre_credit_impossible
        and (
            no_loan_due
            or (
                payment_value is not None
                and payment_value >= 0
                and capped_payment <= max_payment
            )
        )
    )

    if pre_credit_impossible:
        feedback_message = t("simulation.feedback_pre_credit")
        accepted_payment = 0.0
        overdraft_from_payment = 0.0
        overdraft_final = money(overdraft.limit)
        cash_final = 0.0
        credit_final = money(loan.balance)
        score_data = zero_score_data()
        invalid_reason = "pre_credit"
    elif payment_valid:
        accepted_payment = 0.0 if no_loan_due else capped_payment
        overdraft_from_payment = money(max(0.0, accepted_payment - liquidity_after_charges))
        overdraft_final = money(overdraft_after_charges + overdraft_from_payment)
        cash_final = money(max(0.0, liquidity_after_charges - accepted_payment))
        credit_final = money(max(0.0, loan.balance - accepted_payment))
        score_data = compute_monthly_score(
            accepted_payment,
            cash_final,
            overdraft_final,
            overdraft.limit,
            loan_obligation,
            loan_balance_before_payment,
            credit_final <= 0 and loan_balance_before_payment > 0,
        )
        feedback_message = t("simulation.feedback_no_payment_due") if no_loan_due else t("simulation.feedback_success")
        invalid_reason = None
    else:
        accepted_payment = 0.0
        overdraft_from_payment = 0.0
        overdraft_final = money(overdraft_after_charges)
        cash_final = money(liquidity_after_charges)
        credit_final = money(loan.balance)
        score_data = zero_score_data()
        feedback_message = t("simulation.feedback_invalid")
        invalid_reason = "payment"

    if overdraft_final > overdraft.limit:
        overdraft_final = money(overdraft.limit)
        cash_final = 0.0
        if score_data["monthly_score"] > 0:
            accepted_payment = 0.0
            credit_final = money(loan.balance)
            overdraft_from_payment = 0.0
            score_data = zero_score_data()
            feedback_message = t("simulation.feedback_invalid")
            invalid_reason = "payment"

    return {
        "month": month,
        "opening_balance": opening_balance,
        "income_total": income_total,
        "expenses_total": expenses_total,
        "loan_balance_before_payment": loan_balance_before_payment,
        "loan_obligation": loan_obligation,
        "credit_interest": credit_interest,
        "overdraft_interest": overdraft_interest,
        "penalties": penalties,
        "available_total": available_total,
        "outflows_before_credit": outflows_before_credit,
        "deficit_before_credit": deficit_before_credit,
        "liquidity_after_charges": liquidity_after_charges,
        "overdraft_after_charges": overdraft_after_charges,
        "overdraft_remaining": overdraft_remaining,
        "max_payment": max_payment,
        "payment_input": 0.0 if payment_value is None else payment_value,
        "accepted_payment": accepted_payment,
        "overdraft_from_payment": overdraft_from_payment,
        "overdraft_final": overdraft_final,
        "cash_final": cash_final,
        "credit_final": credit_final,
        **score_data,
        "costs_this_month": money(credit_interest + overdraft_interest + penalties),
        "feedback_message": feedback_message,
        "invalid_reason": invalid_reason,
        "pre_credit_impossible": pre_credit_impossible,
        "payment_valid": payment_valid,
    }

