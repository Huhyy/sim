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


def create_bonus_payment(study_id, submission_id, amount_gbp):
    payload = {
        "study_id": str(study_id),
        "csv_bonuses": f"{submission_id},{float(amount_gbp):.2f}\n",
    }
    return _request("POST", "/submissions/bonus-payments/", payload)


def pay_bonus_payment(payment_id):
    return _request("POST", f"/bulk-bonus-payments/{payment_id}/pay/", {})


def process_prolific_bonus(client, session_id, summary):
    """Claim, create, and pay one bonus; never retry an ambiguous payment."""
    if not summary.get("prolific_pid") or not summary.get("prolific_study_id") or not summary.get("prolific_session_id"):
        return {"prolific_bonus_status": "not_applicable"}
    if not autopay_configured():
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

    amount = float(summary.get("performance_bonus_gbp") or 0)
    try:
        created = create_bonus_payment(
            summary["prolific_study_id"],
            summary["prolific_session_id"],
            amount,
        )
        payment_id = created.get("id")
        if not payment_id:
            raise RuntimeError("Prolific did not return a bonus payment ID")
        pay_bonus_payment(payment_id)
    except (HTTPError, URLError, RuntimeError, ValueError) as exc:
        error = str(exc)[:1000]
        client.table("session_summaries").update(
            {
                "payment_status": "manual_review",
                "prolific_bonus_status": "manual_review",
                "prolific_bonus_error": error,
                "updated_at": _utcnow(),
            }
        ).eq("session_id", session_id).execute()
        return {"prolific_bonus_status": "manual_review", "prolific_bonus_error": error}

    paid_at = _utcnow()
    client.table("session_summaries").update(
        {
            "prolific_bonus_status": "paid",
            "payment_status": "paid",
            "prolific_bonus_payment_id": payment_id,
            "prolific_bonus_created_at": paid_at,
            "prolific_bonus_paid_at": paid_at,
            "updated_at": paid_at,
        }
    ).eq("session_id", session_id).execute()
    return {
        "prolific_bonus_status": "paid",
        "prolific_bonus_payment_id": payment_id,
        "prolific_bonus_created_at": paid_at,
        "prolific_bonus_paid_at": paid_at,
    }


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
    "create_bonus_payment",
    "pay_bonus_payment",
    "process_prolific_bonus",
]
