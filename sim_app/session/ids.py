"""Session ID helpers."""

import uuid


def new_session_id():
    return str(uuid.uuid4())


__all__ = [
    "new_session_id",
]

