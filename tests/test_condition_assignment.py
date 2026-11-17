import hashlib

import pytest

from sim_app.application.admin_services import AdminService
from sim_app.application.principal import ParticipantPrincipal
from sim_app.application.services import ExperimentService
from sim_app.domain.experimental_conditions import assign_participant_condition, assign_prolific_condition, condition_config
from sim_app.persistence.admin_memory import MemoryAdminRepository
from sim_app.persistence.experiment_repository import _state_payload
from sim_app.persistence.memory import InMemoryExperimentRepository


ACTIVE = {"C1", "C2", "C3", "C4"}


@pytest.mark.parametrize("identity_kind", ["oidc", "prolific"])
def test_every_participant_gets_a_stable_persisted_c1_to_c4_assignment(identity_kind):
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    assigned = set()
    for index in range(64):
        principal = ParticipantPrincipal(
            hashlib.sha256(f"participant-{index}".encode()).hexdigest(),
            identity_kind=identity_kind,
            prolific_pid=f"pid-{index}" if identity_kind == "prolific" else None,
            prolific_study_id="study" if identity_kind == "prolific" else None,
            prolific_session_id=f"attempt-{index}" if identity_kind == "prolific" else None,
        )
        first = service.bootstrap_session(principal, expected_version=0, language="en", request_id="create")
        saved = repository.load(first.state.session_id)
        assigned.add(saved.experimental_condition)
        assert saved.experimental_condition in ACTIVE
        config = condition_config(saved.experimental_condition)
        payload = _state_payload(saved)
        for key, value in config.items():
            assert getattr(saved, key) == value
            assert payload[key] == value
        retry = service.bootstrap_session(principal, expected_version=0, language="en", request_id="create")
        assert retry.idempotency_hit
        assert retry.state.session_id == saved.session_id
        assert retry.state.experimental_condition == saved.experimental_condition
    assert assigned == ACTIVE


def test_prolific_assignment_never_selects_legacy_conditions():
    assert {assign_prolific_condition(f"pid-{i}", "study")["experimental_condition"] for i in range(128)} == ACTIVE


@pytest.mark.parametrize("code_condition", ["C1", "C2", "C3", "C4"])
def test_study_code_applies_the_code_condition(code_condition):
    repository = InMemoryExperimentRepository()
    repository.add_study_session({"id": "study-id", "session_code": "123456", "status": "active", **condition_config(code_condition)})
    service = ExperimentService(repository)
    # Pick an account whose random assignment differs, so the test proves the code wins.
    principal = next(
        p for p in (ParticipantPrincipal(hashlib.sha256(f"participant-{i}".encode()).hexdigest()) for i in range(64))
        if assign_participant_condition(p.account_key)["experimental_condition"] != code_condition
    )
    first = service.bootstrap_session(principal, expected_version=0, language="en", request_id="create")
    result = service.bind_study_session(
        first.state.session_id, principal, session_code="123456", participant_code="P001",
        expected_version=first.state.state_version, request_id="study",
    )
    saved = repository.load(first.state.session_id)
    for key, value in condition_config(code_condition).items():
        assert getattr(result.state, key) == value
        assert getattr(saved, key) == value
    assert saved.participant_code == "P001"
    assert saved.treatment_bound


def test_skipping_study_code_keeps_random_assignment():
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    principal = ParticipantPrincipal(hashlib.sha256(b"participant-1").hexdigest())
    first = service.bootstrap_session(principal, expected_version=0, language="en", request_id="create")
    result = service.skip_study_session(
        first.state.session_id, principal, expected_version=first.state.state_version, request_id="study",
    )
    assert result.state.experimental_condition == first.state.experimental_condition
    assert repository.load(first.state.session_id).experimental_condition == first.state.experimental_condition


def test_admin_restart_rerandomizes_condition():
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    admin = ParticipantPrincipal("a" * 64, email="admin@example.com", is_admin=True)
    seen = set()
    for index in range(32):
        result = service.bootstrap_session(
            admin, expected_version=0, language="en", request_id=f"restart-{index}", restart=index > 0,
        )
        seen.add(result.state.experimental_condition)
        assert repository.load(result.state.session_id).experimental_condition == result.state.experimental_condition
    assert seen == ACTIVE


def test_admin_create_retry_keeps_its_condition():
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    admin = ParticipantPrincipal("a" * 64, email="admin@example.com", is_admin=True)
    first = service.bootstrap_session(admin, expected_version=0, language="en", request_id="create")
    retry = service.bootstrap_session(admin, expected_version=0, language="en", request_id="create")
    assert retry.state.session_id == first.state.session_id
    assert retry.state.experimental_condition == first.state.experimental_condition


def test_admin_results_display_saved_participant_condition():
    repository = MemoryAdminRepository()
    row = repository.create_study_session("admin@example.com", "C8")
    repository.participants[row["id"]] = [{"participant_code": "P001", "experimental_condition": "C2"}]
    results = AdminService(repository).list_participant_results(ParticipantPrincipal("a" * 64, email="admin@example.com", is_admin=True))
    assert results[0]["experimental_condition"] == "C2"
