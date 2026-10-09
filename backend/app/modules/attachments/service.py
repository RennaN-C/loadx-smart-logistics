import hashlib
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.integrations.evidence_storage import EvidenceStorage, EvidenceStorageError
from app.modules.attachments.models import RESOURCE_COLUMNS, OperationalAttachment
from app.modules.attachments.repository import AttachmentRepository
from app.modules.attachments.schemas import (
    AttachmentCreate,
    AttachmentRead,
    AttachmentResource,
)
from app.modules.deliveries.evidence_content import validate_evidence_content
from app.modules.deliveries.service import TripService
from app.modules.occurrences.service import OccurrenceService
from app.modules.orders.service import OrderService
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService
from app.modules.users.models import User
from app.modules.users.service import UserService

logger = logging.getLogger(__name__)


class AttachmentForbiddenError(Exception):
    pass


class AttachmentNotFoundError(Exception):
    pass


class AttachmentIdentityConflictError(Exception):
    pass


class AttachmentRevokedError(Exception):
    pass


class AttachmentService:
    def __init__(self, db: Session, storage: EvidenceStorage | None = None) -> None:
        self.db = db
        self.storage = storage
        self.repository = AttachmentRepository(db)

    def _authorize(
        self,
        resource_type: AttachmentResource,
        resource_id: uuid.UUID,
        current_user: User,
        *,
        operate: bool = False,
    ) -> User:
        actor = UserService(self.db).get_user_for_authorization(current_user.id)
        if not actor.active:
            raise AttachmentForbiddenError
        if resource_type == "orders":
            roles = (
                {"ADMIN", "LOGISTICS_MANAGER"}
                if operate
                else {"ADMIN", "LOGISTICS_MANAGER", "CHECKER"}
            )
            if actor.role not in roles:
                raise AttachmentForbiddenError
            OrderService(self.db).get_order(resource_id)
        elif resource_type == "trips":
            TripService(self.db).get_trip(resource_id, current_user=actor)
        elif resource_type == "deliveries":
            TripService(self.db).get_delivery_for_access(
                resource_id, current_user=actor, operate=operate
            )
        elif resource_type == "occurrences":
            OccurrenceService(self.db).get_occurrence_for_access(
                resource_id, current_user=actor
            )
        else:
            raise AttachmentNotFoundError
        return actor

    def register(
        self,
        resource_type: AttachmentResource,
        resource_id: uuid.UUID,
        data: AttachmentCreate,
        *,
        current_user: User,
    ) -> AttachmentRead:
        new_key = None
        try:
            if not isinstance(self.db.get_bind(), Engine) or self.storage is None:
                raise EvidenceStorageError
            actor = self._authorize(
                resource_type, resource_id, current_user, operate=True
            )
            content = validate_evidence_content(data.content_base64)
            fingerprint = hashlib.sha256(
                f"{resource_type}:{resource_id}:{content.source_hash}".encode()
            ).hexdigest()
            candidate = OperationalAttachment(
                id=uuid.uuid4(),
                recorded_by=actor.id,
                event_id=data.event_id,
                media_type=content.media_type,
                size_bytes=len(content.data),
                sha256=hashlib.sha256(content.data).hexdigest(),
                fingerprint=fingerprint,
                **{RESOURCE_COLUMNS[resource_type]: resource_id},
            )
            row, claimed = self.repository.claim(candidate)
            if row.fingerprint != fingerprint:
                raise AttachmentIdentityConflictError
            if claimed:
                new_key = row.id
                self.storage.put(new_key, content.data)
                self._audit("ATTACHMENT_REGISTERED", row.id, actor.id)
            result = AttachmentRead.model_validate(row)
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            if new_key is not None:
                self._compensate(new_key)
            raise

    def _compensate(self, key: uuid.UUID) -> None:
        try:
            committed = self.repository.exists(key)
            self.db.rollback()
            if not committed and self.storage is not None:
                self.storage.discard(key)
        except Exception:  # noqa: BLE001 - uncertain commit must preserve confirmed bytes
            self.db.rollback()
            logger.error("attachment cleanup unavailable: %s", key)

    def list(
        self,
        resource_type: AttachmentResource,
        resource_id: uuid.UUID,
        pagination: PaginationParams,
        *,
        current_user: User,
    ) -> PageResult[AttachmentRead]:
        self._authorize(resource_type, resource_id, current_user)
        page = self.repository.list(resource_type, resource_id, pagination)
        return PageResult(
            tuple(AttachmentRead.model_validate(row) for row in page.items),
            page.page,
            page.page_size,
            page.total,
            page.total_pages,
        )

    def get(
        self,
        resource_type: AttachmentResource,
        resource_id: uuid.UUID,
        key: uuid.UUID,
        *,
        current_user: User,
    ) -> AttachmentRead:
        self._authorize(resource_type, resource_id, current_user)
        return AttachmentRead.model_validate(
            self._get_row(resource_type, resource_id, key)
        )

    def _get_row(
        self, resource_type: AttachmentResource, resource_id: uuid.UUID, key: uuid.UUID
    ) -> OperationalAttachment:
        row = self.repository.get(resource_type, resource_id, key)
        if row is None:
            raise AttachmentNotFoundError
        return row

    def download(
        self,
        resource_type: AttachmentResource,
        resource_id: uuid.UUID,
        key: uuid.UUID,
        *,
        current_user: User,
    ) -> tuple[bytes, str]:
        self._authorize(resource_type, resource_id, current_user)
        row = self._get_row(resource_type, resource_id, key)
        if row.status != "ACTIVE":
            raise AttachmentRevokedError
        if self.storage is None:
            raise EvidenceStorageError
        content = self.storage.read(key)
        if (
            len(content) != row.size_bytes
            or hashlib.sha256(content).hexdigest() != row.sha256
        ):
            raise EvidenceStorageError
        return content, row.media_type

    def revoke(
        self,
        resource_type: AttachmentResource,
        resource_id: uuid.UUID,
        key: uuid.UUID,
        *,
        current_user: User,
    ) -> AttachmentRead:
        try:
            actor = self._authorize(
                resource_type, resource_id, current_user, operate=True
            )
            row = self._get_row(resource_type, resource_id, key)
            if row.status == "ACTIVE":
                row.status = "REVOKED"
                row.revoked_at = datetime.now(UTC)
                row.revoked_by = actor.id
                self._audit("ATTACHMENT_REVOKED", key, actor.id)
            self.db.flush()
            result = AttachmentRead.model_validate(row)
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    def _audit(self, event: str, key: uuid.UUID, actor_id: uuid.UUID) -> None:
        AuditService(self.db).stage_administrative_event(
            AuditEventCreate(
                event_type=event,
                entity_type="ATTACHMENT",
                entity_id=key,
                actor_id=actor_id,
                changed_fields=["status"],
            )
        )
