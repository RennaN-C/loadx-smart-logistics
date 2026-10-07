import uuid

from sqlalchemy import asc, desc, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.deliveries.evidence_models import DeliveryEvidence


class DeliveryEvidenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def claim(self, evidence: DeliveryEvidence) -> tuple[DeliveryEvidence, bool]:
        values = {
            field: getattr(evidence, field)
            for field in (
                "id",
                "delivery_id",
                "receipt_id",
                "recorded_by",
                "event_id",
                "kind",
                "media_type",
                "size_bytes",
                "sha256",
                "fingerprint",
            )
        }
        claimed = self.db.scalar(
            insert(DeliveryEvidence)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["recorded_by", "event_id"])
            .returning(DeliveryEvidence.id)
        )
        row = self.db.scalar(
            select(DeliveryEvidence).where(
                DeliveryEvidence.recorded_by == evidence.recorded_by,
                DeliveryEvidence.event_id == evidence.event_id,
            )
        )
        if row is None:
            raise RuntimeError("evidence claim unavailable")
        return row, claimed is not None

    def get(
        self, delivery_id: uuid.UUID, evidence_id: uuid.UUID
    ) -> DeliveryEvidence | None:
        return self.db.scalar(
            select(DeliveryEvidence)
            .where(
                DeliveryEvidence.id == evidence_id,
                DeliveryEvidence.delivery_id == delivery_id,
            )
            .execution_options(populate_existing=True)
        )

    def list(
        self, delivery_id: uuid.UUID, pagination: PaginationParams
    ) -> PageResult[DeliveryEvidence]:
        filters = (DeliveryEvidence.delivery_id == delivery_id,)
        total = (
            self.db.scalar(
                select(func.count()).select_from(DeliveryEvidence).where(*filters)
            )
            or 0
        )
        direction = asc if pagination.sort_order == "asc" else desc
        rows = self.db.scalars(
            select(DeliveryEvidence)
            .where(*filters)
            .order_by(
                direction(DeliveryEvidence.recorded_at), direction(DeliveryEvidence.id)
            )
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).all()
        return PageResult.create(rows, pagination, total)
