"""Runtime default state values."""

from sim_app.application.state import ParticipantState
from sim_app.config import SCENARIO_VERSION


def runtime_defaults():
    return ParticipantState.initial(SCENARIO_VERSION).to_runtime_defaults()


__all__ = [
    "runtime_defaults",
]
