import hashlib
import hmac
import os

import streamlit as st


def _get_secret(name):
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name)


def is_logged_in():
    try:
        return bool(st.user.is_logged_in)
    except Exception:
        return False


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
