"""Prolific URL identity and deterministic condition assignment."""

import hashlib
import json
from urllib.parse import quote_plus, unquote

import streamlit as st

from sim_app.domain.experimental_conditions import condition_config, condition_options
from sim_app.infra.secrets import _get_secret
from sim_app.session.query_params import get_query_param


PROLIFIC_QUERY_PARAMS = ("PROLIFIC_PID", "STUDY_ID", "SESSION_ID")
_PROLIFIC_COOKIE_PREFIX = "sim_prolific_"


def load_prolific_params():
    stored = st.session_state.get("_prolific_params") or {}
    cookies = _browser_cookie_params()
    params = {
        name: _clean(get_query_param(name)) or _clean(stored.get(name)) or _clean(cookies.get(name))
        for name in PROLIFIC_QUERY_PARAMS
    }
    if any(params.values()):
        st.session_state._prolific_params = params
        _remember_in_browser(params)
    return params


def _browser_cookie_params():
    try:
        cookies = st.context.cookies
    except Exception:
        return {}
    return {
        name: unquote(cookies.get(f"{_PROLIFIC_COOKIE_PREFIX}{name}"))
        for name in PROLIFIC_QUERY_PARAMS
        if cookies.get(f"{_PROLIFIC_COOKIE_PREFIX}{name}")
    }


def _remember_in_browser(params):
    values = {
        name: str(params.get(name) or "")
        for name in PROLIFIC_QUERY_PARAMS
        if params.get(name)
    }
    if not values:
        return
    assignments = "".join(
        "window.top.document.cookie = %s + encodeURIComponent(%s) + '; Path=/; Max-Age=1800; SameSite=Lax';"
        % (json.dumps(f"{_PROLIFIC_COOKIE_PREFIX}{name}="), json.dumps(value))
        for name, value in values.items()
    )
    try:
        st.components.v1.html(
            f"<script>try {{ {assignments} }} catch (e) {{}}</script>",
            height=0,
        )
    except Exception:
        pass


def clear_browser_prolific_params():
    assignments = "".join(
        "window.top.document.cookie = %s + '=; Path=/; Max-Age=0; SameSite=Lax';"
        % json.dumps(f"{_PROLIFIC_COOKIE_PREFIX}{name}")
        for name in PROLIFIC_QUERY_PARAMS
    )
    try:
        st.components.v1.html(f"<script>try {{ {assignments} }} catch (e) {{}}</script>", height=0)
    except Exception:
        pass


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
