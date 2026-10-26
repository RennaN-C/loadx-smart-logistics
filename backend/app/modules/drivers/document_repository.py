from __future__ import annotations

import uuid
from datetime import datetime
from typing import TypeVar

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.drivers.document_schemas import LICENSE_CATEGORIES
from app.modules.drivers.models import (
    CNH_TYPE_ID,
    DriverDocument,
    DriverDocumentPolicy,
    DriverDocumentType,
)
from app.shared.document_validity import document_status

Record = TypeVar("Record", DriverDocument, DriverDocumentPolicy, DriverDocumentType)


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def types(self) -> list[DriverDocumentType]:
        return list(
            self.db.scalars(
                select(DriverDocumentType).order_by(DriverDocumentType.code)
            ).all()
        )

    def get_type(self, identifier: uuid.UUID) -> DriverDocumentType | None:
        return self.db.get(DriverDocumentType, identifier)

    def list_documents(
        self, driver_id: uuid.UUID, pagination: PaginationParams
    ) -> PageResult[DriverDocument]:
        filters = (DriverDocument.driver_id == driver_id,)
        total = (
            self.db.scalar(
                select(func.count()).select_from(DriverDocument).where(*filters)
            )
            or 0
        )
        direction = asc if pagination.sort_order == "asc" else desc
        rows = self.db.scalars(
            select(DriverDocument)
            .where(*filters)
            .order_by(
                direction(DriverDocument.created_at), direction(DriverDocument.id)
            )
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).all()
        return PageResult.create(rows, pagination, total)

    def current(
        self, driver_id: uuid.UUID, type_id: uuid.UUID
    ) -> DriverDocument | None:
        return self.db.scalar(
            select(DriverDocument)
            .where(
                DriverDocument.driver_id == driver_id,
                DriverDocument.document_type_id == type_id,
                DriverDocument.superseded_at.is_(None),
            )
            .execution_options(populate_existing=True)
        )

    def get(self, driver_id: uuid.UUID, identifier: uuid.UUID) -> DriverDocument | None:
        return self.db.scalar(
            select(DriverDocument)
            .where(
                DriverDocument.driver_id == driver_id, DriverDocument.id == identifier
            )
            .execution_options(populate_existing=True)
        )

    def policies(self, driver_id: uuid.UUID) -> list[DriverDocumentPolicy]:
        return list(
            self.db.scalars(
                select(DriverDocumentPolicy)
                .where(DriverDocumentPolicy.driver_id == driver_id)
                .execution_options(populate_existing=True)
            ).all()
        )

    def has_block(self, driver_id: uuid.UUID, at: datetime) -> bool:
        for policy in self.policies(driver_id):
            if not policy.required:
                continue
            current = self.current(driver_id, policy.document_type_id)
            if current is None or document_status(current, at=at) not in (
                "VALID",
                "EXPIRING",
            ):
                return True
            if policy.document_type_id == CNH_TYPE_ID:
                if (
                    current.expires_at is None
                    or current.category not in LICENSE_CATEGORIES
                ):
                    return True
                if (
                    policy.allowed_categories
                    and current.category not in policy.allowed_categories
                ):
                    return True
        return False

    def save(self, record: Record) -> Record:
        self.db.add(record)
        self.db.flush()
        return record
