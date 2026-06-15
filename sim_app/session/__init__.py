"""Participant session lifecycle."""

__all__ = [
    "bootstrap_authenticated_session",
    "clear_query_param",
    "ensure_current_scenario_version",
    "finalize_participant",
    "get_query_param",
    "set_query_param",
    "start_new_scenario",
]


def __getattr__(name):
    if name == "finalize_participant":
        from .finalization import finalize_participant

        return finalize_participant
    if name in {"bootstrap_authenticated_session", "ensure_current_scenario_version", "start_new_scenario"}:
        from . import manager

        return getattr(manager, name)
    if name in {"clear_query_param", "get_query_param", "set_query_param"}:
        from . import query_params

        return getattr(query_params, name)
    raise AttributeError(name)
