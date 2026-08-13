"""Framework-neutral Prolific launch configuration and validation."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import quote_plus

from sim_app.domain.experimental_conditions import assign_prolific_condition, condition_options
from sim_app.infra.secrets import _get_secret


PROLIFIC_QUERY_PARAMS = ("PROLIFIC_PID", "STUDY_ID", "SESSION_ID")


def normalize_prolific_params(values: Mapping[str, object] | None) -> dict[str, str | None]:
    values = values or {}
    return {name: _clean(values.get(name)) for name in PROLIFIC_QUERY_PARAMS}


def has_any_prolific_param(params: Mapping[str, object] | None = None) -> bool:
    return any(normalize_prolific_params(params).values())


def prolific_params_complete(params: Mapping[str, object] | None = None) -> bool:
    return all(normalize_prolific_params(params).values())


def completion_redirect_url(completion_code=None):
    template = _get_secret("PROLIFIC_COMPLETION_URL")
    code = completion_code or _get_secret("PROLIFIC_COMPLETION_CODE") or ""
    if not template:
        if not code:
            return None
        return f"https://app.prolific.com/submissions/complete?cc={quote_plus(code)}"
    if "{completion_code}" in template:
        return template.replace("{completion_code}", quote_plus(code))
    return template


def configured_completion_code():
    return _get_secret("PROLIFIC_COMPLETION_CODE")


def _clean(value):
    value = str(value or "").strip()
    return value or None


__all__ = [
    "PROLIFIC_QUERY_PARAMS",
    "assign_prolific_condition",
    "completion_redirect_url",
    "condition_options",
    "configured_completion_code",
    "has_any_prolific_param",
    "normalize_prolific_params",
    "prolific_params_complete",
]
