import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.integrity import get_integrity_constraint_name
from app.modules.load_planning.distribution_models import (
    LoadDistribution,
    LoadDistributionOrder,
    LoadDistributionPart,
    LoadDistributionVolume,
)
from app.modules.load_planning.distribution_repository import LoadDistributionRepository
from app.modules.load_planning.distribution_schemas import (
    DistributionCreate,
    DistributionNeedRead,
    DistributionNeedRequest,
    DistributionPartCreate,
    DistributionPartRead,
    DistributionPartReprocess,
    DistributionRead,
    DistributionVolumeRead,
    IneligibleTruckRead,
    NeedVolumeRead,
    VolumeReference,
)
from app.modules.load_planning.optimizer.capacity import TruckCapacityInput
from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    VolumeIdentity,
)
from app.modules.load_planning.optimizer.engine import (
    MAX_VOLUMES,
    LoadPlanVolumeLimitExceededError,
)
from app.modules.load_planning.optimizer.multi_truck import (
    MultiTruckCandidate,
    optimize_multi_truck,
)
from app.modules.load_planning.optimizer.volumes import expand_order_items
from app.modules.load_planning.schemas import TruckSnapshotRead, map_load_plan_read
from app.modules.load_planning.service import (
    InvalidLoadPlanInputError,
    LoadPlanningService,
    LoadPlanOrdersNotEligibleError,
    LoadPlanOrdersNotFoundError,
    LoadPlanProductsNotFoundError,
    LoadPlanTruckInactiveError,
    LoadPlanTruckNotFoundError,
)
from app.modules.orders.service import OrderService
from app.modules.products.service import ProductService
from app.modules.status_history.schemas import StatusHistoryCreate
from app.modules.status_history.service import StatusHistoryService
from app.modules.trucks.service import TruckNotFoundError, TruckService


class DistributionError(Exception):
    def __init__(
        self, code: str, *, status: int = 409, details: list | None = None
    ) -> None:
        self.code = code
        self.status = status
        self.details = details or []
        super().__init__(code)


class LoadDistributionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = LoadDistributionRepository(db)
        self.planning = LoadPlanningService(db)
        self.orders = OrderService(db)
        self.products = ProductService(db)
        self.trucks = TruckService(db)
        self.history = StatusHistoryService(db)

    def _sources(self, order_ids, *, lock: bool, allow_operational: bool = False):
        orders = tuple(self.orders.get_orders(order_ids, for_update=lock))
        missing = set(order_ids) - {o.id for o in orders}
        if missing:
            raise LoadPlanOrdersNotFoundError(sorted(missing, key=lambda x: x.int))
        eligible = (
            {"READY", "PLANNED", "IN_TRANSIT"} if allow_operational else {"READY"}
        )
        ineligible = [o for o in orders if o.status not in eligible]
        if ineligible:
            raise LoadPlanOrdersNotEligibleError(ineligible)
        items = {i.id: i for o in orders for i in o.items}
        count = sum(i.quantity for i in items.values())
        if count > MAX_VOLUMES:
            raise LoadPlanVolumeLimitExceededError(count)
        if count == 0:
            raise InvalidLoadPlanInputError("order_ids", "must contain volumes")
        product_ids = sorted(
            {i.product_id for i in items.values()}, key=lambda x: x.int
        )
        self.orders.ensure_operational_sources(orders, for_update=lock)
        products = {
            p.id: p for p in self.products.get_products(product_ids, for_update=lock)
        }
        if set(product_ids) != set(products):
            raise LoadPlanProductsNotFoundError(set(product_ids) - set(products))
        inputs = tuple(
            self.planning._map_optimizer_item(i, products[i.product_id])
            for i in items.values()
        )
        volumes = expand_order_items(inputs)
        return orders, items, products, {v.identity: v for v in volumes}

    def preflight(self, data: DistributionNeedRequest) -> DistributionNeedRead:
        if self.repository.has_active_orders(data.order_ids):
            raise DistributionError("DISTRIBUTION_ORDER_CLAIMED")
        _, _, _, volumes = self._sources(data.order_ids, lock=False)
        eligible, ineligible = [], []
        trucks = self.trucks.list_all_trucks()
        conflicts = self.trucks.get_operational_conflicts()
        for truck in trucks:
            if truck.id in conflicts.documents:
                ineligible.append(
                    IneligibleTruckRead(
                        truck_id=truck.id, reason="TRUCK_DOCUMENT_INELIGIBLE"
                    )
                )
                continue
            if truck.id in conflicts.maintenance:
                ineligible.append(
                    IneligibleTruckRead(
                        truck_id=truck.id, reason="TRUCK_IN_MAINTENANCE"
                    )
                )
                continue
            reason = None
            if not truck.active:
                reason = "INACTIVE"
            elif truck.id in conflicts.operations:
                reason = "TRUCK_OPERATION_CONFLICT"
            if reason:
                ineligible.append(IneligibleTruckRead(truck_id=truck.id, reason=reason))
            else:
                eligible.append(
                    TruckSnapshotRead(
                        id=truck.id,
                        plate=truck.plate,
                        model=truck.model,
                        width_cm=truck.internal_width_cm,
                        height_cm=truck.internal_height_cm,
                        length_cm=truck.internal_length_cm,
                        max_weight_kg=truck.max_weight_kg,
                    )
                )
        return DistributionNeedRead(
            order_ids=sorted(data.order_ids, key=lambda x: x.int),
            volumes=[
                NeedVolumeRead(
                    order_item_id=v.order_item_id,
                    volume_index=v.volume_index,
                    order_id=v.order_id,
                    product_id=v.product_id,
                    width_cm=v.original_width_cm,
                    height_cm=v.original_height_cm,
                    length_cm=v.original_length_cm,
                    weight_kg=v.weight_kg,
                    delivery_sequence=v.delivery_sequence,
                    fragile=v.fragile,
                    stackable=v.stackable,
                    rotation_allowed=v.rotation_allowed,
                )
                for v in sorted(
                    volumes.values(),
                    key=lambda v: (v.order_item_id.int, v.volume_index),
                )
            ],
            eligible_trucks=eligible,
            ineligible_trucks=ineligible,
        )

    def optimize(
        self,
        data: DistributionNeedRequest,
        *,
        changed_by: uuid.UUID,
    ) -> DistributionRead:
        need = self.preflight(data)

        candidates = tuple(
            MultiTruckCandidate(
                truck_id=truck.id,
                capacity=TruckCapacityInput(
                    internal_width_cm=truck.width_cm,
                    internal_height_cm=truck.height_cm,
                    internal_length_cm=truck.length_cm,
                    max_weight_kg=truck.max_weight_kg,
                ),
            )
            for truck in need.eligible_trucks
        )
        volumes = tuple(
            IndividualVolume(
                identity=VolumeIdentity(
                    volume.order_item_id,
                    volume.volume_index,
                ),
                order_id=volume.order_id,
                product_id=volume.product_id,
                product_name=None,
                delivery_sequence=volume.delivery_sequence,
                original_width_cm=volume.width_cm,
                original_height_cm=volume.height_cm,
                original_length_cm=volume.length_cm,
                volume_cm3=(volume.width_cm * volume.height_cm * volume.length_cm),
                weight_kg=volume.weight_kg,
                fragile=volume.fragile,
                stackable=volume.stackable,
                rotation_allowed=volume.rotation_allowed,
            )
            for volume in need.volumes
        )

        result = optimize_multi_truck(candidates, volumes)

        if not result.complete:
            failures = {
                (
                    failure.identity.order_item_id,
                    failure.identity.volume_index,
                ): failure.reasons
                for failure in result.failures
            }
            raise DistributionError(
                "DISTRIBUTION_CAPACITY_INSUFFICIENT",
                status=422,
                details=[
                    {
                        "remaining_volumes": [
                            {
                                "order_item_id": str(volume.order_item_id),
                                "volume_index": volume.volume_index,
                                "reasons": list(
                                    failures.get(
                                        (
                                            volume.order_item_id,
                                            volume.volume_index,
                                        ),
                                        (),
                                    )
                                ),
                            }
                            for volume in result.remaining_volumes
                        ],
                        "ineligible_trucks": [
                            {
                                "truck_id": str(truck.truck_id),
                                "reason": truck.reason,
                            }
                            for truck in sorted(
                                need.ineligible_trucks,
                                key=lambda truck: truck.truck_id.int,
                            )
                        ],
                        "attempt_count": result.attempt_count,
                    }
                ],
            )

        proposal = DistributionCreate(
            order_ids=list(need.order_ids),
            parts=[
                DistributionPartCreate(
                    truck_id=part.truck_id,
                    volumes=[
                        VolumeReference(
                            order_item_id=volume.order_item_id,
                            volume_index=volume.volume_index,
                        )
                        for volume in part.volumes
                    ],
                )
                for part in result.parts
            ],
        )
        return self.create(proposal, changed_by=changed_by)

    def _lock_trucks(self, identifiers):
        trucks = {}
        for identifier in sorted(set(identifiers), key=lambda x: x.int):
            try:
                truck = self.trucks.ensure_no_operation_conflict(identifier)
            except TruckNotFoundError as error:
                raise LoadPlanTruckNotFoundError([identifier]) from error
            if not truck.active:
                raise LoadPlanTruckInactiveError([identifier])
            trucks[identifier] = truck
        return trucks

    def create(
        self, data: DistributionCreate, *, changed_by: uuid.UUID
    ) -> DistributionRead:
        try:
            trucks = self._lock_trucks([p.truck_id for p in data.parts])
            orders, items, products, volumes = self._sources(data.order_ids, lock=True)
            if self.repository.has_active_orders(data.order_ids):
                raise DistributionError("DISTRIBUTION_ORDER_CLAIMED")
            selected = [
                VolumeIdentity(v.order_item_id, v.volume_index)
                for p in data.parts
                for v in p.volumes
            ]
            if len(selected) != len(set(selected)) or set(selected) != set(volumes):
                raise DistributionError("DISTRIBUTION_INVALID_PARTITION", status=422)
            distribution = LoadDistribution(
                id=uuid.uuid4(), created_by=changed_by, status="PROPOSED"
            )
            self.repository.add(distribution)
            distribution.orders = [
                LoadDistributionOrder(order_id=o.id, active=True) for o in orders
            ]
            self.db.flush()
            for proposed in data.parts:
                part_volumes = [
                    volumes[VolumeIdentity(v.order_item_id, v.volume_index)]
                    for v in proposed.volumes
                ]
                plan = self._stage_part_plan(
                    trucks[proposed.truck_id],
                    orders,
                    items,
                    products,
                    part_volumes,
                    changed_by,
                )
                part = LoadDistributionPart(
                    id=uuid.uuid4(),
                    distribution_id=distribution.id,
                    load_plan_id=plan.id,
                    status="PENDING",
                )
                distribution.parts.append(part)
                self.db.flush()
                distribution.volumes.extend(
                    LoadDistributionVolume(
                        distribution_id=distribution.id,
                        order_item_id=v.order_item_id,
                        volume_index=v.volume_index,
                        order_id=v.order_id,
                        product_id=v.product_id,
                        snapshot_quantity=items[v.order_item_id].quantity,
                        part_id=part.id,
                        active=True,
                    )
                    for v in part_volumes
                )
                self._history(
                    "LOAD_DISTRIBUTION_PART", part.id, None, "PENDING", changed_by
                )
            self._history(
                "LOAD_DISTRIBUTION", distribution.id, None, "PROPOSED", changed_by
            )
            return self._commit(distribution.id)
        except Exception as error:
            self._rollback(error)
            raise

    def _stage_part_plan(
        self, truck, orders, items, products, volumes, actor, source=None
    ):
        related_ids = {v.order_id for v in volumes}
        plan, result = self.planning.stage_plan_for_volumes(
            truck=truck,
            orders=[o for o in orders if o.id in related_ids],
            products_by_id=products,
            source_items=items,
            volumes=volumes,
            changed_by=actor,
            recalculated_from_id=source,
        )
        if result.rejected_volumes:
            raise DistributionError(
                "DISTRIBUTION_CAPACITY_REJECTED",
                status=422,
                details=[
                    {
                        "truck_id": str(truck.id),
                        "rejections": [
                            {
                                "order_item_id": str(v.volume.order_item_id),
                                "volume_index": v.volume.volume_index,
                                "reason": v.rejection_reason.value,
                            }
                            for v in result.rejected_volumes
                        ],
                    }
                ],
            )
        return plan

    def _read_part(
        self, part: LoadDistributionPart, distribution_id: uuid.UUID
    ) -> DistributionPartRead:
        plan = self.planning.get_load_plan(part.load_plan_id)
        return DistributionPartRead(
            id=part.id,
            status=part.status,
            truck=TruckSnapshotRead(
                id=plan.truck_id,
                plate=plan.truck_snapshot_plate,
                model=plan.truck_snapshot_model,
                width_cm=plan.truck_snapshot_internal_width_cm,
                height_cm=plan.truck_snapshot_internal_height_cm,
                length_cm=plan.truck_snapshot_internal_length_cm,
                max_weight_kg=plan.truck_snapshot_max_weight_kg,
            ),
            load_plan=map_load_plan_read(plan, distribution_id=distribution_id),
        )

    def get(self, identifier: uuid.UUID) -> DistributionRead:
        distribution = self._get(identifier)
        return DistributionRead(
            id=distribution.id,
            status=distribution.status,
            created_by=distribution.created_by,
            created_at=distribution.created_at,
            order_ids=sorted(
                (o.order_id for o in distribution.orders), key=lambda x: x.int
            ),
            truck_count=len(distribution.parts),
            volume_count=len(distribution.volumes),
            parts=[
                self._read_part(p, distribution.id)
                for p in sorted(distribution.parts, key=lambda p: p.id.int)
            ],
            volumes=[
                DistributionVolumeRead(
                    order_item_id=v.order_item_id,
                    volume_index=v.volume_index,
                    order_id=v.order_id,
                    product_id=v.product_id,
                    quantity=v.snapshot_quantity,
                    part_id=v.part_id,
                )
                for v in sorted(
                    distribution.volumes,
                    key=lambda v: (v.order_item_id.int, v.volume_index),
                )
            ],
        )

    def _get(self, identifier, *, lock=False):
        distribution = self.repository.get(identifier, for_update=lock)
        if distribution is None:
            raise DistributionError("DISTRIBUTION_NOT_FOUND", status=404)
        return distribution

    def _part(self, distribution, identifier):
        part = next((p for p in distribution.parts if p.id == identifier), None)
        if part is None:
            raise DistributionError("DISTRIBUTION_PART_NOT_FOUND", status=404)
        return part

    def _mutable(self, distribution):
        if distribution.status in {"APPROVED", "CANCELED"}:
            raise DistributionError("DISTRIBUTION_IMMUTABLE")

    def approve(
        self,
        identifier: uuid.UUID,
        *,
        changed_by: uuid.UUID,
        part_id: uuid.UUID | None = None,
    ) -> DistributionRead:
        try:
            distribution = self._get(identifier, lock=True)
            if distribution.status == "APPROVED":
                if part_id is not None:
                    self._part(distribution, part_id)
                return self._commit(identifier)
            self._mutable(distribution)
            plans = {
                p.id: self.planning.get_load_plan(p.load_plan_id)
                for p in distribution.parts
            }
            is_reapproval = any(
                plan.recalculated_from_id is not None for plan in plans.values()
            )
            available_ids = [
                plan.truck_id
                for plan in plans.values()
                if not is_reapproval or plan.status == "CALCULATED"
            ]
            self._lock_trucks(available_ids)
            if is_reapproval:
                # Already-approved siblings legitimately reserve their vehicles.
                for sibling_truck_id in sorted(
                    {
                        plan.truck_id
                        for plan in plans.values()
                        if plan.status == "APPROVED"
                    },
                    key=lambda value: value.int,
                ):
                    self.trucks.get_truck_for_update(sibling_truck_id)
            for p in sorted(distribution.parts, key=lambda p: p.load_plan_id.int):
                plans[p.id] = self.planning.repository.get_for_update(p.load_plan_id)
            orders, _, _, _ = self._sources(
                [o.order_id for o in distribution.orders],
                lock=True,
                allow_operational=is_reapproval,
            )
            targets = (
                [self._part(distribution, part_id)] if part_id else distribution.parts
            )
            if any(p.status == "CANCELED" for p in targets):
                raise DistributionError("DISTRIBUTION_INCOMPLETE")
            for part in targets:
                if part.status == "PENDING":
                    part.status = "APPROVED"
                    self._history(
                        "LOAD_DISTRIBUTION_PART",
                        part.id,
                        "PENDING",
                        "APPROVED",
                        changed_by,
                    )
            if is_reapproval:
                # Validate that the replacement part is approved before
                # changing the aggregate distribution state (OC94 / 0034).
                self.db.flush()
            old = distribution.status
            distribution.status = self._status(distribution)
            if distribution.status == "APPROVED":
                starting_orders = tuple(
                    order for order in orders if order.status == "READY"
                )
                if starting_orders:
                    self.orders.stage_orders_as_planned(starting_orders)
                for part in distribution.parts:
                    plan = plans[part.id]
                    if plan.status == "CALCULATED":
                        plan.status = "APPROVED"
                        plan.approved_at = datetime.now(UTC)
                        self._history(
                            "LOAD_PLAN",
                            plan.id,
                            "CALCULATED",
                            "APPROVED",
                            changed_by,
                        )
                for order in starting_orders:
                    self._history("ORDER", order.id, "READY", "PLANNED", changed_by)
            if old != distribution.status:
                self._history(
                    "LOAD_DISTRIBUTION",
                    identifier,
                    old,
                    distribution.status,
                    changed_by,
                )
            return self._commit(identifier)
        except Exception as error:
            self._rollback(error)
            raise

    @staticmethod
    def _status(distribution):
        states = {p.status for p in distribution.parts}
        if "CANCELED" in states:
            return "INCOMPLETE"
        if states == {"APPROVED"}:
            return "APPROVED"
        return "PARTIALLY_APPROVED" if "APPROVED" in states else "PROPOSED"

    def cancel(
        self,
        identifier: uuid.UUID,
        *,
        changed_by: uuid.UUID,
        part_id: uuid.UUID | None = None,
    ) -> DistributionRead:
        try:
            distribution = self._get(identifier, lock=True)
            if distribution.status == "CANCELED":
                if part_id:
                    self._part(distribution, part_id)
                return self._commit(identifier)
            self._mutable(distribution)
            # Order locks serialize release against legacy approval and a new claim.
            self.orders.get_orders(
                [o.order_id for o in distribution.orders], for_update=True
            )
            targets = (
                [self._part(distribution, part_id)] if part_id else distribution.parts
            )
            for part in targets:
                old = part.status
                part.status = "CANCELED"
                if old != "CANCELED":
                    self._history(
                        "LOAD_DISTRIBUTION_PART", part.id, old, "CANCELED", changed_by
                    )
            old = distribution.status
            distribution.status = "INCOMPLETE" if part_id else "CANCELED"
            if not part_id:
                for row in (*distribution.orders, *distribution.volumes):
                    row.active = False
            if old != distribution.status:
                self._history(
                    "LOAD_DISTRIBUTION",
                    identifier,
                    old,
                    distribution.status,
                    changed_by,
                )
            return self._commit(identifier)
        except Exception as error:
            self._rollback(error)
            raise

    def reprocess(
        self,
        identifier: uuid.UUID,
        part_id: uuid.UUID,
        data: DistributionPartReprocess,
        *,
        changed_by: uuid.UUID,
    ) -> DistributionRead:
        try:
            distribution = self._get(identifier, lock=True)
            self._mutable(distribution)
            part = self._part(distribution, part_id)
            if part.status != "CANCELED":
                raise DistributionError("DISTRIBUTION_PART_REPROCESS_REQUIRES_CANCELED")
            if part.load_plan_id != data.expected_load_plan_id:
                raise DistributionError("DISTRIBUTION_VERSION_CONFLICT")
            old_plan = self.planning.get_load_plan(part.load_plan_id)
            all_truck_ids = [
                self.planning.get_load_plan(p.load_plan_id).truck_id
                for p in distribution.parts
                if p.id != part_id
            ]
            if data.truck_id in all_truck_ids:
                raise DistributionError("DISTRIBUTION_TRUCK_DUPLICATED")
            # Sibling trucks can be legitimately in route.
            # Lock them, but do not demand that they be idle.
            trucks = self._lock_trucks([data.truck_id])
            for sibling_id in sorted(set(all_truck_ids), key=lambda value: value.int):
                self.trucks.get_truck_for_update(sibling_id)
            self.planning.repository.get_for_update(old_plan.id)
            orders, items, products, volumes = self._sources(
                [o.order_id for o in distribution.orders],
                lock=True,
                allow_operational=True,
            )
            selected = [
                volumes[VolumeIdentity(v.order_item_id, v.volume_index)]
                for v in distribution.volumes
                if v.part_id == part_id
            ]
            plan = self._stage_part_plan(
                trucks[data.truck_id],
                orders,
                items,
                products,
                selected,
                changed_by,
                old_plan.id,
            )
            old = part.status
            part.load_plan_id = plan.id
            part.status = "PENDING"
            self._history("LOAD_DISTRIBUTION_PART", part.id, old, "PENDING", changed_by)
            # Guard requires a current replacement plan + a canceled original.
            # Persist the part's version transition before updating its parent.
            self.db.flush()
            previous = distribution.status
            distribution.status = self._status(distribution)
            if previous != distribution.status:
                self._history(
                    "LOAD_DISTRIBUTION",
                    identifier,
                    previous,
                    distribution.status,
                    changed_by,
                )
            return self._commit(identifier)
        except Exception as error:
            self._rollback(error)
            raise

    def _history(self, kind, identifier, old, new, actor):
        self.history.stage_status_change(
            StatusHistoryCreate(
                entity_type=kind,
                entity_id=identifier,
                old_status=old,
                new_status=new,
                changed_by=actor,
            )
        )

    def _commit(self, identifier):
        self.db.flush()
        self.db.commit()
        return self.get(identifier)

    def _rollback(self, error):
        self.db.rollback()
        if isinstance(error, IntegrityError):
            name = get_integrity_constraint_name(error) or ""
            if name.startswith(
                (
                    "uq_load_distribution",
                    "pk_load_distribution",
                    "ck_load_distribution",
                    "fk_load_distribution",
                )
            ):
                raise DistributionError("DISTRIBUTION_INTEGRITY_CONFLICT") from error
