from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PageResult, PaginationParams
from app.database.integrity import get_integrity_constraint_name
from app.modules.drivers.document_history import stage_document_audit
from app.modules.drivers.document_repository import DocumentRepository
from app.modules.drivers.document_schemas import (
    LICENSE_CATEGORIES,
    DocumentCreate,
    DocumentTypeCreate,
    PolicyUpdate,
)
from app.modules.drivers.models import (
    CNH_TYPE_ID,
    DriverDocument,
    DriverDocumentPolicy,
    DriverDocumentType,
)
from app.modules.drivers.service import DriverService
from app.shared.record_lifecycle import ensure_record_active
from app.shared.validators import CNH


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.drivers = DriverService(db)
        self.repository = DocumentRepository(db)

    def types(self) -> list[DriverDocumentType]:
        return self.repository.types()

    def approve_type(
        self, data: DocumentTypeCreate, *, actor: uuid.UUID
    ) -> DriverDocumentType:
        try:
            record = self.repository.save(DriverDocumentType(**data.model_dump()))
            stage_document_audit(
                self.db,
                record,
                "DRIVER_DOCUMENT_TYPE_APPROVED",
                "DRIVER_DOCUMENT_TYPE",
                actor,
            )
            self.db.commit()
            self.db.refresh(record)
            return record
        except IntegrityError as error:
            self.db.rollback()
            if get_integrity_constraint_name(error) != "uq_driver_document_types__code":
                raise
            raise ApiError(
                409,
                "DRIVER_DOCUMENT_TYPE_DUPLICATE",
                "Código de tipo documental já cadastrado.",
            ) from error
        except Exception:
            self.db.rollback()
            raise

    def get_type(self, identifier: uuid.UUID) -> DriverDocumentType:
        record = self.repository.get_type(identifier)
        if record is None:
            raise ApiError(
                404, "DRIVER_DOCUMENT_TYPE_NOT_FOUND", "Tipo documental não aprovado."
            )
        return record

    def list_documents(
        self, driver_id: uuid.UUID, pagination: PaginationParams
    ) -> PageResult[DriverDocument]:
        self.drivers.get_driver(driver_id)
        return self.repository.list_documents(driver_id, pagination)

    def policies(self, driver_id: uuid.UUID) -> list[DriverDocumentPolicy]:
        self.drivers.get_driver(driver_id)
        return self.repository.policies(driver_id)

    @staticmethod
    def validate_license(data: DocumentCreate) -> None:
        if data.document_type_id != CNH_TYPE_ID:
            if data.category is not None:
                raise ApiError(
                    422, "DRIVER_DOCUMENT_INVALID", "Categoria pertence somente à CNH."
                )
            return
        try:
            TypeAdapter(CNH).validate_python(data.reference)
        except ValidationError as error:
            raise ApiError(
                422, "DRIVER_LICENSE_INVALID", "Informe CNH válida de 11 dígitos."
            ) from error
        if data.category is not None and data.category not in LICENSE_CATEGORIES:
            raise ApiError(
                422,
                "DRIVER_LICENSE_CATEGORY_INVALID",
                "Categoria fora do catálogo operacional atual.",
            )
        if data.expires_at is None:
            raise ApiError(
                422,
                "DRIVER_LICENSE_EXPIRY_REQUIRED",
                "Informe a validade da nova versão da CNH.",
            )

    def replace_current(
        self,
        driver_id: uuid.UUID,
        data: DocumentCreate,
        replacing: uuid.UUID | None,
        actor: uuid.UUID,
    ) -> None:
        current = self.repository.current(driver_id, data.document_type_id)
        if replacing is None:
            if current is not None:
                raise ApiError(
                    409,
                    "DRIVER_DOCUMENT_DUPLICATE",
                    "Tipo já possui versão corrente; utilize renovação.",
                )
            return
        old = self.repository.get(driver_id, replacing)
        if old is None:
            raise ApiError(
                404,
                "DRIVER_DOCUMENT_NOT_FOUND",
                "Documento não encontrado para este motorista.",
            )
        if (
            current is None
            or current.id != old.id
            or old.document_type_id != data.document_type_id
        ):
            raise ApiError(
                409,
                "DRIVER_DOCUMENT_NOT_CURRENT",
                "Renove a versão corrente do mesmo tipo.",
            )
        if all(getattr(old, key) == value for key, value in data.model_dump().items()):
            raise ApiError(
                409, "DRIVER_DOCUMENT_DUPLICATE", "Renovação deve alterar o documento."
            )
        old.superseded_at = datetime.now(UTC)
        self.repository.save(old)
        stage_document_audit(
            self.db, old, "DRIVER_DOCUMENT_RENEWED", "DRIVER_DOCUMENT", actor
        )

    def create(
        self,
        driver_id: uuid.UUID,
        data: DocumentCreate,
        *,
        actor: uuid.UUID,
        replacing: uuid.UUID | None = None,
    ) -> DriverDocument:
        try:
            driver = self.drivers.get_driver_for_update(driver_id)
            ensure_record_active(driver, "DRIVER")
            self.get_type(data.document_type_id)
            self.validate_license(data)
            self.replace_current(driver_id, data, replacing, actor)
            if data.document_type_id == CNH_TYPE_ID:
                driver.license_number = data.reference
                driver.license_category = data.category
                driver.license_expires_at = data.expires_at
            record = self.repository.save(
                DriverDocument(driver_id=driver_id, **data.model_dump())
            )
            stage_document_audit(
                self.db, record, "DRIVER_DOCUMENT_CREATED", "DRIVER_DOCUMENT", actor
            )
            self.db.commit()
            self.db.refresh(record)
            return record
        except IntegrityError as error:
            self.db.rollback()
            constraint = get_integrity_constraint_name(error)
            if constraint not in {"uq_drivers__license_number", "uq_driver_documents__current_type"}:
                raise
            code = (
                "DRIVER_LICENSE_NUMBER_ALREADY_EXISTS"
                if get_integrity_constraint_name(error) == "uq_drivers__license_number"
                else "DRIVER_DOCUMENT_DUPLICATE"
            )
            raise ApiError(409, code, "CNH ou versão corrente duplicada.") from error
        except Exception:
            self.db.rollback()
            raise

    def update_policy(
        self,
        driver_id: uuid.UUID,
        type_id: uuid.UUID,
        data: PolicyUpdate,
        *,
        actor: uuid.UUID,
    ) -> DriverDocumentPolicy:
        try:
            driver = self.drivers.get_driver_for_update(driver_id)
            ensure_record_active(driver, "DRIVER")
            self.get_type(type_id)
            if type_id != CNH_TYPE_ID and data.allowed_categories:
                raise ApiError(
                    422,
                    "DRIVER_DOCUMENT_POLICY_INVALID",
                    "Categorias aceitas pertencem somente à política CNH.",
                )
            policy = next(
                (
                    row
                    for row in self.repository.policies(driver_id)
                    if row.document_type_id == type_id
                ),
                None,
            )
            changed = policy is None or (
                policy.required,
                policy.allowed_categories,
            ) != (data.required, data.allowed_categories)
            if policy is None:
                policy = DriverDocumentPolicy(
                    driver_id=driver_id, document_type_id=type_id
                )
            policy.required = data.required
            policy.allowed_categories = list(data.allowed_categories)
            self.repository.save(policy)
            if changed:
                stage_document_audit(
                    self.db,
                    policy,
                    "DRIVER_DOCUMENT_POLICY_UPDATED",
                    "DRIVER_DOCUMENT_POLICY",
                    actor,
                )
            self.db.commit()
            self.db.refresh(policy)
            return policy
        except Exception:
            self.db.rollback()
            raise
