from pathlib import Path

import pytest

from sim_app.application.errors import AuthenticationRequired
from sim_app.application.principal import ParticipantPrincipal
from sim_app.auth.browser_session import BrowserSessionManager


ROOT = Path(__file__).resolve().parent.parent


def test_dockerfile_is_a_non_root_runtime_only_uvicorn_image():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert dockerfile.startswith("FROM python:3.13-slim-bookworm\n")
    assert "COPY requirements.txt" in dockerfile
    assert "COPY sim_app ./sim_app" in dockerfile
    assert "requirements-test.txt" not in dockerfile
    assert "playwright" not in dockerfile.lower()
    assert "streamlit" not in dockerfile.lower()
    assert "USER 10001:10001" in dockerfile
    assert "uvicorn sim_app.api.app:app" in dockerfile
    assert "--host 0.0.0.0" in dockerfile
    assert '${PORT:-8080}' in dockerfile
    assert "--reload" not in dockerfile
    assert "gunicorn" not in dockerfile.lower()


def test_docker_context_is_runtime_allowlisted_and_secret_safe():
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    rules = {line.strip() for line in dockerignore if line.strip() and not line.startswith("#")}

    assert "**" in rules
    assert "!requirements.txt" in rules
    assert "!sim_app/**" in rules
    assert ".env" in rules
    assert ".env.*" in rules
    assert ".git/" in rules
    assert ".codex-remote-attachments/" in rules
    assert "tests/" in rules
    assert "requirements-test.txt" in rules
    assert "sim_app/persistence/memory.py" in rules
    assert "sim_app/persistence/admin_memory.py" in rules


def test_runtime_requirements_exclude_browser_and_retired_ui_dependencies():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()

    assert "fastapi==" in requirements
    assert "uvicorn==" in requirements
    assert "supabase==" in requirements
    assert "playwright" not in requirements
    assert "pytest" not in requirements
    assert "streamlit" not in requirements


def test_browser_session_survives_process_replacement_with_stable_secret():
    principal = ParticipantPrincipal(
        account_key="opaque-account-key",
        identity_kind="google",
        email="participant@example.test",
        display_name="Participant",
        bound_session_id="00000000-0000-0000-0000-000000000001",
    )
    container_a = BrowserSessionManager(secret="stable-external-secret", secure=True)
    cookie = container_a.encode_principal(principal, csrf_token="stable-csrf-token")

    # A fresh manager models a replacement process/container with no shared
    # memory or filesystem, but with the same externally supplied secret.
    container_b = BrowserSessionManager(secret="stable-external-secret", secure=True)
    restored, csrf_token = container_b.decode_principal(cookie)

    assert restored == principal
    assert csrf_token == "stable-csrf-token"

    unrelated_container = BrowserSessionManager(secret="different-secret", secure=True)
    with pytest.raises(AuthenticationRequired):
        unrelated_container.decode_principal(cookie)
