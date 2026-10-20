import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.database.integrity import get_integrity_constraint_name
from app.modules.access_profiles.catalog import Permission, has_permission
from app.modules.deliveries.models import (
    DELIVERY_STATUS_VALUES,
    TRIP_STATUS_VALUES,
    Delivery,
    Trip,
)
from app.modules.deliveries.repository import TripListItem, TripRepository
from app.modules.deliveries.schemas import DeliveryReceiptRead, TripCreate
from app.modules.drivers.service import DriverNotFoundError, DriverService
from app.modules.load_planning.reference_service import LoadPlanReferenceService
from app.modules.loading.reference_service import LoadingReferenceService
from app.modules.notifications.service import OperationalNotificationService
from app.modules.orders.models import Order
from app.modules.orders.service import OrderService
from app.modules.status_history.models import StatusHistory
from app.modules.status_history.schemas import StatusHistoryCreate
from app.modules.status_history.service import StatusHistoryService
from app.modules.trucks.service import TruckService
from app.modules.users.models import User
from app.shared.record_lifecycle import ensure_record_active

TRIP_STATUS_TRANSITIONS = {
    "SCHEDULED": frozenset({"IN_ROUTE"}),
    "IN_ROUTE": frozenset({"FINISHED"}),
}
DELIVERY_STATUS_TRANSITIONS = {
    "PENDING": frozenset({"IN_DELIVERY"}),
    "IN_DELIVERY": frozenset({"DELIVERED"}),
}


class TripNotFoundError(Exception):
    pass


class DeliveryNotFoundError(Exception):
    pass


class TripLoadPlanNotFoundError(Exception):
    pass


class TripLoadPlanNotApprovedError(Exception):
    pass


class TripLoadPlanAlreadyAssignedError(Exception):
    pass


class TripDriverNotFoundError(Exception):
    pass


class TripDriverInactiveError(Exception):
    pass


class TripOrderNotEligibleError(Exception):
    pass


class TripOrderAlreadyAssignedError(Exception):
    def __init__(self, order_ids: Sequence[uuid.UUID]) -> None:
        self.order_ids = tuple(order_ids)
        super().__init__("one or more orders already have a delivery")


class TripDeliverySequenceConflictError(Exception):
    def __init__(self, order_id: uuid.UUID) -> None:
        self.order_id = order_id
        super().__init__("order items use different delivery sequences")


class TripStatusTransitionNotAllowedError(Exception):
    def __init__(self, current_status: str, requested_status: str) -> None:
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__("trip status transition is not allowed")


class DeliveryStatusTransitionNotAllowedError(Exception):
    def __init__(self, current_status: str, requested_status: str) -> None:
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__("delivery status transition is not allowed")


class TripLoadingNotFinishedError(Exception):
    pass


class TripDeliveriesNotFinishedError(Exception):
    pass


class DeliveryTripNotInRouteError(Exception):
    pass


class DeliveryReceiptNotAvailableError(Exception):
    pass


class DeliveryReceiptHistoryInvalidError(Exception):
    pass


class TripAccessForbiddenError(Exception):
    pass


class TripService:
    def __init__(
        self,
        db: Session,
        *,
        loading_reference_service: LoadingReferenceService | None = None,
        notification_service: OperationalNotificationService | None = None,
    ) -> None:
        self.db = db
        self.repository = TripRepository(db)
        self.driver_service = DriverService(db)
        self.load_plan_reference_service = LoadPlanReferenceService(db)
        self.loading_reference_service = (
            loading_reference_service or LoadingReferenceService(db)
        )
        self.notification_service = (
            notification_service or OperationalNotificationService()
        )
        self.order_service = OrderService(db)
        self.status_history_service = StatusHistoryService(db)
        self.truck_service = TruckService(db)

    def get_trip(
        self, trip_id: uuid.UUID, *, current_user: User, for_update: bool = False
    ) -> Trip:
        trip = (
            self.repository.get_for_update(trip_id)
            if for_update
            else self.repository.get(trip_id)
        )
        if trip is None:
            raise TripNotFoundError
        self._ensure_can_read(current_user, trip)
        return trip

    def list_trips(
        self,
        pagination: PaginationParams,
        *,
        current_user: User,
        search: str | None = None,
    ) -> PageResult[TripListItem]:
        if has_permission(current_user, Permission.TRIPS_READ):
            return self.repository.list(pagination, search=search)
        if current_user.role != "DRIVER" or current_user.driver_id is None:
            raise TripAccessForbiddenError
        try:
            driver = self.driver_service.get_driver(current_user.driver_id)
        except DriverNotFoundError as exc:
            raise TripAccessForbiddenError from exc
        if not driver.active:
            raise TripAccessForbiddenError
        return self.repository.list(pagination, driver_id=driver.id, search=search)

    def create_trip(self, data: TripCreate, *, changed_by: uuid.UUID) -> Trip:
        try:
            load_plan = self.load_plan_reference_service.get_operational_plan(
                data.load_plan_id,
                for_update=True,
            )
            if load_plan is None:
                raise TripLoadPlanNotFoundError
            if load_plan.status != "APPROVED" or not load_plan.operational_ready:
                raise TripLoadPlanNotApprovedError
            part = self.load_plan_reference_service.get_distribution_part_for_plan(
                load_plan.id
            )
            if self.repository.get_by_load_plan_id(load_plan.id) is not None:
                raise TripLoadPlanAlreadyAssignedError

            truck = self.truck_service.ensure_no_operation_conflict(
                load_plan.truck_id,
                exclude_load_plan_id=load_plan.id,
            )

            ensure_record_active(truck, "TRUCK")

            try:
                driver = self.driver_service.ensure_no_operation_conflict(
                    data.driver_id
                )
            except DriverNotFoundError as exc:
                raise TripDriverNotFoundError from exc
            if not driver.active:
                raise TripDriverInactiveError

            orders = tuple(
                self.order_service.get_orders(load_plan.order_ids, for_update=True)
            )
            if {order.id for order in orders} != set(load_plan.order_ids) or not orders:
                raise TripOrderNotEligibleError
            eligible_statuses = {"PLANNED", "IN_TRANSIT"} if part else {"PLANNED"}
            if any(order.status not in eligible_statuses for order in orders):
                raise TripOrderNotEligibleError

            assigned_ids = self.repository.assigned_order_ids(
                load_plan.order_ids,
                allowed_other_part_ids=tuple(
                    p for p in part.distribution_part_ids if p != part.part_id
                )
                if part
                else (),
            )
            if assigned_ids:
                raise TripOrderAlreadyAssignedError(
                    sorted(assigned_ids, key=lambda value: value.int)
                )

            trip = Trip(
                load_plan_id=load_plan.id,
                driver_id=driver.id,
                status="SCHEDULED",
                deliveries=self._build_deliveries(
                    orders, distribution_part_id=part.part_id if part else None
                ),
            )
            self.repository.add(trip)
            self._stage_status_change(
                entity_type="TRIP",
                entity_id=trip.id,
                old_status=None,
                new_status="SCHEDULED",
                changed_by=changed_by,
            )
            for delivery in trip.deliveries:
                self._stage_status_change(
                    entity_type="DELIVERY",
                    entity_id=delivery.id,
                    old_status=None,
                    new_status="PENDING",
                    changed_by=changed_by,
                )
            self.db.commit()
            return self._get_persisted_trip(trip.id)
        except IntegrityError as exc:
            self.db.rollback()
            self._raise_integrity_error(exc)
            raise
        except Exception:
            self.db.rollback()
            raise

    def change_trip_status(
        self,
        trip_id: uuid.UUID,
        requested_status: str,
        *,
        current_user: User,
    ) -> Trip:
        normalized_status = requested_status.strip().upper()
        try:
            trip = self.repository.get_for_update(trip_id)
            if trip is None:
                raise TripNotFoundError
            deliveries = tuple(self.repository.list_deliveries_for_update(trip.id))
            self._ensure_can_operate(current_user, trip)

            current_status = trip.status
            if normalized_status == current_status:
                self.db.commit()
                return self._get_persisted_trip(trip.id)
            if (
                normalized_status not in TRIP_STATUS_VALUES
                or normalized_status
                not in TRIP_STATUS_TRANSITIONS.get(current_status, frozenset())
            ):
                raise TripStatusTransitionNotAllowedError(
                    current_status,
                    normalized_status,
                )

            if normalized_status == "IN_ROUTE":
                self._stage_trip_start(trip, deliveries, current_user.id)
            else:
                self._stage_trip_finish(trip, deliveries, current_user.id)

            self.db.commit()
            OperationalNotificationService.dispatch_after_commit(self.db)
            return self._get_persisted_trip(trip.id)
        except Exception:
            self.db.rollback()
            raise

    def change_delivery_status(
        self,
        delivery_id: uuid.UUID,
        requested_status: str,
        *,
        current_user: User,
    ) -> Delivery:
        try:
            delivery = self._stage_delivery_status(
                delivery_id, requested_status, current_user=current_user
            )
            self.db.commit()
            return self._get_persisted_delivery(delivery.id)
        except Exception:
            self.db.rollback()
            raise

    def register_delivery_receipt(
        self, delivery_id: uuid.UUID, *, current_user: User
    ) -> DeliveryReceiptRead:
        """Reuse the completion transaction and project its history before commit."""
        try:
            delivery = self._stage_delivery_status(
                delivery_id, "DELIVERED", current_user=current_user
            )
            trip = self.repository.get(delivery.trip_id)
            if trip is None:
                raise TripNotFoundError
            receipt = self._build_delivery_receipt(delivery, trip)
            self.db.commit()
            return receipt
        except Exception:
            self.db.rollback()
            raise

    def get_delivery_receipt(
        self, delivery_id: uuid.UUID, *, current_user: User
    ) -> DeliveryReceiptRead:
        delivery = self.repository.get_delivery(delivery_id)
        if delivery is None:
            raise DeliveryNotFoundError
        trip = self.repository.get(delivery.trip_id)
        if trip is None:
            raise TripNotFoundError
        self._ensure_can_read_delivery(current_user, trip)
        return self._build_delivery_receipt(delivery, trip)

    def _build_delivery_receipt(
        self, delivery: Delivery, trip: Trip
    ) -> DeliveryReceiptRead:
        if delivery.status != "DELIVERED" or delivery.delivered_at is None:
            raise DeliveryReceiptNotAvailableError
        completions = [
            row
            for row in self.status_history_service.list_status_history(
                "DELIVERY", delivery.id
            )
            if row.old_status == "IN_DELIVERY" and row.new_status == "DELIVERED"
        ]
        if len(completions) != 1 or completions[0].changed_by is None:
            raise DeliveryReceiptHistoryInvalidError
        completion = completions[0]
        return DeliveryReceiptRead(
            id=completion.id,
            delivery_id=delivery.id,
            trip_id=delivery.trip_id,
            order_id=delivery.order_id,
            driver_id=trip.driver_id,
            delivered_at=delivery.delivered_at,
            recorded_at=completion.created_at,
            recorded_by=completion.changed_by,
        )

    def _stage_delivery_status(
        self,
        delivery_id: uuid.UUID,
        requested_status: str,
        *,
        current_user: User,
    ) -> Delivery:
        """Stage the existing transition under the trip/deliveries lock order."""
        normalized_status = requested_status.strip().upper()
        delivery = self.get_delivery_for_access(
            delivery_id, current_user=current_user, operate=True
        )
        trip = self.repository.get(delivery.trip_id)
        if trip is None:
            raise TripNotFoundError

        current_status = delivery.status
        if normalized_status == current_status:
            return delivery
        if (
            normalized_status not in DELIVERY_STATUS_VALUES
            or normalized_status
            not in DELIVERY_STATUS_TRANSITIONS.get(current_status, frozenset())
        ):
            raise DeliveryStatusTransitionNotAllowedError(
                current_status, normalized_status
            )
        if trip.status != "IN_ROUTE":
            raise DeliveryTripNotInRouteError

        if normalized_status == "DELIVERED":
            # Serialize the aggregate BEFORE making this leg visible. The scalar
            # query below runs after this lock, in READ COMMITTED, and sees the
            # preceding leg's commit even with stale objects in the identity map.
            orders = tuple(
                self.order_service.get_orders((delivery.order_id,), for_update=True)
            )
            if len(orders) != 1 or orders[0].status != "IN_TRANSIT":
                raise TripOrderNotEligibleError
            delivery.status = normalized_status
            delivery.delivered_at = datetime.now(UTC)
            self.repository.update_delivery(delivery)
            self._stage_order_delivered(delivery, current_user.id, order=orders[0])
        else:
            delivery.status = normalized_status
            self.repository.update_delivery(delivery)
        self._stage_status_change(
            entity_type="DELIVERY",
            entity_id=delivery.id,
            old_status=current_status,
            new_status=normalized_status,
            changed_by=current_user.id,
        )
        return delivery

    def get_delivery_for_access(
        self, delivery_id: uuid.UUID, *, current_user: User, operate: bool = False
    ) -> Delivery:
        """Public locking/authorization boundary for state and evidence access."""
        snapshot = self.repository.get_delivery(delivery_id)
        if snapshot is None:
            raise DeliveryNotFoundError
        trip = self.repository.get_for_update(snapshot.trip_id)
        if trip is None:
            raise TripNotFoundError
        self.repository.list_deliveries_for_update(trip.id)
        delivery = self.repository.get_delivery_for_update(delivery_id)
        if delivery is None:
            raise DeliveryNotFoundError
        if operate:
            self._ensure_can_operate(current_user, trip, Permission.DELIVERIES_MANAGE)
        else:
            self._ensure_can_read_delivery(current_user, trip)
        return delivery

    def _stage_trip_start(
        self,
        trip: Trip,
        deliveries: Sequence[Delivery],
        changed_by: uuid.UUID,
    ) -> None:
        plan = self.load_plan_reference_service.get_operational_plan(trip.load_plan_id)
        if plan is None or plan.status != "APPROVED" or not plan.operational_ready:
            raise TripLoadPlanNotApprovedError
        self.truck_service.get_truck_for_update(plan.truck_id)
        self.truck_service.ensure_operational_eligibility(plan.truck_id)
        self.driver_service.ensure_no_operation_conflict(
            trip.driver_id, exclude_trip_id=trip.id
        )
        if not self.loading_reference_service.is_load_plan_finished(trip.load_plan_id):
            raise TripLoadingNotFinishedError
        order_ids = tuple(delivery.order_id for delivery in deliveries)
        orders = tuple(self.order_service.get_orders(order_ids, for_update=True))
        is_distribution = all(
            delivery.distribution_part_id is not None for delivery in deliveries
        )
        eligible_statuses = (
            {"PLANNED", "IN_TRANSIT"} if is_distribution else {"PLANNED"}
        )
        if (
            not deliveries
            or {order.id for order in orders} != set(order_ids)
            or any(order.status not in eligible_statuses for order in orders)
        ):
            raise TripOrderNotEligibleError

        starting_orders = tuple(order for order in orders if order.status == "PLANNED")
        if starting_orders:
            self.order_service.stage_orders_as_in_transit(starting_orders)
        trip.status = "IN_ROUTE"
        trip.started_at = datetime.now(UTC)
        self.repository.update_trip(trip)
        history = self._stage_status_change(
            entity_type="TRIP",
            entity_id=trip.id,
            old_status="SCHEDULED",
            new_status="IN_ROUTE",
            changed_by=changed_by,
        )
        for order in starting_orders:
            self._stage_status_change(
                entity_type="ORDER",
                entity_id=order.id,
                old_status="PLANNED",
                new_status="IN_TRANSIT",
                changed_by=changed_by,
            )

        self.notification_service.stage(
            self.db,
            event_type="TRIP_STARTED",
            trip_id=trip.id,
            recipient_driver_id=trip.driver_id,
            status_history_id=history.id,
        )

    def _stage_trip_finish(
        self,
        trip: Trip,
        deliveries: Sequence[Delivery],
        changed_by: uuid.UUID,
    ) -> None:
        if not deliveries or any(
            delivery.status != "DELIVERED" for delivery in deliveries
        ):
            raise TripDeliveriesNotFinishedError
        order_ids = tuple(
            delivery.order_id
            for delivery in deliveries
            if delivery.distribution_part_id is None
        )
        orders = tuple(self.order_service.get_orders(order_ids, for_update=True))
        if {order.id for order in orders} != set(order_ids) or any(
            order.status != "DELIVERED" for order in orders
        ):
            raise TripOrderNotEligibleError

        trip.status = "FINISHED"
        trip.finished_at = datetime.now(UTC)
        self.repository.update_trip(trip)
        self._stage_status_change(
            entity_type="TRIP",
            entity_id=trip.id,
            old_status="IN_ROUTE",
            new_status="FINISHED",
            changed_by=changed_by,
        )

    def _stage_order_delivered(
        self,
        delivery: Delivery,
        changed_by: uuid.UUID,
        *,
        order: Order,
    ) -> None:
        if delivery.distribution_part_id is not None:
            required = self.load_plan_reference_service.get_distribution_order_for_part(
                delivery.distribution_part_id, delivery.order_id
            )
            if required is None:
                raise TripOrderNotEligibleError
            if not set(required.part_ids) <= self.repository.delivered_part_ids(
                order.id
            ):
                return
        self.order_service.stage_order_as_delivered(order)
        self._stage_status_change(
            entity_type="ORDER",
            entity_id=order.id,
            old_status="IN_TRANSIT",
            new_status="DELIVERED",
            changed_by=changed_by,
        )

    def _build_deliveries(
        self, orders: Sequence[Order], *, distribution_part_id: uuid.UUID | None = None
    ) -> list[Delivery]:
        sortable: list[tuple[int, int, Order]] = []
        for order in orders:
            sequences = {item.delivery_sequence for item in order.items}
            if len(sequences) != 1:
                raise TripDeliverySequenceConflictError(order.id)
            sortable.append((sequences.pop(), order.id.int, order))
        sortable.sort(key=lambda value: (value[0], value[1]))
        return [
            Delivery(
                order_id=order.id,
                distribution_part_id=distribution_part_id,
                status="PENDING",
                sequence=index,
            )
            for index, (_, _, order) in enumerate(sortable, start=1)
        ]

    def _ensure_can_read(self, current_user: User, trip: Trip) -> None:
        if has_permission(current_user, Permission.TRIPS_READ):
            return
        self._ensure_linked_driver(current_user, trip)

    def _ensure_can_read_delivery(self, current_user: User, trip: Trip) -> None:
        if has_permission(current_user, Permission.DELIVERIES_READ):
            return
        self._ensure_linked_driver(current_user, trip)

    def _ensure_can_operate(
        self,
        current_user: User,
        trip: Trip,
        permission: Permission = Permission.TRIPS_MANAGE,
    ) -> None:
        if has_permission(current_user, permission):
            return
        self._ensure_linked_driver(current_user, trip)

    def _ensure_linked_driver(self, current_user: User, trip: Trip) -> None:
        if current_user.role != "DRIVER" or current_user.driver_id != trip.driver_id:
            raise TripAccessForbiddenError
        try:
            driver = self.driver_service.get_driver(current_user.driver_id)
        except DriverNotFoundError as exc:
            raise TripAccessForbiddenError from exc
        if not driver.active:
            raise TripAccessForbiddenError

    def _stage_status_change(
        self,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
        old_status: str | None,
        new_status: str,
        changed_by: uuid.UUID,
    ) -> StatusHistory:
        return self.status_history_service.stage_status_change(
            StatusHistoryCreate(
                entity_type=entity_type,
                entity_id=entity_id,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
            )
        )

    def _raise_integrity_error(self, exc: IntegrityError) -> None:
        constraint_name = get_integrity_constraint_name(exc)
        if constraint_name == "uq_trips__load_plan_id":
            raise TripLoadPlanAlreadyAssignedError from exc
        if constraint_name in {
            "uq_deliveries__order_id",
            "uq_deliveries__trip_order",
            "uq_deliveries__legacy_order",
            "uq_deliveries__part_order",
            "ck_deliveries__assignment",
        }:
            raise TripOrderAlreadyAssignedError(()) from exc
        if constraint_name == "fk_trips__load_plans":
            raise TripLoadPlanNotFoundError from exc
        if constraint_name == "fk_trips__drivers":
            raise TripDriverNotFoundError from exc
        if constraint_name == "fk_deliveries__orders":
            raise TripOrderNotEligibleError from exc
        if constraint_name == "ck_deliveries__part_context":
            raise TripOrderNotEligibleError from exc

    def _get_persisted_trip(self, trip_id: uuid.UUID) -> Trip:
        trip = self.repository.get(trip_id)
        if trip is None:  # pragma: no cover - guarded by the transaction
            raise TripNotFoundError
        return trip

    def _get_persisted_delivery(self, delivery_id: uuid.UUID) -> Delivery:
        delivery = self.repository.get_delivery(delivery_id)
        if delivery is None:  # pragma: no cover - guarded by the transaction
            raise DeliveryNotFoundError
        return delivery
