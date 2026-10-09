import uuid

from sqlalchemy import asc, desc, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.attachments.models import RESOURCE_COLUMNS, OperationalAttachment


class AttachmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def claim(
        self, candidate: OperationalAttachment
    ) -> tuple[OperationalAttachment, bool]:
        fields = (
            "id",
            "recorded_by",
            "event_id",
            "media_type",
            "size_bytes",
            "sha256",
            "fingerprint",
            *RESOURCE_COLUMNS.values(),
        )
        claimed = self.db.scalar(
            insert(OperationalAttachment)
            .values(**{field: getattr(candidate, field) for field in fields})
            .on_conflict_do_nothing(index_elements=["recorded_by", "event_id"])
            .returning(OperationalAttachment.id)
        )
        row = self.db.scalar(
            select(OperationalAttachment)
            .where(
                OperationalAttachment.recorded_by == candidate.recorded_by,
                OperationalAttachment.event_id == candidate.event_id,
            )
            .with_for_update()
        )
        if row is None:
            raise RuntimeError("attachment claim unavailable")
        return row, claimed is not None

    def exists(self, key: uuid.UUID) -> bool:
        return (
            self.db.scalar(
                select(OperationalAttachment.id).where(OperationalAttachment.id == key)
            )
            is not None
        )

    @staticmethod
    def resource_filter(resource_type: str, resource_id: uuid.UUID):
        return (
            getattr(OperationalAttachment, RESOURCE_COLUMNS[resource_type])
            == resource_id
        )

    def get(
        self, resource_type: str, resource_id: uuid.UUID, key: uuid.UUID
    ) -> OperationalAttachment | None:
        return self.db.scalar(
            select(OperationalAttachment)
            .where(
                OperationalAttachment.id == key,
                self.resource_filter(resource_type, resource_id),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def list(
        self, resource_type: str, resource_id: uuid.UUID, pagination: PaginationParams
    ) -> PageResult[OperationalAttachment]:
        filter_ = self.resource_filter(resource_type, resource_id)
        total = (
            self.db.scalar(
                select(func.count()).select_from(OperationalAttachment).where(filter_)
            )
            or 0
        )
        direction = asc if pagination.sort_order == "asc" else desc
        rows = self.db.scalars(
            select(OperationalAttachment)
            .where(filter_)
            .order_by(
                direction(OperationalAttachment.recorded_at),
                direction(OperationalAttachment.id),
            )
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).all()
        return PageResult.create(rows, pagination, total)
