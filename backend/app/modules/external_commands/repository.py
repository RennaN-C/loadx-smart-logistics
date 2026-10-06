import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.external_commands.models import ExternalCommand


class ExternalCommandRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def claim(
        self,
        *,
        integration_id: str,
        event_hash: str,
        fingerprint: str,
        user_id: uuid.UUID,
        command: str,
        expires_at: datetime,
    ) -> tuple[ExternalCommand, bool]:
        """Unique index waits for another transaction; rollback lets retry claim."""
        claimed_id = self.db.scalar(
            insert(ExternalCommand)
            .values(
                id=uuid.uuid4(),
                integration_id=integration_id,
                event_hash=event_hash,
                fingerprint=fingerprint,
                user_id=user_id,
                command=command,
                expires_at=expires_at,
            )
            .on_conflict_do_nothing(index_elements=["integration_id", "event_hash"])
            .returning(ExternalCommand.id)
        )
        row = self.db.scalar(
            select(ExternalCommand).where(
                ExternalCommand.integration_id == integration_id,
                ExternalCommand.event_hash == event_hash,
            )
        )
        if row is None:
            raise RuntimeError("command claim unavailable")
        return row, claimed_id is not None

    def complete(self, row: ExternalCommand, completed_at: datetime) -> None:
        row.completed_at = completed_at
        self.db.flush()
