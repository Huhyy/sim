"""Prolific URL identity and deterministic condition assignment."""

import hashlib
from urllib.parse import quote_plus

from sim_app.domain.experimental_conditions import condition_config, condition_options
from sim_app.infra.secrets import _get_secret
from sim_app.session.query_params import get_query_param


PROLIFIC_QUERY_PARAMS = ("PROLIFIC_PID", "STUDY_ID", "SESSION_ID")


def load_prolific_params():
    return {
        name: _clean(get_query_param(name))
        for name in PROLIFIC_QUERY_PARAMS
    }


def has_any_prolific_param(params=None):
    params = params or load_prolific_params()
    return any(params.get(name) for name in PROLIFIC_QUERY_PARAMS)


def prolific_params_complete(params=None):
    params = params or load_prolific_params()
    return all(params.get(name) for name in PROLIFIC_QUERY_PARAMS)


def assign_prolific_condition(prolific_pid, study_id):
    key = f"{prolific_pid}-{study_id}"
    value = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)
    condition = condition_options()[value % len(condition_options())]
    return condition_config(condition)


def completion_redirect_url(completion_code=None):
    template = _get_secret("PROLIFIC_COMPLETION_URL")
    if not template:
        return None
    code = completion_code or _get_secret("PROLIFIC_COMPLETION_CODE") or ""
    if "{completion_code}" in template:
        return template.replace("{completion_code}", quote_plus(code))
    return template


def configured_completion_code():
    return _get_secret("PROLIFIC_COMPLETION_CODE")


def prolific_study_allowed(study_id):
    raw = _get_secret("PROLIFIC_ALLOWED_STUDY_IDS")
    if not raw:
        return True
    allowed = {
        item.strip()
        for item in str(raw).replace(";", ",").split(",")
        if item.strip()
    }
    return str(study_id or "").strip() in allowed


def _clean(value):
    value = str(value or "").strip()
    return value or None
