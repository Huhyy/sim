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


def current_user_email():
    if not is_logged_in():
        return None

    email = st.user.get("email")
    if not email:
        return None
    return str(email).strip().lower()


def _parse_admin_emails(raw_value):
    if not raw_value:
        return set()

    if isinstance(raw_value, str):
        parts = raw_value.replace(";", ",").split(",")
        return {part.strip().lower() for part in parts if part.strip()}

    if isinstance(raw_value, (list, tuple, set)):
        return {str(part).strip().lower() for part in raw_value if str(part).strip()}

    return set()


def admin_emails():
    return _parse_admin_emails(_get_secret("ADMIN_EMAILS"))


def is_admin_user():
    email = current_user_email()
    if not email:
        return False
    return email in admin_emails()


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
