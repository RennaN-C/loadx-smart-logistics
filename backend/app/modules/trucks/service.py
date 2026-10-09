import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PageResult, PaginationParams
from app.database.integrity import get_integrity_constraint_name
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService
from app.modules.trucks.maintenance_repository import MaintenanceRepository
from app.modules.trucks.models import Truck
from app.modules.trucks.repository import TruckRepository
from app.modules.trucks.schemas import TruckCreate, TruckUpdate
from app.shared.record_lifecycle import stage_lifecycle_event, validate_reactivation


class TruckNotFoundError(Exception):
    pass


class TruckPlateAlreadyExistsError(Exception):
    pass


class TruckOperationConflictError(Exception):
    def __init__(self, truck_id: uuid.UUID) -> None:
        self.truck_id = truck_id
        super().__init__("truck already belongs to another active operation")


class TruckService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TruckRepository(db)

    def list_trucks(
        self, pagination: PaginationParams, *, active: bool | None = None
    ) -> PageResult[Truck]:
        return self.repository.list(pagination, active=active)

    def list_all_trucks(self) -> Sequence[Truck]:
        return self.repository.list_all()

    def get_truck(self, truck_id: uuid.UUID) -> Truck:
        truck = self.repository.get(truck_id)
        if truck is None:
            raise TruckNotFoundError
        return truck

    def get_trucks(self, truck_ids: Sequence[uuid.UUID]) -> Sequence[Truck]:
        return self.repository.get_many(truck_ids)

    def get_truck_for_update(self, truck_id: uuid.UUID) -> Truck:
        truck = self.repository.get_for_update(truck_id)
        if truck is None:
            raise TruckNotFoundError
        return truck

    def has_operation_conflict(
        self,
        truck_id: uuid.UUID,
        *,
        exclude_load_plan_id: uuid.UUID | None = None,
    ) -> bool:
        self.get_truck(truck_id)
        return self.repository.has_operation_conflict(
            truck_id,
            exclude_load_plan_id=exclude_load_plan_id,
        )

    def ensure_no_operation_conflict(
        self,
        truck_id: uuid.UUID,
        *,
        exclude_load_plan_id: uuid.UUID | None = None,
    ) -> Truck:
        truck = self.get_truck_for_update(truck_id)
        self.ensure_not_in_maintenance(truck_id)
        if self.repository.has_operation_conflict(
            truck_id,
            exclude_load_plan_id=exclude_load_plan_id,
        ):
            raise TruckOperationConflictError(truck_id)
        return truck

    def has_maintenance_conflict(
        self, truck_id: uuid.UUID, *, at: datetime | None = None
    ) -> bool:
        return MaintenanceRepository(self.db).has_block(
            truck_id, at or datetime.now(UTC)
        )

    def ensure_not_in_maintenance(self, truck_id: uuid.UUID) -> None:
        if self.has_maintenance_conflict(truck_id):
            raise ApiError(
                409, "TRUCK_IN_MAINTENANCE", "Caminhão indisponível por manutenção."
            )

    def stage_maintenance_audit(
        self, identifier: uuid.UUID, event: str, fields: Sequence[str], actor: uuid.UUID
    ) -> None:
        AuditService(self.db).stage_administrative_event(
            AuditEventCreate(
                event_type=event,
                entity_type="TRUCK_MAINTENANCE",
                entity_id=identifier,
                actor_id=actor,
                changed_fields=list(fields),
            )
        )

    def stage_odometer(
        self, truck: Truck, value: int | None, *, actor: uuid.UUID | None
    ) -> None:
        if value is None or value == truck.odometer_km:
            return
        if truck.odometer_km is not None and value < truck.odometer_km:
            raise ApiError(
                409, "ODOMETER_DECREASE", "A quilometragem não pode diminuir."
            )
        truck.odometer_km = value
        if actor is not None:
            AuditService(self.db).stage_administrative_event(
                AuditEventCreate(
                    event_type="TRUCK_ODOMETER_UPDATED",
                    entity_type="TRUCK",
                    entity_id=truck.id,
                    actor_id=actor,
                    changed_fields=["odometer_km"],
                )
            )

    def create_truck(self, data: TruckCreate) -> Truck:
        if self.repository.get_by_plate(data.plate) is not None:
            raise TruckPlateAlreadyExistsError

        truck = Truck(**data.model_dump())
        return self._persist(lambda: self.repository.add(truck))

    def update_truck(
        self,
        truck_id: uuid.UUID,
        data: TruckUpdate,
        *,
        changed_by: uuid.UUID | None = None,
    ) -> Truck:
        truck = self.repository.get_for_update(truck_id)
        if truck is None:
            raise TruckNotFoundError
        old_active = truck.active
        update_data = data.model_dump(exclude_unset=True)

        new_plate = update_data.get("plate")
        if new_plate is not None and new_plate != truck.plate:
            existing_truck = self.repository.get_by_plate(new_plate)
            if existing_truck is not None and existing_truck.id != truck.id:
                raise TruckPlateAlreadyExistsError

        odometer = update_data.pop("odometer_km", None)

        for field_name, value in update_data.items():
            setattr(truck, field_name, value)

        def stage_update() -> Truck:
            self.stage_odometer(truck, odometer, actor=changed_by)
            if not old_active and truck.active:
                validate_reactivation(TruckCreate, truck)
            self.repository.update(truck)
            stage_lifecycle_event(
                self.db,
                entity_type="TRUCK",
                entity_id=truck.id,
                old_active=old_active,
                new_active=truck.active,
                changed_by=changed_by,
            )
            return truck

        return self._persist(stage_update)

    def _persist(self, operation: Callable[[], Truck]) -> Truck:
        try:
            truck = operation()
            self.db.commit()
            self.db.refresh(truck)
        except IntegrityError as exc:
            self.db.rollback()
            if get_integrity_constraint_name(exc) == "uq_trucks__plate":
                raise TruckPlateAlreadyExistsError from exc
            raise
        except Exception:
            self.db.rollback()
            raise
        return truck
