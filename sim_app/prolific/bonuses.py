"""One-time Prolific performance-bonus payments."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sim_app.infra.secrets import _get_secret
from sim_app.infra.time import _utcnow


PROLIFIC_API_BASE = "https://api.prolific.com/api/v1"
PROLIFIC_USER_AGENT = "ScenariuCredit/1.0 (Prolific API integration)"


def bonus_creation_configured():
    return bool(_get_secret("PROLIFIC_API_TOKEN"))


def create_bonus_payment(study_id, submission_id, amount_gbp):
    payload = {
        "study_id": str(study_id),
        "csv_bonuses": f"{submission_id},{float(amount_gbp):.2f}\n",
    }
    return _request("POST", "/submissions/bonus-payments/", payload)


def process_prolific_bonus(client, session_id, summary, *, metrics=None):
    """Create a reviewable Prolific bonus after an atomic durable claim.

    This never pays or completes a submission through the API. A retry never
    repeats bonus creation. An observed ``processing``
    claim means a previous worker may already have contacted Prolific, so the
    session is moved to manual review for safe reconciliation.
    """
    if not summary.get("prolific_pid") or not summary.get("prolific_study_id") or not summary.get("prolific_session_id"):
        return {"prolific_bonus_status": "not_applicable"}
    payment_request_id = summary.get("payment_idempotency_key")
    if not payment_request_id:
        raise RuntimeError("Finalization did not create a durable payment idempotency key")
    if not bonus_creation_configured():
        _finish_payment(
            client,
            session_id,
            payment_request_id,
            attempt_status="not_configured",
            bonus_status="not_configured",
            error="Prolific bonus creation is not configured",
            metrics=metrics,
        )
        return {"prolific_bonus_status": "not_configured"}

    claim = _rpc_data(
        client,
        "claim_prolific_payment_v3",
        {"p_session_id": session_id, "p_request_id": payment_request_id},
        metrics=metrics,
    )
    if not claim.get("claimed"):
        if claim.get("status") == "processing":
            _finish_payment(
                client,
                session_id,
                payment_request_id,
                attempt_status="manual_review",
                bonus_status="manual_review",
                error="Recovered an in-flight payment with an uncertain external outcome",
                metrics=metrics,
            )
        return {}

    bonus = float(summary.get("performance_bonus_gbp") or 0)
    try:
        created = create_bonus_payment(
            summary["prolific_study_id"],
            summary["prolific_session_id"],
            bonus,
        )
        payment_id = created.get("id")
        if not payment_id:
            raise RuntimeError("Prolific did not return a bonus payment ID")
    except (HTTPError, URLError, RuntimeError, ValueError) as exc:
        error = _error_detail(exc)
        _finish_payment(
            client,
            session_id,
            payment_request_id,
            attempt_status="manual_review",
            bonus_status="manual_review",
            error=error,
            metrics=metrics,
        )
        return {"prolific_bonus_status": "manual_review", "prolific_bonus_error": error}

    created_at = _utcnow()
    _finish_payment(
        client,
        session_id,
        payment_request_id,
        attempt_status="succeeded",
        bonus_status="awaiting_approval",
        response=created,
        created_at=created_at,
        metrics=metrics,
    )
    return {
        "prolific_bonus_status": "awaiting_approval",
        "prolific_bonus_created_at": created_at,
        "prolific_bonus_payment_id": payment_id,
    }


def _finish_payment(
    client,
    session_id,
    request_id,
    *,
    attempt_status,
    bonus_status,
    error=None,
    response=None,
    created_at=None,
    metrics=None,
):
    return _rpc_data(
        client,
        "finish_prolific_payment_v3",
        {
            "p_session_id": session_id,
            "p_request_id": request_id,
            "p_attempt_status": attempt_status,
            "p_bonus_status": bonus_status,
            "p_payment_status": "manual_review",
            "p_error": str(error)[:1000] if error else None,
            "p_response": response,
            "p_created_at": created_at,
        },
        metrics=metrics,
    )


def _rpc_data(client, name, params, *, metrics=None):
    if metrics is None:
        response = client.rpc(name, params).execute()
    else:
        with metrics.measure(name, layer="database"):
            metrics.increment("database_request_count")
            metrics.increment(f"database.{name}.request_count")
            response = client.rpc(name, params).execute()
    data = getattr(response, "data", None)
    if isinstance(data, list):
        data = data[0] if data else {}
    return data or {}


def _error_detail(exc):
    if isinstance(exc, HTTPError):
        try:
            body = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:
            body = ""
        if body:
            return f"HTTP {exc.code}: {body}"[:1000]
    return str(exc)[:1000]


def _request(method, path, payload):
    token = _get_secret("PROLIFIC_API_TOKEN")
    request = Request(
        f"{PROLIFIC_API_BASE}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Token {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Referer": _get_secret("PROLIFIC_INTEGRATION_URL") or _get_secret("PUBLIC_ORIGIN") or "http://localhost:8000/",
            "User-Agent": PROLIFIC_USER_AGENT,
        },
        method=method,
    )
    with urlopen(request, timeout=20) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else {}


__all__ = [
    "bonus_creation_configured",
    "create_bonus_payment",
    "process_prolific_bonus",
]
