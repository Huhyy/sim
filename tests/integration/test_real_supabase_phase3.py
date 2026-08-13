"""Opt-in Phase 3.5 verification against a real, disposable Supabase project.

Run only through scripts/load-integration-env.ps1. Every test uses unique
identifiers and deletes only records created by that test module.
"""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

from sim_app.application.errors import ConcurrencyConflict, IdempotencyConflict, SessionNotFound
from sim_app.application.instrumentation import OperationMetrics
from sim_app.application.state import ParticipantState
from sim_app.application.services import ExperimentService
from sim_app.config import SCENARIO_VERSION
from sim_app.content.tables import get_month
from sim_app.domain.experimental_conditions import condition_config
from sim_app.domain.loan import Loan
from sim_app.domain.overdraft import Overdraft
from sim_app.domain.simulation import compute_month_preview, compute_month_result
from sim_app.infra.supabase import get_client, reset_shared_client
from sim_app.persistence.experiment_repository import SupabaseExperimentRepository
from sim_app.composition import get_experiment_service, set_experiment_service


ENABLED = (
    os.getenv("RUN_SUPABASE_INTEGRATION") == "1"
    and os.getenv("SUPABASE_INTEGRATION_ALLOW_SYNTHETIC_WRITES") == "1"
    and bool(os.getenv("SUPABASE_URL"))
    and bool(os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
)
pytestmark = pytest.mark.skipif(
    not ENABLED,
    reason="real Supabase tests require explicit Phase 3.5 environment and write opt-in",
)

GOLDEN_DIGEST = "17f8a2632d861e432c2cd81f86495c4b75356deaa7b55911c2eca6a53f75ab43"
RPC_NAMES = (
    "claim_participant_session_v3",
    "commit_stage_transition_v3",
    "commit_quality_transition_v3",
    "commit_month_decision_v3",
    "acknowledge_month_feedback_v3",
    "backfill_legacy_session_v3",
    "finalize_experiment_v3",
    "claim_prolific_payment_v3",
    "finish_prolific_payment_v3",
)


@pytest.fixture(scope="module")
def production():
    reset_shared_client()
    set_experiment_service(None)
    yield get_experiment_service(), get_client()
    set_experiment_service(None)
    reset_shared_client()


def _state(session_id, *, condition="C1", page="simulation"):
    state = ParticipantState.initial(SCENARIO_VERSION)
    state.session_id = session_id
    state.page = page
    treatment = condition_config(condition)
    state.experimental_condition = treatment["experimental_condition"]
    state.score_frame = treatment["score_frame"]
    state.monthly_score_feedback = treatment["monthly_score_feedback"]
    state.treatment_bound = True
    return state


def _identity(label):
    session_id = str(uuid4())
    account_key = hashlib.sha256(f"phase35:{label}:{session_id}".encode()).hexdigest()
    return session_id, account_key


def _cleanup(client, session_id, account_key):
    for table, column in (
        ("quality_checks", "app_session_id"),
        ("psychometric_pre_answers", "session_id"),
        ("psychometric_post_answers", "session_id"),
        ("session_summaries", "session_id"),
        ("prolific_payment_attempts", "session_id"),
        ("experiment_idempotency", "session_id"),
        ("month_results", "session_id"),
        ("resume_links", "session_id"),
    ):
        client.table(table).delete().eq(column, session_id).execute()
    client.table("completed_accounts").delete().eq("account_key", account_key).execute()
    client.table("participant_sessions").delete().eq("id", session_id).execute()


def _create(service, label, *, condition="C1", page="simulation"):
    session_id, account_key = _identity(label)
    result = service.create_session(
        _state(session_id, condition=condition, page=page),
        account_key=account_key,
        request_id=f"phase35:{label}:create:{session_id}",
    )
    return result.state, account_key


def test_real_schema_rpc_visibility_not_found_and_instrumentation(production):
    service, client = production
    response = client.postgrest.session.request("GET", "/", headers={"Accept": "application/openapi+json"})
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert all(f"/rpc/{name}" in paths for name in RPC_NAMES)

    with pytest.raises(SessionNotFound):
        service.load_session(str(uuid4()))

    metrics = OperationMetrics()
    measured = ExperimentService(SupabaseExperimentRepository(metrics=metrics), metrics=metrics)
    assert measured.find_session(str(uuid4())) is None
    snapshot = metrics.snapshot()
    assert snapshot["application.load_session.count"] == 1
    assert snapshot["database_request_count"] >= 1
    assert snapshot["database.load_participant.count"] == 1


def test_real_month_idempotency_feedback_and_treatment_trigger(production):
    service, client = production
    state, account_key = _create(service, "month")
    try:
        request_id = f"phase35:month:{state.session_id}"
        first = service.submit_month_decision(
            session_id=state.session_id,
            expected_version=0,
            expected_month=1,
            payment=317.71,
            request_id=request_id,
        )
        rows = client.table("month_results").select("*").eq("session_id", state.session_id).execute().data
        assert len(rows) == 1
        assert float(rows[0]["monthly_score"]) == float(first.result["monthly_score"])
        assert rows[0]["decision_request_id"] == request_id
        assert first.state.state_version == 1
        assert first.state.page == "month_feedback"

        retry = service.submit_month_decision(
            session_id=state.session_id,
            expected_version=0,
            expected_month=1,
            payment=317.71,
            request_id=request_id,
        )
        assert retry.idempotency_hit is True
        assert retry.state.state_version == 1

        with pytest.raises(IdempotencyConflict):
            service.submit_month_decision(
                session_id=state.session_id,
                expected_version=0,
                expected_month=1,
                payment=300.0,
                request_id=request_id,
            )

        acknowledged = service.acknowledge_month_feedback(
            session_id=state.session_id,
            expected_version=1,
            expected_month=1,
            request_id=f"phase35:ack:{state.session_id}",
        )
        assert acknowledged.state.state_version == 2
        assert acknowledged.state.month == 2
        assert acknowledged.state.page == "simulation"
        assert len(client.table("month_results").select("session_id").eq("session_id", state.session_id).execute().data) == 1

        with pytest.raises(Exception):
            client.table("participant_sessions").update({"experimental_condition": "C2"}).eq("id", state.session_id).execute()
        durable = client.table("participant_sessions").select("experimental_condition").eq("id", state.session_id).single().execute().data
        assert durable["experimental_condition"] == "C1"
    finally:
        _cleanup(client, state.session_id, account_key)


def test_real_concurrent_same_version_has_one_winner(production):
    service, client = production
    for trial in range(3):
        state, account_key = _create(service, f"concurrency-{trial}")
        try:
            barrier = Barrier(2)

            def submit(payment, label):
                barrier.wait()
                try:
                    result = service.submit_month_decision(
                        session_id=state.session_id,
                        expected_version=0,
                        expected_month=1,
                        payment=payment,
                        request_id=f"phase35:concurrency:{trial}:{label}:{state.session_id}",
                    )
                    return "success", payment, result.state.state_version, id(get_client())
                except ConcurrencyConflict:
                    return "conflict", payment, None, id(get_client())

            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = (pool.submit(submit, 317.71, "a"), pool.submit(submit, 300.0, "b"))
                outcomes = [future.result() for future in futures]

            assert [item[0] for item in outcomes].count("success") == 1
            assert [item[0] for item in outcomes].count("conflict") == 1
            assert len({item[3] for item in outcomes}) == 2
            rows = client.table("month_results").select("payment_input").eq("session_id", state.session_id).execute().data
            participant = client.table("participant_sessions").select("state_version,current_page").eq("id", state.session_id).single().execute().data
            winner = next(item[1] for item in outcomes if item[0] == "success")
            assert len(rows) == 1
            assert float(rows[0]["payment_input"]) == winner
            assert int(participant["state_version"]) == 1
            assert participant["current_page"] == "month_feedback"
        finally:
            _cleanup(client, state.session_id, account_key)


def test_real_quality_and_legacy_backfill(production):
    service, client = production
    state, account_key = _create(service, "quality", page="comprehension")
    try:
        proposed = state.copy()
        proposed.comprehension_attempts = 1
        proposed.comprehension_passed = True
        proposed.page = "simulation"
        event = {
            "event_index": 0,
            "page_id": "comprehension",
            "check_type": "comprehension",
            "check_id": "phase35",
            "attempt_number": 1,
            "passed": True,
            "response_value": "A",
            "response_time_ms": 10,
        }
        request_id = f"phase35:quality:{state.session_id}"
        first = service.save_quality_transition(proposed, [event], expected_version=0, request_id=request_id)
        retry = service.save_quality_transition(proposed, [event], expected_version=0, request_id=request_id)
        assert first.state.state_version == 1
        assert retry.idempotency_hit is True
        assert len(client.table("quality_checks").select("id").eq("app_session_id", state.session_id).execute().data) == 1
    finally:
        _cleanup(client, state.session_id, account_key)

    state, account_key = _create(service, "legacy")
    try:
        loan = Loan(balance=7000.0, annual_interest=0.0835, months=24)
        overdraft = Overdraft(limit=3000.0, annual_interest=0.18)
        month_data = get_month(1)
        preview = compute_month_preview(1, month_data, loan, overdraft, [])
        payment = min(317.71, preview["max_payment"], loan.balance)
        result = compute_month_result(1, month_data, loan, overdraft, payment, monthly_results=[], translate=lambda key: key)
        legacy = _state(state.session_id)
        legacy.month = 2
        legacy.monthly_results = [result]
        legacy.loan.balance = result["credit_final"]
        legacy.overdraft.balance = result["overdraft_final"]
        legacy.total_score = result["monthly_score"]
        legacy.monthly_points = result["monthly_score"]
        legacy.accumulated_costs = result["costs_this_month"]
        client.table("participant_sessions").update({
            "checkpoint": legacy.to_checkpoint(),
            "current_month": 1,
            "loan_balance": 7000,
            "overdraft_balance": 0,
            "total_score": 0,
            "monthly_points": 0,
            "accumulated_costs": 0,
        }).eq("id", state.session_id).execute()

        migrated = service.load_session(state.session_id)
        loaded_again = service.load_session(state.session_id)
        assert migrated.month == 2
        assert migrated.state_version == loaded_again.state_version == 1
        assert len(client.table("month_results").select("month_number").eq("session_id", state.session_id).execute().data) == 1

        mismatch = legacy.to_checkpoint()
        mismatch["monthly_results"][0] = dict(mismatch["monthly_results"][0], monthly_score=1.0)
        client.table("participant_sessions").update({"checkpoint": mismatch}).eq("id", state.session_id).execute()
        with pytest.raises(ConcurrencyConflict):
            service.load_session(state.session_id)
    finally:
        _cleanup(client, state.session_id, account_key)


def test_real_24_month_journey_and_finalization(production):
    service, client = production
    state, account_key = _create(service, "full", condition="C4")
    try:
        results = []
        for month in range(1, 25):
            data = get_month(month)
            preview = compute_month_preview(month, data, state.loan, state.overdraft, state.monthly_results)
            payment = min(317.71, preview["max_payment"], state.loan.balance)
            committed = service.submit_month_decision(
                session_id=state.session_id,
                expected_version=state.state_version,
                expected_month=month,
                payment=payment,
                request_id=f"phase35:full:month:{month}:{state.session_id}",
            )
            state = committed.state
            results.append(committed.result)
            state = service.acknowledge_month_feedback(
                session_id=state.session_id,
                expected_version=state.state_version,
                expected_month=month,
                request_id=f"phase35:full:ack:{month}:{state.session_id}",
            ).state

        digest = hashlib.sha256(json.dumps(results, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        rows = client.table("month_results").select("month_number").eq("session_id", state.session_id).order("month_number").execute().data
        assert digest == GOLDEN_DIGEST
        assert [int(row["month_number"]) for row in rows] == list(range(1, 25))
        assert state.loan.balance == 0.0
        assert state.overdraft.balance == 1836.0

        proposed = state.copy()
        proposed.page = "done"
        state = service.save_stage(
            proposed,
            expected_version=state.state_version,
            request_id=f"phase35:full:done:{state.session_id}",
        ).state
        request_id = f"phase35:full:finalize:{state.session_id}"
        finalized = service.finalize(
            session_id=state.session_id,
            expected_version=state.state_version,
            request_id=request_id,
            account_key=account_key,
            pre_sections=[],
            post_sections=[],
        )
        retry = service.finalize(
            session_id=state.session_id,
            expected_version=state.state_version,
            request_id=request_id,
            account_key=account_key,
            pre_sections=[],
            post_sections=[],
        )
        assert finalized.state.final_score == 83.78
        assert finalized.state.submission_finalized is True
        assert retry.idempotency_hit is True
        assert len(client.table("completed_accounts").select("account_key").eq("account_key", account_key).execute().data) == 1
        assert client.table("resume_links").select("session_id").eq("session_id", state.session_id).execute().data == []
    finally:
        _cleanup(client, state.session_id, account_key)

def test_real_fake_prolific_lifecycle(production, monkeypatch):
    service, client = production
    # Exercise the real payment RPC lifecycle with a fake external processor.
    import sim_app.prolific.bonuses as bonuses

    state, account_key = _create(service, "payment", page="done")
    payment_request = f"phase35:payment:{state.session_id}"
    try:
        client.table("session_summaries").insert({
            "session_id": state.session_id,
            "months_completed": 24,
            "final_score": 83.78,
            "performance_bonus_gbp": 2,
            "prolific_base_reward_gbp": 5,
            "prolific_pid": "synthetic-pid",
            "prolific_study_id": "synthetic-study",
            "prolific_session_id": "synthetic-submission",
            "completion_code": "SYNTHETIC-CODE",
            "payment_idempotency_key": payment_request,
            "prolific_bonus_status": "pending",
        }).execute()
        client.table("prolific_payment_attempts").insert({
            "session_id": state.session_id,
            "request_id": payment_request,
            "status": "pending",
        }).execute()
        summary = client.table("session_summaries").select("*").eq("session_id", state.session_id).single().execute().data
        external_calls = []
        monkeypatch.setattr(bonuses, "_get_secret", lambda name: "synthetic-local-value")
        monkeypatch.setattr(
            bonuses,
            "create_bonus_payment",
            lambda *args: external_calls.append(args) or {"id": "synthetic-bonus-payment"},
        )
        bonuses.process_prolific_bonus(client, state.session_id, summary)
        summary = client.table("session_summaries").select("*").eq("session_id", state.session_id).single().execute().data
        bonuses.process_prolific_bonus(client, state.session_id, summary)
        attempt = client.table("prolific_payment_attempts").select("status,attempt_count").eq("session_id", state.session_id).single().execute().data
        participant = client.table("participant_sessions").select("completion_status").eq("id", state.session_id).single().execute().data
        assert len(external_calls) == 1
        assert attempt["status"] == "succeeded"
        assert int(attempt["attempt_count"]) == 1
        assert participant["completion_status"] == "payment_manual_review"
    finally:
        _cleanup(client, state.session_id, account_key)
