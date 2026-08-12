"""Framework-neutral derivation of opaque participant account identifiers."""

from __future__ import annotations

import hashlib
import hmac

from sim_app.infra.secrets import _get_secret


def derive_account_key(*, issuer: str, subject: str) -> str:
    pepper = _get_secret("ACCOUNT_KEY_PEPPER")
    if not pepper:
        raise RuntimeError("ACCOUNT_KEY_PEPPER is required")
    if not issuer or not subject:
        raise ValueError("A trusted issuer and subject are required")
    identity = f"{issuer}|{subject}".encode("utf-8")
    return hmac.new(str(pepper).encode("utf-8"), identity, hashlib.sha256).hexdigest()


def derive_prolific_account_key(*, prolific_pid: str, study_id: str) -> str:
    return derive_account_key(issuer="prolific", subject=f"{study_id}|{prolific_pid}")


__all__ = ["derive_account_key", "derive_prolific_account_key"]
