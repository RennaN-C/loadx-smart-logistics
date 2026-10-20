import uuid
from dataclasses import dataclass
from datetime import timedelta
from random import SystemRandom

from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PaginationParams, to_page_response
from app.integrations.outbox import (
    DeliveryEnvelope,
    OutboxTransport,
    PermanentDeliveryError,
    TransientDeliveryError,
)
from app.modules.deliveries.reference_service import DeliveryReferenceService
from app.modules.deliveries.service import TripService
from app.modules.drivers.service import DriverService
from app.modules.notifications.models import OperationalNotification
from app.modules.notifications.outbox_models import STATES, OutboxEvent
from app.modules.notifications.outbox_repository import OutboxRepository
from app.modules.notifications.repository import OperationalNotificationRepository
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService
from app.modules.users.service import UserService


@dataclass(frozen=True)
class Claim:
    event_id: uuid.UUID
    generation: int
    envelope: DeliveryEnvelope


def retry_delay(
    attempt: int, *, base_seconds: int, cap_seconds: int, jitter: float
) -> float:
    """Equal jitter: bounded [half, full] exponential delay, never a tight retry loop."""
    bound = min(cap_seconds, base_seconds * 2 ** min(max(attempt - 1, 0), 30))
    return bound * (0.5 + 0.5 * max(0, min(jitter, 1)))


class OutboxService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OutboxRepository(db)

    def stage(self, notification: OperationalNotification) -> None:
        self.repository.stage(notification)

    def _get(self, identifier: uuid.UUID, *, lock: bool = False) -> OutboxEvent:
        event = self.repository.get(identifier, lock=lock)
        if event is None:
            raise ApiError(404, "OUTBOX_NOT_FOUND", "Evento não encontrado.")
        return event

    def claim(self, lease_seconds: int) -> Claim | None:
        event = self.repository.next_due()
        if event is None:
            return None
        now = self.repository.now()
        if event.status == "PROCESSING":
            self._finish(event, "UNCERTAIN", "LEASE_EXPIRED", now)
            return None
        notification = OperationalNotificationRepository(self.db).get_for_update(
            event.notification_id
        )
        if event.generation == 0 and event.attempt_count == 0:
            if notification.mock_status != "NOT_ATTEMPTED":
                status, code = legacy_outcome(notification.mock_status)
                self.repository.legacy_attempt(event, notification, status, code)
                event.status, event.last_error_code, event.updated_at = (
                    status,
                    code,
                    now,
                )
                return None
            OperationalNotificationRepository(self.db).claim(notification.id)
        # Snapshot current authorized destination. Transaction ends before transport.
        trip = DeliveryReferenceService(self.db).get_trip_for_notification(
            notification.trip_id
        )
        driver = DriverService(self.db).get_driver_for_update(
            notification.recipient_driver_id
        )
        self.repository.begin_attempt(event, lease_seconds)
        if (
            trip is None
            or trip.driver_id != driver.id
            or not driver.active
            or not (driver.phone or "").strip()
        ):
            self._finish(event, "TERMINAL", "NO_RECIPIENT", now)
            return None
        content = (
            f"Viagem {notification.trip_id} iniciada."
            if notification.event_type == "TRIP_STARTED"
            else f"Ocorrência registrada na viagem {notification.trip_id}."
        )
        return Claim(
            event.id,
            event.generation,
            DeliveryEnvelope(driver.phone.strip(), content, event.idempotency_key),
        )

    def complete(
        self,
        claim: Claim,
        status: str,
        code: str | None,
        *,
        max_attempts: int,
        base_seconds: int,
        cap_seconds: int,
    ) -> bool:
        event = self._get(claim.event_id, lock=True)
        now = self.repository.now()
        if event.status != "PROCESSING" or event.generation != claim.generation:
            return False
        if event.lease_expires_at <= now:
            self._finish(event, "UNCERTAIN", "LEASE_EXPIRED", now)
            return False
        if status == "RETRYABLE":
            if event.attempt_count >= max_attempts:
                status, code = "TERMINAL", "EXHAUSTED"
            else:
                event.next_attempt_at = now + timedelta(
                    seconds=retry_delay(
                        event.attempt_count,
                        base_seconds=base_seconds,
                        cap_seconds=cap_seconds,
                        jitter=SystemRandom().random(),
                    )
                )
        self._finish(event, status, code, now)
        return True

    def _finish(self, event, status, code, now) -> None:
        attempt = self.repository.attempt(event)
        attempt.result, attempt.error_code, attempt.finished_at = status, code, now
        event.status, event.last_error_code, event.updated_at = status, code, now
        event.lease_expires_at = None
        # Only the first claim owned by this worker may complete the OC84 attempt.
        # Terminal OC84 states are never reopened by retries.
        if event.generation == 1 and status != "UNCERTAIN":
            legacy_status = "FAILED"
            if status == "SUCCEEDED":
                legacy_status = "SIMULATED"
            elif code == "NO_RECIPIENT":
                legacy_status = "NO_RECIPIENT"
            OperationalNotificationRepository(self.db).complete(
                event.notification_id, legacy_status
            )

    def list_events(self, pagination, **filters):
        from app.modules.notifications.outbox_schemas import EventRead

        result = self.repository.list(pagination, **filters)
        return to_page_response(
            result, [EventRead.model_validate(row) for row in result.items]
        )

    def summary(self):
        from app.modules.notifications.outbox_schemas import QueueSummary

        rows = self.repository.summary()
        return QueueSummary(
            counts={
                state: next((row[1] for row in rows if row[0] == state), 0)
                for state in STATES
            },
            oldest_pending_at=min(
                (row[2] for row in rows if row[0] in {"PENDING", "RETRYABLE"}),
                default=None,
            ),
        )

    def detail(self, identifier):
        from app.modules.notifications.outbox_schemas import EventRead

        return EventRead.model_validate(self._get(identifier))

    def attempts(self, identifier, pagination: PaginationParams):
        from app.modules.notifications.outbox_schemas import AttemptRead

        self._get(identifier)
        result = self.repository.attempts(identifier, pagination)
        return to_page_response(
            result, [AttemptRead.model_validate(row) for row in result.items]
        )

    def source(self, identifier, actor):
        event = self._get(identifier)
        notification = OperationalNotificationRepository(self.db).get(
            event.notification_id
        )
        TripService(self.db).get_trip(notification.trip_id, current_user=actor)
        return f"/trips/{notification.trip_id}"

    def retry(self, identifier, command_id, actor):
        try:
            actor = UserService(self.db).get_user_for_authorization(actor.id)
            if not actor.active or actor.role != "ADMIN":
                raise ApiError(
                    403, "AUTH_FORBIDDEN", "Reprocessamento exclusivo do ADMIN ativo."
                )
            # Lock the parent before inserting its FK command. Otherwise two
            # commands hold KEY SHARE and deadlock when upgrading to FOR UPDATE.
            event = self._get(identifier, lock=True)
            inserted = self.repository.retry_command(command_id, identifier, actor.id)
            if inserted is None:
                command = self.repository.get_command(command_id)
                if (command.outbox_event_id, command.actor_id) != (
                    identifier,
                    actor.id,
                ):
                    raise ApiError(
                        409,
                        "OUTBOX_COMMAND_CONFLICT",
                        "Identificador de comando já utilizado.",
                    )
                return self.detail(identifier)
            if event.status not in {"RETRYABLE", "TERMINAL", "UNCERTAIN"}:
                raise ApiError(
                    409,
                    "OUTBOX_NOT_RETRYABLE",
                    "Este evento não permite reprocessamento.",
                )
            event.status = "PENDING"
            event.attempt_count = 0
            event.next_attempt_at = event.updated_at = self.repository.now()
            event.last_error_code = None
            # Fence increases on the next claim, never resets with a new cycle.
            # Adopted legacy attempts use generation 0; skip re-adoption on manual retry.
            if event.generation == 0:
                event.generation = 1
            AuditService(self.db).stage_administrative_event(
                AuditEventCreate(
                    event_type="OUTBOX_REPROCESSED",
                    entity_type="OUTBOX_EVENT",
                    entity_id=event.id,
                    actor_id=actor.id,
                    changed_fields=["status", "next_attempt_at"],
                )
            )
            self.db.commit()
            return self.detail(identifier)
        except Exception:
            self.db.rollback()
            raise


def legacy_outcome(status: str) -> tuple[str, str | None]:
    if status in {"SIMULATED", "NO_RECIPIENT"}:
        return "SUCCEEDED", "NO_RECIPIENT" if status == "NO_RECIPIENT" else None
    if status == "FAILED":
        return "TERMINAL", "LEGACY_FAILED"
    return "UNCERTAIN", "LEGACY_UNKNOWN"


def deliver(transport: OutboxTransport, claim: Claim) -> tuple[str, str | None]:
    try:
        transport.send(claim.envelope)
    except TransientDeliveryError:
        return "RETRYABLE", "TRANSIENT"
    except PermanentDeliveryError:
        return "TERMINAL", "PERMANENT"
    except TimeoutError:
        return "UNCERTAIN", "TIMEOUT_UNKNOWN"
    except Exception:  # noqa: BLE001 - unknown effects must never be replayed automatically
        return "UNCERTAIN", "UNKNOWN_RESULT"
    return "SUCCEEDED", None
