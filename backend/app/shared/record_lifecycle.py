"""Common lifecycle contracts for the four OC105 registries."""

import uuid
from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService

ArchiveStatus = Literal["active", "archived", "all"]
ArchiveFilter = Annotated[ArchiveStatus, Query()]


def active_filter(status: ArchiveStatus) -> bool | None:
    return None if status == "all" else status == "active"


def ensure_record_active(record: object, entity_type: str) -> None:
    if not getattr(record, "active", True):
        raise ApiError(
            409,
            "RECORD_ARCHIVED",
            "Cadastro arquivado não pode ser usado em nova operação.",
            [{"entity_type": entity_type, "id": str(record.id)}],
        )


def validate_reactivation(schema: type[BaseModel], record: object) -> None:
    try:
        schema.model_validate(
            {field: getattr(record, field) for field in schema.model_fields}
        )
    except ValidationError as error:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Revise os dados do cadastro antes de reativar.",
            [{"field": ".".join(map(str, item["loc"]))} for item in error.errors()],
        ) from None


def stage_lifecycle_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    old_active: bool,
    new_active: bool,
    changed_by: uuid.UUID | None,
) -> None:
    if old_active == new_active or changed_by is None:
        return
    AuditService(db).stage_administrative_event(
        AuditEventCreate(
            event_type="RECORD_REACTIVATED" if new_active else "RECORD_ARCHIVED",
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=changed_by,
            changed_fields=["active"],
        )
    )
