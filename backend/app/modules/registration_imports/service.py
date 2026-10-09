import hashlib
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.database.integrity import get_integrity_constraint_name
from app.modules.customers.service import CustomerDocumentAlreadyExistsError
from app.modules.drivers.service import (
    DriverDocumentAlreadyExistsError,
    DriverLicenseNumberAlreadyExistsError,
)
from app.modules.products.service import ProductCodeAlreadyExistsError
from app.modules.registration_imports.csv_content import (
    ParsedImport,
    ParsedRow,
    parse_csv,
    row_error,
)
from app.modules.registration_imports.models import RegistrationImport
from app.modules.registration_imports.registry import (
    RegistrationAdapter,
    registration_adapter,
)
from app.modules.registration_imports.repository import ImportRepository
from app.modules.registration_imports.schemas import (
    ImportConfirm,
    ImportEntity,
    ImportFile,
    ImportListRead,
    ImportPreview,
    ImportPreviewRow,
    ImportRead,
)
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService
from app.modules.trucks.service import TruckPlateAlreadyExistsError
from app.modules.users.models import User
from app.modules.users.service import UserService

DUPLICATE_ERRORS = {
    CustomerDocumentAlreadyExistsError: "document",
    DriverDocumentAlreadyExistsError: "document",
    DriverLicenseNumberAlreadyExistsError: "license_number",
    ProductCodeAlreadyExistsError: "code",
    TruckPlateAlreadyExistsError: "plate",
}
DUPLICATE_CONSTRAINTS = {
    "uq_customers__document": "document",
    "uq_drivers__document": "document",
    "uq_drivers__license_number": "license_number",
    "uq_products__code": "code",
    "uq_trucks__plate": "plate",
}


class ImportForbiddenError(Exception):
    pass


class ImportNotFoundError(Exception):
    pass


class ImportIdentityConflictError(Exception):
    pass


class ImportPreviewMismatchError(Exception):
    pass


class ImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ImportRepository(db)

    def _authorize(self, current_user: User) -> User:
        actor = UserService(self.db).get_user_for_authorization(current_user.id)
        if not actor.active or actor.role not in {"ADMIN", "LOGISTICS_MANAGER"}:
            raise ImportForbiddenError
        return actor

    def template(self, entity: ImportEntity, *, current_user: User) -> bytes:
        self._authorize(current_user)
        schema = registration_adapter(self.db, entity).schema
        return (",".join(schema.model_fields) + "\r\n").encode("utf-8-sig")

    def preview(
        self, entity: ImportEntity, data: ImportFile, *, current_user: User
    ) -> ImportPreview:
        self._authorize(current_user)
        adapter = registration_adapter(self.db, entity)
        parsed = parse_csv(data, adapter.schema)
        self._duplicates(parsed, adapter)
        invalid_lines = {error.line for error in parsed.errors}
        valid_count = sum(row.line not in invalid_lines for row in parsed.rows)
        return ImportPreview(
            entity_type=entity,
            sha256=parsed.sha256,
            row_count=parsed.row_count,
            valid_count=valid_count,
            can_confirm=bool(parsed.row_count and not parsed.errors),
            errors=parsed.errors,
            rows=[
                ImportPreviewRow(line=row.line, data=row.data.model_dump(mode="json"))
                for row in parsed.rows
            ],
        )

    @staticmethod
    def _duplicates(parsed: ParsedImport, adapter: RegistrationAdapter) -> None:
        keys = {
            field: {getattr(row.data, field) for row in parsed.rows}
            for field in adapter.unique_fields
        }
        existing = adapter.existing(keys) if parsed.rows else {}
        for field in adapter.unique_fields:
            seen: dict[str, int] = {}
            marked: set[int] = set()
            for row in parsed.rows:
                value = getattr(row.data, field)
                if value in existing.get(field, set()):
                    parsed.errors.append(
                        row_error(
                            row.line,
                            field,
                            "DUPLICATE_EXISTING",
                            "Valor já usado por um cadastro, inclusive arquivado.",
                        )
                    )
                if value in seen:
                    first = seen[value]
                    if first not in marked:
                        parsed.errors.append(
                            row_error(
                                first,
                                field,
                                "DUPLICATE_IN_FILE",
                                "Valor repetido no arquivo após normalização.",
                            )
                        )
                        marked.add(first)
                    parsed.errors.append(
                        row_error(
                            row.line,
                            field,
                            "DUPLICATE_IN_FILE",
                            "Valor repetido no arquivo após normalização.",
                        )
                    )
                else:
                    seen[value] = row.line

    def confirm(
        self, entity: ImportEntity, data: ImportConfirm, *, current_user: User
    ) -> ImportRead:
        try:
            actor = self._authorize(current_user)
            adapter = registration_adapter(self.db, entity)
            parsed = parse_csv(data, adapter.schema)
            if parsed.sha256 != data.preview_sha256:
                raise ImportPreviewMismatchError
            fingerprint = hashlib.sha256(
                f"{entity}:{parsed.sha256}".encode()
            ).hexdigest()
            row, claimed = self.repository.claim(
                RegistrationImport(
                    id=uuid.uuid4(),
                    entity_type=entity,
                    recorded_by=actor.id,
                    event_id=data.event_id,
                    sha256=parsed.sha256,
                    fingerprint=fingerprint,
                    row_count=parsed.row_count,
                )
            )
            if (
                row.fingerprint != fingerprint
                or row.status == "PROCESSING"
                and not claimed
            ):
                raise ImportIdentityConflictError
            if claimed:
                self._duplicates(parsed, adapter)
                self._stage_result(row, parsed, adapter, actor.id)
            result = ImportRead.model_validate(row)
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    def _stage_result(
        self,
        result: RegistrationImport,
        parsed: ParsedImport,
        adapter: RegistrationAdapter,
        actor: uuid.UUID,
    ) -> None:
        records: list[dict] = []
        if not parsed.errors:
            current: ParsedRow | None = None
            try:
                with self.db.begin_nested():
                    for current in parsed.rows:
                        created = adapter.stage(current.data, actor)
                        records.append({"line": current.line, "id": str(created.id)})
            except (*DUPLICATE_ERRORS, IntegrityError) as error:
                field = DUPLICATE_ERRORS.get(type(error))
                if isinstance(error, IntegrityError):
                    field = DUPLICATE_CONSTRAINTS.get(
                        get_integrity_constraint_name(error)
                    )
                if current is None or field is None:
                    raise
                parsed.errors.append(
                    row_error(
                        current.line,
                        field,
                        "DUPLICATE_CONCURRENT",
                        "Unicidade alterada durante a confirmação; arquivo inteiro rejeitado.",
                    )
                )
                records.clear()
        result.status = "REJECTED" if parsed.errors else "COMPLETED"
        result.created_count = 0 if parsed.errors else parsed.row_count
        result.rejected_count = parsed.row_count if parsed.errors else 0
        result.errors = [error.model_dump() for error in parsed.errors]
        result.records = records
        self.db.flush()
        AuditService(self.db).stage_administrative_event(
            AuditEventCreate(
                event_type=f"IMPORT_{result.status}",
                entity_type="REGISTRATION_IMPORT",
                entity_id=result.id,
                actor_id=actor,
                changed_fields=[
                    "status",
                    "row_count",
                    "created_count",
                    "rejected_count",
                ],
            )
        )

    def get(self, key: uuid.UUID, *, current_user: User) -> ImportRead:
        self._authorize(current_user)
        row = self.repository.get(key)
        if row is None:
            raise ImportNotFoundError
        return ImportRead.model_validate(row)

    def list(
        self,
        pagination: PaginationParams,
        entity: ImportEntity | None,
        *,
        current_user: User,
    ) -> PageResult[ImportListRead]:
        self._authorize(current_user)
        page = self.repository.list(pagination, entity)
        return PageResult(
            tuple(ImportListRead.model_validate(row) for row in page.items),
            page.page,
            page.page_size,
            page.total,
            page.total_pages,
        )
