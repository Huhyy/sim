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

