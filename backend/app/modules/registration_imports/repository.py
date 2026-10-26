import uuid

from sqlalchemy import asc, desc, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.registration_imports.models import RegistrationImport


class ImportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def claim(self, candidate: RegistrationImport) -> tuple[RegistrationImport, bool]:
        values = {
            field: getattr(candidate, field)
            for field in (
                "id",
                "entity_type",
                "recorded_by",
                "event_id",
                "sha256",
                "fingerprint",
                "row_count",
            )
        }
        claimed = self.db.scalar(
            insert(RegistrationImport)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["recorded_by", "event_id"])
            .returning(RegistrationImport.id)
        )
        row = self.db.scalar(
            select(RegistrationImport)
            .where(
                RegistrationImport.recorded_by == candidate.recorded_by,
                RegistrationImport.event_id == candidate.event_id,
            )
            .with_for_update()
        )
        if row is None:
            raise RuntimeError("import claim unavailable")
        return row, claimed is not None

    def get(self, key: uuid.UUID) -> RegistrationImport | None:
        return self.db.scalar(
            select(RegistrationImport).where(
                RegistrationImport.id == key, RegistrationImport.status != "PROCESSING"
            )
        )

    def list(
        self, pagination: PaginationParams, entity_type: str | None
    ) -> PageResult[RegistrationImport]:
        filters = [RegistrationImport.status != "PROCESSING"]
        if entity_type is not None:
            filters.append(RegistrationImport.entity_type == entity_type)
        total = (
            self.db.scalar(
                select(func.count()).select_from(RegistrationImport).where(*filters)
            )
            or 0
        )
        direction = asc if pagination.sort_order == "asc" else desc
        rows = self.db.scalars(
            select(RegistrationImport)
            .where(*filters)
            .order_by(
                direction(RegistrationImport.recorded_at),
                direction(RegistrationImport.id),
            )
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).all()
        return PageResult.create(rows, pagination, total)
