from sim_app.domain.loan import Loan
from sim_app.domain.overdraft import Overdraft


class DummySessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


def test_extracted_hydrate_preserves_existing_session_id(monkeypatch):
    import sim_app.state.checkpoint as checkpoint
    import sim_app.state.navigation as navigation

    dummy_state = DummySessionState(
        session_id="session-123",
        loan=Loan(balance=7000.0, annual_interest=0.0835, months=24),
        overdraft=Overdraft(limit=3000.0, annual_interest=0.24),
    )
    monkeypatch.setattr(checkpoint.st, "session_state", dummy_state)
    monkeypatch.setattr(navigation.st, "session_state", dummy_state)

    checkpoint.hydrate_from_checkpoint(
        {
            "page": "simulation",
            "month": 3,
            "loan_balance": 6350.0,
            "overdraft_balance": 0.0,
            "participant_code": "P001",
            "experimental_condition": "C3",
            "score_frame": "loss_frame",
            "monthly_score_feedback": "hidden",
            "answers": {},
        }
    )

    assert dummy_state.session_id == "session-123"
    assert dummy_state.page == "simulation"
    assert dummy_state.month == 3
    assert dummy_state.participant_code == "P001"
    assert dummy_state.experimental_condition == "C3"
    assert dummy_state.score_frame == "loss_frame"
    assert dummy_state.monthly_score_feedback == "hidden"


def test_extracted_persist_recovers_session_id_from_url(monkeypatch):
    import sim_app.state.checkpoint as checkpoint
    import sim_app.state.navigation as navigation

    dummy_state = DummySessionState(
        session_id=None,
        page="simulation",
        month=2,
        participant_code="P002",
        experimental_condition="C2",
        score_frame="gain_frame",
        monthly_score_feedback="hidden",
        loan=Loan(balance=6500.0, annual_interest=0.0835, months=24),
        overdraft=Overdraft(limit=3000.0, annual_interest=0.24),
    )
    saved = {}
    monkeypatch.setattr(checkpoint.st, "session_state", dummy_state)
    monkeypatch.setattr(navigation.st, "session_state", dummy_state)
    monkeypatch.setattr(navigation, "get_query_param", lambda name: "session-456" if name == "sid" else None)
    monkeypatch.setattr(
        checkpoint,
        "save_session_checkpoint",
        lambda session_id, saved_checkpoint, status="in_progress": saved.update(
            session_id=session_id,
            checkpoint=saved_checkpoint,
            status=status,
        ),
    )

    assert checkpoint.persist_checkpoint()
    assert dummy_state.session_id == "session-456"
    assert dummy_state.checkpoint_last_save["ok"] is True
    assert saved["session_id"] == "session-456"
    assert saved["checkpoint"]["participant_code"] == "P002"
    assert saved["checkpoint"]["experimental_condition"] == "C2"
    assert saved["checkpoint"]["monthly_score_feedback"] == "hidden"


def test_save_session_checkpoint_writes_condition_columns(monkeypatch):
    import sim_app.persistence.participant_sessions as participant_sessions

    saved = {}

    class FakeTable:
        def upsert(self, row):
            saved.update(row)
            return self

        def execute(self):
            return None

    class FakeClient:
        def table(self, name):
            assert name == "participant_sessions"
            return FakeTable()

    monkeypatch.setattr(participant_sessions, "_require_client", lambda: FakeClient())
    monkeypatch.setattr(participant_sessions, "_utcnow", lambda: "2026-06-16T00:00:00+00:00")

    participant_sessions.save_session_checkpoint(
        "session-1",
        {
            "page": "simulation",
            "study_session_code": "022809",
            "participant_code": "P031",
            "experimental_condition": "C4",
            "score_frame": "loss_frame",
            "monthly_score_feedback": "hidden",
        },
    )

    assert saved["experimental_condition"] == "C4"
    assert saved["score_frame"] == "loss_frame"
    assert saved["monthly_score_feedback"] == "hidden"


def test_extracted_finalize_recovers_session_id_before_final_save(monkeypatch):
    import sim_app.session.finalization as finalization
    import sim_app.state.navigation as navigation

    dummy_state = DummySessionState(
        session_id=None,
        checkpoint_last_load={"session_id": "session-789"},
    )
    saved = {}
    monkeypatch.setattr(finalization.st, "session_state", dummy_state)
    monkeypatch.setattr(navigation.st, "session_state", dummy_state)
    monkeypatch.setattr(finalization, "resolve_session_id", navigation.resolve_session_id)
    monkeypatch.setattr(navigation, "get_query_param", lambda _name: None)
    monkeypatch.setattr(finalization, "clear_query_param", lambda _name: None)
    monkeypatch.setattr(finalization, "current_account_key", lambda: "account-key")
    monkeypatch.setattr(
        finalization,
        "db_finalize_participation",
        lambda account_key, session_id, answers, final_score, **kwargs: saved.update(
            account_key=account_key,
            session_id=session_id,
            answers=answers,
            final_score=final_score,
            allow_repeat=kwargs.get("allow_repeat"),
            monthly_results=kwargs.get("monthly_results"),
        ),
    )

    finalization.finalize_participant(None, {"q_1": 5}, 18.25)

    assert dummy_state.session_id == "session-789"
    assert saved["account_key"] == "account-key"
    assert saved["session_id"] == "session-789"
    assert dummy_state.submission_finalized is True


def test_extracted_repeat_mode_does_not_block_previously_completed_account(monkeypatch):
    import sim_app.session.manager as manager

    dummy_state = DummySessionState()
    checked_completion = []
    monkeypatch.setattr(manager.st, "session_state", dummy_state)
    monkeypatch.setattr(manager, "REPEAT_SCENARIO_DEV_MODE", True)
    monkeypatch.setattr(manager, "current_account_key", lambda: "a" * 64)
    monkeypatch.setattr(
        manager,
        "account_has_completed",
        lambda _account_key: checked_completion.append(True) or True,
    )
    monkeypatch.setattr(manager, "load_linked_session_id", lambda _account_key: None)
    monkeypatch.setattr(manager, "get_query_param", lambda _name: None)
    monkeypatch.setattr(manager, "set_query_param", lambda _name, _value: None)
    monkeypatch.setattr(manager, "load_session_checkpoint", lambda _session_id: None)
    monkeypatch.setattr(manager, "persist_checkpoint", lambda: True)
    monkeypatch.setattr(manager, "save_resume_link", lambda _account_key, _session_id: None)
    monkeypatch.setattr(manager, "new_session_id", lambda: "session-new")

    manager.bootstrap_authenticated_session()

    assert checked_completion == []
    assert dummy_state.page == "home"
    assert dummy_state.already_completed is False


def test_new_authenticated_session_persists_checkpoint_before_resume_link(monkeypatch):
    import sim_app.session.manager as manager

    dummy_state = DummySessionState()
    calls = []
    monkeypatch.setattr(manager.st, "session_state", dummy_state)
    monkeypatch.setattr(manager, "REPEAT_SCENARIO_DEV_MODE", True)
    monkeypatch.setattr(manager, "current_account_key", lambda: "a" * 64)
    monkeypatch.setattr(manager, "account_has_completed", lambda _account_key: False)
    monkeypatch.setattr(manager, "load_linked_session_id", lambda _account_key: None)
    monkeypatch.setattr(manager, "get_query_param", lambda _name: None)
    monkeypatch.setattr(manager, "set_query_param", lambda _name, _value: None)
    monkeypatch.setattr(manager, "load_session_checkpoint", lambda _session_id: None)
    monkeypatch.setattr(manager, "new_session_id", lambda: "session-new")
    monkeypatch.setattr(manager, "persist_checkpoint", lambda: calls.append("persist_checkpoint") or True)
    monkeypatch.setattr(
        manager,
        "save_resume_link",
        lambda _account_key, _session_id: calls.append("save_resume_link"),
    )

    manager.bootstrap_authenticated_session()

    assert calls == ["persist_checkpoint", "save_resume_link"]
