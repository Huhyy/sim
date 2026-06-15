"""Authenticated user identity helpers.

Participant identity and study session identity are intentionally separate:
``current_account_key`` identifies the logged-in account, while session IDs
identify individual simulation attempts.
"""

import hashlib
import hmac
import os

import streamlit as st


def _get_secret(name):
    try:
        if name in st.secrets:
            value = st.secrets[name]
            if value is not None:
                return value
        value = st.secrets.get(name)
        if value is not None:
            return value
        auth_section = st.secrets.get("auth")
        if auth_section and name in auth_section:
            value = auth_section[name]
            if value is not None:
                return value
        admin_section = st.secrets.get("admin")
        if admin_section and name in admin_section:
            value = admin_section[name]
            if value is not None:
                return value
    except Exception:
        pass
    return os.getenv(name)


def is_logged_in():
    try:
        return bool(st.user.is_logged_in)
    except Exception:
        return False


def current_user_email():
    if not is_logged_in():
        return None

    email = st.user.get("email")
    if not email:
        return None
    return str(email).strip().lower()


def current_account_key():
    if not is_logged_in():
        return None

    subject = st.user.get("sub")
    if not subject:
        raise RuntimeError("Google authentication did not return a stable subject identifier.")

    pepper = _get_secret("ACCOUNT_KEY_PEPPER")
    if not pepper:
        raise RuntimeError("Set ACCOUNT_KEY_PEPPER in Streamlit secrets before enabling Google login.")

    issuer = st.user.get("iss", "google")
    identity = f"{issuer}|{subject}".encode("utf-8")
    return hmac.new(str(pepper).encode("utf-8"), identity, hashlib.sha256).hexdigest()


__all__ = [
    "_get_secret",
    "current_account_key",
    "current_user_email",
    "is_logged_in",
]
