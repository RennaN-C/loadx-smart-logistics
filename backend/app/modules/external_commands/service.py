import hashlib
import json
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.security_events import SecurityEvent, emit_security_event
from app.integrations.external_commands import (
    ExternalActorResolver,
    ExternalAuthenticator,
    TrustedIntegration,
)
from app.modules.deliveries.reference_service import DeliveryReferenceService
from app.modules.deliveries.service import (
    DeliveryNotFoundError,
    DeliveryStatusTransitionNotAllowedError,
    DeliveryTripNotInRouteError,
    TripAccessForbiddenError,
    TripDriverInactiveError,
    TripLoadingNotFinishedError,
    TripNotFoundError,
    TripOrderNotEligibleError,
    TripService,
    TripStatusTransitionNotAllowedError,
)
from app.modules.drivers.service import (
    DriverNotFoundError,
    DriverOperationConflictError,
    DriverService,
)
from app.modules.external_commands.errors import (
    ExternalCommandError,
    ExternalCommandErrorCode,
)
from app.modules.external_commands.repository import ExternalCommandRepository
from app.modules.external_commands.schemas import (
    CommandName,
    ExternalCommandEnvelope,
    ExternalCommandReceipt,
)
from app.modules.trucks.service import TruckOperationConflictError
from app.modules.users.models import User
from app.modules.users.service import UserNotFoundError, UserService

MAX_BODY_BYTES = 16 * 1024
DOMAIN_ERRORS = (
    DeliveryNotFoundError,
    DeliveryStatusTransitionNotAllowedError,
    DeliveryTripNotInRouteError,
    DriverOperationConflictError,
    TripDriverInactiveError,
    TripLoadingNotFinishedError,
    TripNotFoundError,
    TripOrderNotEligibleError,
    TripStatusTransitionNotAllowedError,
    TruckOperationConflictError,
)


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class ExternalCommandService:
    """Owns the transaction; domain services remain the only business writers."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        authenticator: ExternalAuthenticator,
        actor_resolver: ExternalActorResolver,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.session_factory = session_factory
        self.authenticator = authenticator
        self.actor_resolver = actor_resolver
        self.clock = clock

    def process(self, body: bytes, signature: str) -> ExternalCommandReceipt:
        correlation_id = str(uuid.uuid4())
        try:
            if not isinstance(body, bytes) or not 0 < len(body) <= MAX_BODY_BYTES:
                raise ExternalCommandError(ExternalCommandErrorCode.PAYLOAD_INVALID)
            integration = self.authenticator.authenticate(body, signature)
            envelope = self._parse(body)
            self._ensure_current(envelope)
            if envelope.command not in integration.capabilities:
                raise ExternalCommandError(ExternalCommandErrorCode.FORBIDDEN)
            receipt = self._process_transaction(integration, envelope, body)
        except ExternalCommandError as error:
            self._log_rejection(correlation_id, error.code)
            raise
        except (TripAccessForbiddenError, UserNotFoundError, DriverNotFoundError):
            code = ExternalCommandErrorCode.FORBIDDEN
            self._log_rejection(correlation_id, code)
            raise ExternalCommandError(code) from None
        except DOMAIN_ERRORS:
            code = ExternalCommandErrorCode.DOMAIN_REJECTED
            self._log_rejection(correlation_id, code)
            raise ExternalCommandError(code) from None
        except Exception:  # noqa: BLE001 - fail closed without exposing adapter/DB details
            code = ExternalCommandErrorCode.PROCESSING_FAILED
            self._log_rejection(correlation_id, code)
            raise ExternalCommandError(code) from None

        emit_security_event(
            SecurityEvent.EXTERNAL_COMMAND_COMPLETED,
            correlation_id=correlation_id,
            command_id=str(receipt.id),
            duplicate=receipt.duplicate,
        )
        return receipt

    def _process_transaction(
        self,
        integration: TrustedIntegration,
        envelope: ExternalCommandEnvelope,
        body: bytes,
    ) -> ExternalCommandReceipt:
        actor_id = self.actor_resolver.resolve(integration, envelope.subject)
        with self.session_factory() as db, db.begin():  # noqa: SIM117 - document transaction ownership
            # All commits/rollbacks made by public domain services are savepoint
            # operations. Only db.begin() can commit the receipt and business state.
            with Session(
                bind=db.connection(),
                autoflush=False,
                join_transaction_mode="create_savepoint",
            ) as domain_db:
                actor = UserService(domain_db).get_user_for_authorization(actor_id)
                self._authorize_actor(domain_db, actor)
                repository = ExternalCommandRepository(db)
                row, claimed = repository.claim(
                    integration_id=integration.integration_id,
                    event_hash=hashlib.sha256(envelope.event_id.encode()).hexdigest(),
                    fingerprint=hashlib.sha256(body).hexdigest(),
                    user_id=actor.id,
                    command=envelope.command.value,
                    expires_at=envelope.expires_at,
                )
                self._ensure_current(envelope)
                if (
                    row.fingerprint != hashlib.sha256(body).hexdigest()
                    or row.user_id != actor.id
                ):
                    raise ExternalCommandError(
                        ExternalCommandErrorCode.IDENTITY_CONFLICT
                    )
                if not claimed:
                    if row.completed_at is None:
                        raise ExternalCommandError(
                            ExternalCommandErrorCode.PROCESSING_FAILED
                        )
                    return ExternalCommandReceipt(id=row.id, duplicate=True)
                self._execute(domain_db, actor, envelope)
                # Services may open another savepoint to read their persisted
                # result. Release it before writing completion in the outer Session.
                domain_db.commit()
                # A domain operation may itself wait on object locks. Expiring
                # while waiting must roll back even a domain service's commit.
                self._ensure_current(envelope)
                repository.complete(row, self.clock())
                return ExternalCommandReceipt(id=row.id, duplicate=False)

    @staticmethod
    def _authorize_actor(db: Session, actor: User) -> None:
        if not actor.active or actor.role not in {"LOGISTICS_MANAGER", "DRIVER"}:
            raise ExternalCommandError(ExternalCommandErrorCode.FORBIDDEN)
        if actor.role == "DRIVER":
            if actor.driver_id is None:
                raise ExternalCommandError(ExternalCommandErrorCode.FORBIDDEN)
            driver = DriverService(db).get_driver_for_update(actor.driver_id)
            if not driver.active:
                raise ExternalCommandError(ExternalCommandErrorCode.FORBIDDEN)

    @staticmethod
    def _execute(db: Session, actor: User, envelope: ExternalCommandEnvelope) -> None:
        # Notifications are deliberately not injected: no external IO before the
        # enclosing transaction is committed. Domain still checks object RBAC.
        service = TripService(db)
        if envelope.command == CommandName.START_TRIP:
            service.change_trip_status(
                envelope.target_id, "IN_ROUTE", current_user=actor
            )
        else:
            delivery = DeliveryReferenceService(db).get_delivery(envelope.target_id)
            if delivery is None:
                raise DeliveryNotFoundError
            service.get_trip(delivery.trip_id, current_user=actor)
            status = (
                "IN_DELIVERY"
                if envelope.command == CommandName.START_DELIVERY
                else "DELIVERED"
            )
            service.change_delivery_status(
                envelope.target_id, status, current_user=actor
            )

    def _ensure_current(self, envelope: ExternalCommandEnvelope) -> None:
        now = self.clock()
        if now >= envelope.expires_at:
            raise ExternalCommandError(ExternalCommandErrorCode.EXPIRED)
        if envelope.issued_at > now + timedelta(seconds=30):
            raise ExternalCommandError(ExternalCommandErrorCode.NOT_YET_VALID)

    @staticmethod
    def _parse(body: bytes) -> ExternalCommandEnvelope:
        try:
            # Pydantic's JSON parser alone accepts duplicate keys. Reject those
            # first, then validate JSON strictly (UUID/aware datetime included).
            raw = json.loads(body, object_pairs_hook=_unique_json_object)
            if not isinstance(raw, dict) or type(raw.get("version")) is not int:
                raise ValueError("invalid version")
            return ExternalCommandEnvelope.model_validate_json(body, strict=True)
        except (ValueError, ValidationError, RecursionError):
            raise ExternalCommandError(
                ExternalCommandErrorCode.PAYLOAD_INVALID
            ) from None

    @staticmethod
    def _log_rejection(correlation_id: str, code: ExternalCommandErrorCode) -> None:
        emit_security_event(
            SecurityEvent.EXTERNAL_COMMAND_REJECTED,
            level=logging.WARNING,
            alert=True,
            correlation_id=correlation_id,
            code=code.value,
        )
