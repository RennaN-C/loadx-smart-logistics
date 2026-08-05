import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.modules.load_planning.models import (
    LoadPlan,
    LoadPlanItem,
    LoadPlanOrder,
)
from app.modules.load_planning.optimizer.capacity import TruckCapacityInput
from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    OrderItemInput,
)
from app.modules.load_planning.optimizer.engine import (
    MAX_VOLUMES,
    LoadPlanResult,
    LoadPlanVolumeLimitExceededError,
    RejectedVolume,
    calculate_load_plan,
)
from app.modules.load_planning.optimizer.loading_sequence import SequencedPlacement
from app.modules.load_planning.repository import LoadPlanRepository
from app.modules.load_planning.schemas import LoadPlanCreate
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.service import OrderService
from app.modules.products.models import Product
from app.modules.products.service import ProductService
from app.modules.status_history.schemas import StatusHistoryCreate
from app.modules.status_history.service import StatusHistoryService
from app.modules.trucks.models import Truck
from app.modules.trucks.service import TruckNotFoundError, TruckService

MAX_PERSISTED_VOLUME_CM3 = 9_223_372_036_854_775_807


class LoadPlanNotFoundError(Exception):
    pass


class LoadPlanTruckNotFoundError(Exception):
    pass


class LoadPlanTruckInactiveError(Exception):
    pass


class LoadPlanOrdersNotFoundError(Exception):
    def __init__(self, order_ids: Sequence[uuid.UUID]) -> None:
        self.order_ids = tuple(order_ids)
        super().__init__("One or more load plan orders were not found")


class LoadPlanProductsNotFoundError(Exception):
    def __init__(self, product_ids: Sequence[uuid.UUID]) -> None:
        self.product_ids = tuple(product_ids)
        super().__init__("One or more load plan products were not found")


class LoadPlanOrdersNotEligibleError(Exception):
    def __init__(self, orders: Sequence[Order]) -> None:
        self.order_statuses = tuple((order.id, order.status) for order in orders)
        super().__init__("One or more orders are not eligible for load planning")


class InvalidLoadPlanInputError(Exception):
    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


class LoadPlanInvalidStatusError(Exception):
    def __init__(self, current_status: str, operation: str) -> None:
        self.current_status = current_status
        self.operation = operation
        super().__init__(f"load plan in {current_status} cannot be {operation}")


class LoadPlanHasRejectionsError(Exception):
    pass


class LoadPlanSourceChangedError(Exception):
    pass


class LoadPlanningService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = LoadPlanRepository(db)
        self.truck_service = TruckService(db)
        self.order_service = OrderService(db)
        self.product_service = ProductService(db)
        self.status_history_service = StatusHistoryService(db)

    def get_load_plan(self, load_plan_id: uuid.UUID) -> LoadPlan:
        load_plan = self.repository.get(load_plan_id)
        if load_plan is None:
            raise LoadPlanNotFoundError
        return load_plan

    def create_load_plan(
        self,
        data: LoadPlanCreate,
        *,
        changed_by: uuid.UUID,
    ) -> LoadPlan:
        return self._calculate_and_persist(
            truck_id=data.truck_id,
            order_ids=data.order_ids,
            changed_by=changed_by,
            recalculated_from_id=None,
            allow_planned_orders=False,
        )

    def recalculate_load_plan(
        self,
        load_plan_id: uuid.UUID,
        *,
        changed_by: uuid.UUID,
    ) -> LoadPlan:
        try:
            source = self.repository.get_for_update(load_plan_id)
            if source is None:
                raise LoadPlanNotFoundError
            order_ids = tuple(link.order_id for link in source.orders)
            return self._calculate_and_persist(
                truck_id=source.truck_id,
                order_ids=order_ids,
                changed_by=changed_by,
                recalculated_from_id=source.id,
                allow_planned_orders=True,
            )
        except Exception:
            self.db.rollback()
            raise

    def approve_load_plan(
        self,
        load_plan_id: uuid.UUID,
        *,
        changed_by: uuid.UUID,
    ) -> LoadPlan:
        try:
            load_plan = self.repository.get_for_update(load_plan_id)
            if load_plan is None:
                raise LoadPlanNotFoundError
            if load_plan.status != "CALCULATED":
                raise LoadPlanInvalidStatusError(load_plan.status, "approved")
            if load_plan.unloaded_count != 0:
                raise LoadPlanHasRejectionsError

            order_ids = tuple(link.order_id for link in load_plan.orders)
            orders = tuple(
                self.order_service.get_orders(order_ids, for_update=True)
            )
            if {order.id for order in orders} != set(order_ids):
                raise LoadPlanSourceChangedError

            allowed_statuses = (
                {"READY", "PLANNED"}
                if load_plan.recalculated_from_id is not None
                else {"READY"}
            )
            ineligible = tuple(
                order for order in orders if order.status not in allowed_statuses
            )
            if ineligible:
                raise LoadPlanOrdersNotEligibleError(ineligible)

            previous_statuses = {order.id: order.status for order in orders}
            self.order_service.stage_orders_as_planned(orders)
            load_plan.status = "APPROVED"
            load_plan.approved_at = datetime.now(UTC)
            self.repository.update(load_plan)

            self._stage_status_change(
                entity_type="LOAD_PLAN",
                entity_id=load_plan.id,
                old_status="CALCULATED",
                new_status="APPROVED",
                changed_by=changed_by,
            )
            for order in orders:
                old_status = previous_statuses[order.id]
                if old_status == "PLANNED":
                    continue
                self._stage_status_change(
                    entity_type="ORDER",
                    entity_id=order.id,
                    old_status=old_status,
                    new_status="PLANNED",
                    changed_by=changed_by,
                )

            self.db.commit()
            return self.get_load_plan(load_plan.id)
        except Exception:
            self.db.rollback()
            raise

    def _calculate_and_persist(
        self,
        *,
        truck_id: uuid.UUID,
        order_ids: Sequence[uuid.UUID],
        changed_by: uuid.UUID,
        recalculated_from_id: uuid.UUID | None,
        allow_planned_orders: bool,
    ) -> LoadPlan:
        try:
            normalized_order_ids = self._validate_order_ids(order_ids)
            try:
                truck = self.truck_service.get_truck_for_update(truck_id)
            except TruckNotFoundError as exc:
                raise LoadPlanTruckNotFoundError from exc
            if not truck.active:
                raise LoadPlanTruckInactiveError
            internal_volume_cm3 = (
                truck.internal_width_cm
                * truck.internal_height_cm
                * truck.internal_length_cm
            )
            if internal_volume_cm3 > MAX_PERSISTED_VOLUME_CM3:
                raise InvalidLoadPlanInputError(
                    "truck_id",
                    "internal volume exceeds the persisted BIGINT range",
                )

            orders = tuple(
                self.order_service.get_orders(
                    normalized_order_ids,
                    for_update=True,
                )
            )
            orders_by_id = {order.id: order for order in orders}
            missing_order_ids = tuple(
                order_id
                for order_id in normalized_order_ids
                if order_id not in orders_by_id
            )
            if missing_order_ids:
                raise LoadPlanOrdersNotFoundError(missing_order_ids)

            allowed_statuses = (
                {"READY", "PLANNED"} if allow_planned_orders else {"READY"}
            )
            ineligible_orders = tuple(
                order for order in orders if order.status not in allowed_statuses
            )
            if ineligible_orders:
                raise LoadPlanOrdersNotEligibleError(ineligible_orders)

            order_items = tuple(
                sorted(
                    (item for order in orders for item in order.items),
                    key=lambda item: (item.order_id.int, item.id.int),
                )
            )
            volume_count = sum(item.quantity for item in order_items)
            if volume_count > MAX_VOLUMES:
                raise LoadPlanVolumeLimitExceededError(volume_count)
            if volume_count <= 0:
                raise InvalidLoadPlanInputError(
                    "order_ids", "must reference at least one volume"
                )

            product_ids = tuple(
                sorted(
                    {item.product_id for item in order_items},
                    key=lambda value: value.int,
                )
            )
            products = tuple(
                self.product_service.get_products(
                    product_ids,
                    for_update=True,
                )
            )
            products_by_id = {product.id: product for product in products}
            missing_product_ids = tuple(
                product_id
                for product_id in product_ids
                if product_id not in products_by_id
            )
            if missing_product_ids:
                raise LoadPlanProductsNotFoundError(missing_product_ids)

            optimizer_items = tuple(
                self._map_optimizer_item(item, products_by_id[item.product_id])
                for item in order_items
            )
            result = calculate_load_plan(
                TruckCapacityInput(
                    internal_width_cm=truck.internal_width_cm,
                    internal_height_cm=truck.internal_height_cm,
                    internal_length_cm=truck.internal_length_cm,
                    max_weight_kg=truck.max_weight_kg,
                ),
                optimizer_items,
            )
            source_items = {item.id: item for item in order_items}
            load_plan = self._build_load_plan(
                truck=truck,
                orders=orders,
                products_by_id=products_by_id,
                source_items=source_items,
                result=result,
                recalculated_from_id=recalculated_from_id,
            )
            self.repository.add(load_plan)
            self._stage_status_change(
                entity_type="LOAD_PLAN",
                entity_id=load_plan.id,
                old_status=None,
                new_status=load_plan.status,
                changed_by=changed_by,
            )
            self.db.commit()
            return self.get_load_plan(load_plan.id)
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _validate_order_ids(
        order_ids: Sequence[uuid.UUID],
    ) -> tuple[uuid.UUID, ...]:
        identifiers = tuple(order_ids)
        if not identifiers:
            raise InvalidLoadPlanInputError("order_ids", "must not be empty")
        if any(not isinstance(order_id, uuid.UUID) for order_id in identifiers):
            raise InvalidLoadPlanInputError("order_ids", "must contain UUID values")
        if len(set(identifiers)) != len(identifiers):
            raise InvalidLoadPlanInputError("order_ids", "must not contain duplicates")
        return tuple(sorted(identifiers, key=lambda value: value.int))

    @staticmethod
    def _map_optimizer_item(
        item: OrderItem,
        product: Product,
    ) -> OrderItemInput:
        return OrderItemInput(
            order_id=item.order_id,
            order_item_id=item.id,
            product_id=product.id,
            quantity=item.quantity,
            delivery_sequence=item.delivery_sequence,
            width_cm=product.width_cm,
            height_cm=product.height_cm,
            length_cm=product.length_cm,
            weight_kg=product.weight_kg,
            fragile=product.fragile,
            stackable=product.stackable,
            rotation_allowed=product.rotation_allowed,
            product_name=product.name,
        )

    def _build_load_plan(
        self,
        *,
        truck: Truck,
        orders: Sequence[Order],
        products_by_id: dict[uuid.UUID, Product],
        source_items: dict[uuid.UUID, OrderItem],
        result: LoadPlanResult,
        recalculated_from_id: uuid.UUID | None,
    ) -> LoadPlan:
        metrics = result.metrics
        status = "REJECTED" if metrics.loaded_count == 0 else "CALCULATED"
        load_plan = LoadPlan(
            truck_id=truck.id,
            recalculated_from_id=recalculated_from_id,
            status=status,
            truck_snapshot_plate=truck.plate,
            truck_snapshot_model=truck.model,
            truck_snapshot_internal_width_cm=result.capacity.internal_width_cm,
            truck_snapshot_internal_height_cm=result.capacity.internal_height_cm,
            truck_snapshot_internal_length_cm=result.capacity.internal_length_cm,
            truck_snapshot_max_weight_kg=result.capacity.max_weight_kg,
            internal_volume_cm3=metrics.internal_volume_cm3,
            used_volume_cm3=metrics.used_volume_cm3,
            occupancy_percent=metrics.occupancy_percent,
            total_weight_kg=metrics.total_weight_kg,
            loaded_count=metrics.loaded_count,
            unloaded_count=metrics.unloaded_count,
            algorithm_version=metrics.algorithm_version,
            approved_at=None,
            orders=[LoadPlanOrder(order_id=order.id) for order in orders],
        )
        load_plan.items = [
            self._build_placed_item(
                item,
                source_items=source_items,
                products_by_id=products_by_id,
            )
            for item in result.placed_volumes
        ]
        load_plan.items.extend(
            self._build_rejected_item(
                item,
                source_items=source_items,
                products_by_id=products_by_id,
            )
            for item in result.rejected_volumes
        )
        return load_plan

    def _build_placed_item(
        self,
        item: SequencedPlacement,
        *,
        source_items: dict[uuid.UUID, OrderItem],
        products_by_id: dict[uuid.UUID, Product],
    ) -> LoadPlanItem:
        source_item = source_items[item.volume.order_item_id]
        product = products_by_id[item.volume.product_id]
        return self._build_item_snapshot(
            volume=item.volume,
            source_item=source_item,
            product=product,
            position_x_cm=item.position_x_cm,
            position_y_cm=item.position_y_cm,
            position_z_cm=item.position_z_cm,
            used_width_cm=item.used_width_cm,
            used_height_cm=item.used_height_cm,
            used_length_cm=item.used_length_cm,
            rotation_code=item.rotation_code.value,
            loading_sequence=item.loading_sequence,
            placed=True,
            rejection_reason=None,
        )

    def _build_rejected_item(
        self,
        item: RejectedVolume,
        *,
        source_items: dict[uuid.UUID, OrderItem],
        products_by_id: dict[uuid.UUID, Product],
    ) -> LoadPlanItem:
        source_item = source_items[item.volume.order_item_id]
        product = products_by_id[item.volume.product_id]
        return self._build_item_snapshot(
            volume=item.volume,
            source_item=source_item,
            product=product,
            position_x_cm=None,
            position_y_cm=None,
            position_z_cm=None,
            used_width_cm=None,
            used_height_cm=None,
            used_length_cm=None,
            rotation_code=None,
            loading_sequence=None,
            placed=False,
            rejection_reason=item.rejection_reason.value,
        )

    @staticmethod
    def _build_item_snapshot(
        *,
        volume: IndividualVolume,
        source_item: OrderItem,
        product: Product,
        position_x_cm: int | None,
        position_y_cm: int | None,
        position_z_cm: int | None,
        used_width_cm: int | None,
        used_height_cm: int | None,
        used_length_cm: int | None,
        rotation_code: str | None,
        loading_sequence: int | None,
        placed: bool,
        rejection_reason: str | None,
    ) -> LoadPlanItem:
        return LoadPlanItem(
            order_id=volume.order_id,
            order_item_id=volume.order_item_id,
            product_id=volume.product_id,
            volume_index=volume.volume_index,
            order_item_snapshot_quantity=source_item.quantity,
            order_item_snapshot_delivery_sequence=source_item.delivery_sequence,
            product_snapshot_code=product.code,
            product_snapshot_name=product.name,
            product_snapshot_width_cm=product.width_cm,
            product_snapshot_height_cm=product.height_cm,
            product_snapshot_length_cm=product.length_cm,
            product_snapshot_weight_kg=product.weight_kg,
            product_snapshot_fragile=product.fragile,
            product_snapshot_stackable=product.stackable,
            product_snapshot_rotation_allowed=product.rotation_allowed,
            position_x_cm=position_x_cm,
            position_y_cm=position_y_cm,
            position_z_cm=position_z_cm,
            used_width_cm=used_width_cm,
            used_height_cm=used_height_cm,
            used_length_cm=used_length_cm,
            rotation_code=rotation_code,
            loading_sequence=loading_sequence,
            placed=placed,
            rejection_reason=rejection_reason,
        )

    def _stage_status_change(
        self,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
        old_status: str | None,
        new_status: str,
        changed_by: uuid.UUID,
    ) -> None:
        self.status_history_service.stage_status_change(
            StatusHistoryCreate(
                entity_type=entity_type,
                entity_id=entity_id,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
            )
        )
