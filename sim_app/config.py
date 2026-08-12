"""Application configuration and feature flags."""

import os


def _feature_flag(name, default):
    value = os.getenv(name, default)
    return str(value).lower() == "true"


REPEAT_SCENARIO_DEV_MODE = _feature_flag("ALLOW_REPEAT_PARTICIPATION", "false")
PROLIFIC_MODE_ENABLED = _feature_flag("PROLIFIC_MODE_ENABLED", "true")
SCENARIO_VERSION = "income-baseline-1000-720-initial-150"


__all__ = [
    "_feature_flag",
    "PROLIFIC_MODE_ENABLED",
    "REPEAT_SCENARIO_DEV_MODE",
    "SCENARIO_VERSION",
]
