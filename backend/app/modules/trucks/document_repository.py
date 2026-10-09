import uuid
from datetime import datetime

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.trucks.models import TruckDocument, TruckDocumentPolicy


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self, truck_id: uuid.UUID, pagination: PaginationParams
    ) -> PageResult[TruckDocument]:
        filters = (TruckDocument.truck_id == truck_id,)
        total = (
            self.db.scalar(
                select(func.count()).select_from(TruckDocument).where(*filters)
            )
            or 0
        )
        direction = asc if pagination.sort_order == "asc" else desc
        rows = self.db.scalars(
            select(TruckDocument)
            .where(*filters)
            .order_by(direction(TruckDocument.created_at), direction(TruckDocument.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).all()
        return PageResult.create(rows, pagination, total)

    def current(self, truck_id: uuid.UUID, kind: str) -> TruckDocument | None:
        return self.db.scalar(
            select(TruckDocument)
            .where(
                TruckDocument.truck_id == truck_id,
                TruckDocument.kind == kind,
                TruckDocument.superseded_at.is_(None),
            )
            .execution_options(populate_existing=True)
        )

    def get(self, truck_id: uuid.UUID, identifier: uuid.UUID) -> TruckDocument | None:
        return self.db.scalar(
            select(TruckDocument)
            .where(TruckDocument.truck_id == truck_id, TruckDocument.id == identifier)
            .execution_options(populate_existing=True)
        )

    def policies(self, truck_id: uuid.UUID) -> list[TruckDocumentPolicy]:
        return list(
            self.db.scalars(
                select(TruckDocumentPolicy)
                .where(TruckDocumentPolicy.truck_id == truck_id)
                .order_by(TruckDocumentPolicy.kind)
            ).all()
        )

    def policy(self, truck_id: uuid.UUID, kind: str) -> TruckDocumentPolicy | None:
        return self.db.scalar(
            select(TruckDocumentPolicy)
            .where(
                TruckDocumentPolicy.truck_id == truck_id,
                TruckDocumentPolicy.kind == kind,
            )
            .execution_options(populate_existing=True)
        )

    def has_block(self, truck_id: uuid.UUID, at: datetime) -> bool:
        valid = (
            select(TruckDocument.id)
            .where(
                TruckDocument.truck_id == TruckDocumentPolicy.truck_id,
                TruckDocument.kind == TruckDocumentPolicy.kind,
                TruckDocument.superseded_at.is_(None),
                or_(TruckDocument.issued_at.is_(None), TruckDocument.issued_at <= at),
                or_(TruckDocument.expires_at.is_(None), TruckDocument.expires_at > at),
            )
            .exists()
        )
        return (
            self.db.scalar(
                select(TruckDocumentPolicy.id)
                .where(
                    TruckDocumentPolicy.truck_id == truck_id,
                    TruckDocumentPolicy.required.is_(True),
                    ~valid,
                )
                .limit(1)
            )
            is not None
        )

    def save(self, record):
        self.db.add(record)
        self.db.flush()
        return record
