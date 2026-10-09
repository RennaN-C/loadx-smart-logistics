import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PageResult, PaginationParams
from app.database.integrity import get_integrity_constraint_name
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService
from app.modules.trucks.document_repository import DocumentRepository
from app.modules.trucks.document_schemas import DocumentCreate, PolicyUpdate
from app.modules.trucks.models import TruckDocument, TruckDocumentPolicy
from app.modules.trucks.service import TruckService
from app.shared.record_lifecycle import ensure_record_active


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trucks = TruckService(db)
        self.repository = DocumentRepository(db)

    def list(
        self, truck_id: uuid.UUID, pagination: PaginationParams
    ) -> PageResult[TruckDocument]:
        self.trucks.get_truck(truck_id)
        return self.repository.list(truck_id, pagination)

    def policies(self, truck_id: uuid.UUID) -> list[TruckDocumentPolicy]:
        self.trucks.get_truck(truck_id)
        return self.repository.policies(truck_id)

    def stage_audit(self, record, event: str, actor: uuid.UUID) -> None:
        AuditService(self.db).stage_administrative_event(
            AuditEventCreate(
                event_type=event,
                entity_type="TRUCK_DOCUMENT_POLICY"
                if isinstance(record, TruckDocumentPolicy)
                else "TRUCK_DOCUMENT",
                entity_id=record.id,
                actor_id=actor,
                changed_fields=["required"]
                if isinstance(record, TruckDocumentPolicy)
                else [
                    "kind",
                    "reference",
                    "issued_at",
                    "expires_at",
                    "file_reference",
                    "superseded_at",
                ],
            )
        )

    def create(
        self,
        truck_id: uuid.UUID,
        data: DocumentCreate,
        *,
        actor: uuid.UUID,
        replacing: uuid.UUID | None = None,
    ) -> TruckDocument:
        try:
            truck = self.trucks.get_truck_for_update(truck_id)
            ensure_record_active(truck, "TRUCK")
            current = self.repository.current(truck_id, data.kind)
            if replacing is not None:
                old = self.repository.get(truck_id, replacing)
                if old is None:
                    raise ApiError(
                        404,
                        "TRUCK_DOCUMENT_NOT_FOUND",
                        "Documento não encontrado para este caminhão.",
                    )
                if old.kind != data.kind or current is None or current.id != old.id:
                    raise ApiError(
                        409,
                        "TRUCK_DOCUMENT_NOT_CURRENT",
                        "Renove somente a versão corrente do mesmo tipo.",
                    )
                if all(
                    getattr(old, key) == value
                    for key, value in data.model_dump().items()
                ):
                    raise ApiError(
                        409,
                        "TRUCK_DOCUMENT_DUPLICATE",
                        "Renovação deve alterar os dados do documento.",
                    )
                old.superseded_at = datetime.now(UTC)
                self.repository.save(old)
                self.stage_audit(old, "TRUCK_DOCUMENT_RENEWED", actor)
            elif current is not None:
                raise ApiError(
                    409,
                    "TRUCK_DOCUMENT_DUPLICATE",
                    "Este tipo já possui documento corrente; utilize renovação.",
                )
            record = self.repository.save(
                TruckDocument(truck_id=truck_id, **data.model_dump())
            )
            self.stage_audit(record, "TRUCK_DOCUMENT_CREATED", actor)
            self.db.commit()
            self.db.refresh(record)
            return record
        except IntegrityError as error:
            self.db.rollback()
            if (
                get_integrity_constraint_name(error)
                == "uq_truck_documents__current_kind"
            ):
                raise ApiError(
                    409,
                    "TRUCK_DOCUMENT_DUPLICATE",
                    "Este tipo já possui documento corrente.",
                ) from error
            raise
        except Exception:
            self.db.rollback()
            raise

    def update_policy(
        self, truck_id: uuid.UUID, kind: str, data: PolicyUpdate, *, actor: uuid.UUID
    ) -> TruckDocumentPolicy:
        try:
            truck = self.trucks.get_truck_for_update(truck_id)
            ensure_record_active(truck, "TRUCK")
            policy = self.repository.policy(truck_id, kind)
            changed = policy is None or policy.required != data.required
            if policy is None:
                policy = TruckDocumentPolicy(
                    truck_id=truck_id, kind=kind, required=data.required
                )
            policy.required = data.required
            self.repository.save(policy)
            if changed:
                self.stage_audit(policy, "TRUCK_DOCUMENT_POLICY_UPDATED", actor)
            self.db.commit()
            self.db.refresh(policy)
            return policy
        except Exception:
            self.db.rollback()
            raise
