"""Opt-in disposable-container verification against the integration Supabase.

This harness never performs Prolific finalization or payment. It requires the
same explicit synthetic-write opt-ins as the Phase 3.5 integration suite.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim_app.application.principal import ParticipantPrincipal
from sim_app.auth.browser_session import BrowserSessionManager, SESSION_COOKIE
from sim_app.infra.supabase import get_client, reset_shared_client


REQUIRED_ENV = (
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
    "BROWSER_SESSION_SECRET",
    "ACCOUNT_KEY_PEPPER",
)
CONTAINER_ENV = (
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
    "BROWSER_SESSION_SECRET",
    "ACCOUNT_KEY_PEPPER",
    "PUBLIC_ORIGIN",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
    "COOKIE_SECURE",
    "API_DOCS_ENABLED",
    "ALLOW_REPEAT_PARTICIPATION",
    "PROLIFIC_MODE_ENABLED",
    "PROLIFIC_API_TOKEN",
    "PROLIFIC_DYNAMIC_PAYMENT_ENABLED",
)
FORBIDDEN_PARTICIPANT_KEYS = {
    "account_key",
    "checkpoint",
    "experimental_condition",
    "monthly_results",
    "monthly_score_feedback",
    "prolific_pid",
    "prolific_session_id",
    "prolific_study_id",
    "score_frame",
    "treatment_bound",
}


def _run(docker: str, *args: str, capture=True) -> str:
    completed = subprocess.run(
        [docker, *args],
        check=True,
        capture_output=capture,
        text=True,
        env=os.environ.copy(),
    )
    return completed.stdout.strip() if capture else ""


def _container_exists(docker: str, name: str) -> bool:
    completed = subprocess.run(
        [docker, "inspect", name],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    return completed.returncode == 0


def _remove_container(docker: str, name: str) -> None:
    if not _container_exists(docker, name):
        return
    subprocess.run(
        [docker, "stop", "--time", "10", name],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    _run(docker, "rm", "--force", name)


def _start_container(docker: str, image: str, name: str, host_port: int) -> None:
    command = [
        "run",
        "--detach",
        "--name",
        name,
        "--publish",
        f"{host_port}:8080",
    ]
    for variable in CONTAINER_ENV:
        command.extend(("--env", variable))
    command.append(image)
    _run(docker, *command)
    base_url = f"http://127.0.0.1:{host_port}"
    deadline = time.time() + 45
    while time.time() < deadline:
        try:
            if httpx.get(f"{base_url}/health", timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    logs = _run(docker, "logs", name)
    raise RuntimeError(f"Container {name} did not become healthy: {logs[-1000:]}")


def _client(base_url: str, cookie: str, csrf_token: str) -> httpx.Client:
    return httpx.Client(
        base_url=base_url,
        cookies={SESSION_COOKIE: cookie},
        headers={
            "Content-Type": "application/json",
            "Origin": os.environ["PUBLIC_ORIGIN"],
            "X-CSRF-Token": csrf_token,
        },
        timeout=30,
    )


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    payload=None,
    idempotency_key: str | None = None,
    expected_status=200,
):
    headers = {"X-Request-ID": f"phase6-http-{uuid.uuid4()}"}
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    response = client.request(method, path, json=payload, headers=headers)
    statuses = {expected_status} if isinstance(expected_status, int) else set(expected_status)
    if response.status_code not in statuses:
        raise AssertionError(
            f"{method} {path}: expected {sorted(statuses)}, got "
            f"{response.status_code}: {response.text[:1000]}"
        )
    return response


def _assert_safe_projection(value) -> None:
    if isinstance(value, dict):
        leaked = FORBIDDEN_PARTICIPANT_KEYS.intersection(value)
        if leaked:
            raise AssertionError(f"Participant projection leaked keys: {sorted(leaked)}")
        for nested in value.values():
            _assert_safe_projection(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_safe_projection(nested)


def _mutation(client, session_id, suffix, path, state, payload=None):
    body = {"expected_version": state["state_version"], **(payload or {})}
    response = _request(
        client,
        "POST",
        f"/api/v1/sessions/{session_id}{path}",
        payload=body,
        idempotency_key=f"phase6-{suffix}-{session_id}",
    )
    state = response.json()
    _assert_safe_projection(state)
    return state


def _advance_to_simulation(client: httpx.Client, session_id: str, state: dict) -> dict:
    state = _mutation(client, session_id, "start", "/start", state)
    state = _mutation(
        client,
        session_id,
        "consent",
        "/consent",
        state,
        {"accepted": True, "anti_ai_declaration": True},
    )
    view = state["view"]
    demographics = {
        "demo_age": 30,
        "demo_country": "Romania",
    }
    demographics.update({key: values[0] for key, values in view["options"].items()})
    state = _mutation(
        client,
        session_id,
        "demographics",
        "/demographics",
        state,
        demographics,
    )
    section_count = 0
    while state["view"]["type"] == "questionnaire_section":
        view = state["view"]
        if view["phase"] != "pre":
            break
        answers = {question["key"]: question["options"][0] for question in view["questions"]}
        payload = {"answers": answers}
        if view.get("attention_check"):
            payload["attention_response"] = next(
                option for option in view["attention_check"]["options"] if str(option).startswith("3")
            )
        state = _mutation(
            client,
            session_id,
            f"pre-{view['section_index']}",
            f"/questionnaires/pre/sections/{view['section_index']}",
            state,
            payload,
        )
        section_count += 1
    if section_count != 22:
        raise AssertionError(f"Expected 22 pre-study sections, advanced through {section_count}")
    if state["view"]["type"] != "instructions":
        raise AssertionError(f"Expected instructions, got {state['view']['type']}")
    state = _mutation(client, session_id, "instructions", "/instructions/acknowledge", state)
    if state["view"]["type"] == "comprehension":
        raise AssertionError("Synthetic ordinary account unexpectedly entered Prolific comprehension")
    state = _mutation(client, session_id, "profile", "/profile/acknowledge", state)
    if state["view"]["type"] != "simulation" or state["month"] != 1:
        raise AssertionError("Participant did not reach month 1 simulation")
    return state


def _cleanup(client, session_id: str, account_key: str) -> None:
    for table, column in (
        ("quality_checks", "app_session_id"),
        ("psychometric_pre_answers", "session_id"),
        ("psychometric_post_answers", "session_id"),
        ("session_summaries", "session_id"),
        ("prolific_payment_attempts", "session_id"),
        ("experiment_idempotency", "session_id"),
        ("month_results", "session_id"),
        ("resume_links", "session_id"),
    ):
        client.table(table).delete().eq(column, session_id).execute()
    client.table("completed_accounts").delete().eq("account_key", account_key).execute()
    client.table("participant_sessions").delete().eq("id", session_id).execute()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--image", default="behavioral-credit-simulator:phase6")
    parser.add_argument("--allow-synthetic-writes", action="store_true")
    args = parser.parse_args()

    if not args.allow_synthetic_writes:
        raise SystemExit("Pass --allow-synthetic-writes to acknowledge real test-database writes")
    if os.getenv("RUN_SUPABASE_INTEGRATION") != "1" or os.getenv("SUPABASE_INTEGRATION_ALLOW_SYNTHETIC_WRITES") != "1":
        raise SystemExit("The Phase 3.5 integration and synthetic-write flags must both equal 1")
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        raise SystemExit(f"Missing required environment names: {', '.join(missing)}")

    # Non-payment, same-origin test configuration. The Supabase values remain
    # inherited by name and are never placed in command arguments or output.
    os.environ.update(
        {
            "PUBLIC_ORIGIN": "http://phase6.test",
            "GOOGLE_CLIENT_ID": "phase6-container-test-client",
            "GOOGLE_CLIENT_SECRET": "phase6-container-test-secret",
            "GOOGLE_REDIRECT_URI": "http://phase6.test/auth/google/callback",
            "COOKIE_SECURE": "false",
            "API_DOCS_ENABLED": "false",
            "ALLOW_REPEAT_PARTICIPATION": "false",
            "PROLIFIC_MODE_ENABLED": "false",
            "PROLIFIC_API_TOKEN": "",
            "PROLIFIC_DYNAMIC_PAYMENT_ENABLED": "false",
        }
    )

    run_id = uuid.uuid4().hex[:10]
    container_a = f"phase6-a-{run_id}"
    container_b = f"phase6-b-{run_id}"
    account_key = hashlib.sha256(f"phase6-container:{uuid.uuid4()}".encode()).hexdigest()
    csrf_token = f"phase6-csrf-{uuid.uuid4()}"
    principal = ParticipantPrincipal(
        account_key=account_key,
        identity_kind="google",
        email="phase6-container@example.test",
        display_name="Phase 6 Container Test",
    )
    manager = BrowserSessionManager(os.environ["BROWSER_SESSION_SECRET"], secure=False)
    initial_cookie = manager.encode_principal(principal, csrf_token=csrf_token)
    session_id = None
    reset_shared_client()
    supabase = get_client()

    try:
        _start_container(args.docker, args.image, container_a, 18081)
        with _client("http://127.0.0.1:18081", initial_cookie, csrf_token) as client_a:
            created = _request(
                client_a,
                "POST",
                "/api/v1/sessions",
                payload={"expected_version": 0, "language": "en"},
                idempotency_key=f"phase6-create-{run_id}",
                expected_status=201,
            )
            state = created.json()
            _assert_safe_projection(state)
            session_id = state["session_id"]
            state = _advance_to_simulation(client_a, session_id, state)

            month_key = f"phase6-month-1-{run_id}"
            month_body = {"expected_version": state["state_version"], "payment": 317.71}
            committed = _request(
                client_a,
                "POST",
                f"/api/v1/sessions/{session_id}/months/1/decision",
                payload=month_body,
                idempotency_key=month_key,
            )
            committed_state = committed.json()
            _assert_safe_projection(committed_state)
            replay = _request(
                client_a,
                "POST",
                f"/api/v1/sessions/{session_id}/months/1/decision",
                payload=month_body,
                idempotency_key=month_key,
            )
            if replay.headers.get("Idempotency-Replayed") != "true":
                raise AssertionError("Same-container idempotent retry was not reported as a replay")
            issued_cookies = [
                cookie
                for cookie in client_a.cookies.jar
                if cookie.name == SESSION_COOKIE and cookie.domain == "127.0.0.1"
            ]
            if len(issued_cookies) != 1:
                raise AssertionError(
                    f"Expected one server-issued bound session cookie, got {len(issued_cookies)}"
                )
            durable_cookie = issued_cookies[0].value

        rows = (
            supabase.table("month_results")
            .select("*")
            .eq("session_id", session_id)
            .eq("month_number", 1)
            .execute()
            .data
        )
        if len(rows or []) != 1:
            raise AssertionError("Month 1 was not immediately durable as exactly one structured row")

        # Destroy A entirely; B gets only the image, external config, and the
        # browser's encrypted cookie. No container filesystem is copied.
        _remove_container(args.docker, container_a)
        _start_container(args.docker, args.image, container_b, 18082)
        with _client("http://127.0.0.1:18082", durable_cookie, csrf_token) as client_b:
            resumed = _request(client_b, "GET", f"/api/v1/sessions/{session_id}").json()
            _assert_safe_projection(resumed)
            for key in ("state_version", "stage", "month", "view"):
                if resumed[key] != committed_state[key]:
                    raise AssertionError(f"Replacement container changed committed {key}")
            resumed = _mutation(
                client_b,
                session_id,
                "ack-month-1",
                "/months/1/feedback/acknowledge",
                resumed,
            )
            if resumed["view"]["type"] != "simulation" or resumed["month"] != 2:
                raise AssertionError("Replacement container could not continue to month 2")

            # A fresh A now runs concurrently with B against the same backend.
            _start_container(args.docker, args.image, container_a, 18081)
            with _client("http://127.0.0.1:18081", durable_cookie, csrf_token) as client_a2:
                seen_a = _request(client_a2, "GET", f"/api/v1/sessions/{session_id}").json()
                seen_b = _request(client_b, "GET", f"/api/v1/sessions/{session_id}").json()
                if seen_a["state_version"] != seen_b["state_version"]:
                    raise AssertionError("Concurrent containers observed divergent durable versions")

                month2_key = f"phase6-month-2-{run_id}"
                month2_body = {"expected_version": seen_a["state_version"], "payment": 0.0}
                through_a = _request(
                    client_a2,
                    "POST",
                    f"/api/v1/sessions/{session_id}/months/2/decision",
                    payload=month2_body,
                    idempotency_key=month2_key,
                )
                through_b = _request(
                    client_b,
                    "POST",
                    f"/api/v1/sessions/{session_id}/months/2/decision",
                    payload=month2_body,
                    idempotency_key=month2_key,
                )
                if through_b.headers.get("Idempotency-Replayed") != "true":
                    raise AssertionError("Cross-container same-key retry was not replayed")
                if through_a.json()["state_version"] != through_b.json()["state_version"]:
                    raise AssertionError("Cross-container replay did not return the committed version")

                conflict = _request(
                    client_b,
                    "POST",
                    f"/api/v1/sessions/{session_id}/months/2/decision",
                    payload={**month2_body, "payment": 1.0},
                    idempotency_key=month2_key,
                    expected_status=409,
                ).json()
                if conflict["error"]["code"] != "idempotency_conflict":
                    raise AssertionError(f"Expected idempotency conflict, got {conflict}")

                stale = _request(
                    client_b,
                    "POST",
                    f"/api/v1/sessions/{session_id}/months/2/decision",
                    payload={**month2_body, "payment": 2.0},
                    idempotency_key=f"phase6-stale-{run_id}",
                    expected_status=409,
                ).json()
                if stale["error"]["code"] != "concurrency_conflict":
                    raise AssertionError(f"Expected concurrency conflict, got {stale}")

                authoritative = _request(client_b, "GET", f"/api/v1/sessions/{session_id}").json()
                if authoritative["state_version"] != through_a.json()["state_version"]:
                    raise AssertionError("Container B did not observe container A's committed version")

        rows = supabase.table("month_results").select("month_number").eq("session_id", session_id).execute().data
        if sorted(row["month_number"] for row in rows or []) != [1, 2]:
            raise AssertionError("Structured ledger did not contain exactly months 1 and 2")
        print("container_restart=passed")
        print("multi_container_visibility=passed")
        print("cross_container_idempotency=passed")
        print("cross_container_stale_conflict=passed")
        print("structured_month_ledger=passed")
        print(f"synthetic_session_id={session_id}")
    finally:
        _remove_container(args.docker, container_a)
        _remove_container(args.docker, container_b)
        if session_id:
            _cleanup(supabase, session_id, account_key)
        reset_shared_client()


if __name__ == "__main__":
    main()
