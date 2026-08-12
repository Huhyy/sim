"""Synchronous Google authorization-code OIDC adapter with PKCE."""

from __future__ import annotations

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx
import jwt

from sim_app.infra.secrets import _get_secret


GOOGLE_ISSUER = "https://accounts.google.com"


class GoogleOidcClient:
    def __init__(self, *, client_id=None, client_secret=None, redirect_uri=None, http_client=None):
        self.client_id = client_id or _get_secret("GOOGLE_CLIENT_ID")
        self.client_secret = client_secret or _get_secret("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or _get_secret("GOOGLE_REDIRECT_URI")
        if not all((self.client_id, self.client_secret, self.redirect_uri)):
            raise RuntimeError("Google OIDC configuration is incomplete")
        self.http = http_client or httpx.Client(timeout=10.0)

    def begin(self):
        discovery = self._discovery()
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        transaction = {
            "state": secrets.token_urlsafe(32),
            "nonce": secrets.token_urlsafe(32),
            "verifier": verifier,
        }
        query = urlencode({
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": transaction["state"],
            "nonce": transaction["nonce"],
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        return f"{discovery['authorization_endpoint']}?{query}", transaction

    def complete(self, *, code, state, transaction):
        if not secrets.compare_digest(str(state or ""), str(transaction.get("state") or "")):
            raise ValueError("OIDC state validation failed")
        discovery = self._discovery()
        token_response = self.http.post(discovery["token_endpoint"], data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "code_verifier": transaction["verifier"],
        })
        token_response.raise_for_status()
        id_token = token_response.json().get("id_token")
        jwks_response = self.http.get(discovery["jwks_uri"])
        jwks_response.raise_for_status()
        # Resolve the signing key from the already-fetched authoritative JWKS.
        header = jwt.get_unverified_header(id_token)
        if header.get("alg") != "RS256":
            raise ValueError("OIDC signing algorithm is not allowed")
        jwk = next(item for item in jwks_response.json()["keys"] if item.get("kid") == header.get("kid"))
        claims = jwt.decode(
            id_token,
            jwt.PyJWK.from_dict(jwk).key,
            algorithms=["RS256"],
            audience=self.client_id,
            issuer=None,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "nonce"]},
        )
        if claims.get("iss") not in {GOOGLE_ISSUER, "accounts.google.com"}:
            raise ValueError("OIDC issuer validation failed")
        if not secrets.compare_digest(str(claims.get("nonce") or ""), str(transaction.get("nonce") or "")):
            raise ValueError("OIDC nonce validation failed")
        if not claims.get("email"):
            raise ValueError("Google did not return an email address")
        return claims

    def configured(self):
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def _discovery(self):
        response = self.http.get(f"{GOOGLE_ISSUER}/.well-known/openid-configuration")
        response.raise_for_status()
        return response.json()


__all__ = ["GoogleOidcClient"]
