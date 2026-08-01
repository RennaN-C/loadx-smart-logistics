import uuid
from collections.abc import Callable, Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.integrity import get_integrity_constraint_name
from app.modules.status_history.models import StatusHistory
from app.modules.status_history.repository import StatusHistoryRepository
from app.modules.status_history.schemas import StatusHistoryCreate
from app.modules.users.service import UserNotFoundError, UserService


class StatusHistoryNotFoundError(Exception):
    pass


class StatusHistoryChangedByNotFoundError(Exception):
    pass


class StatusHistoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = StatusHistoryRepository(db)
        self.user_service = UserService(db)

    def list_status_history(
        self,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> Sequence[StatusHistory]:
        normalized_entity_type = (
            entity_type.upper() if entity_type is not None else None
        )
        return self.repository.list(normalized_entity_type, entity_id)

    def get_status_history(self, status_history_id: uuid.UUID) -> StatusHistory:
        status_history = self.repository.get(status_history_id)
        if status_history is None:
            raise StatusHistoryNotFoundError
        return status_history

    def record_status_change(self, data: StatusHistoryCreate) -> StatusHistory:
        if data.changed_by is not None:
            self._ensure_changed_by_exists(data.changed_by)

        status_history = StatusHistory(**data.model_dump())
        return self._persist(lambda: self.repository.add(status_history))

    def _ensure_changed_by_exists(self, changed_by: uuid.UUID) -> None:
        try:
            self.user_service.get_user(changed_by)
        except UserNotFoundError as exc:
            raise StatusHistoryChangedByNotFoundError from exc

    def _persist(self, operation: Callable[[], StatusHistory]) -> StatusHistory:
        try:
            status_history = operation()
            self.db.commit()
            self.db.refresh(status_history)
        except IntegrityError as exc:
            self.db.rollback()
            if get_integrity_constraint_name(exc) == "fk_status_history__users":
                raise StatusHistoryChangedByNotFoundError from exc
            raise
        return status_history
