import hashlib
import json
from types import SimpleNamespace

import pytest

from sim_app.application.commands import (
    accept_consent,
    acknowledge_month_feedback,
    calculate_final_scores,
    complete_final_score,
    complete_instructions,
    complete_post_question,
    complete_pre_question,
    complete_profile,
    submit_comprehension,
    submit_demographics,
    submit_month_decision,
)
from sim_app.application.progression import (
    redirect_before_simulation,
    required_page_before_demographics,
    required_page_before_pre_questions,
)
from sim_app.application.state import ParticipantState
from sim_app.config import SCENARIO_VERSION
from sim_app.content.tables import get_month
from sim_app.domain.experimental_conditions import condition_config, performance_bonus
from sim_app.domain.loan import Loan
from sim_app.domain.overdraft import Overdraft
from sim_app.domain.scoring import compute_monthly_score
from sim_app.domain.simulation import compute_month_preview, compute_month_result
from sim_app.application.services import ExperimentService
from sim_app.persistence.memory import InMemoryExperimentRepository
from sim_app.session.streamlit_state import navigate
from sim_app.ui.pages.month_feedback import render_month_feedback_page
from sim_app.ui.pages.simulation import render_simulation_page


class DummySessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


def _translate(key):
    return key


def _golden_month_journey():
    loan = Loan(balance=7000.0, annual_interest=0.0835, months=24)
    overdraft = Overdraft(limit=3000.0, annual_interest=0.18)
    results = []
    states_before = []
    for month in range(1, 25):
        states_before.append((loan.balance, overdraft.balance, list(results)))
        data = get_month(month)
        preview = compute_month_preview(month, data, loan, overdraft, results)
        payment = min(317.71, preview["max_payment"], loan.balance)
        result = compute_month_result(
            month,
            data,
            loan,
            overdraft,
            payment,
            monthly_results=results,
            translate=_translate,
        )
        results.append(result)
        loan.balance = result["credit_final"]
        overdraft.balance = result["overdraft_final"]
    return results, states_before, loan, overdraft


def test_all_24_months_match_the_production_golden_journey():
    results, _, loan, overdraft = _golden_month_journey()
    digest = hashlib.sha256(
        json.dumps(results, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    assert digest == "17f8a2632d861e432c2cd81f86495c4b75356deaa7b55911c2eca6a53f75ab43"
    assert [result["month"] for result in results] == list(range(1, 25))
    assert loan.balance == 0.0
    assert overdraft.balance == 1836.0
    assert round(sum(result["monthly_score"] for result in results), 2) == 2010.67


@pytest.mark.parametrize("condition", ["C1", "C2", "C3", "C4"])
def test_final_breakdown_preserves_every_treatment_and_payment_field(condition):
    results, _, loan, overdraft = _golden_month_journey()
    config = condition_config(condition)
    state = ParticipantState.initial(SCENARIO_VERSION)
    state.monthly_results = results
    state.loan = loan
    state.overdraft = overdraft
    state.experimental_condition = condition
    state.score_frame = config["score_frame"]
    state.monthly_score_feedback = config["monthly_score_feedback"]
    state.study_session_id = "study-session"
    state.study_session_code = "123456"
    state.participant_code = "P007"
    state.prolific_pid = "pid"
    state.prolific_study_id = "study"
    state.prolific_session_id = "submission"
    state.prolific_completion_code = "COMPLETE"

    calculated = calculate_final_scores(state)
    breakdown = calculated.final_score_breakdown

    assert calculated.final_score == 83.78
    assert breakdown["experimental_condition"] == condition
    assert breakdown["score_frame"] == config["score_frame"]
    assert breakdown["monthly_score_feedback"] == config["monthly_score_feedback"]
    assert breakdown["performance_bonus_gbp"] == 2
    assert breakdown["loss_amount_gbp"] == 1
    assert breakdown["prolific_base_reward_gbp"] == 5
    assert breakdown["total_payout_gbp"] == 7
    assert breakdown["participant_code"] == "P007"
    assert breakdown["completion_code"] == "COMPLETE"


@pytest.mark.parametrize(
    ("accepted_payment", "cash_final", "overdraft_final", "expected"),
    [
        (0.0, 0.0, 0.0, 30.0),
        (317.71, 5.0, 0.0, 100.0),
        (317.71, 0.0, 3000.0, 40.0),
        (158.855, 2.5, 1500.0, 50.0),
    ],
)
def test_monthly_score_edge_cases_are_stable(accepted_payment, cash_final, overdraft_final, expected):
    score = compute_monthly_score(
        accepted_payment,
        cash_final,
        overdraft_final,
        3000.0,
        317.71,
        7000.0,
    )
    assert score["monthly_score"] == expected


def test_valid_invalid_blocked_and_closed_loan_states_are_stable():
    data = {
        "position": {"initial": 0.0},
        "income": {"salary": 0.0},
        "expenses": {"living": 100.0},
        "obligations": {},
    }
    blocked_loan = Loan(7000.0, 0.0835, 24)
    blocked_overdraft = Overdraft(3000.0, 0.18)
    blocked_overdraft.balance = 2999.0
    blocked = compute_month_result(1, data, blocked_loan, blocked_overdraft, 0.0, translate=_translate)
    assert blocked["pre_credit_impossible"] is True
    assert blocked["invalid_reason"] == "pre_credit"
    assert blocked["monthly_score"] == 0.0

    available_data = {
        "position": {"initial": 1000.0},
        "income": {"salary": 1000.0},
        "expenses": {"living": 0.0},
        "obligations": {},
    }
    loan = Loan(7000.0, 0.0835, 24)
    overdraft = Overdraft(3000.0, 0.18)
    invalid = compute_month_result(1, available_data, loan, overdraft, 5000.0, translate=_translate)
    assert invalid["payment_valid"] is False
    assert invalid["invalid_reason"] == "payment"

    closed = compute_month_result(
        1,
        available_data,
        Loan(0.0, 0.0835, 24),
        Overdraft(3000.0, 0.18),
        None,
        translate=_translate,
    )
    assert closed["payment_valid"] is True
    assert closed["accepted_payment"] == 0.0
    assert closed["score_repayment"] == 40.0


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (74.99, {"performance_bonus_gbp": 0, "loss_amount_gbp": 3}),
        (75, {"performance_bonus_gbp": 1, "loss_amount_gbp": 2}),
        (80, {"performance_bonus_gbp": 2, "loss_amount_gbp": 1}),
        (90, {"performance_bonus_gbp": 3, "loss_amount_gbp": 0}),
    ],
)
def test_performance_bonus_thresholds_remain_authoritative(score, expected):
    assert performance_bonus(score) == expected


def test_checkpoint_round_trip_preserves_the_exact_legacy_representation():
    checkpoint = {
        "scenario_version": SCENARIO_VERSION,
        "page": "month_feedback",
        "admin_return_page": "home",
        "language": "ro",
        "month": 7,
        "study_session_id": "study-session",
        "study_session_code": "123456",
        "participant_code": "P011",
        "prolific_pid": "pid",
        "prolific_study_id": "study",
        "prolific_session_id": "submission",
        "prolific_mode": True,
        "prolific_completion_url": "https://example.test/complete",
        "prolific_completion_code": "CODE",
        "prolific_redirected": False,
        "experimental_condition": "C4",
        "score_frame": "loss_frame",
        "monthly_score_feedback": "hidden",
        "loan_balance": 6100.25,
        "overdraft_balance": 234.5,
        "savings": None,
        "total_score": 432.1,
        "monthly_points": 432.1,
        "accumulated_costs": 171.2,
        "monthly_results": [{"month": 6, "monthly_score": 75.0}],
        "pending_month_result": {"month": 7, "monthly_score": 80.0},
        "final_score": None,
        "final_score_breakdown": None,
        "answers": {"consent_agreed": "1 - Da", "demo_age": 34},
        "comprehension_attempts": 1,
        "comprehension_passed": True,
        "attention_failed_count": 0,
        "payment_values": {"payment_7": 300.0},
    }
    state = ParticipantState.from_checkpoint(checkpoint, SCENARIO_VERSION)
    assert state.to_checkpoint() == checkpoint


def test_full_framework_neutral_progression_matches_the_streamlit_flow():
    state = ParticipantState.initial(SCENARIO_VERSION)
    assert required_page_before_demographics(state) == "consent"
    assert required_page_before_pre_questions(state) == "consent"

    state = accept_consent(state).state
    assert state.page == "demographics"
    assert required_page_before_pre_questions(state) == "demographics"

    demographics = {
        "demo_age": 30,
        "demo_gender": "x",
        "demo_education": "x",
        "demo_field": "x",
        "demo_occupation": "x",
        "demo_income": "x",
        "demo_financial_decisions": "x",
        "demo_credit_experience": "x",
        "demo_financial_familiarity": "x",
        "demo_living_situation": "x",
        "demo_recurring_responsibilities": "x",
        "demo_country": "x",
    }
    state = submit_demographics(state, demographics).state
    assert state.page == "pre_question_0"
    state = complete_pre_question(state, section_index=0, section_count=2).state
    assert state.page == "pre_question_1"
    state = complete_pre_question(state, section_index=1, section_count=2).state
    assert state.page == "instructions"
    state = complete_instructions(state).state
    assert state.page == "profile"
    state = complete_profile(state).state
    assert state.page == "simulation"

    for month in range(1, 25):
        data = get_month(month)
        preview = compute_month_preview(month, data, state.loan, state.overdraft, state.monthly_results)
        payment = None if preview["no_loan_due"] else min(317.71, preview["max_payment"], state.loan.balance)
        submitted = submit_month_decision(state, month_data=data, payment=payment, translate=_translate)
        assert submitted.next_page == "month_feedback"
        state = acknowledge_month_feedback(submitted.state).state
        assert state.page == "simulation"

    assert state.month == 25
    assert redirect_before_simulation(state.month) == "post_question_0"
    state.page = "post_question_0"
    state = complete_post_question(state, section_index=0, section_count=2).state
    assert state.page == "post_question_1"
    state = complete_post_question(state, section_index=1, section_count=2).state
    assert state.page == "final_score"
    state = calculate_final_scores(state)
    state = complete_final_score(state).state
    assert state.page == "done"
    assert len(state.monthly_results) == 24


def test_prolific_instructions_and_comprehension_progression_are_stable():
    state = ParticipantState.initial(SCENARIO_VERSION)
    state.prolific_mode = True
    state = complete_instructions(state).state
    assert state.page == "comprehension"
    first_failure = submit_comprehension(state, passed=False)
    assert first_failure.next_page is None
    assert first_failure.state.comprehension_attempts == 1
    passed = submit_comprehension(first_failure.state, passed=True, passed_at="now")
    assert passed.next_page == "profile"
    assert passed.state.comprehension_attempts == 2
    assert passed.state.answers["comprehension_passed_at"] == "now"


def test_navigation_preserves_checkpoint_then_rerun_order():
    calls = []
    state = DummySessionState(page="home", scroll_to_top=False)
    navigate(
        state,
        "consent",
        lambda: calls.append(("checkpoint", state.page, state.scroll_to_top)),
        lambda: calls.append(("rerun", state.page, state.scroll_to_top)),
    )
    assert calls == [
        ("checkpoint", "consent", True),
        ("rerun", "consent", True),
    ]


class _NoOpColumn:
    def metric(self, *args, **kwargs):
        return None


class _FeedbackStreamlit:
    def __init__(self, session_state):
        self.session_state = session_state

    def __getattr__(self, name):
        if name == "button":
            return lambda *args, **kwargs: True
        if name == "columns":
            return lambda count: [_NoOpColumn() for _ in range(count)]
        return lambda *args, **kwargs: None


class _ContextBlock:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _SimulationStreamlit(_FeedbackStreamlit):
    def __getattr__(self, name):
        if name == "expander":
            return lambda *args, **kwargs: _ContextBlock()
        if name == "number_input":
            return lambda *args, **kwargs: 100.0
        return super().__getattr__(name)


def test_normal_month_commits_before_feedback_and_acknowledges_separately():
    runtime = ParticipantState.initial(SCENARIO_VERSION)
    runtime.session_id = "session"
    runtime.page = "simulation"
    runtime.monthly_score_feedback = "hidden"
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    service.create_session(runtime, account_key="a" * 64, request_id="create")
    session_state = DummySessionState(runtime.to_runtime_defaults())
    session_state.session_id = runtime.session_id
    calls = []
    ctx = SimpleNamespace(
        st=_SimulationStreamlit(session_state),
        t=lambda key, **kwargs: key,
        experiment_service=service,
        goto=lambda page: calls.append(("unexpected_navigation", page)),
        scroll_top_anchor=lambda: None,
        get_month=get_month,
        get_localized_narrative=lambda _month: "Narrative",
        auto_open_context_narrativ=lambda _label: None,
        get_category_label=lambda value: value,
        attach_payment_keyboard_bridge=lambda: None,
    )

    render_simulation_page(ctx)
    assert calls == []
    assert session_state.pending_month_result["month"] == 1
    assert repository.month_result_count("session") == 1
    assert session_state.state_version == 1

    feedback_ctx = SimpleNamespace(
        st=_FeedbackStreamlit(session_state),
        t=lambda key, **kwargs: key,
        scroll_top_anchor=lambda: None,
        experiment_service=service,
        goto=lambda page: calls.append(("unexpected_navigation", page)),
    )
    render_month_feedback_page(feedback_ctx)

    assert calls == []
    assert session_state.month == 2
    assert session_state.state_version == 2
    assert repository.month_result_count("session") == 1


def test_month_24_acknowledgment_uses_existing_structured_ledger():
    results, states_before, _, _ = _golden_month_journey()
    loan_balance, overdraft_balance, previous = states_before[23]
    runtime = ParticipantState.initial(SCENARIO_VERSION)
    runtime.session_id = "session"
    runtime.page = "month_feedback"
    runtime.month = 24
    runtime.loan.balance = results[23]["credit_final"]
    runtime.overdraft.balance = results[23]["overdraft_final"]
    runtime.monthly_results = results
    runtime.pending_month_result = results[23]
    runtime.monthly_score_feedback = "hidden"
    runtime.total_score = sum(result["monthly_score"] for result in results)
    runtime.monthly_points = runtime.total_score
    runtime.accumulated_costs = sum(result["costs_this_month"] for result in results)
    runtime.state_version = 47
    repository = InMemoryExperimentRepository()
    repository.seed_legacy(runtime, account_key="a" * 64)
    repository.replace_state_and_ledger(runtime)
    service = ExperimentService(repository)
    session_state = DummySessionState(runtime.to_runtime_defaults())
    session_state.session_id = runtime.session_id
    session_state.pending_month_result = runtime.pending_month_result
    ctx = SimpleNamespace(
        st=_FeedbackStreamlit(session_state),
        t=lambda key, **kwargs: key,
        scroll_top_anchor=lambda: None,
        experiment_service=service,
        goto=lambda page: None,
    )
    render_month_feedback_page(ctx)

    assert session_state.month == 25
    assert session_state.pending_month_result is None
    assert repository.month_result_count("session") == 24
