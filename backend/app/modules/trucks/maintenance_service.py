import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PageResult, PaginationParams
from app.modules.trucks.maintenance_repository import MaintenanceRepository
from app.modules.trucks.maintenance_schemas import MaintenanceClose, MaintenanceCreate
from app.modules.trucks.models import TruckMaintenance
from app.modules.trucks.service import TruckService
from app.shared.record_lifecycle import ensure_record_active


class MaintenanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trucks = TruckService(db)
        self.repository = MaintenanceRepository(db)

    def list(
        self, truck_id: uuid.UUID, pagination: PaginationParams
    ) -> PageResult[TruckMaintenance]:
        self.trucks.get_truck(truck_id)
        return self.repository.list(truck_id, pagination)

    def create(
        self, truck_id: uuid.UUID, data: MaintenanceCreate, *, actor: uuid.UUID
    ) -> TruckMaintenance:
        try:
            truck = self.trucks.get_truck_for_update(truck_id)
            ensure_record_active(truck, "TRUCK")
            if self.trucks.has_operation_conflict(truck_id):
                raise ApiError(
                    409,
                    "TRUCK_OPERATION_CONFLICT",
                    "Encerre a operação do caminhão antes de registrar manutenção.",
                )
            self.trucks.stage_odometer(truck, data.odometer_km, actor=actor)
            record = TruckMaintenance(truck_id=truck_id, **data.model_dump())
            if record.odometer_km is None:
                record.odometer_km = truck.odometer_km
            self.repository.save(record)
            self.trucks.stage_maintenance_audit(
                record.id, "MAINTENANCE_CREATED", data.model_fields_set, actor
            )
            self.db.commit()
            self.db.refresh(record)
            return record
        except Exception:
            self.db.rollback()
            raise

    def close(
        self,
        truck_id: uuid.UUID,
        identifier: uuid.UUID,
        data: MaintenanceClose,
        *,
        actor: uuid.UUID,
    ) -> TruckMaintenance:
        try:
            truck = self.trucks.get_truck_for_update(truck_id)
            record = self.repository.get_for_update(truck_id, identifier)
            if record is None:
                raise ApiError(
                    404,
                    "MAINTENANCE_NOT_FOUND",
                    "Manutenção não encontrada para este caminhão.",
                )
            if record.closed_at is not None:
                raise ApiError(
                    409, "MAINTENANCE_ALREADY_CLOSED", "Manutenção já encerrada."
                )
            # Closing a future window also cancels its planned unavailability.
            self.trucks.stage_odometer(truck, data.odometer_km, actor=actor)
            now = datetime.now(UTC)
            if data.next_service_at is not None and data.next_service_at <= now:
                raise ApiError(
                    422,
                    "NEXT_SERVICE_INVALID",
                    "A próxima revisão deve estar no futuro.",
                )
            if (
                data.next_service_km is not None
                and truck.odometer_km is not None
                and data.next_service_km <= truck.odometer_km
            ):
                raise ApiError(
                    422,
                    "NEXT_SERVICE_INVALID",
                    "A próxima revisão deve superar a quilometragem atual.",
                )
            record.closed_at = now
            record.completion_odometer_km = truck.odometer_km
            for field in ("next_service_at", "next_service_km"):
                if field in data.model_fields_set:
                    setattr(truck, field, getattr(data, field))
                setattr(record, field, getattr(truck, field))
            self.repository.save(record)
            self.trucks.stage_maintenance_audit(
                record.id,
                "MAINTENANCE_CLOSED",
                ["closed_at", *data.model_fields_set],
                actor,
            )
            self.db.commit()
            self.db.refresh(record)
            return record
        except Exception:
            self.db.rollback()
            raise
