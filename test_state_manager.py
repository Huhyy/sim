from loan import Loan
from overdraft import Overdraft

import state_manager


class DummySessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


def test_hydrate_preserves_existing_session_id(monkeypatch):
    dummy_state = DummySessionState(
        session_id="session-123",
        loan=Loan(balance=7000.0, annual_interest=0.0835, months=24),
        overdraft=Overdraft(limit=3000.0, annual_interest=0.24),
    )
    monkeypatch.setattr(state_manager.st, "session_state", dummy_state)

    state_manager.hydrate_from_checkpoint(
        {
            "page": "simulation",
            "month": 3,
            "loan_balance": 6350.0,
            "overdraft_balance": 0.0,
            "answers": {},
        }
    )

    assert dummy_state.session_id == "session-123"
    assert dummy_state.page == "simulation"
    assert dummy_state.month == 3


def test_persist_recovers_session_id_from_url(monkeypatch):
    dummy_state = DummySessionState(
        session_id=None,
        page="simulation",
        month=2,
        loan=Loan(balance=6500.0, annual_interest=0.0835, months=24),
        overdraft=Overdraft(limit=3000.0, annual_interest=0.24),
    )
    saved = {}
    monkeypatch.setattr(state_manager.st, "session_state", dummy_state)
    monkeypatch.setattr(state_manager, "get_query_param", lambda name: "session-456" if name == "sid" else None)
    monkeypatch.setattr(
        state_manager,
        "save_session_checkpoint",
        lambda session_id, checkpoint, status="in_progress": saved.update(
            session_id=session_id,
            checkpoint=checkpoint,
            status=status,
        ),
    )

    assert state_manager.persist_checkpoint()
    assert dummy_state.session_id == "session-456"
    assert dummy_state.checkpoint_last_save["ok"] is True
    assert saved["session_id"] == "session-456"


def test_finalize_participant_recovers_session_id_before_final_save(monkeypatch):
    dummy_state = DummySessionState(
        session_id=None,
        checkpoint_last_load={"session_id": "session-789"},
    )
    saved = {}
    monkeypatch.setattr(state_manager.st, "session_state", dummy_state)
    monkeypatch.setattr(state_manager, "get_query_param", lambda _name: None)
    monkeypatch.setattr(state_manager, "clear_query_param", lambda _name: None)
    monkeypatch.setattr(state_manager, "current_account_key", lambda: "account-key")
    monkeypatch.setattr(
        state_manager,
        "db_finalize_participation",
        lambda account_key, session_id, answers, final_score: saved.update(
            account_key=account_key,
            session_id=session_id,
            answers=answers,
            final_score=final_score,
        ),
    )

    state_manager.finalize_participant(None, {"q_1": 5}, 18.25)

    assert dummy_state.session_id == "session-789"
    assert saved == {
        "account_key": "account-key",
        "session_id": "session-789",
        "answers": {"q_1": 5},
        "final_score": 18.25,
    }
    assert dummy_state.submission_finalized is True


def test_persist_does_not_recreate_deleted_finalized_checkpoint(monkeypatch):
    dummy_state = DummySessionState(submission_finalized=True)
    monkeypatch.setattr(state_manager.st, "session_state", dummy_state)
    monkeypatch.setattr(
        state_manager,
        "save_session_checkpoint",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("save should not run")),
    )

    assert state_manager.persist_checkpoint()


def test_bootstrap_claims_url_checkpoint_before_loading_answers(monkeypatch):
    dummy_state = DummySessionState()
    events = []
    monkeypatch.setattr(state_manager.st, "session_state", dummy_state)
    monkeypatch.setattr(state_manager, "current_account_key", lambda: "a" * 64)
    monkeypatch.setattr(state_manager, "account_has_completed", lambda _account_key: False)
    monkeypatch.setattr(state_manager, "load_linked_session_id", lambda _account_key: None)
    monkeypatch.setattr(state_manager, "get_query_param", lambda _name: "session-from-url")
    monkeypatch.setattr(
        state_manager,
        "save_resume_link",
        lambda _account_key, _session_id: events.append("claim"),
    )

    def load_checkpoint(_session_id):
        events.append("load")
        return {
            "page": "simulation",
            "month": 2,
            "loan_balance": 6650.0,
            "overdraft_balance": 0.0,
            "answers": {"private": 5},
        }

    monkeypatch.setattr(state_manager, "load_session_checkpoint", load_checkpoint)

    state_manager.bootstrap_authenticated_session()

    assert events == ["claim", "load"]
    assert dummy_state.answers == {"private": 5}
