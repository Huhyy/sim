"""Adapter between Streamlit's mapping-like state and ParticipantState."""

from sim_app.application.state import ParticipantState
from sim_app.config import SCENARIO_VERSION


def read_participant_state(runtime_state) -> ParticipantState:
    return ParticipantState.from_runtime_state(runtime_state, SCENARIO_VERSION)


def apply_participant_state(runtime_state, participant_state: ParticipantState) -> None:
    participant_state.apply_to_runtime_state(runtime_state)


def navigate(runtime_state, page, persist_checkpoint, rerun) -> None:
    """Preserve legacy navigation mutation, write, then rerun ordering."""
    runtime_state.page = page
    runtime_state.scroll_to_top = True
    persist_checkpoint()
    rerun()


__all__ = ["apply_participant_state", "navigate", "read_participant_state"]
