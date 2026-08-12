"""Server-derived participant identity used for session authorization."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParticipantPrincipal:
    """Trusted identity material produced by a transport authentication adapter.

    None of these values are accepted from participant command payloads.
    Prolific fields are optional because the current Streamlit transport also
    supports ordinary OIDC participants.
    """

    account_key: str
    identity_kind: str = "oidc"
    prolific_pid: str | None = None
    prolific_study_id: str | None = None
    prolific_session_id: str | None = None


__all__ = ["ParticipantPrincipal"]
