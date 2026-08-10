"""Process-level composition for the shared experiment service."""

from threading import RLock

from sim_app.application.services import ExperimentService
from sim_app.persistence.experiment_repository import SupabaseExperimentRepository
from sim_app.persistence.payment_processor import SupabaseProlificPaymentProcessor


_lock = RLock()
_service = None


def get_experiment_service():
    global _service
    with _lock:
        if _service is None:
            repository = SupabaseExperimentRepository()
            _service = ExperimentService(
                repository,
                payment_processor=SupabaseProlificPaymentProcessor(repository),
            )
        return _service


def set_experiment_service(service):
    global _service
    with _lock:
        _service = service


__all__ = ["get_experiment_service", "set_experiment_service"]
