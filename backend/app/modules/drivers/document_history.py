import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.modules.drivers.document_repository import DocumentRepository
from app.modules.drivers.models import CNH_TYPE_ID, Driver, DriverDocument
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService


def stage_document_audit(
    db: Session, record: object, event: str, entity: str, actor: uuid.UUID | None
) -> None:
    if actor is not None:
        AuditService(db).stage_administrative_event(
            AuditEventCreate(
                event_type=event,
                entity_type=entity,
                entity_id=record.id,
                actor_id=actor,
                changed_fields=[
                    "document_type_id",
                    "reference",
                    "category",
                    "issued_at",
                    "expires_at",
                    "superseded_at",
                ]
                if entity == "DRIVER_DOCUMENT"
                else ["required", "allowed_categories"]
                if entity == "DRIVER_DOCUMENT_POLICY"
                else ["code", "name"],
            )
        )


def stage_license_history(
    db: Session, driver: Driver, *, actor: uuid.UUID | None
) -> None:
    repository = DocumentRepository(db)
    if repository.get_type(CNH_TYPE_ID) is None:
        raise RuntimeError("Native CNH document type is missing; apply migrations")
    current = repository.current(driver.id, CNH_TYPE_ID)
    if current is not None and (
        current.reference,
        current.category,
        current.expires_at,
    ) == (driver.license_number, driver.license_category, driver.license_expires_at):
        return
    issued_at = current.issued_at if current is not None else None
    if (
        issued_at is not None
        and driver.license_expires_at is not None
        and driver.license_expires_at <= issued_at
    ):
        raise ApiError(
            422,
            "DRIVER_LICENSE_PERIOD_INVALID",
            "Validade deve ser posterior à emissão.",
        )
    if current is not None:
        current.superseded_at = datetime.now(UTC)
        repository.save(current)
        stage_document_audit(
            db, current, "DRIVER_DOCUMENT_RENEWED", "DRIVER_DOCUMENT", actor
        )
    record = repository.save(
        DriverDocument(
            driver_id=driver.id,
            document_type_id=CNH_TYPE_ID,
            reference=driver.license_number,
            category=driver.license_category,
            issued_at=issued_at,
            expires_at=driver.license_expires_at,
        )
    )
    stage_document_audit(
        db, record, "DRIVER_DOCUMENT_CREATED", "DRIVER_DOCUMENT", actor
    )
