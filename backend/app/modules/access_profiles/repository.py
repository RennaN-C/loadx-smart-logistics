import uuid

from sqlalchemy import asc, delete, desc, func, select, text
from sqlalchemy.orm import Session

from app.modules.access_profiles.models import AccessProfile, ProfilePermission


class ProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def serialize_mutations(self) -> None:
        self.db.execute(text("SELECT pg_advisory_xact_lock(112159)"))

    def get(self, identity: uuid.UUID, *, shared: bool = False, lock: bool = False):
        query = (
            select(AccessProfile)
            .where(AccessProfile.id == identity)
            .execution_options(populate_existing=True)
        )
        if shared or lock:
            query = query.with_for_update(read=shared)
        return self.db.scalar(query)

    def list(self, offset: int, limit: int, sort_order: str = "desc"):
        direction = asc if sort_order == "asc" else desc
        return self.db.scalars(
            select(AccessProfile)
            .order_by(direction(AccessProfile.created_at), direction(AccessProfile.id))
            .offset(offset)
            .limit(limit)
        ).all()

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(AccessProfile)) or 0

    def names(self, identities):
        if not identities:
            return {}
        return dict(
            self.db.execute(
                select(AccessProfile.id, AccessProfile.name).where(
                    AccessProfile.id.in_(identities)
                )
            ).all()
        )

    def grants(self, identities):
        if not identities:
            return {}
        result = {}
        for identity, code in self.db.execute(
            select(
                ProfilePermission.profile_id, ProfilePermission.permission_code
            ).where(ProfilePermission.profile_id.in_(identities))
        ):
            result.setdefault(identity, []).append(code)
        return {identity: sorted(codes) for identity, codes in result.items()}

    def set_grants(self, identity, codes):
        self.db.execute(
            delete(ProfilePermission).where(ProfilePermission.profile_id == identity)
        )
        self.db.add_all(
            ProfilePermission(profile_id=identity, permission_code=code)
            for code in codes
        )
