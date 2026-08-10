"""Durably claimed Prolific side-effect coordinator."""

from sim_app.application.errors import ExperimentError, PersistenceReadError, PersistenceWriteError
from sim_app.prolific.bonuses import process_prolific_bonus


class SupabaseProlificPaymentProcessor:
    def __init__(self, repository):
        self.repository = repository

    def process(self, state, *, request_id):
        del request_id  # The durable payment key is created by finalization RPC.
        if not state.prolific_pid:
            return state
        try:
            with self.repository.metrics.measure("load_payment_summary", layer="database"):
                self.repository.metrics.increment("database_request_count")
                self.repository.metrics.increment("database.load_payment_summary.request_count")
                response = (
                    self.repository.client.table("session_summaries")
                    .select("*")
                    .eq("session_id", state.session_id)
                    .limit(1)
                    .execute()
                )
            rows = getattr(response, "data", None) or []
            if not rows:
                raise PersistenceReadError("Finalized session summary could not be loaded for payment processing")
            process_prolific_bonus(
                self.repository.client,
                state.session_id,
                rows[0],
                metrics=self.repository.metrics,
            )
            return self.repository.load(state.session_id)
        except ExperimentError:
            raise
        except Exception as exc:
            raise PersistenceWriteError(
                "Internal finalization committed, but payment-state processing must be retried"
            ) from exc


__all__ = ["SupabaseProlificPaymentProcessor"]
