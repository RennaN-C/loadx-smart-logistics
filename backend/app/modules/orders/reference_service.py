"""Public SQL projections for operational consumers; no customer personal data."""

from sqlalchemy import func, select

from app.modules.deliveries.reference_service import DeliveryReferenceService
from app.modules.orders.models import Order


class OrderReferenceService:
    @staticmethod
    def ready_count_query(order_ids):
        return (
            select(func.count())
            .select_from(Order)
            .where(Order.id.in_(order_ids), Order.status == "READY")
        )

    @staticmethod
    def planning_status_projection():
        return select(
            Order.id.label("order_id"),
            Order.status,
            Order.id.in_(DeliveryReferenceService.delivered_order_ids()).label(
                "has_delivered_leg"
            ),
        ).subquery()
