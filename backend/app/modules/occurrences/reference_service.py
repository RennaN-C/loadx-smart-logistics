from sqlalchemy.orm import Session

from app.modules.occurrences.repository import OccurrenceRepository


class OccurrenceReferenceService:
    """Fronteira pública de leitura para consumidores de ocorrências."""

    def __init__(self, db: Session) -> None:
        self.repository = OccurrenceRepository(db)

    def count_occurrences(self) -> int:
        return self.repository.count_all()
