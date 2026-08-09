from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import AuthLoginThrottle


class AuthLoginThrottleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_update(
        self,
        scope: str,
        subject_hash: str,
    ) -> AuthLoginThrottle | None:
        statement = (
            select(AuthLoginThrottle)
            .where(
                AuthLoginThrottle.scope == scope,
                AuthLoginThrottle.subject_hash == subject_hash,
            )
            .with_for_update()
        )
        return self.db.scalar(statement)

    def add(self, throttle: AuthLoginThrottle) -> AuthLoginThrottle:
        self.db.add(throttle)
        self.db.flush()
        return throttle

    def delete(self, throttle: AuthLoginThrottle) -> None:
        self.db.delete(throttle)
