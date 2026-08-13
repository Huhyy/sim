"""Server-side verification for Prolific launch parameters."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from sim_app.application.errors import ProlificLaunchError
from sim_app.infra.secrets import _get_secret


PROLIFIC_API_BASE = "https://api.prolific.com/api/v1"
PROLIFIC_USER_AGENT = "ScenariuCredit/1.0 (Prolific API integration)"


def verify_prolific_submission(*, submission_id: str, participant_id: str, study_id: str) -> dict:
    """Verify the complete launch tuple against Prolific's submission record.

    URL parameters are browser input and are not trusted until Prolific confirms
    that the submission belongs to the supplied participant and study.
    """

    token = _get_secret("PROLIFIC_API_TOKEN")
    if not token:
        raise ProlificLaunchError("Prolific launch verification is not configured")

    submission = _get_json(
        f"/submissions/{quote(str(submission_id), safe='')}/",
        token=token,
    )
    if not isinstance(submission, dict):
        raise ProlificLaunchError("Prolific returned an invalid submission record")
    if (
        str(submission.get("id") or "") != str(submission_id)
        or str(submission.get("participant") or "") != str(participant_id)
        or str(submission.get("study_id") or "") != str(study_id)
    ):
        raise ProlificLaunchError("The Prolific launch identity did not match its submission")

    study = _get_json(f"/studies/{quote(str(study_id), safe='')}/", token=token)
    if not isinstance(study, dict) or not _same_study_destination(
        study.get("external_study_url"),
        _get_secret("PUBLIC_ORIGIN"),
    ):
        raise ProlificLaunchError("This Prolific study is not configured for this application")
    return submission


def _get_json(path: str, *, token: str):
    request = Request(
        f"{PROLIFIC_API_BASE}{path}",
        headers={
            "Authorization": f"Token {token}",
            "Accept": "application/json",
            "User-Agent": PROLIFIC_USER_AGENT,
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise ProlificLaunchError("Prolific could not verify this study launch") from exc


def _same_study_destination(external_url, public_origin):
    try:
        external = urlsplit(str(external_url or ""))
        expected = urlsplit(str(public_origin or ""))
    except ValueError:
        return False
    return (
        external.scheme == expected.scheme
        and external.netloc == expected.netloc
        and external.path.rstrip("/") == expected.path.rstrip("/")
        and bool(expected.scheme and expected.netloc)
    )


__all__ = ["verify_prolific_submission"]
