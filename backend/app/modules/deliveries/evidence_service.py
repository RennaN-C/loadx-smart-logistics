import hashlib
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.core.security_events import SecurityEvent, emit_security_event
from app.integrations.evidence_storage import EvidenceStorage, EvidenceStorageError
from app.modules.deliveries.evidence_content import validate_evidence_content
from app.modules.deliveries.evidence_models import DeliveryEvidence
from app.modules.deliveries.evidence_repository import DeliveryEvidenceRepository
from app.modules.deliveries.evidence_schemas import (
    DeliveryEvidenceCreate,
    DeliveryEvidenceRead,
)
from app.modules.deliveries.schemas import DeliveryReceiptRead
from app.modules.deliveries.service import TripAccessForbiddenError, TripService
from app.modules.users.models import User
from app.modules.users.service import UserService


class EvidenceNotFoundError(Exception):
    pass


class EvidenceIdentityConflictError(Exception):
    pass


class EvidenceRevokedError(Exception):
    pass


class DeliveryEvidenceService:
    def __init__(self, db: Session, storage: EvidenceStorage) -> None:
        self.db = db
        self.storage = storage
        self.repository = DeliveryEvidenceRepository(db)
        self.trip_service = TripService(db)

    def _authorize(
        self, delivery_id: uuid.UUID, current_user: User, *, operate: bool = False
    ) -> DeliveryReceiptRead:
        actor = UserService(self.db).get_user_for_authorization(current_user.id)
        if not actor.active:
            raise TripAccessForbiddenError
        self.trip_service.get_delivery_for_access(
            delivery_id, current_user=actor, operate=operate
        )
        return self.trip_service.get_delivery_receipt(delivery_id, current_user=actor)

    def register(
        self,
        delivery_id: uuid.UUID,
        data: DeliveryEvidenceCreate,
        *,
        current_user: User,
    ) -> DeliveryEvidenceRead:
        new_key: uuid.UUID | None = None
        try:
            # Binary IO needs a real owning transaction, not OC79's domain
            # savepoint. Runtime request Sessions are bound directly to Engine.
            if not isinstance(self.db.get_bind(), Engine):
                raise EvidenceStorageError
            receipt = self._authorize(delivery_id, current_user, operate=True)
            content = validate_evidence_content(data.content_base64)
            fingerprint = hashlib.sha256(
                f"{delivery_id}:{data.kind}:{content.source_hash}".encode()
            ).hexdigest()
            candidate = DeliveryEvidence(
                id=uuid.uuid4(),
                delivery_id=delivery_id,
                receipt_id=receipt.id,
                recorded_by=current_user.id,
                event_id=data.event_id,
                kind=data.kind,
                media_type=content.media_type,
                size_bytes=len(content.data),
                sha256=hashlib.sha256(content.data).hexdigest(),
                fingerprint=fingerprint,
            )
            row, claimed = self.repository.claim(candidate)
            if row.fingerprint != fingerprint:
                raise EvidenceIdentityConflictError
            if claimed:
                new_key = row.id
                self.storage.put(new_key, content.data)
            result = DeliveryEvidenceRead.model_validate(row)
            self.db.commit()
        except Exception:
            self.db.rollback()
            if new_key is not None:
                self._compensate_if_uncommitted(new_key)
            raise
        self._log(SecurityEvent.DELIVERY_EVIDENCE_REGISTERED, result.id)
        return result

    def _compensate_if_uncommitted(self, key: uuid.UUID) -> None:
        try:
            # A network failure during COMMIT can leave its outcome uncertain.
            # Never delete bytes that a committed metadata row may reference.
            committed = self.db.get(DeliveryEvidence, key)
            self.db.rollback()
            if committed is None:
                self.storage.discard(key)
        except Exception:  # noqa: BLE001 - preserve original failure without provider details
            self.db.rollback()
            emit_security_event(
                SecurityEvent.DELIVERY_EVIDENCE_CLEANUP_FAILED,
                level=logging.ERROR,
                alert=True,
                evidence_id=str(key),
            )

    def get(
        self, delivery_id: uuid.UUID, evidence_id: uuid.UUID, *, current_user: User
    ) -> DeliveryEvidenceRead:
        self._authorize(delivery_id, current_user)
        return DeliveryEvidenceRead.model_validate(
            self._get_row(delivery_id, evidence_id)
        )

    def list(
        self,
        delivery_id: uuid.UUID,
        pagination: PaginationParams,
        *,
        current_user: User,
    ) -> PageResult[DeliveryEvidenceRead]:
        self._authorize(delivery_id, current_user)
        page = self.repository.list(delivery_id, pagination)
        return PageResult(
            tuple(DeliveryEvidenceRead.model_validate(row) for row in page.items),
            page.page,
            page.page_size,
            page.total,
            page.total_pages,
        )

    def download(
        self, delivery_id: uuid.UUID, evidence_id: uuid.UUID, *, current_user: User
    ) -> tuple[bytes, str]:
        # Operational locks remain held while reading; revoke cannot race a
        # newly-authorized download. ADMIN retains read-only authorization.
        self._authorize(delivery_id, current_user)
        row = self._get_row(delivery_id, evidence_id)
        if row.status != "ACTIVE":
            raise EvidenceRevokedError
        content = self.storage.read(row.id)
        if (
            len(content) != row.size_bytes
            or hashlib.sha256(content).hexdigest() != row.sha256
        ):
            raise EvidenceStorageError
        return content, row.media_type

    def revoke(
        self, delivery_id: uuid.UUID, evidence_id: uuid.UUID, *, current_user: User
    ) -> DeliveryEvidenceRead:
        try:
            self._authorize(delivery_id, current_user, operate=True)
            row = self._get_row(delivery_id, evidence_id)
            if row.status == "ACTIVE":
                row.status = "REVOKED"
                row.revoked_at = datetime.now(UTC)
                row.revoked_by = current_user.id
                self.db.flush()
            result = DeliveryEvidenceRead.model_validate(row)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self._log(SecurityEvent.DELIVERY_EVIDENCE_REVOKED, evidence_id)
        return result

    def _get_row(
        self, delivery_id: uuid.UUID, evidence_id: uuid.UUID
    ) -> DeliveryEvidence:
        row = self.repository.get(delivery_id, evidence_id)
        if row is None:
            raise EvidenceNotFoundError
        return row

    @staticmethod
    def _log(event: SecurityEvent, evidence_id: uuid.UUID) -> None:
        emit_security_event(event, evidence_id=str(evidence_id))
