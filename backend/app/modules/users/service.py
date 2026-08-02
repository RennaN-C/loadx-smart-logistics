import uuid
from collections.abc import Callable, Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.integrity import get_integrity_constraint_name
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserUpdate


class UserNotFoundError(Exception):
    pass


class UserEmailAlreadyExistsError(Exception):
    pass


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = UserRepository(db)

    def list_users(self) -> Sequence[User]:
        return self.repository.list()

    def has_users(self) -> bool:
        return self.repository.has_any()

    def get_user(self, user_id: uuid.UUID) -> User:
        user = self.repository.get(user_id)
        if user is None:
            raise UserNotFoundError
        return user

    def get_user_by_email(self, email: str) -> User | None:
        return self.repository.get_by_email(email)

    def create_user(self, data: UserCreate) -> User:
        if self.repository.get_by_email(data.email) is not None:
            raise UserEmailAlreadyExistsError

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

        password = update_data.pop("password", None)
        if password is not None:
            user.password_hash = hash_password(password)

        for field_name, value in update_data.items():
            setattr(user, field_name, value)

        return self._persist(lambda: self.repository.update(user))

    def _persist(self, operation: Callable[[], User]) -> User:
        try:
            user = operation()
            self.db.commit()
            self.db.refresh(user)
        except IntegrityError as exc:
            self.db.rollback()
            if get_integrity_constraint_name(exc) == "uq_users__email":
                raise UserEmailAlreadyExistsError from exc
            raise
        return user
