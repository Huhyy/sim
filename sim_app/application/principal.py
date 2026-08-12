"""Server-derived participant identity used for session authorization."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParticipantPrincipal:
    """Trusted identity material produced by a transport authentication adapter.

    None of these values are accepted from participant command payloads.
    Prolific fields are optional because ordinary OIDC participants do not
    carry research-launch identifiers.
    """

    account_key: str
    identity_kind: str = "oidc"
    prolific_pid: str | None = None
    prolific_study_id: str | None = None
    prolific_session_id: str | None = None
    email: str | None = None
    display_name: str | None = None
    bound_session_id: str | None = None
    is_admin: bool = False


__all__ = ["ParticipantPrincipal"]
