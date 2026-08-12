"""Supabase implementation of the narrow admin persistence contract."""

from sim_app.persistence.study_sessions import (
    cancel_admin_study_session,
    create_admin_study_session,
    list_admin_study_sessions,
    list_participant_sessions_for_study_session,
)


class SupabaseAdminRepository:
    def create_study_session(self, created_by_email, experimental_condition):
        return create_admin_study_session(created_by_email, experimental_condition)

    def list_study_sessions(self, created_by_email):
        return list_admin_study_sessions(created_by_email)

    def list_participants(self, study_session_id, study_session_code):
        return list_participant_sessions_for_study_session(study_session_id, study_session_code)

    def cancel_study_session(self, session_id, created_by_email):
        return cancel_admin_study_session(session_id, created_by_email)


__all__ = ["SupabaseAdminRepository"]
