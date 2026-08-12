"""Transport-neutral composition for the experiment application service."""

from threading import RLock

from sim_app.application.services import ExperimentService
from sim_app.application.admin_services import AdminService
from sim_app.persistence.admin_repository import SupabaseAdminRepository
from sim_app.persistence.experiment_repository import SupabaseExperimentRepository
from sim_app.persistence.payment_processor import SupabaseProlificPaymentProcessor


_lock = RLock()
_service = None
_admin_service = None


def get_experiment_service():
    """Return the process-level service over thread-local Supabase resources."""
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
    """Override composition for tests and controlled transport adapters."""
    global _service
    with _lock:
        _service = service


def get_admin_service():
    global _admin_service
    with _lock:
        if _admin_service is None:
            _admin_service = AdminService(SupabaseAdminRepository())
        return _admin_service


def set_admin_service(service):
    global _admin_service
    with _lock:
        _admin_service = service


__all__ = ["get_admin_service", "get_experiment_service", "set_admin_service", "set_experiment_service"]
