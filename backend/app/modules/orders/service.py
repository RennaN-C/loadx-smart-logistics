import uuid
from collections.abc import Callable, Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.integrity import get_integrity_constraint_name
from app.modules.customers.service import CustomerNotFoundError, CustomerService
from app.modules.load_planning.reference_service import LoadPlanReferenceService
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import (
    ORDER_STATUS_VALUES,
    OrderCreate,
    OrderItemCreate,
    OrderUpdate,
)
from app.modules.products.service import ProductNotFoundError, ProductService
from app.modules.status_history.schemas import StatusHistoryCreate
from app.modules.status_history.service import StatusHistoryService

MANUAL_ORDER_STATUS_TRANSITIONS = {
    "DRAFT": frozenset({"READY", "CANCELED"}),
    "READY": frozenset({"DRAFT", "CANCELED"}),
}


class OrderNotFoundError(Exception):
    pass


class OrderCustomerNotFoundError(Exception):
    pass


class OrderProductNotFoundError(Exception):
    def __init__(self, product_ids: Sequence[uuid.UUID]) -> None:
        self.product_ids = list(product_ids)
        super().__init__("One or more order products were not found.")


class OrderItemsReferencedByLoadPlanError(Exception):
    pass


class OrderEditNotAllowedError(Exception):
    def __init__(self, current_status: str) -> None:
        self.current_status = current_status
        super().__init__(f"order in {current_status} cannot be edited")


class OrderStatusTransitionNotAllowedError(Exception):
    def __init__(self, current_status: str, requested_status: str) -> None:
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__(
            f"order cannot transition from {current_status} to {requested_status}"
        )


class OrderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OrderRepository(db)
        self.customer_service = CustomerService(db)
        self.load_plan_reference_service = LoadPlanReferenceService(db)
        self.product_service = ProductService(db)
        self.status_history_service = StatusHistoryService(db)

    def list_orders(self) -> Sequence[Order]:
        return self.repository.list()

    def get_order(self, order_id: uuid.UUID) -> Order:
        order = self.repository.get(order_id)
        if order is None:
            raise OrderNotFoundError
        return order

    def get_orders(
        self,
        order_ids: Sequence[uuid.UUID],
        *,
        for_update: bool = False,
    ) -> Sequence[Order]:
        return self.repository.get_many(order_ids, for_update=for_update)

    def create_order(self, data: OrderCreate, *, changed_by: uuid.UUID) -> Order:
        self._ensure_customer_exists(data.customer_id)
        self._ensure_products_exist(data.items)

        order = Order(
            customer_id=data.customer_id,
            status="DRAFT",
            priority=data.priority,
            delivery_address=data.delivery_address,
            expected_delivery_at=data.expected_delivery_at,
            items=[self._build_order_item(item) for item in data.items],
        )

        def stage_order_with_history() -> Order:
            persisted_order = self.repository.add(order)
            self._stage_status_change(
                order_id=persisted_order.id,
                old_status=None,
                new_status="DRAFT",
                changed_by=changed_by,
            )
            return persisted_order

        return self._persist(
            stage_order_with_history,
            product_ids=[item.product_id for item in data.items],
        )

    def update_order(self, order_id: uuid.UUID, data: OrderUpdate) -> Order:
        try:
            return self._update_order_locked(order_id, data)
        except Exception:
            self.db.rollback()
            raise

    def _update_order_locked(
        self,
        order_id: uuid.UUID,
        data: OrderUpdate,
    ) -> Order:
        order = self.repository.get_for_update(order_id)
        if order is None:
            raise OrderNotFoundError
        if order.status != "DRAFT":
            raise OrderEditNotAllowedError(order.status)
        update_data = data.model_dump(exclude_unset=True)

        new_customer_id = update_data.get("customer_id")
        if new_customer_id is not None:
            self._ensure_customer_exists(new_customer_id)

        update_data.pop("items", None)
        if "items" in data.model_fields_set and data.items is not None:
            if self.load_plan_reference_service.has_order_item_references(
                [item.id for item in order.items]
            ):
                raise OrderItemsReferencedByLoadPlanError
            self._ensure_products_exist(data.items)
            order.items = [self._build_order_item(item) for item in data.items]

        for field_name, value in update_data.items():
            setattr(order, field_name, value)

        replacement_product_ids = (
            [item.product_id for item in data.items]
            if "items" in data.model_fields_set and data.items is not None
            else []
        )
        return self._persist(
            lambda: self.repository.update(order),
            product_ids=replacement_product_ids,
        )

    def change_order_status(
        self,
        order_id: uuid.UUID,
        requested_status: str,
        *,
        changed_by: uuid.UUID,
    ) -> Order:
        normalized_status = requested_status.strip().upper()
        try:
            order = self.repository.get_for_update(order_id)
            if order is None:
                raise OrderNotFoundError

            current_status = order.status
            if normalized_status == current_status:
                self.db.commit()
                return self.get_order(order_id)

            if (
                normalized_status not in ORDER_STATUS_VALUES
                or normalized_status
                not in MANUAL_ORDER_STATUS_TRANSITIONS.get(
                    current_status,
                    frozenset(),
                )
            ):
                raise OrderStatusTransitionNotAllowedError(
                    current_status,
                    normalized_status,
                )

            order.status = normalized_status
            self.repository.update(order)
            self._stage_status_change(
                order_id=order.id,
                old_status=current_status,
                new_status=normalized_status,
                changed_by=changed_by,
            )
            self.db.commit()
            return self.get_order(order_id)
        except Exception:
            self.db.rollback()
            raise

    def stage_orders_as_planned(self, orders: Sequence[Order]) -> None:
        """Stage READY/PLANNED orders for an outer atomic planning transaction."""

        staged_orders = tuple(orders)
        if not staged_orders or any(
            not isinstance(order, Order) for order in staged_orders
        ):
            raise ValueError("orders must be a non-empty sequence of Order")
        if len({order.id for order in staged_orders}) != len(staged_orders):
            raise ValueError("orders must contain unique ids")
        if any(order.status not in {"READY", "PLANNED"} for order in staged_orders):
            raise ValueError("orders must be READY or PLANNED")

        for order in staged_orders:
            order.status = "PLANNED"
            self.db.add(order)
        self.db.flush()

    def _ensure_customer_exists(self, customer_id: uuid.UUID) -> None:
        try:
            self.customer_service.get_customer(customer_id)
        except CustomerNotFoundError as exc:
            raise OrderCustomerNotFoundError from exc

    def _ensure_products_exist(self, items: Sequence[OrderItemCreate]) -> None:
        missing_product_ids: list[uuid.UUID] = []
        seen_product_ids: set[uuid.UUID] = set()
        for item in items:
            if item.product_id in seen_product_ids:
                continue
            seen_product_ids.add(item.product_id)
            try:
                self.product_service.get_product(item.product_id)
            except ProductNotFoundError:
                missing_product_ids.append(item.product_id)

        if missing_product_ids:
            raise OrderProductNotFoundError(missing_product_ids)

    def _build_order_item(self, item: OrderItemCreate) -> OrderItem:
        return OrderItem(**item.model_dump())

    def _stage_status_change(
        self,
        *,
        order_id: uuid.UUID,
        old_status: str | None,
        new_status: str,
        changed_by: uuid.UUID,
    ) -> None:
        self.status_history_service.stage_status_change(
            StatusHistoryCreate(
                entity_type="ORDER",
                entity_id=order_id,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
            )
        )

    def _persist(
        self,
        operation: Callable[[], Order],
        *,
        product_ids: Sequence[uuid.UUID],
    ) -> Order:
        try:
            order = operation()
            self.db.commit()
            self.db.refresh(order)
        except IntegrityError as exc:
            self.db.rollback()
            constraint_name = get_integrity_constraint_name(exc)
            if constraint_name == "fk_orders__customers":
                raise OrderCustomerNotFoundError from exc
            if constraint_name == "fk_order_items__products":
                raise OrderProductNotFoundError(product_ids) from exc
            if constraint_name in {
                "fk_load_plan_items__order_items",
                "fk_load_plan_items__order_item_provenance",
            }:
                raise OrderItemsReferencedByLoadPlanError from exc
            raise
        except Exception:
            self.db.rollback()
            raise
        return self.get_order(order.id)
