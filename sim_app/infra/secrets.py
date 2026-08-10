"""Framework-neutral secret lookup with an injectable host adapter."""

import os
from threading import RLock


_provider = None
_provider_lock = RLock()


def configure_secret_provider(provider):
    global _provider
    with _provider_lock:
        _provider = provider


def _get_secret(name: str):
    with _provider_lock:
        provider = _provider
    if provider is not None:
        try:
            value = provider(name)
            if value is not None and value != "":
                return value
        except Exception:
            pass
    return os.getenv(name)


def _first_secret(*names):
    for name in names:
        value = _get_secret(name)
        if value:
            return value
    return None


__all__ = [
    "_first_secret",
    "_get_secret",
    "configure_secret_provider",
]
