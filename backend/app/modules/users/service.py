import uuid
from collections.abc import Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.core.security import hash_password
from app.core.security_events import SecurityEvent, emit_security_event
from app.database.integrity import get_integrity_constraint_name
from app.modules.auth.sessions import AuthSessionService
from app.modules.drivers.service import DriverNotFoundError, DriverService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserUpdate


class UserNotFoundError(Exception):
    pass


class UserEmailAlreadyExistsError(Exception):
    pass


class UserLastActiveAdminRequiredError(Exception):
    pass


class UserDriverNotFoundError(Exception):
    pass


class UserDriverAlreadyLinkedError(Exception):
    pass


class UserDriverRoleRequiredError(Exception):
    pass


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = UserRepository(db)
        self.auth_sessions = AuthSessionService(db)
        self.driver_service = DriverService(db)

    def list_users(self, pagination: PaginationParams) -> PageResult[User]:
        return self.repository.list(pagination)

    def has_users(self) -> bool:
        return self.repository.has_any()

    def get_user(self, user_id: uuid.UUID) -> User:
        user = self.repository.get(user_id)
        if user is None:
            raise UserNotFoundError
        return user

    def get_user_by_email(self, email: str) -> User | None:
        return self.repository.get_by_email(email)

    def upgrade_password_hash(self, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        return self._persist(lambda: self.repository.update(user))

    def create_user(self, data: UserCreate) -> User:
        if self.repository.get_by_email(data.email) is not None:
            raise UserEmailAlreadyExistsError
        self._ensure_driver_link_is_valid(data.role, data.driver_id)

        user_data = data.model_dump(exclude={"password"})
        user = User(**user_data, password_hash=hash_password(data.password))
        return self._persist(lambda: self.repository.add(user))

    def update_user(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        user = self.get_user(user_id)
        update_data = data.model_dump(exclude_unset=True)

        new_email = update_data.get("email")
        if new_email is not None and new_email != user.email:
            existing_user = self.repository.get_by_email(new_email)
            if existing_user is not None and existing_user.id != user.id:
                raise UserEmailAlreadyExistsError

        self._ensure_active_admin_remains(user.id, update_data)

        final_role = update_data.get("role", user.role)
        final_driver_id = update_data.get("driver_id", user.driver_id)
        self._ensure_driver_link_is_valid(
            str(final_role),
            final_driver_id if isinstance(final_driver_id, uuid.UUID) else None,
            current_user_id=user.id,
        )

        password = update_data.pop("password", None)
        password_changed = password is not None
        if password is not None:
            user.password_hash = hash_password(password)

        role_changed = "role" in update_data and update_data["role"] != user.role
        user_deactivated = update_data.get("active") is False and user.active
        driver_link_changed = (
            "driver_id" in update_data and update_data["driver_id"] != user.driver_id
        )

        for field_name, value in update_data.items():
            setattr(user, field_name, value)

        def persist_user_and_revoke_sessions() -> User:
            updated_user = self.repository.update(user)
            if (
                password_changed
                or role_changed
                or user_deactivated
                or driver_link_changed
            ):
                self.auth_sessions.stage_revoke_all_for_user(user.id)
            return updated_user

        updated_user = self._persist(persist_user_and_revoke_sessions)
        if password_changed or role_changed or user_deactivated or driver_link_changed:
            emit_security_event(
                SecurityEvent.USER_SECURITY_STATE_CHANGED,
                alert=role_changed or user_deactivated,
                user_id=str(user.id),
                password_changed=password_changed,
                role_changed=role_changed,
                user_deactivated=user_deactivated,
                driver_link_changed=driver_link_changed,
            )
        return updated_user

    def _ensure_driver_link_is_valid(
        self,
        role: str,
        driver_id: uuid.UUID | None,
        *,
        current_user_id: uuid.UUID | None = None,
    ) -> None:
        if driver_id is None:
            return
        if role != "DRIVER":
            raise UserDriverRoleRequiredError
        try:
            self.driver_service.get_driver(driver_id)
        except DriverNotFoundError as exc:
            raise UserDriverNotFoundError from exc
        linked_user = self.repository.get_by_driver_id(driver_id)
        if linked_user is not None and linked_user.id != current_user_id:
            raise UserDriverAlreadyLinkedError

    def _ensure_active_admin_remains(
        self,
        user_id: uuid.UUID,
        update_data: dict[str, object],
    ) -> None:
        deactivates_user = update_data.get("active") is False
        removes_admin_role = "role" in update_data and update_data["role"] != "ADMIN"
        if not deactivates_user and not removes_admin_role:
            return

        active_admin_ids = set(self.repository.lock_active_admin_ids())
        if user_id in active_admin_ids and len(active_admin_ids) == 1:
            self.db.rollback()
            raise UserLastActiveAdminRequiredError

    def _persist(self, operation: Callable[[], User]) -> User:
        try:
            user = operation()
            self.db.commit()
            self.db.refresh(user)
        except IntegrityError as exc:
            self.db.rollback()
            constraint_name = get_integrity_constraint_name(exc)
            if constraint_name == "uq_users__email":
                raise UserEmailAlreadyExistsError from exc
            if constraint_name == "uq_users__driver_id":
                raise UserDriverAlreadyLinkedError from exc
            if constraint_name == "fk_users__drivers":
                raise UserDriverNotFoundError from exc
            raise
        except Exception:
            self.db.rollback()
            raise
        return user
