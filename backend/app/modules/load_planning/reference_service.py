import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.modules.load_planning.repository import LoadPlanRepository


class LoadPlanReferenceService:
    """Public cross-module queries owned by load planning."""

    def __init__(self, db: Session) -> None:
        self.repository = LoadPlanRepository(db)

    def has_order_item_references(
        self,
        order_item_ids: Sequence[uuid.UUID],
    ) -> bool:
        return self.repository.has_order_item_references(order_item_ids)
