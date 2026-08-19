from __future__ import annotations

import pytest

import sim_app.application.services as services_module
from sim_app.application.errors import ParticipationCompleted, ProlificLaunchError
from sim_app.application.principal import ParticipantPrincipal
from sim_app.application.services import ExperimentService
from sim_app.application.state import ParticipantState
from sim_app.application.participant_views import participant_session_view
from sim_app.content.i18n_questionnaire import POST_SECTIONS_EN, PRE_SECTIONS_EN
from sim_app.content.questions import POST_SECTIONS, PRE_SECTIONS
from sim_app.persistence.mappers import _psychometric_rows
from sim_app.persistence.memory import InMemoryExperimentRepository


def _created(*, principal=None):
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    principal = principal or ParticipantPrincipal("a" * 64)
    result = service.bootstrap_session(principal, expected_version=0, language="en", request_id="create")
    return repository, service, principal, result.state


def test_questionnaire_structure_and_localized_order_are_unchanged():
    assert (len(PRE_SECTIONS), sum(len(section["questions"]) for section in PRE_SECTIONS)) == (22, 163)
    assert (len(POST_SECTIONS), sum(len(section["questions"]) for section in POST_SECTIONS)) == (2, 45)
    assert (len(PRE_SECTIONS_EN), sum(len(section["questions"]) for section in PRE_SECTIONS_EN)) == (22, 163)
    assert (len(POST_SECTIONS_EN), sum(len(section["questions"]) for section in POST_SECTIONS_EN)) == (2, 45)
    for romanian, english in zip(PRE_SECTIONS + POST_SECTIONS, PRE_SECTIONS_EN + POST_SECTIONS_EN):
        assert romanian["key_prefix"] == english["key_prefix"]
        assert len(romanian["questions"]) == len(english["questions"])
        assert len(romanian["scale"]) == len(english["scale"])


def test_new_post_psychometric_items_use_explicit_keys_scales_and_blind_labels():
    pre = PRE_SECTIONS[-1]
    post_stress = POST_SECTIONS[0]
    post_perception = POST_SECTIONS[1]
    assert pre["question_keys"][-7:] == [f"state_stress_pre_{i}" for i in range(1, 8)]
    assert post_stress["question_keys"][:7] == [f"state_stress_post_{i}" for i in range(1, 8)]
    assert post_perception["question_keys"][-3:] == ["score_check", "score_perceived", "mcheck_avoid"]
    assert post_perception["question_scales"][-3:] == [
        ["1", "2", "3", "4", "5", "6", "7"],
        ["1", "2", "3"],
        ["1", "2", "3", "4", "5"],
    ]
    assert post_perception["question_option_labels"][-1][0].endswith("dezacord total")
    assert post_perception["question_option_labels"][-3][1:3] == ["", ""]


def test_new_post_items_keep_legacy_persistent_question_numbers():
    answers = {}
    for section in POST_SECTIONS:
        for index, key in enumerate(section["question_keys"]):
            answers[key] = section.get("question_scales", [section["scale"]] * len(section["questions"]))[index][0]
    rows = _psychometric_rows("session", answers, POST_SECTIONS)
    numbers = {row["question_key"]: row["question_number"] for row in rows}
    assert numbers["post_stress_0"] == 1
    assert numbers["state_stress_post_1"] == 36
    assert numbers["post_perception_0"] == 26
    assert numbers["score_check"] == 43
    assert numbers["mcheck_avoid"] == 45


@pytest.mark.parametrize(
    ("page", "expected_first", "expected_last"),
    [
        ("pre_question_0", 1, 7),
        ("pre_question_4", 29, 58),
        ("post_question_0", 1, 32),
        ("post_question_1", 33, 45),
    ],
)
def test_questionnaire_safe_view_preserves_global_numbering_without_scale_titles(
    page, expected_first, expected_last
):
    state = ParticipantState.initial("questionnaire-numbering-test")
    state.page = page
    state.language = "en"
    view = participant_session_view(state)["view"]

    assert "title" not in view
    assert view["questions"][0]["number"] == expected_first
    assert view["questions"][-1]["number"] == expected_last


def test_language_change_is_versioned_idempotent_and_authoritative():
    _repository, service, principal, state = _created()
    changed = service.change_language(state.session_id, principal, expected_version=0, request_id="language", language="ro")
    assert changed.state.language == "ro" and changed.state.state_version == 1
    replay = service.change_language(state.session_id, principal, expected_version=0, request_id="language", language="ro")
    assert replay.idempotency_hit and replay.state.state_version == 1


def test_consent_decline_can_return_to_consent_without_skipping_progression():
    _repository, service, principal, state = _created()
    state = service.start_experiment(state.session_id, principal, expected_version=0, request_id="start").state
    state = service.submit_consent(state.session_id, principal, expected_version=1, request_id="decline", accepted=False).state
    assert state.page == "consent_declined"
    state = service.reconsider_consent(state.session_id, principal, expected_version=2, request_id="reconsider").state
    assert state.page == "consent"


@pytest.mark.parametrize("legacy", ["home", "enter_session_code"])
def test_study_session_commands_accept_canonical_and_legacy_stage(legacy):
    repository, service, principal, state = _created()
    state.page = legacy
    repository.replace_state_and_ledger(state)
    skipped = service.skip_study_session(state.session_id, principal, expected_version=0, request_id=f"skip-{legacy}")
    assert skipped.state.page == "home"


def test_completed_account_does_not_silently_create_a_fresh_attempt(monkeypatch):
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    principal = ParticipantPrincipal("a" * 64)
    repository._completed_accounts.add(principal.account_key)
    monkeypatch.setattr(services_module, "REPEAT_SCENARIO_DEV_MODE", False)
    with pytest.raises(ParticipationCompleted):
        service.bootstrap_session(principal, expected_version=0, language="en", request_id="create")
    assert repository._sessions == {}


def test_finalized_session_can_be_recovered_only_from_encrypted_bound_identity():
    repository, service, principal, state = _created()
    state.submission_finalized = True
    state.saved = True
    state.page = "done"
    repository.replace_state_and_ledger(state)
    repository._accounts.pop(principal.account_key)
    bound = ParticipantPrincipal(principal.account_key, bound_session_id=state.session_id)
    assert service.load_owned_session(state.session_id, bound).saved
    with pytest.raises(Exception):
        service.load_owned_session(state.session_id, principal)


def test_finalization_request_id_is_not_an_ownership_credential():
    repository, service, principal, state = _created()
    state.submission_finalized = True
    state.saved = True
    state.page = "done"
    repository.replace_state_and_ledger(state)
    repository._accounts.pop(principal.account_key)
    repository._idempotency[(state.session_id, "finalize", "known-request")] = {
        "payload_hash": "irrelevant",
    }

    attacker = ParticipantPrincipal("b" * 64)
    with pytest.raises(Exception):
        service.finalize_owned_session(
            state.session_id,
            attacker,
            expected_version=state.state_version,
            request_id="known-request",
        )


def test_prolific_relaunch_rebinds_active_attempt_but_rejects_new_completed_attempt(monkeypatch):
    monkeypatch.setenv("PROLIFIC_COMPLETION_CODE", "COMPLETE")
    first = ParticipantPrincipal(
        "p" * 64,
        identity_kind="prolific",
        prolific_pid="pid",
        prolific_study_id="study",
        prolific_session_id="attempt-1",
    )
    repository, service, _principal, state = _created(principal=first)
    second = ParticipantPrincipal(
        first.account_key,
        identity_kind="prolific",
        prolific_pid="pid",
        prolific_study_id="study",
        prolific_session_id="attempt-2",
    )
    rebound = service.bootstrap_session(second, expected_version=0, language="en", request_id="relaunch")
    assert rebound.state.session_id == state.session_id
    assert rebound.state.prolific_session_id == "attempt-2"
    completed = rebound.state.copy()
    completed.submission_finalized = True
    completed.saved = True
    repository.replace_state_and_ledger(completed)
    repository._accounts.pop(first.account_key, None)
    third = ParticipantPrincipal(
        first.account_key,
        identity_kind="prolific",
        prolific_pid="pid",
        prolific_study_id="study",
        prolific_session_id="attempt-3",
    )
    with pytest.raises(ProlificLaunchError):
        service.find_prolific_owned_session_id(third)
