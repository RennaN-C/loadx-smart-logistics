import uuid

from sqlalchemy.orm import Session

from app.modules.deliveries.models import Delivery


class DeliveryReferenceService:
    """Public read boundary for modules that reference deliveries."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_delivery(self, delivery_id: uuid.UUID) -> Delivery | None:
        return self.db.get(Delivery, delivery_id)
