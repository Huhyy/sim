from __future__ import annotations

import base64
import json
import time
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from sim_app.api.app import create_app
from sim_app.application.admin_services import AdminService
from sim_app.application.errors import ProlificLaunchError
from sim_app.application.principal import ParticipantPrincipal
from sim_app.application.services import ExperimentService
from sim_app.auth.browser_session import BrowserSessionManager, OIDC_COOKIE, SESSION_COOKIE
from sim_app.auth.oidc import GOOGLE_ISSUER, GoogleOidcClient
from sim_app.persistence.admin_memory import MemoryAdminRepository
from sim_app.persistence.memory import InMemoryExperimentRepository
import sim_app.api.auth_routes as auth_routes_module


def _browser_app(*, principal=None, admin_service=None):
    manager = BrowserSessionManager("test-browser-secret", secure=False)
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    app = create_app(
        service=service,
        admin_service=admin_service,
        browser_session_manager=manager,
        docs_enabled=False,
    )
    client = TestClient(app)
    if principal:
        client.cookies.set(SESSION_COOKIE, manager.encode_principal(principal, csrf_token="csrf-test"))
    return client, service, repository, manager


def test_encrypted_browser_session_and_csrf_boundary():
    principal = ParticipantPrincipal("a" * 64, email="person@example.com", display_name="Person")
    client, _service, _repository, _manager = _browser_app(principal=principal)
    auth = client.get("/api/v1/auth/session")
    assert auth.status_code == 200
    assert auth.json() == {
        "authenticated": True,
        "identity_kind": "oidc",
        "display_name": "Person",
        "email": "person@example.com",
        "is_admin": False,
        "session_id": None,
        "csrf_token": "csrf-test",
    }
    assert "account_key" not in auth.text
    denied = client.post(
        "/api/v1/sessions",
        headers={"Idempotency-Key": "create", "Origin": "http://testserver"},
        json={"expected_version": 0, "language": "en"},
    )
    assert denied.status_code == 401
    accepted = client.post(
        "/api/v1/sessions",
        headers={"Idempotency-Key": "create", "X-CSRF-Token": "csrf-test", "Origin": "http://testserver"},
        json={"expected_version": 0, "language": "en"},
    )
    assert accepted.status_code == 201
    cookie = accepted.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie


def test_csrf_requires_json_and_origin_or_referer():
    principal = ParticipantPrincipal("a" * 64, email="person@example.com")
    client, *_ = _browser_app(principal=principal)
    base_headers = {"Idempotency-Key": "create", "X-CSRF-Token": "csrf-test"}

    missing_origin = client.post(
        "/api/v1/sessions",
        headers=base_headers,
        json={"expected_version": 0, "language": "en"},
    )
    assert missing_origin.status_code == 401

    non_json = client.post(
        "/api/v1/sessions",
        headers={**base_headers, "Origin": "http://testserver", "Content-Type": "text/plain"},
        content='{"expected_version":0,"language":"en"}',
    )
    assert non_json.status_code == 401

    referer_fallback = client.post(
        "/api/v1/sessions",
        headers={**base_headers, "Referer": "http://testserver/current-page"},
        json={"expected_version": 0, "language": "en"},
    )
    assert referer_fallback.status_code == 201


def test_admin_routes_are_server_authorized_and_never_expose_checkpoint():
    repository = MemoryAdminRepository()
    admin_service = AdminService(repository)
    non_admin = ParticipantPrincipal("a" * 64, email="user@example.com")
    client, *_ = _browser_app(principal=non_admin, admin_service=admin_service)
    assert client.get("/api/v1/admin/sessions").status_code == 403

    admin = ParticipantPrincipal("b" * 64, email="admin@example.com", is_admin=True)
    client, *_ = _browser_app(principal=admin, admin_service=admin_service)
    headers = {"X-CSRF-Token": "csrf-test", "Origin": "http://testserver"}
    created = client.post("/api/v1/admin/sessions", headers=headers, json={"experimental_condition": "C3"})
    assert created.status_code == 201
    session = created.json()
    assert session["experimental_condition"] == "C3"
    repository.participants[session["id"]] = [{
        "participant_code": "P001",
        "status": "in_progress",
        "current_page": "simulation",
        "checkpoint": {"page": "simulation", "month": 7, "answers": {"secret": "value"}},
        "summary": None,
    }]
    listing = client.get("/api/v1/admin/sessions")
    assert listing.status_code == 200
    assert listing.json()[0]["participants"][0]["progress_percent"] > 0
    assert "checkpoint" not in listing.text and "secret" not in listing.text
    repository.participants[session["id"]][0]["summary"] = {
        "final_score": 87.5,
        "performance_bonus_gbp": 2,
        "total_payout_gbp": 7,
    }
    repository.participants[session["id"]][0]["prolific_pid"] = "prolific-participant"
    results = client.get("/api/v1/admin/participants")
    assert results.status_code == 200
    assert results.json() == [{
        "participant_code": "P001",
        "session_code": session["session_code"],
        "final_score": 87.5,
        "performance_bonus_gbp": 2.0,
        "payout_gbp": 7.0,
        "status": "in_progress",
    }]
    cancelled = client.post(f"/api/v1/admin/sessions/{session['id']}/cancel", headers=headers, json={})
    assert cancelled.status_code == 200


def test_frontend_shell_and_assets_are_same_origin():
    client, *_ = _browser_app()
    shell = client.get("/")
    assert shell.status_code == 200
    assert "default-src 'self'" in shell.headers["content-security-policy"]
    assert shell.headers["x-content-type-options"] == "nosniff"
    assert "/static/css/app.css?v=20260813-framing1" in shell.text
    assert "/static/js/app.js?v=20260819-session-guard1" in shell.text
    assert client.get("/admin").status_code == 200
    script = client.get("/static/js/app.js")
    assert script.status_code == 200
    assert "ExperimentService" not in script.text
    assert "experimental_condition" not in script.text
    assert "account_key" not in script.text

    unauthenticated = client.get("/api/v1/auth/session")
    assert unauthenticated.headers["cache-control"] == "no-store"


class _Response:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): return None
    def json(self): return self.payload


class _OidcHttp:
    def __init__(self, discovery, jwks, token): self.discovery, self.jwks, self.token = discovery, jwks, token
    def get(self, url):
        if url.endswith("openid-configuration"): return _Response(self.discovery)
        return _Response(self.jwks)
    def post(self, _url, data):
        assert data["code_verifier"]
        return _Response({"id_token": self.token})


def test_google_oidc_validates_state_nonce_issuer_audience_and_expiry():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_numbers()
    enc = lambda value: base64.urlsafe_b64encode(value.to_bytes((value.bit_length() + 7) // 8, "big")).rstrip(b"=").decode()
    jwks = {"keys": [{"kty": "RSA", "kid": "kid", "use": "sig", "alg": "RS256", "n": enc(public.n), "e": enc(public.e)}]}
    discovery = {"authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth", "token_endpoint": "https://oauth2.googleapis.com/token", "jwks_uri": "https://keys.example/jwks"}
    bootstrap = GoogleOidcClient(client_id="client", client_secret="secret", redirect_uri="https://app.example/auth/google/callback", http_client=_OidcHttp(discovery, jwks, "unused"))
    url, transaction = bootstrap.begin()
    query = parse_qs(urlparse(url).query)
    assert query["state"][0] == transaction["state"] and query["nonce"][0] == transaction["nonce"]
    assert query["code_challenge_method"] == ["S256"]
    token = jwt.encode({
        "iss": GOOGLE_ISSUER, "aud": "client", "sub": "subject", "email": "person@example.com", "email_verified": True,
        "nonce": transaction["nonce"], "iat": int(time.time()), "exp": int(time.time()) + 300,
    }, key, algorithm="RS256", headers={"kid": "kid"})
    client = GoogleOidcClient(client_id="client", client_secret="secret", redirect_uri="https://app.example/auth/google/callback", http_client=_OidcHttp(discovery, jwks, token))
    claims = client.complete(code="code", state=transaction["state"], transaction=transaction)
    assert claims["sub"] == "subject"
    with pytest.raises(ValueError, match="state"):
        client.complete(code="code", state="wrong", transaction=transaction)


def test_google_browser_login_callback_sets_only_server_session(monkeypatch):
    monkeypatch.setenv("ACCOUNT_KEY_PEPPER", "stable-pepper")
    manager = BrowserSessionManager("test-browser-secret", secure=False)

    class FakeOidc:
        def begin(self):
            return "https://accounts.google.com/auth", {"state": "state", "nonce": "nonce", "verifier": "verifier"}
        def complete(self, **kwargs):
            assert kwargs["code"] == "code" and kwargs["state"] == "state"
            return {
                "iss": GOOGLE_ISSUER, "sub": "subject", "email": "person@example.com",
                "email_verified": True, "name": "Person",
            }

    app = create_app(
        service=ExperimentService(InMemoryExperimentRepository()),
        browser_session_manager=manager,
        oidc_client=FakeOidc(),
        docs_enabled=False,
    )
    with TestClient(app) as client:
        login = client.get("/auth/google/login", follow_redirects=False)
        assert login.status_code == 302
        assert OIDC_COOKIE in login.headers["set-cookie"] and "HttpOnly" in login.headers["set-cookie"]
        callback = client.get("/auth/google/callback?code=code&state=state", follow_redirects=False)
        assert callback.status_code == 303 and callback.headers["location"] == "/"
        assert SESSION_COOKIE in callback.headers["set-cookie"] and "HttpOnly" in callback.headers["set-cookie"]
        session = client.get("/api/v1/auth/session")
        assert session.status_code == 200 and session.json()["email"] == "person@example.com"
        assert "stable-pepper" not in session.text and "account_key" not in session.text

        # Browser Back can revisit the now-consumed one-time callback. It must
        # fail closed without replacing the principal or showing raw API JSON.
        replay = client.get("/auth/google/callback?code=code&state=state", follow_redirects=False)
        assert replay.status_code == 303 and replay.headers["location"] == "/"
        assert "authentication_required" not in replay.text
        resumed = client.get("/api/v1/auth/session")
        assert resumed.status_code == 200 and resumed.json()["email"] == "person@example.com"


def test_google_callback_without_transaction_returns_to_login_safely():
    manager = BrowserSessionManager("test-browser-secret", secure=False)
    app = create_app(
        service=ExperimentService(InMemoryExperimentRepository()),
        browser_session_manager=manager,
        docs_enabled=False,
    )
    with TestClient(app) as client:
        callback = client.get("/auth/google/callback?code=expired&state=expired", follow_redirects=False)
        assert callback.status_code == 303 and callback.headers["location"] == "/"
        assert "authentication_required" not in callback.text
        assert client.get("/api/v1/auth/session").status_code == 401


def test_prolific_launch_requires_complete_api_verified_parameters(monkeypatch):
    monkeypatch.setenv("ACCOUNT_KEY_PEPPER", "pepper")
    verified = []

    def verify(**params):
        verified.append(params)
        if params != {"submission_id": "s", "participant_id": "p", "study_id": "study"}:
            raise ProlificLaunchError("The Prolific launch identity did not match its submission")

    monkeypatch.setattr(auth_routes_module, "verify_prolific_submission", verify)
    client, *_ = _browser_app()
    assert client.get("/auth/prolific/launch?PROLIFIC_PID=p&STUDY_ID=study").status_code == 400
    denied = client.get("/auth/prolific/launch?PROLIFIC_PID=p&STUDY_ID=other&SESSION_ID=s")
    assert denied.status_code == 400
    accepted = client.get("/auth/prolific/launch?PROLIFIC_PID=p&STUDY_ID=study&SESSION_ID=s", follow_redirects=False)
    assert accepted.status_code == 303 and accepted.headers["location"] == "/"
    assert "PROLIFIC_PID" not in accepted.headers["location"]
    cookie = accepted.headers["set-cookie"]
    assert SESSION_COOKIE in cookie and "HttpOnly" in cookie
    assert verified[-1] == {"submission_id": "s", "participant_id": "p", "study_id": "study"}

    monkeypatch.setattr(auth_routes_module, "PROLIFIC_MODE_ENABLED", False)
    disabled = client.get("/auth/prolific/launch?PROLIFIC_PID=p&STUDY_ID=study&SESSION_ID=s")
    assert disabled.status_code == 400


def test_browser_prolific_launch_errors_redirect_without_identity_parameters(monkeypatch):
    monkeypatch.setenv("ACCOUNT_KEY_PEPPER", "pepper")
    monkeypatch.setattr(
        auth_routes_module,
        "verify_prolific_submission",
        lambda **_params: (_ for _ in ()).throw(ProlificLaunchError("Launch rejected")),
    )
    client, *_ = _browser_app()
    response = client.get(
        "/auth/prolific/launch?PROLIFIC_PID=participant&STUDY_ID=blocked&SESSION_ID=attempt",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/?prolific_error=invalid_study"
    assert "participant" not in response.headers["location"]
