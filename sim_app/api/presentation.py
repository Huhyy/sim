"""HTTP serialization over the application-owned participant-safe view."""

from sim_app.application.participant_views import participant_session_view
from sim_app.api.schemas import ParticipantSessionResponse


def present_state(state, *, idempotency_replayed=False):
    return ParticipantSessionResponse.model_validate(
        participant_session_view(state, idempotency_replayed=idempotency_replayed)
    )


def present_result(result):
    return present_state(result.state, idempotency_replayed=result.idempotency_hit)


__all__ = ["present_result", "present_state"]
