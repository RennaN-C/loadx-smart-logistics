import uuid
from collections.abc import Callable, Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.customers.service import CustomerNotFoundError, CustomerService
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import OrderCreate, OrderItemCreate, OrderUpdate
from app.modules.products.service import ProductNotFoundError, ProductService


class OrderNotFoundError(Exception):
    pass


class OrderCustomerNotFoundError(Exception):
    pass


class OrderProductNotFoundError(Exception):
    def __init__(self, product_ids: Sequence[uuid.UUID]) -> None:
        self.product_ids = list(product_ids)
        super().__init__("One or more order products were not found.")


class OrderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OrderRepository(db)
        self.customer_service = CustomerService(db)
        self.product_service = ProductService(db)

    def list_orders(self) -> Sequence[Order]:
        return self.repository.list()

    def get_order(self, order_id: uuid.UUID) -> Order:
        order = self.repository.get(order_id)
        if order is None:
            raise OrderNotFoundError
        return order

    def create_order(self, data: OrderCreate) -> Order:
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
        return self._persist(lambda: self.repository.add(order))

    def update_order(self, order_id: uuid.UUID, data: OrderUpdate) -> Order:
        order = self.get_order(order_id)
        update_data = data.model_dump(exclude_unset=True)

        new_customer_id = update_data.get("customer_id")
        if new_customer_id is not None:
            self._ensure_customer_exists(new_customer_id)

        update_data.pop("items", None)
        if "items" in data.model_fields_set and data.items is not None:
            self._ensure_products_exist(data.items)
            order.items = [self._build_order_item(item) for item in data.items]

        for field_name, value in update_data.items():
            setattr(order, field_name, value)

        return self._persist(lambda: self.repository.update(order))

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

    def _persist(self, operation: Callable[[], Order]) -> Order:
        try:
            order = operation()
            self.db.commit()
            self.db.refresh(order)
        except IntegrityError as exc:
            self.db.rollback()
            raise OrderCustomerNotFoundError from exc
        return self.get_order(order.id)
