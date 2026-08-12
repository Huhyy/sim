"""Encrypted, HttpOnly browser authentication sessions."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from dataclasses import asdict

from cryptography.fernet import Fernet, InvalidToken

from sim_app.application.errors import AuthenticationRequired
from sim_app.application.principal import ParticipantPrincipal
from sim_app.infra.secrets import _get_secret


SESSION_COOKIE = "sim_browser_session"
OIDC_COOKIE = "sim_oidc_transaction"
DEFAULT_MAX_AGE = 8 * 60 * 60


class BrowserSessionManager:
    def __init__(self, secret=None, *, secure=None, max_age=DEFAULT_MAX_AGE):
        secret = secret or _get_secret("BROWSER_SESSION_SECRET")
        if not secret:
            raise RuntimeError("BROWSER_SESSION_SECRET is required")
        key = base64.urlsafe_b64encode(hashlib.sha256(str(secret).encode("utf-8")).digest())
        self._fernet = Fernet(key)
        self.secure = _truthy(_get_secret("COOKIE_SECURE"), default=True) if secure is None else bool(secure)
        self.max_age = int(max_age)

    def encode_principal(self, principal: ParticipantPrincipal, *, csrf_token=None) -> str:
        payload = asdict(principal)
        payload.update({"kind": "principal", "csrf": csrf_token or secrets.token_urlsafe(32), "exp": int(time.time()) + self.max_age})
        return self._encode(payload)

    def decode_principal(self, token: str | None) -> tuple[ParticipantPrincipal, str]:
        payload = self._decode(token, expected_kind="principal")
        fields = {name: payload.get(name) for name in ParticipantPrincipal.__dataclass_fields__}
        principal = ParticipantPrincipal(**fields)
        if not principal.account_key:
            raise AuthenticationRequired("The browser authentication session is invalid")
        return principal, str(payload["csrf"])

    def encode_oidc_transaction(self, transaction: dict) -> str:
        return self._encode({**transaction, "kind": "oidc", "exp": int(time.time()) + 600})

    def decode_oidc_transaction(self, token: str | None) -> dict:
        return self._decode(token, expected_kind="oidc")

    def set_principal_cookie(self, response, principal, *, csrf_token=None):
        response.set_cookie(
            SESSION_COOKIE,
            self.encode_principal(principal, csrf_token=csrf_token),
            max_age=self.max_age,
            httponly=True,
            secure=self.secure,
            samesite="lax",
            path="/",
        )

    def clear_principal_cookie(self, response):
        response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, secure=self.secure, samesite="lax")

    def _encode(self, payload):
        return self._fernet.encrypt(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")

    def _decode(self, token, *, expected_kind):
        if not token:
            raise AuthenticationRequired("No browser authentication session is present")
        try:
            payload = json.loads(self._fernet.decrypt(str(token).encode("ascii")).decode("utf-8"))
        except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise AuthenticationRequired("The browser authentication session is invalid") from exc
        if payload.get("kind") != expected_kind or int(payload.get("exp", 0)) < int(time.time()):
            raise AuthenticationRequired("The browser authentication session has expired")
        return payload


def _truthy(value, *, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


__all__ = ["BrowserSessionManager", "OIDC_COOKIE", "SESSION_COOKIE"]
