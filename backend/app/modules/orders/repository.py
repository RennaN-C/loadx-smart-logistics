import uuid
from collections.abc import Sequence

from sqlalchemy import Select, String, asc, cast, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.pagination import PageResult, PaginationParams
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.schemas import OrderStatus
from app.shared.search import search_pattern


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        pagination: PaginationParams,
        *,
        search: str | None = None,
        status: OrderStatus | None = None,
        customer_name_ids: Select[tuple[uuid.UUID]] | None = None,
    ) -> PageResult[Order]:
        direction = asc if pagination.sort_order == "asc" else desc
        filters = []
        pattern = search_pattern(search)
        if pattern is not None:
            reference_filters = [
                cast(Order.id, String).ilike(pattern, escape="\\"),
                cast(Order.customer_id, String).ilike(pattern, escape="\\"),
            ]
            if customer_name_ids is not None:
                reference_filters.append(Order.customer_id.in_(customer_name_ids))
            filters.append(or_(*reference_filters))
        if status is not None:
            filters.append(Order.status == status)
        total = (
            self.db.scalar(select(func.count()).select_from(Order).where(*filters)) or 0
        )
        statement = (
            select(Order)
            .where(*filters)
            .options(selectinload(Order.items))
            .order_by(direction(Order.created_at), direction(Order.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        return PageResult.create(
            self.db.scalars(statement).all(),
            pagination,
            total,
        )

    def get(self, order_id: uuid.UUID) -> Order | None:
        statement = (
            select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        )
        return self.db.scalar(statement)

    def get_many(
        self,
        order_ids: Sequence[uuid.UUID],
        *,
        for_update: bool = False,
    ) -> Sequence[Order]:
        unique_ids = tuple(sorted(set(order_ids), key=lambda value: value.int))
        if not unique_ids:
            return ()
        statement = (
            select(Order).where(Order.id.in_(unique_ids)).order_by(Order.id.asc())
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        else:
            statement = statement.options(selectinload(Order.items))
        orders = self.db.scalars(statement).all()
        if for_update:
            item_lock = (
                select(OrderItem.id)
                .where(OrderItem.order_id.in_(unique_ids))
                .order_by(OrderItem.id.asc())
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            self.db.scalars(item_lock).all()
            for order in orders:
                self.db.refresh(order, attribute_names=["items"])
        return orders

    def get_for_update(self, order_id: uuid.UUID) -> Order | None:
        orders = self.get_many((order_id,), for_update=True)
        return orders[0] if orders else None

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
