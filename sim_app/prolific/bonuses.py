"""One-time Prolific performance-bonus payments."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sim_app.infra.secrets import _get_secret
from sim_app.infra.time import _utcnow


PROLIFIC_API_BASE = "https://api.prolific.com/api/v1"
PROLIFIC_USER_AGENT = "ScenariuCredit/1.0 (Prolific API integration)"


def dynamic_payment_configured():
    token = _get_secret("PROLIFIC_API_TOKEN")
    enabled = str(_get_secret("PROLIFIC_DYNAMIC_PAYMENT_ENABLED") or "true").lower()
    return bool(token) and enabled not in {"0", "false", "no", "off"}


def dynamic_reward_percentage(base_reward_gbp, performance_bonus_gbp):
    base_reward = float(base_reward_gbp or 0)
    if base_reward <= 0:
        raise ValueError("Prolific base reward must be greater than zero")
    total_reward = base_reward + float(performance_bonus_gbp or 0)
    return round(total_reward / base_reward * 100, 2)


def complete_with_dynamic_payment(submission_id, completion_code, percentage_of_reward, message):
    payload = {
        "action": "COMPLETE",
        "completion_code": str(completion_code),
        "completion_code_data": {
            "percentage_of_reward": float(percentage_of_reward),
            "message_to_participant": str(message),
        },
    }
    return _request("POST", f"/submissions/{submission_id}/transition/", payload)


def process_prolific_bonus(client, session_id, summary, *, metrics=None):
    """Complete a Prolific submission after an atomic durable payment claim.

    A retry never repeats the external transition.  An observed ``processing``
    claim means a previous worker may already have contacted Prolific, so the
    session is moved to manual review for safe reconciliation.
    """
    if not summary.get("prolific_pid") or not summary.get("prolific_study_id") or not summary.get("prolific_session_id"):
        return {"prolific_bonus_status": "not_applicable"}
    payment_request_id = summary.get("payment_idempotency_key")
    if not payment_request_id:
        raise RuntimeError("Finalization did not create a durable payment idempotency key")
    if not dynamic_payment_configured():
        _finish_payment(
            client,
            session_id,
            payment_request_id,
            attempt_status="not_configured",
            bonus_status="not_configured",
            error="Prolific dynamic payment is not configured",
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

    completion_code = summary.get("completion_code") or _get_secret("PROLIFIC_COMPLETION_CODE")
    if not completion_code:
        error = "PROLIFIC_COMPLETION_CODE is not configured"
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

    base_reward = float(summary.get("prolific_base_reward_gbp") or 5)
    bonus = float(summary.get("performance_bonus_gbp") or 0)
    percentage = dynamic_reward_percentage(base_reward, bonus)
    message = f"Performance reward: {base_reward:g} GBP base payment plus {bonus:g} GBP performance bonus."
    try:
        completed = complete_with_dynamic_payment(
            summary["prolific_session_id"],
            completion_code,
            percentage,
            message,
        )
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
    prolific_status = str(completed.get("status") or "").upper()
    _finish_payment(
        client,
        session_id,
        payment_request_id,
        attempt_status="succeeded",
        bonus_status="awaiting_approval",
        response=completed,
        created_at=created_at,
        metrics=metrics,
    )
    return {
        "prolific_bonus_status": "awaiting_approval",
        "prolific_bonus_created_at": created_at,
        "prolific_submission_status": prolific_status,
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
    "complete_with_dynamic_payment",
    "dynamic_payment_configured",
    "dynamic_reward_percentage",
    "process_prolific_bonus",
]
