import uuid

from sqlalchemy import Select, asc, delete, desc, func, select, text
from sqlalchemy.orm import Session

from app.modules.access_profiles.models import AccessProfile, ProfilePermission
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID


class ProfileRepository:
    def __init__(
        self, db: Session, organization_id: uuid.UUID = LEGACY_ORGANIZATION_ID
    ):
        self.db = db
        self.organization_id = organization_id

    def serialize_mutations(self) -> None:
        self.db.execute(text("SELECT pg_advisory_xact_lock(112159)"))

    def get(self, identity: uuid.UUID, *, shared: bool = False, lock: bool = False):
        query = (
            select(AccessProfile)
            .where(
                AccessProfile.id == identity,
                AccessProfile.organization_id == self.organization_id,
            )
            .execution_options(populate_existing=True)
        )
        if shared or lock:
            query = query.with_for_update(read=shared)
        return self.db.scalar(query)

    def list(self, offset: int, limit: int, sort_order: str = "desc"):
        direction = asc if sort_order == "asc" else desc
        return self.db.scalars(
            select(AccessProfile)
            .where(AccessProfile.organization_id == self.organization_id)
            .order_by(direction(AccessProfile.created_at), direction(AccessProfile.id))
            .offset(offset)
            .limit(limit)
        ).all()

    def count(self) -> int:
        statement = (
            select(func.count())
            .select_from(AccessProfile)
            .where(AccessProfile.organization_id == self.organization_id)
        )
        return self.db.scalar(statement) or 0

    def names(self, identities):
        if not identities:
            return {}
        return dict(
            self.db.execute(
                select(AccessProfile.id, AccessProfile.name).where(
                    AccessProfile.id.in_(identities),
                    AccessProfile.organization_id == self.organization_id,
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
            ).where(
                ProfilePermission.profile_id.in_(identities),
                ProfilePermission.organization_id == self.organization_id,
            )
        ):
            result.setdefault(identity, []).append(code)
        return {identity: sorted(codes) for identity, codes in result.items()}

    def set_grants(self, identity, codes):
        self.db.execute(
            delete(ProfilePermission).where(
                ProfilePermission.profile_id == identity,
                ProfilePermission.organization_id == self.organization_id,
            )
        )
        self.db.add_all(
            ProfilePermission(
                organization_id=self.organization_id,
                profile_id=identity,
                permission_code=code,
            )
            for code in codes
        )

    def ids_with_permissions(self, codes: tuple[str, ...]) -> Select[tuple[uuid.UUID]]:
        return select(AccessProfile.id).where(
            AccessProfile.active.is_(True),
            AccessProfile.organization_id == self.organization_id,
            *(
                select(ProfilePermission.profile_id)
                .where(
                    ProfilePermission.profile_id == AccessProfile.id,
                    ProfilePermission.organization_id == self.organization_id,
                    ProfilePermission.permission_code == code,
                )
                .exists()
                for code in codes
            ),
        )
