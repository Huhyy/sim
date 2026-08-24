"""Narrow, authorization-aware admin use cases and safe monitoring views."""

from __future__ import annotations

from sim_app.application.errors import AuthenticationRequired, InputValidationError, SessionAccessDenied
from sim_app.application.principal import ParticipantPrincipal
from sim_app.content.questions import POST_SECTIONS, PRE_SECTIONS
from sim_app.content.translations import get_ui_section
from sim_app.domain.experimental_conditions import condition_options


class AdminService:
    def __init__(self, repository):
        self.repository = repository

    def list_sessions(self, principal: ParticipantPrincipal):
        email = self._require_admin(principal)
        rows = self.repository.list_study_sessions(email)
        return [self._session_view(row) for row in rows]

    def list_participant_results(self, principal: ParticipantPrincipal):
        self._require_admin(principal)
        return [_participant_result_view(row) for row in self.repository.list_all_participant_results()]

    def localized_content(self, principal: ParticipantPrincipal, *, language: str):
        self._require_admin(principal)
        if language not in {"en", "ro"}:
            raise InputValidationError("Language must be en or ro")
        return get_ui_section("admin", language)

    def create_session(self, principal: ParticipantPrincipal, *, experimental_condition: str):
        email = self._require_admin(principal)
        if experimental_condition not in condition_options():
            raise InputValidationError("Experimental condition must be C1, C2, C3, or C4")
        return self._session_view(self.repository.create_study_session(email, experimental_condition))

    def cancel_session(self, principal: ParticipantPrincipal, *, session_id: str):
        email = self._require_admin(principal)
        cancelled = self.repository.cancel_study_session(session_id, email)
        if not cancelled:
            raise InputValidationError("The active study session could not be cancelled")
        return {"id": str(cancelled["id"]), "status": "cancelled"}

    def _session_view(self, row):
        participants = self.repository.list_participants(row.get("id"), row.get("session_code"))
        return {
            "id": str(row.get("id")),
            "session_code": str(row.get("session_code") or ""),
            "experimental_condition": row.get("experimental_condition") or "C1",
            "status": row.get("status") or "active",
            "created_at": row.get("created_at"),
            "participants": [_participant_view(item) for item in participants],
        }

    @staticmethod
    def _require_admin(principal):
        if not isinstance(principal, ParticipantPrincipal) or not principal.account_key:
            raise AuthenticationRequired("Administrator authentication is required")
        if not principal.is_admin or not principal.email:
            raise SessionAccessDenied("Administrator authorization is required")
        return principal.email.strip().lower()


def _participant_view(row):
    page = _participant_page(row)
    month = _participant_month(row)
    summary = row.get("summary") or {}
    payout = None
    if summary.get("final_score") is not None and summary.get("performance_bonus_gbp") is not None:
        performance = float(summary["performance_bonus_gbp"])
        payout = {
            "final_score": float(summary["final_score"]),
            "performance_bonus_gbp": performance,
            "total_payout_gbp": float(summary.get("total_payout_gbp") or (5 + performance)),
            "payment_status": summary.get("payment_status") or "unpaid",
            "prolific_bonus_status": summary.get("prolific_bonus_status") or "not_applicable",
        }
    return {
        "participant_code": row.get("participant_code"),
        "stage": _participant_stage(page),
        "page_label": f"{page} - month {month}" if page in {"simulation", "month_feedback"} else page,
        "progress_percent": _progress(page, month),
        "status": row.get("status") or "in_progress",
        "payout": payout,
        "updated_at": row.get("updated_at"),
    }


def _participant_result_view(row):
    summary = row.get("summary") or {}
    prolific_pid = row.get("prolific_pid") or summary.get("prolific_pid")
    is_prolific = bool(prolific_pid)
    identifier = row.get("participant_code") or prolific_pid
    return {
        "participant_code": row.get("participant_code"),
        "prolific_pid": str(prolific_pid) if prolific_pid else None,
        "participant_identifier": str(identifier or ""),
        "session_code": str(row.get("session_code") or ""),
        "final_score": _float_or_none(summary.get("final_score")),
        "performance_bonus_gbp": _float_or_none(summary.get("performance_bonus_gbp")),
        "payout_gbp": _float_or_none(summary.get("total_payout_gbp")) if is_prolific else None,
        "status": row.get("status") or "in_progress",
        "updated_at": row.get("updated_at"),
    }


def _float_or_none(value):
    return float(value) if value is not None else None


def _participant_page(row):
    if row.get("status") == "completed":
        return "done"
    checkpoint = row.get("checkpoint") or {}
    return checkpoint.get("page") or row.get("current_page") or "unknown"


def _participant_month(row):
    try:
        return int((row.get("checkpoint") or {}).get("month") or 1)
    except (TypeError, ValueError):
        return 1


def _participant_stage(page):
    if page.startswith("post_question_") or page in {"final_score", "done"}:
        return "post"
    if page in {"instructions", "profile", "simulation", "month_feedback"}:
        return "months"
    return "pre"


def _progress(page, month):
    if page == "done": return 100
    if page == "final_score": return 96
    if page.startswith("post_question_"):
        return min(95, 82 + int(((_page_index(page) + 1) / max(1, len(POST_SECTIONS))) * 12))
    if page == "month_feedback": return min(80, 30 + int((max(1, month) / 24) * 50))
    if page == "simulation": return min(78, 30 + int(((max(1, month) - 1) / 24) * 50))
    if page == "profile": return 30
    if page == "instructions": return 27
    if page.startswith("pre_question_"):
        return min(25, 14 + int(((_page_index(page) + 1) / max(1, len(PRE_SECTIONS))) * 11))
    if page == "demographics": return 12
    if page == "consent": return 8
    if page == "home": return 5
    return 3


def _page_index(page):
    try: return int(str(page).rsplit("_", 1)[1])
    except (IndexError, TypeError, ValueError): return 0


__all__ = ["AdminService"]
