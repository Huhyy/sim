from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sim_app.api.app import create_app
from sim_app.application.principal import ParticipantPrincipal
from sim_app.application.services import ExperimentService
from sim_app.domain.experimental_conditions import condition_config
from sim_app.persistence.memory import InMemoryExperimentRepository


ACCOUNT_KEY = "a" * 64
OTHER_ACCOUNT_KEY = "b" * 64


@pytest.fixture
def harness():
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    principal = ParticipantPrincipal(ACCOUNT_KEY)
    app = create_app(
        service=service,
        principal_provider=lambda _request: principal,
        docs_enabled=False,
    )
    with TestClient(app) as client:
        yield app, client, service, repository, principal


def _headers(key):
    return {"Idempotency-Key": key}


def _create(client, *, key="create", language="en"):
    response = client.post(
        "/api/v1/sessions",
        headers=_headers(key),
        json={"expected_version": 0, "language": language},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _seed_stage(repository, service, session_id, *, page, condition="C1"):
    state = service.load_session(session_id)
    state.page = page
    treatment = condition_config(condition)
    state.experimental_condition = treatment["experimental_condition"]
    state.score_frame = treatment["score_frame"]
    state.monthly_score_feedback = treatment["monthly_score_feedback"]
    state.treatment_bound = True
    repository.replace_state_and_ledger(state)
    return state


def _all_keys(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from _all_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _all_keys(nested)


def test_health_ready_and_request_id(harness):
    _app, client, _service, _repository, _principal = harness
    health = client.get("/health", headers={"X-Request-ID": "transport-attempt"})
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert health.headers["X-Request-ID"] == "transport-attempt"
    assert client.get("/ready").json() == {"status": "ready"}


def test_readiness_fails_without_server_configuration(monkeypatch):
    for name in (
        "SUPABASE_URL", "SUPABASE_PROJECT_URL", "SUPABASE_SECRET_KEY",
        "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    with TestClient(create_app(docs_enabled=False)) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "persistence_read_failed"


def test_participant_routes_require_authentication():
    service = ExperimentService(InMemoryExperimentRepository())
    with TestClient(create_app(service=service, docs_enabled=False)) as client:
        response = client.get("/api/v1/sessions/unknown")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_session_ownership_and_not_found(harness):
    app, client, _service, repository, _principal = harness
    created = _create(client)
    session_id = created["session_id"]
    assert client.get(f"/api/v1/sessions/{session_id}").status_code == 200

    app.state.principal_provider = lambda _request: ParticipantPrincipal(OTHER_ACCOUNT_KEY)
    denied = client.get(f"/api/v1/sessions/{session_id}")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "session_access_denied"

    app.state.principal_provider = lambda _request: ParticipantPrincipal(ACCOUNT_KEY)
    missing = client.get("/api/v1/sessions/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 403
    assert missing.json()["error"]["code"] == "session_access_denied"

    # A stale durable ownership link is the only safe way to distinguish a
    # missing session after ownership has first been established.
    stale_session_id = "00000000-0000-0000-0000-000000000001"
    repository._accounts[ACCOUNT_KEY] = stale_session_id
    not_found = client.get(f"/api/v1/sessions/{stale_session_id}")
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "session_not_found"


def test_strict_validation_and_required_idempotency(harness):
    _app, client, _service, _repository, _principal = harness
    missing_create_key = client.post(
        "/api/v1/sessions",
        json={"expected_version": 0, "language": "en"},
    )
    assert missing_create_key.status_code == 400
    assert missing_create_key.json()["error"]["code"] == "idempotency_key_required"

    missing_create_version = client.post(
        "/api/v1/sessions",
        headers=_headers("missing-create-version"),
        json={"language": "en"},
    )
    assert missing_create_version.status_code == 422

    nonzero_create_version = client.post(
        "/api/v1/sessions",
        headers=_headers("nonzero-create-version"),
        json={"expected_version": 1, "language": "en"},
    )
    assert nonzero_create_version.status_code == 422

    created = _create(client)
    session_id = created["session_id"]
    missing_key = client.post(
        f"/api/v1/sessions/{session_id}/start",
        json={"expected_version": 0},
    )
    assert missing_key.status_code == 400
    assert missing_key.json()["error"]["code"] == "idempotency_key_required"

    extra = client.post(
        f"/api/v1/sessions/{session_id}/start",
        headers=_headers("extra"),
        json={"expected_version": 0, "treatment": "C4"},
    )
    assert extra.status_code == 422
    assert extra.json()["error"]["code"] == "validation_error"

    invalid_version = client.post(
        f"/api/v1/sessions/{session_id}/start",
        headers=_headers("bad-version"),
        json={"expected_version": "not-an-integer"},
    )
    assert invalid_version.status_code == 422


def test_stage_idempotency_and_stale_version(harness):
    _app, client, _service, repository, _principal = harness
    created = _create(client)
    session_id = created["session_id"]
    url = f"/api/v1/sessions/{session_id}/start"
    payload = {"expected_version": 0}
    first = client.post(url, headers=_headers("start-action"), json=payload)
    retry = client.post(url, headers=_headers("start-action"), json=payload)
    stale = client.post(url, headers=_headers("different-action"), json=payload)
    assert first.status_code == retry.status_code == 200
    assert first.json()["state_version"] == retry.json()["state_version"] == 1
    assert retry.json()["idempotency_replayed"] is True
    assert retry.headers["Idempotency-Replayed"] == "true"
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "concurrency_conflict"
    assert (session_id, "save_stage", "start-action") in repository._idempotency


def test_session_creation_rejects_same_key_with_different_payload(harness):
    _app, client, _service, _repository, _principal = harness
    created = _create(client, key="create-language", language="en")
    replay = _create(client, key="create-language", language="en")
    assert replay["session_id"] == created["session_id"]
    assert replay["idempotency_replayed"] is True

    conflict = client.post(
        "/api/v1/sessions",
        headers=_headers("create-language"),
        json={"expected_version": 0, "language": "ro"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"


def test_month_idempotency_conflict_and_response_loss_retry(harness):
    _app, client, service, repository, _principal = harness
    created = _create(client)
    session_id = created["session_id"]
    state = _seed_stage(repository, service, session_id, page="simulation")
    url = f"/api/v1/sessions/{session_id}/months/1/decision"
    first = client.post(url, headers=_headers("month-one"), json={"expected_version": state.state_version, "payment": 100})
    retry = client.post(url, headers=_headers("month-one"), json={"expected_version": state.state_version, "payment": 100})
    conflict = client.post(url, headers=_headers("month-one"), json={"expected_version": state.state_version, "payment": 101})
    assert first.status_code == retry.status_code == 200
    assert repository.month_result_count(session_id) == 1
    assert retry.json()["idempotency_replayed"] is True
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"
    assert (session_id, "month_decision", "month-one") in repository._idempotency


def test_economically_invalid_payment_remains_a_committed_domain_result(harness):
    _app, client, service, repository, _principal = harness
    created = _create(client)
    session_id = created["session_id"]
    state = _seed_stage(repository, service, session_id, page="simulation")
    response = client.post(
        f"/api/v1/sessions/{session_id}/months/1/decision",
        headers=_headers("invalid-economic-payment"),
        json={"expected_version": state.state_version, "payment": 999999},
    )
    assert response.status_code == 200, response.text
    assert response.json()["view"]["feedback"]["tone"] == "warning"
    assert repository.month_result_count(session_id) == 1
    durable = repository.month_results(session_id)[0]
    assert durable["payment_valid"] is False


@pytest.mark.parametrize("bind", [True, False])
def test_study_session_binding_and_skip_are_server_derived(bind):
    repository = InMemoryExperimentRepository()
    repository.add_study_session({
        "id": "00000000-0000-0000-0000-000000000123",
        "session_code": "123456",
        "status": "active",
        "experimental_condition": "C4",
        "score_frame": "loss_frame",
        "monthly_score_feedback": "hidden",
    })
    service = ExperimentService(repository)
    principal = ParticipantPrincipal(ACCOUNT_KEY)
    with TestClient(create_app(service=service, principal_provider=lambda _request: principal, docs_enabled=False)) as client:
        created = _create(client)
        session_id = created["session_id"]
        if bind:
            response = client.post(
                f"/api/v1/sessions/{session_id}/study-session",
                headers=_headers("bind-study"),
                json={"expected_version": 0, "session_code": "123456", "participant_code": "P001"},
            )
        else:
            response = client.post(
                f"/api/v1/sessions/{session_id}/study-session/skip",
                headers=_headers("skip-study"),
                json={"expected_version": 0},
            )
    assert response.status_code == 200, response.text
    assert "experimental_condition" not in set(_all_keys(response.json()))
    durable = service.load_session(session_id)
    assert durable.treatment_bound is True
    assert durable.experimental_condition == ("C4" if bind else "C1")


def test_concurrent_month_double_click_commits_once(harness):
    app, _client, service, repository, _principal = harness
    with TestClient(app) as setup_client:
        created = _create(setup_client)
    session_id = created["session_id"]
    state = _seed_stage(repository, service, session_id, page="simulation")

    def submit():
        with TestClient(app) as concurrent_client:
            return concurrent_client.post(
                f"/api/v1/sessions/{session_id}/months/1/decision",
                headers=_headers("double-click"),
                json={"expected_version": state.state_version, "payment": 100},
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _index: submit(), range(2)))
    assert [response.status_code for response in responses] == [200, 200]
    assert repository.month_result_count(session_id) == 1
    assert sum(bool(response.json()["idempotency_replayed"]) for response in responses) == 1


@pytest.mark.parametrize("condition,score_visible", [("C1", True), ("C2", False), ("C3", True), ("C4", False)])
def test_feedback_experimental_blindness(harness, condition, score_visible):
    _app, client, service, repository, _principal = harness
    created = _create(client, key=f"create-{condition}")
    session_id = created["session_id"]
    state = _seed_stage(repository, service, session_id, page="simulation", condition=condition)
    response = client.post(
        f"/api/v1/sessions/{session_id}/months/1/decision",
        headers=_headers(f"decision-{condition}"),
        json={"expected_version": state.state_version, "payment": 100},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert ("score" in body["view"]) is score_visible
    forbidden = {
        "experimental_condition", "score_frame", "monthly_score_feedback",
        "treatment_bound", "monthly_results", "pending_month_result",
        "prolific_pid", "prolific_study_id", "prolific_session_id",
        "checkpoint", "answers", "account_key", "payment_status",
    }
    assert forbidden.isdisjoint(set(_all_keys(body)))
    assert ACCOUNT_KEY not in json.dumps(body)
    if score_visible:
        assert body["view"]["score"]["monthly_score"] >= 0
        assert "monthly_loss" not in body["view"]["score"]
    if not score_visible:
        keys = set(_all_keys(body))
        assert not {key for key in keys if key.startswith("score_") or key.startswith("monthly_score")}


def test_questionnaire_attention_and_comprehension_are_server_evaluated():
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    principal = ParticipantPrincipal(
        ACCOUNT_KEY,
        identity_kind="prolific",
        prolific_pid="participant",
        prolific_study_id="study",
        prolific_session_id="submission",
    )
    app = create_app(service=service, principal_provider=lambda _request: principal, docs_enabled=False)
    with TestClient(app) as client:
        created = _create(client)
        session_id = created["session_id"]
        state = service.load_session(session_id)
        state.page = "pre_question_0"
        repository.replace_state_and_ledger(state)
        current = client.get(f"/api/v1/sessions/{session_id}").json()
        view = current["view"]
        answers = {question["key"]: question["options"][0] for question in view["questions"]}
        attention = next(option for option in view["attention_check"]["options"] if str(option).startswith("3"))
        submitted = client.post(
            f"/api/v1/sessions/{session_id}/questionnaires/pre/sections/0",
            headers=_headers("attention"),
            json={
                "expected_version": current["state_version"],
                "answers": answers,
                "attention_response": attention,
            },
        )
        assert submitted.status_code == 200, submitted.text
        events = repository.quality_checks(session_id)
        assert len(events) == 1 and events[0]["passed"] is True

        state = service.load_session(session_id)
        state.page = "comprehension"
        repository.replace_state_and_ledger(state)
        comprehension = client.get(f"/api/v1/sessions/{session_id}").json()
        assert "correct" not in set(_all_keys(comprehension))
        responses = {
            question["id"]: next(option for option in question["options"] if str(option).startswith("A"))
            for question in comprehension["view"]["questions"]
        }
        result = client.post(
            f"/api/v1/sessions/{session_id}/comprehension",
            headers=_headers("comprehension"),
            json={"expected_version": comprehension["state_version"], "responses": responses},
        )
        assert result.status_code == 200, result.text
        assert result.json()["stage"] == "profile"
        assert service.load_session(session_id).comprehension_passed is True


def test_persistence_and_transition_error_mapping(harness):
    _app, client, service, repository, _principal = harness
    created = _create(client)
    session_id = created["session_id"]
    repository.fail_next("load", phase="before")
    read_failure = client.get(f"/api/v1/sessions/{session_id}")
    assert read_failure.status_code == 503
    assert read_failure.json()["error"]["code"] == "persistence_read_failed"

    repository.fail_next("save_stage", phase="before")
    write_failure = client.post(
        f"/api/v1/sessions/{session_id}/start",
        headers=_headers("write-failure"),
        json={"expected_version": 0},
    )
    assert write_failure.status_code == 503
    assert write_failure.json()["error"]["code"] == "persistence_write_failed"
    assert service.load_session(session_id).page == "home"

    state = service.load_session(session_id)
    state.page = "demographics"
    repository.replace_state_and_ledger(state)
    invalid = client.post(
        f"/api/v1/sessions/{session_id}/start",
        headers=_headers("invalid-transition"),
        json={"expected_version": state.state_version},
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "invalid_transition"


def test_complete_non_prolific_api_journey(harness):
    app, client, _service, repository, _principal = harness
    current = _create(client, key="journey-create")
    session_id = current["session_id"]

    current = client.post(
        f"/api/v1/sessions/{session_id}/start",
        headers=_headers("journey-start"),
        json={"expected_version": current["state_version"]},
    ).json()
    current = client.post(
        f"/api/v1/sessions/{session_id}/consent",
        headers=_headers("journey-consent"),
        json={"expected_version": current["state_version"], "accepted": True},
    ).json()
    options = current["view"]["options"]
    demographics = {
        "expected_version": current["state_version"],
        "demo_age": 30,
        "demo_country": "Romania",
        **{key: values[0] for key, values in options.items()},
    }
    response = client.post(
        f"/api/v1/sessions/{session_id}/demographics",
        headers=_headers("journey-demographics"),
        json=demographics,
    )
    assert response.status_code == 200, response.text
    current = response.json()

    while current["stage"].startswith("pre_question_"):
        view = current["view"]
        answers = {question["key"]: question["options"][0] for question in view["questions"]}
        response = client.post(
            f"/api/v1/sessions/{session_id}/questionnaires/pre/sections/{view['section_index']}",
            headers=_headers(f"journey-pre-{view['section_index']}"),
            json={"expected_version": current["state_version"], "answers": answers},
        )
        assert response.status_code == 200, response.text
        current = response.json()

    assert current["stage"] == "instructions"
    current = client.post(
        f"/api/v1/sessions/{session_id}/instructions/acknowledge",
        headers=_headers("journey-instructions"),
        json={"expected_version": current["state_version"]},
    ).json()
    assert current["stage"] == "profile"
    current = client.post(
        f"/api/v1/sessions/{session_id}/profile/acknowledge",
        headers=_headers("journey-profile"),
        json={"expected_version": current["state_version"]},
    ).json()

    for month in range(1, 25):
        assert current["stage"] == "simulation" and current["month"] == month
        payment = 317.71 if current["view"]["payment"]["required"] else None
        response = client.post(
            f"/api/v1/sessions/{session_id}/months/{month}/decision",
            headers=_headers(f"journey-month-{month}"),
            json={"expected_version": current["state_version"], "payment": payment},
        )
        assert response.status_code == 200, response.text
        current = response.json()
        assert current["stage"] == "month_feedback"
        response = client.post(
            f"/api/v1/sessions/{session_id}/months/{month}/feedback/acknowledge",
            headers=_headers(f"journey-feedback-{month}"),
            json={"expected_version": current["state_version"]},
        )
        assert response.status_code == 200, response.text
        current = response.json()

    assert repository.month_result_count(session_id) == 24
    while current["stage"].startswith("post_question_"):
        view = current["view"]
        answers = {question["key"]: question["options"][0] for question in view["questions"]}
        response = client.post(
            f"/api/v1/sessions/{session_id}/questionnaires/post/sections/{view['section_index']}",
            headers=_headers(f"journey-post-{view['section_index']}"),
            json={
                "expected_version": current["state_version"],
                "answers": answers,
                "feedback": "",
                "strategy_feedback": "",
            },
        )
        assert response.status_code == 200, response.text
        current = response.json()

    assert current["stage"] == "final_score"
    current = client.post(
        f"/api/v1/sessions/{session_id}/final-score/acknowledge",
        headers=_headers("journey-final-score"),
        json={"expected_version": current["state_version"]},
    ).json()
    assert current["stage"] == "done"
    response = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        headers=_headers("journey-finalize"),
        json={"expected_version": current["state_version"]},
    )
    assert response.status_code == 200, response.text
    completed = response.json()
    assert completed["stage"] == "done"
    assert completed["view"]["saved"] is True
    assert repository.finalization_count(session_id) == 1
    app.state.principal_provider = lambda _request: ParticipantPrincipal(
        ACCOUNT_KEY,
        bound_session_id=session_id,
    )
    retry = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        headers=_headers("journey-finalize"),
        json={"expected_version": current["state_version"]},
    )
    assert retry.status_code == 200, retry.text
    assert retry.json()["idempotency_replayed"] is True
    assert repository.finalization_count(session_id) == 1
    app.state.principal_provider = lambda _request: ParticipantPrincipal(OTHER_ACCOUNT_KEY)
    stolen_retry = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        headers=_headers("journey-finalize"),
        json={"expected_version": current["state_version"]},
    )
    assert stolen_retry.status_code == 403
    assert stolen_retry.json()["error"]["code"] == "session_access_denied"


def test_api_architecture_has_no_persistence_shortcut():
    root = Path(__file__).resolve().parents[1]
    routes = (root / "sim_app" / "api" / "routes.py").read_text(encoding="utf-8")
    assert "supabase" not in routes.lower()
    assert "experiment_repository" not in routes
    assert ".table(" not in routes and ".rpc(" not in routes
    for folder in (root / "sim_app" / "application", root / "sim_app" / "domain"):
        for source in folder.glob("*.py"):
            text = source.read_text(encoding="utf-8").lower()
            assert "import fastapi" not in text
            assert "from fastapi" not in text
            assert "sim_app.api" not in text
