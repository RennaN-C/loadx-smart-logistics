from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.company_profile.models import PROFILE_ID, CompanyProfile


class CompanyProfileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self) -> CompanyProfile | None:
        return self.db.get(CompanyProfile, PROFILE_ID)

    def lock_or_create(
        self, values: dict[str, str | None]
    ) -> tuple[CompanyProfile, bool]:
        created = (
            self.db.scalar(
                insert(CompanyProfile)
                .values(id=PROFILE_ID, **values)
                .on_conflict_do_nothing(index_elements=[CompanyProfile.id])
                .returning(CompanyProfile.id)
            )
            is not None
        )
        profile = self.db.scalar(
            select(CompanyProfile)
            .where(CompanyProfile.id == PROFILE_ID)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        assert profile is not None
        return profile, created
