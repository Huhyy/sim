from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from urllib.error import URLError

import pytest

from sim_app.application.errors import (
    ConcurrencyConflict,
    InvalidTransition,
    PersistenceReadError,
    PersistenceWriteError,
    TreatmentConflict,
)
from sim_app.application.services import ExperimentService
from sim_app.application.principal import ParticipantPrincipal
from sim_app.application.state import ParticipantState
from sim_app.config import SCENARIO_VERSION
from sim_app.domain.experimental_conditions import condition_config
from sim_app.persistence.memory import InMemoryExperimentRepository


def _service_state(condition="C1"):
    state = ParticipantState.initial(SCENARIO_VERSION)
    state.session_id = "00000000-0000-0000-0000-000000000001"
    state.page = "simulation"
    treatment = condition_config(condition)
    state.experimental_condition = treatment["experimental_condition"]
    state.score_frame = treatment["score_frame"]
    state.monthly_score_feedback = treatment["monthly_score_feedback"]
    state.treatment_bound = True
    return state


def _service():
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    state = _service_state()
    service.create_session(state, account_key="a" * 64, request_id="create-1")
    return service, repository


def test_month_commit_is_atomic_authoritative_and_feedback_preserving():
    service, repository = _service()

    committed = service.submit_month_decision(
        session_id=_service_state().session_id,
        expected_version=0,
        expected_month=1,
        payment=317.71,
        request_id="month-1",
    )

    assert committed.state.state_version == 1
    assert committed.state.page == "month_feedback"
    assert committed.state.month == 1
    assert committed.state.pending_month_result == committed.result
    assert repository.month_result_count(committed.state.session_id) == 1
    assert repository.month_results(committed.state.session_id)[0] == committed.result

    acknowledged = service.acknowledge_month_feedback(
        session_id=committed.state.session_id,
        expected_version=1,
        expected_month=1,
        request_id="feedback-1",
    )
    assert acknowledged.state.state_version == 2
    assert acknowledged.state.month == 2
    assert acknowledged.state.page == "simulation"
    assert acknowledged.state.pending_month_result is None
    assert repository.month_result_count(committed.state.session_id) == 1


@pytest.mark.parametrize("phase", ["before", "during"])
def test_database_failure_cannot_partially_commit_or_advance(phase):
    service, repository = _service()
    repository.fail_next("commit_month_decision", phase=phase)

    with pytest.raises(PersistenceWriteError):
        service.submit_month_decision(
            session_id=_service_state().session_id,
            expected_version=0,
            expected_month=1,
            payment=317.71,
            request_id=f"failed-{phase}",
        )

    stored = service.load_session(_service_state().session_id)
    assert stored.state_version == 0
    assert stored.month == 1
    assert stored.page == "simulation"
    assert repository.month_result_count(stored.session_id) == 0


def test_response_lost_retry_and_double_click_are_idempotent():
    service, repository = _service()
    first = service.submit_month_decision(
        session_id=_service_state().session_id,
        expected_version=0,
        expected_month=1,
        payment=317.71,
        request_id="same-logical-request",
    )
    retried = service.submit_month_decision(
        session_id=_service_state().session_id,
        expected_version=0,
        expected_month=1,
        payment=317.71,
        request_id="same-logical-request",
    )

    assert first.result == retried.result
    assert retried.idempotency_hit is True
    assert repository.month_result_count(first.state.session_id) == 1
    assert service.load_session(first.state.session_id).state_version == 1


def test_competing_same_month_decisions_only_allow_one_commit():
    service, repository = _service()
    session_id = _service_state().session_id

    def submit(payment, request_id):
        return service.submit_month_decision(
            session_id=session_id,
            expected_version=0,
            expected_month=1,
            payment=payment,
            request_id=request_id,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(submit, 317.71, "choice-a"),
            pool.submit(submit, 100.0, "choice-b"),
        ]

    outcomes = []
    for future in futures:
        try:
            outcomes.append(future.result())
        except ConcurrencyConflict:
            outcomes.append("conflict")

    assert sum(item == "conflict" for item in outcomes) == 1
    assert repository.month_result_count(session_id) == 1
    assert service.load_session(session_id).state_version == 1


def test_stale_stage_cannot_overwrite_newer_state():
    service, _ = _service()
    state_a = service.load_session(_service_state().session_id)
    state_b = service.load_session(_service_state().session_id)
    state_a.page = "consent"
    service.save_stage(state_a, expected_version=0, request_id="stage-a")
    state_b.page = "demographics"

    with pytest.raises(ConcurrencyConflict):
        service.save_stage(state_b, expected_version=0, request_id="stage-b")

    assert service.load_session(state_a.session_id).page == "consent"


def test_read_failure_is_not_interpreted_as_missing_state():
    service, repository = _service()
    repository.fail_next("load", phase="before")

    with pytest.raises(PersistenceReadError):
        service.find_session(_service_state().session_id)


@pytest.mark.parametrize("submitted_month", [0, 2, 8])
def test_months_cannot_commit_out_of_order(submitted_month):
    service, repository = _service()
    with pytest.raises(ConcurrencyConflict):
        service.submit_month_decision(
            session_id=_service_state().session_id,
            expected_version=0,
            expected_month=submitted_month,
            payment=317.71,
            request_id=f"month-{submitted_month}",
        )
    assert repository.month_result_count(_service_state().session_id) == 0


def test_month_decision_is_blocked_outside_simulation_stage():
    service, repository = _service()
    state = repository.raw_state(_service_state().session_id)
    state.page = "demographics"
    repository.replace_state_and_ledger(state)

    with pytest.raises(InvalidTransition):
        service.submit_month_decision(
            session_id=state.session_id,
            expected_version=0,
            expected_month=1,
            payment=317.71,
            request_id="wrong-stage",
        )

    assert repository.month_result_count(state.session_id) == 0


def test_treatment_is_immutable_after_binding():
    service, _ = _service()
    changed = service.load_session(_service_state().session_id)
    changed.experimental_condition = "C4"
    changed.score_frame = "loss_frame"
    changed.monthly_score_feedback = "hidden"

    with pytest.raises(TreatmentConflict):
        service.save_stage(changed, expected_version=0, request_id="change-treatment")


@pytest.mark.parametrize("phase", ["before", "during"])
def test_quality_event_and_progression_commit_atomically(phase):
    service, repository = _service()
    proposed = service.load_session(_service_state().session_id)
    proposed.attention_failed_count = 1
    proposed.page = "pre_question_1"
    event = {
        "check_type": "attention",
        "check_id": "attention_pre_1",
        "attempt_number": 1,
        "passed": False,
        "response_value": "2",
        "response_time_ms": None,
        "page_id": "pre_question_0",
    }
    repository.fail_next("save_quality_transition", phase=phase)

    with pytest.raises(PersistenceWriteError):
        service.save_quality_transition(
            proposed,
            [event],
            expected_version=0,
            request_id=f"quality-{phase}",
        )

    stored = service.load_session(proposed.session_id)
    assert stored.state_version == 0
    assert stored.attention_failed_count == 0
    assert repository.quality_checks(proposed.session_id) == []


def test_quality_transition_retry_is_idempotent():
    service, repository = _service()
    proposed = service.load_session(_service_state().session_id)
    proposed.comprehension_attempts = 1
    events = [{
        "check_type": "comprehension",
        "check_id": "who_completes",
        "attempt_number": 1,
        "passed": True,
        "response_value": "A",
        "response_time_ms": None,
        "page_id": "comprehension",
    }]
    first = service.save_quality_transition(
        proposed,
        events,
        expected_version=0,
        request_id="quality-request",
    )
    retried = service.save_quality_transition(
        proposed,
        events,
        expected_version=0,
        request_id="quality-request",
    )

    assert first.state.state_version == 1
    assert retried.idempotency_hit is True
    assert repository.quality_checks(proposed.session_id) == events


def test_repeated_feedback_acknowledgment_does_not_recompute_month():
    service, repository = _service()
    committed = service.submit_month_decision(
        session_id=_service_state().session_id,
        expected_version=0,
        expected_month=1,
        payment=317.71,
        request_id="month-1",
    )
    first = service.acknowledge_month_feedback(
        session_id=committed.state.session_id,
        expected_version=1,
        expected_month=1,
        request_id="ack-1",
    )
    retry = service.acknowledge_month_feedback(
        session_id=committed.state.session_id,
        expected_version=1,
        expected_month=1,
        request_id="ack-1",
    )
    assert first.state.month == retry.state.month == 2
    assert retry.idempotency_hit is True
    assert repository.month_result_count(committed.state.session_id) == 1


def test_legacy_month_history_backfills_once_without_duplication():
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    legacy = _service_state()
    legacy.treatment_bound = False
    legacy.monthly_results = [{
        "month": 1,
        "credit_final": 6800.0,
        "overdraft_final": 0.0,
        "monthly_score": 80.0,
        "costs_this_month": 48.71,
        "accepted_payment": 200.0,
        "credit_interest": 48.71,
        "overdraft_interest": 0.0,
        "payment_valid": True,
        "pre_credit_impossible": False,
        "score_model": "behavioral_v1",
    }]
    legacy.month = 2
    legacy.loan.balance = 6800.0
    legacy.total_score = 80.0
    repository.seed_legacy(legacy, account_key="a" * 64)

    first = service.load_session(legacy.session_id)
    second = service.load_session(legacy.session_id)
    assert first.monthly_results == second.monthly_results == legacy.monthly_results
    assert repository.month_result_count(legacy.session_id) == 1
    assert first.treatment_bound is True


def test_internal_finalization_is_atomic_and_idempotent():
    service, repository = _service()
    state = repository.raw_state(_service_state().session_id)
    state.month = 25
    state.page = "done"
    state.state_version = 40
    state.monthly_results = [
        {"month": month, "monthly_score": 80.0, "score_model": "behavioral_v1", "accepted_payment": 0.0,
         "credit_interest": 0.0, "overdraft_interest": 0.0}
        for month in range(1, 25)
    ]
    repository.replace_state_and_ledger(state)

    first = service.finalize(
        session_id=state.session_id,
        expected_version=40,
        request_id="finalize-1",
        account_key="a" * 64,
        pre_sections=[],
        post_sections=[],
    )
    retry = service.finalize(
        session_id=state.session_id,
        expected_version=40,
        request_id="finalize-1",
        account_key="a" * 64,
        pre_sections=[],
        post_sections=[],
    )
    assert first.state.submission_finalized is True
    assert retry.idempotency_hit is True
    assert repository.finalization_count(state.session_id) == 1
    assert retry.state.final_score == 80.0

    refreshed_retry = service.finalize(
        session_id=state.session_id,
        expected_version=first.state.state_version,
        request_id="finalize-after-refresh",
        account_key="a" * 64,
        pre_sections=[],
        post_sections=[],
    )
    assert refreshed_retry.idempotency_hit is True
    assert repository.finalization_count(state.session_id) == 1


def test_finalization_failure_rolls_back_all_internal_state():
    service, repository = _service()
    state = repository.raw_state(_service_state().session_id)
    state.month = 25
    state.page = "done"
    state.state_version = 40
    state.monthly_results = [
        {"month": month, "monthly_score": 80.0, "score_model": "behavioral_v1", "accepted_payment": 0.0,
         "credit_interest": 0.0, "overdraft_interest": 0.0}
        for month in range(1, 25)
    ]
    repository.replace_state_and_ledger(state)
    repository.fail_next("finalize", phase="during")

    with pytest.raises(PersistenceWriteError):
        service.finalize(
            session_id=state.session_id,
            expected_version=40,
            request_id="failed-finalize",
            account_key="a" * 64,
            pre_sections=[],
            post_sections=[],
        )

    persisted = service.load_session(state.session_id)
    assert persisted.submission_finalized is False
    assert persisted.state_version == 40
    assert repository.finalization_count(state.session_id) == 0


def test_supabase_client_is_reused_within_a_worker_thread(monkeypatch):
    import sim_app.infra.supabase as supabase

    created = []
    monkeypatch.setattr(supabase, "_first_secret", lambda *names: "url" if "SUPABASE_URL" in names else "secret")
    monkeypatch.setattr(supabase, "_build_client", lambda url, key: created.append((url, key)) or object())
    supabase.reset_shared_client()

    first = supabase.get_client()
    second = supabase.get_client()

    assert first is second
    assert created == [("url", "secret")]
    supabase.reset_shared_client()


def test_supabase_client_is_isolated_between_worker_threads(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    import sim_app.infra.supabase as supabase

    created = []
    monkeypatch.setattr(supabase, "_first_secret", lambda *names: "url" if "SUPABASE_URL" in names else "secret")
    monkeypatch.setattr(
        supabase,
        "_build_client",
        lambda url, key: created.append((url, key, object())) or created[-1][2],
    )
    supabase.reset_shared_client()
    barrier = Barrier(2)

    def obtain_twice(_):
        barrier.wait()
        first = supabase.get_client()
        return first, supabase.get_client()

    with ThreadPoolExecutor(max_workers=2) as pool:
        pairs = list(pool.map(obtain_twice, range(2)))

    assert all(first is second for first, second in pairs)
    assert pairs[0][0] is not pairs[1][0]
    assert len(created) == 2
    supabase.reset_shared_client()


def test_resume_projection_excludes_authoritative_economic_and_treatment_data():
    state = _service_state("C4")
    state.monthly_results = [{"month": 1, "monthly_score": 80.0}]
    state.loan.balance = 6500.0
    state.final_score = 80.0
    projection = state.to_resume_projection()

    for key in (
        "monthly_results", "pending_month_result", "loan_balance", "overdraft_balance",
        "total_score", "final_score", "experimental_condition", "score_frame",
        "monthly_score_feedback", "submission_finalized",
    ):
        assert key not in projection


def test_bootstrap_read_failure_does_not_initialize_or_replace_state():
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    principal = ParticipantPrincipal("a" * 64)
    repository.fail_next("find_session_for_account", phase="before")
    with pytest.raises(PersistenceReadError):
        service.bootstrap_session(principal, expected_version=0, language="en", request_id="create")
    assert repository._sessions == {}


def test_application_does_not_return_advanced_state_when_write_fails():
    state = _service_state()
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    service.create_session(state, account_key="a" * 64, request_id="create")
    proposed = state.copy()
    proposed.page = "consent"
    repository.fail_next("save_stage", phase="before")
    with pytest.raises(PersistenceWriteError):
        service.save_stage(proposed, expected_version=0, request_id="stage")
    durable = service.load_session(state.session_id)
    assert durable.page == "simulation"
    assert durable.state_version == 0


class _PaymentQuery:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.values = None
        self.filters = []
        self.return_rows = False

    def update(self, values):
        self.values = values
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def select(self, *_args):
        self.return_rows = True
        return self

    def execute(self):
        matching = [
            row for row in self.client.rows[self.table]
            if all(row.get(key) == value for key, value in self.filters)
        ]
        if self.values is not None:
            for row in matching:
                row.update(self.values)
        return SimpleNamespace(data=[dict(row) for row in matching] if self.return_rows else matching)


class _PaymentClient:
    def __init__(self):
        self.rows = {
            "prolific_payment_attempts": [{
                "session_id": "session", "request_id": "payment:finalize", "status": "pending", "attempt_count": 0,
            }],
            "session_summaries": [{
                "session_id": "session", "prolific_bonus_status": "pending", "payment_status": "unpaid",
            }],
            "participant_sessions": [{"id": "session", "completion_status": "payment_pending"}],
        }

    def table(self, name):
        return _PaymentQuery(self, name)

    def rpc(self, name, params):
        client = self

        class Rpc:
            def execute(self):
                attempt = client.rows["prolific_payment_attempts"][0]
                summary = client.rows["session_summaries"][0]
                participant = client.rows["participant_sessions"][0]
                if name == "claim_prolific_payment_v3":
                    if attempt["status"] != "pending":
                        return SimpleNamespace(data={"claimed": False, "status": attempt["status"]})
                    attempt.update(status="processing", attempt_count=attempt["attempt_count"] + 1)
                    summary["prolific_bonus_status"] = "processing"
                    participant["completion_status"] = "payment_processing"
                    return SimpleNamespace(data={"claimed": True, "status": "processing"})
                if name == "finish_prolific_payment_v3":
                    if attempt["status"] in {"succeeded", "manual_review", "not_configured", "not_applicable"}:
                        return SimpleNamespace(data={"updated": False, "status": attempt["status"]})
                    attempt.update(
                        status=params["p_attempt_status"],
                        response_json=params["p_response"],
                        last_error=params["p_error"],
                    )
                    summary.update(
                        prolific_bonus_status=params["p_bonus_status"],
                        payment_status=params["p_payment_status"],
                    )
                    participant["completion_status"] = "payment_manual_review"
                    return SimpleNamespace(data={"updated": True, "status": attempt["status"]})
                raise AssertionError(f"Unexpected RPC {name}")

        return Rpc()


@pytest.mark.parametrize("outcome", ["timeout", "accepted"])
def test_prolific_side_effect_is_never_repeated_after_ambiguous_or_successful_call(monkeypatch, outcome):
    import sim_app.prolific.bonuses as bonuses

    client = _PaymentClient()
    summary = {
        "prolific_pid": "pid",
        "prolific_study_id": "study",
        "prolific_session_id": "submission",
        "payment_idempotency_key": "payment:finalize",
        "completion_code": "CODE",
        "prolific_base_reward_gbp": 5,
        "performance_bonus_gbp": 2,
    }
    external_calls = []
    monkeypatch.setattr(bonuses, "dynamic_payment_configured", lambda: True)

    def external(*_args, **_kwargs):
        external_calls.append("called")
        if outcome == "timeout":
            raise URLError("response lost")
        return {"status": "AWAITING REVIEW"}

    monkeypatch.setattr(bonuses, "complete_with_dynamic_payment", external)
    bonuses.process_prolific_bonus(client, "session", summary)
    bonuses.process_prolific_bonus(client, "session", summary)

    assert external_calls == ["called"]
    attempt = client.rows["prolific_payment_attempts"][0]
    assert attempt["status"] == ("manual_review" if outcome == "timeout" else "succeeded")
    assert client.rows["participant_sessions"][0]["completion_status"] == "payment_manual_review"


def test_recovered_in_flight_prolific_payment_goes_to_manual_review_without_retrying_external(monkeypatch):
    import sim_app.prolific.bonuses as bonuses

    client = _PaymentClient()
    client.rows["prolific_payment_attempts"][0]["status"] = "processing"
    summary = {
        "prolific_pid": "pid",
        "prolific_study_id": "study",
        "prolific_session_id": "submission",
        "payment_idempotency_key": "payment:finalize",
        "completion_code": "CODE",
        "prolific_base_reward_gbp": 5,
        "performance_bonus_gbp": 2,
    }
    external_calls = []
    monkeypatch.setattr(bonuses, "dynamic_payment_configured", lambda: True)
    monkeypatch.setattr(bonuses, "complete_with_dynamic_payment", lambda *_args, **_kwargs: external_calls.append("called"))

    bonuses.process_prolific_bonus(client, "session", summary)

    assert external_calls == []
    assert client.rows["prolific_payment_attempts"][0]["status"] == "manual_review"


def test_phase3_migration_declares_atomic_rpc_and_database_invariants():
    from pathlib import Path

    sql = Path("migration_phase3_persistence_hardening.sql").read_text(encoding="utf-8")
    required = (
        "state_version BIGINT NOT NULL",
        "PRIMARY KEY (session_id, operation, request_id)",
        "month_results_decision_request_idx",
        "participant_sessions_treatment_immutable_v3",
        "claim_participant_session_v3",
        "commit_stage_transition_v3",
        "commit_quality_transition_v3",
        "commit_month_decision_v3",
        "acknowledge_month_feedback_v3",
        "backfill_legacy_session_v3",
        "finalize_experiment_v3",
        "claim_prolific_payment_v3",
        "finish_prolific_payment_v3",
        "completion_status='payment_manual_review'",
        "FOR UPDATE",
    )
    assert all(fragment in sql for fragment in required)
    assert "DROP TABLE" not in sql.upper()


def test_supabase_repository_uses_one_month_commit_rpc(monkeypatch):
    from sim_app.application.repositories import RepositoryCommit
    from sim_app.persistence.experiment_repository import SupabaseExperimentRepository

    class Rpc:
        def __init__(self, calls, name, params):
            self.calls = calls
            self.name = name
            self.params = params

        def execute(self):
            self.calls.append((self.name, self.params))
            return SimpleNamespace(data={"state_version": 1, "result": self.params["p_result"]["result_json"]})

    class Client:
        def __init__(self):
            self.calls = []

        def rpc(self, name, params):
            return Rpc(self.calls, name, params)

    client = Client()
    repository = SupabaseExperimentRepository(client)
    state = _service_state()
    state.pending_month_result = {"month": 1}
    state.monthly_results = [{"month": 1}]
    result = {
        "month": 1, "monthly_score": 80.0, "score_model": "behavioral_v1",
        "credit_final": 6800.0, "overdraft_final": 0.0,
    }
    monkeypatch.setattr(
        repository,
        "_committed",
        lambda session_id, data, result=None: RepositoryCommit(state, result=result),
    )

    repository.commit_month_decision(
        state,
        result,
        expected_version=0,
        expected_month=1,
        request_id="request",
        payload_hash="a" * 64,
    )

    assert [name for name, _params in client.calls] == ["commit_month_decision_v3"]
