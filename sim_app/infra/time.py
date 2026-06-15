"""Time helpers for persistence rows."""

from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "_utcnow",
]
