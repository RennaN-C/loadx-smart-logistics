import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.company_profile.models import CompanyProfile
from app.modules.company_profile.repository import CompanyProfileRepository
from app.modules.company_profile.schemas import CompanyProfileInput
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService


class CompanyProfileService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CompanyProfileRepository(db)
        self.audit = AuditService(db)

    def get(self) -> CompanyProfile | None:
        return self.repository.get()

    def update(self, data: CompanyProfileInput, actor_id: uuid.UUID) -> CompanyProfile:
        values = data.model_dump()
        try:
            profile, created = self.repository.lock_or_create(values)
            changed = (
                list(values)
                if created
                else [
                    key
                    for key, value in values.items()
                    if getattr(profile, key) != value
                ]
            )
            for key, value in values.items():
                setattr(profile, key, value)
            if changed:
                profile.updated_at = datetime.now(timezone.utc)
                self.audit.stage_administrative_event(
                    AuditEventCreate(
                        event_type="COMPANY_PROFILE_CREATED"
                        if created
                        else "COMPANY_PROFILE_UPDATED",
                        entity_type="COMPANY_PROFILE",
                        entity_id=profile.id,
                        actor_id=actor_id,
                        changed_fields=changed,
                    )
                )
            self.db.commit()
            self.db.refresh(profile)
            return profile
        except Exception:
            self.db.rollback()
            raise
