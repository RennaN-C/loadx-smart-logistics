import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.orders.models import Order


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> Sequence[Order]:
        statement = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
        return self.db.scalars(statement).all()

    def get(self, order_id: uuid.UUID) -> Order | None:
        statement = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        return self.db.scalar(statement)

    def add(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        self.db.refresh(order)
        return order

    def update(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        self.db.refresh(order)
        return order
