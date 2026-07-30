import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.models import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> Sequence[User]:
        statement = select(User).order_by(User.created_at.desc(), User.email.asc())
        return self.db.scalars(statement).all()

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.db.scalar(statement)

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user
