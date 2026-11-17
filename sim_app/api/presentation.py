"""HTTP serialization over the application-owned participant-safe view."""

from sim_app.application.participant_views import participant_session_view
from sim_app.api.schemas import ParticipantSessionResponse


def present_state(state, *, idempotency_replayed=False, admin=False):
    view = participant_session_view(state, idempotency_replayed=idempotency_replayed)
    # Participants stay blind to their treatment; only admins receive it.
    if admin:
        view["admin_condition"] = state.experimental_condition
    return ParticipantSessionResponse.model_validate(view)


def present_result(result, *, admin=False):
    return present_state(result.state, idempotency_replayed=result.idempotency_hit, admin=admin)


__all__ = ["present_result", "present_state"]
