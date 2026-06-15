"""Application configuration and feature flags."""

import os

import streamlit as st


def _feature_flag(name, default):
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = os.getenv(name, default)
    return str(value).lower() == "true"


REPEAT_SCENARIO_DEV_MODE = _feature_flag("ALLOW_REPEAT_PARTICIPATION", "true")
SCENARIO_VERSION = "income-baseline-1000-720-initial-150"


__all__ = [
    "_feature_flag",
    "REPEAT_SCENARIO_DEV_MODE",
    "SCENARIO_VERSION",
]
