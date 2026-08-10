"""Application-level persistence and transition errors."""


class ExperimentError(RuntimeError):
    pass


class SessionNotFound(ExperimentError):
    pass


class PersistenceReadError(ExperimentError):
    pass


class PersistenceWriteError(ExperimentError):
    pass


class ConcurrencyConflict(ExperimentError):
    def __init__(self, message="Participant state changed in another client", *, current_version=None):
        super().__init__(message)
        self.current_version = current_version


class IdempotencyConflict(ConcurrencyConflict):
    pass


class TreatmentConflict(ConcurrencyConflict):
    pass


class InvalidTransition(ExperimentError):
    pass


__all__ = [
    "ConcurrencyConflict",
    "ExperimentError",
    "IdempotencyConflict",
    "InvalidTransition",
    "PersistenceReadError",
    "PersistenceWriteError",
    "SessionNotFound",
    "TreatmentConflict",
]
