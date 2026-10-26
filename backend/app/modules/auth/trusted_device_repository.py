"""Trusted credentials; all writers must first lock the owning account."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.auth.models import AuthTrustedDevice


class TrustedDeviceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find(self, user_id: uuid.UUID, token_hash: str) -> AuthTrustedDevice | None:
        return self.db.scalar(
            select(AuthTrustedDevice)
            .where(
                AuthTrustedDevice.user_id == user_id,
                AuthTrustedDevice.token_hash == token_hash,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def list_live(self, user_id: uuid.UUID, now: datetime) -> list[AuthTrustedDevice]:
        return list(
            self.db.scalars(
                select(AuthTrustedDevice)
                .where(
                    AuthTrustedDevice.user_id == user_id,
                    AuthTrustedDevice.revoked_at.is_(None),
                    AuthTrustedDevice.expires_at > now,
                )
                .order_by(AuthTrustedDevice.created_at, AuthTrustedDevice.id)
            )
        )

    def add(self, device: AuthTrustedDevice) -> AuthTrustedDevice:
        self.db.add(device)
        self.db.flush()
        return device

    def revoke(
        self, user_id: uuid.UUID, now: datetime, device_id: uuid.UUID | None = None
    ) -> int:
        statement = update(AuthTrustedDevice).where(
            AuthTrustedDevice.user_id == user_id, AuthTrustedDevice.revoked_at.is_(None)
        )
        if device_id is not None:
            statement = statement.where(AuthTrustedDevice.id == device_id)
        return self.db.execute(statement.values(revoked_at=now)).rowcount
