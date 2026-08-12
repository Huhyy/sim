"""Admin authorization helpers."""

import ast

from sim_app.infra.secrets import _get_secret


def _parse_admin_emails(raw_value):
    if not raw_value:
        return set()

    if isinstance(raw_value, str):
        parsed = raw_value.strip()
        if parsed.startswith("[") and parsed.endswith("]"):
            try:
                loaded = ast.literal_eval(parsed)
                if isinstance(loaded, (list, tuple, set)):
                    return {str(part).strip().lower() for part in loaded if str(part).strip()}
            except Exception:
                parsed = parsed[1:-1]
        parts = parsed.replace(";", ",").split(",")
        cleaned = set()
        for part in parts:
            item = part.strip().strip('"').strip("'").lower()
            if item:
                cleaned.add(item)
        return cleaned

    if isinstance(raw_value, (list, tuple, set)):
        return {str(part).strip().lower() for part in raw_value if str(part).strip()}

    return set()


def admin_emails():
    return _parse_admin_emails(_get_secret("ADMIN_EMAILS"))


def configured_admin_emails_text():
    emails = sorted(admin_emails())
    if not emails:
        return "none"
    return ", ".join(emails)


def is_admin_email(email):
    if not email:
        return False
    return str(email).strip().lower() in admin_emails()


__all__ = [
    "_parse_admin_emails",
    "admin_emails",
    "configured_admin_emails_text",
    "is_admin_email",
]
