"""In-memory admin repository for transport and browser tests."""

from __future__ import annotations

import uuid


class MemoryAdminRepository:
    def __init__(self):
        self.sessions = []
        self.participants = {}

    def create_study_session(self, created_by_email, experimental_condition):
        row = {
            "id": str(uuid.uuid4()),
            "session_code": f"{len(self.sessions) + 1:06d}",
            "created_by_email": created_by_email,
            "experimental_condition": experimental_condition,
            "status": "active",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        self.sessions.insert(0, row)
        return dict(row)

    def list_study_sessions(self, created_by_email):
        return [dict(row) for row in self.sessions if row["created_by_email"] == created_by_email and row["status"] == "active"]

    def list_participants(self, study_session_id, study_session_code):
        del study_session_code
        return [dict(row) for row in self.participants.get(study_session_id, [])]

    def cancel_study_session(self, session_id, created_by_email):
        for row in self.sessions:
            if row["id"] == session_id and row["created_by_email"] == created_by_email and row["status"] == "active":
                row["status"] = "cancelled"
                return dict(row)
        return None


__all__ = ["MemoryAdminRepository"]
