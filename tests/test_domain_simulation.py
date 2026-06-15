from sim_app.content.tables import get_month
from sim_app.domain.loan import Loan
from sim_app.domain.overdraft import Overdraft
from sim_app.domain.scoring import compute_final_score_from_results, compute_monthly_score
from sim_app.domain.simulation import compute_month_result, get_opening_balance


def test_compute_monthly_score_returns_behavioral_v1_breakdown():
    score = compute_monthly_score(
        accepted_payment=317.71,
        cash_final=5.0,
        overdraft_final=0.0,
        overdraft_limit=3000.0,
        loan_obligation=317.71,
        loan_balance_before_payment=7000.0,
    )

    assert score == {
        "score_model": "behavioral_v1",
        "score_repayment": 40.0,
        "score_liquidity": 30.0,
        "score_overdraft": 30.0,
        "monthly_score": 100.0,
        "bonus_lunar": 0.5,
    }


def test_compute_final_score_from_results_averages_over_session_months():
    assert compute_final_score_from_results(
        [
            {"score_model": "behavioral_v1", "monthly_score": 100.0},
            {"score_model": "behavioral_v1", "monthly_score": 50.0},
        ]
    ) == 6.25


def test_get_opening_balance_prefers_previous_month_result():
    data = {"position": {"initial": 150.0}}

    assert get_opening_balance(1, data) == 150.0
    assert get_opening_balance(2, data, monthly_results=[{"month": 1, "cash_final": 42.5}]) == 42.5


def test_compute_month_result_returns_expected_shape():
    data = get_month(1)
    loan = Loan(balance=7000.0, annual_interest=0.0835, months=24)
    overdraft = Overdraft(limit=3000.0, annual_interest=0.18)

    result = compute_month_result(
        1,
        data,
        loan,
        overdraft,
        payment=100.0,
        translate=lambda key: key,
    )

    assert result["month"] == 1
    assert result["loan_balance_before_payment"] == 7000.0
    assert result["payment_input"] == 100.0
    assert result["score_model"] == "behavioral_v1"
    assert "feedback_message" in result
