"""One-time Prolific performance-bonus payments."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sim_app.infra.secrets import _get_secret
from sim_app.infra.time import _utcnow


PROLIFIC_API_BASE = "https://api.prolific.com/api/v1"


def autopay_configured():
    token = _get_secret("PROLIFIC_API_TOKEN")
    enabled = str(_get_secret("PROLIFIC_BONUS_AUTOPAY_ENABLED") or "true").lower()
    return bool(token) and enabled not in {"0", "false", "no", "off"}


def dynamic_payment_configured():
    token = _get_secret("PROLIFIC_API_TOKEN")
    enabled = str(_get_secret("PROLIFIC_DYNAMIC_PAYMENT_ENABLED") or "true").lower()
    return bool(token) and enabled not in {"0", "false", "no", "off"}


def create_bonus_payment(study_id, submission_id, amount_gbp):
    payload = {
        "study_id": str(study_id),
        "csv_bonuses": f"{submission_id},{float(amount_gbp):.2f}\n",
    }
    return _request("POST", "/submissions/bonus-payments/", payload)


def pay_bonus_payment(payment_id):
    return _request("POST", f"/bulk-bonus-payments/{payment_id}/pay/", {})


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


def process_prolific_bonus(client, session_id, summary):
    """Complete a Prolific submission with its performance-based dynamic reward."""
    if not summary.get("prolific_pid") or not summary.get("prolific_study_id") or not summary.get("prolific_session_id"):
        return {"prolific_bonus_status": "not_applicable"}
    if not dynamic_payment_configured():
        return {"prolific_bonus_status": "not_configured"}

    claim = (
        client.table("session_summaries")
        .update({"prolific_bonus_status": "processing", "updated_at": _utcnow()})
        .eq("session_id", session_id)
        .eq("prolific_bonus_status", "pending")
        .select("session_id")
        .execute()
    )
    if not (getattr(claim, "data", None) or []):
        return {}

    completion_code = summary.get("completion_code") or _get_secret("PROLIFIC_COMPLETION_CODE")
    if not completion_code:
        error = "PROLIFIC_COMPLETION_CODE is not configured"
        _mark_manual_review(client, session_id, error)
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
        _mark_manual_review(client, session_id, error)
        return {"prolific_bonus_status": "manual_review", "prolific_bonus_error": error}

    created_at = _utcnow()
    prolific_status = str(completed.get("status") or "").upper()
    client.table("session_summaries").update(
        {
            "prolific_bonus_status": "awaiting_approval",
            "payment_status": "manual_review",
            "prolific_bonus_created_at": created_at,
            "prolific_bonus_error": None,
            "updated_at": created_at,
        }
    ).eq("session_id", session_id).execute()
    return {
        "prolific_bonus_status": "awaiting_approval",
        "prolific_bonus_created_at": created_at,
        "prolific_submission_status": prolific_status,
    }


def _mark_manual_review(client, session_id, error):
    client.table("session_summaries").update(
        {
            "payment_status": "manual_review",
            "prolific_bonus_status": "manual_review",
            "prolific_bonus_error": str(error)[:1000],
            "updated_at": _utcnow(),
        }
    ).eq("session_id", session_id).execute()


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
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urlopen(request, timeout=20) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else {}


__all__ = [
    "autopay_configured",
    "complete_with_dynamic_payment",
    "create_bonus_payment",
    "dynamic_payment_configured",
    "dynamic_reward_percentage",
    "pay_bonus_payment",
    "process_prolific_bonus",
]
