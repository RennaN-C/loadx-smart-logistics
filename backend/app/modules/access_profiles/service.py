import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PageResult, PaginationParams
from app.modules.access_profiles.catalog import SYSTEM_LABELS, SYSTEM_PERMISSIONS
from app.modules.access_profiles.models import AccessProfile
from app.modules.access_profiles.repository import ProfileRepository
from app.modules.access_profiles.schemas import ProfileRead, ProfileUpdate, ProfileWrite
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService


class ProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ProfileRepository(db)

    def resolve(self, user, *, lock: bool = False) -> None:
        if user.role != "CUSTOM":
            return
        profile = self.repository.get(user.custom_profile_id, shared=lock)
        user._effective_permissions = ()
        user._custom_profile_name = profile.name if profile else None
        if profile and profile.active:
            user._effective_permissions = self.repository.grants([profile.id]).get(
                profile.id, []
            )

    def validate_assignment(self, role: str, identity: uuid.UUID | None) -> None:
        if role == "CUSTOM" or identity is not None:
            self.repository.serialize_mutations()
        if (role == "CUSTOM") != (identity is not None):
            raise ApiError(
                409,
                "USER_PROFILE_INVALID",
                "Selecione um perfil personalizado válido ou um perfil do sistema.",
            )
        if identity is not None:
            profile = self.repository.get(identity, shared=True)
            if profile is None or not profile.active:
                raise ApiError(
                    409,
                    "USER_PROFILE_INACTIVE",
                    "O perfil selecionado não existe ou está inativo.",
                )

    def list_profiles(self, pagination: PaginationParams):
        from app.modules.users.service import UserService

        counts = UserService(self.db).profile_counts()
        fixed_count = len(SYSTEM_LABELS)
        fixed_in_page = max(
            0, min(pagination.page_size, fixed_count - pagination.offset)
        )
        profiles = self.repository.list(
            max(0, pagination.offset - fixed_count),
            pagination.page_size - fixed_in_page,
        )
        grants = self.repository.grants([profile.id for profile in profiles])
        results = [
            ProfileRead(
                id=uuid.uuid5(uuid.NAMESPACE_URL, f"loadx:role:{role}"),
                name=name,
                description="Perfil protegido do sistema",
                active=True,
                version=1,
                permissions=sorted(SYSTEM_PERMISSIONS[role]),
                system_role=role,
                user_count=counts.get(role, 0),
            )
            for role, name in SYSTEM_LABELS.items()
        ]
        results = (
            results[pagination.offset : pagination.offset + fixed_in_page]
            if fixed_in_page
            else []
        )
        results.extend(
            self._read(profile, grants.get(profile.id, []), counts.get(profile.id, 0))
            for profile in profiles
        )
        return PageResult.create(
            results,
            pagination,
            fixed_count + self.repository.count(),
        )

    def get_profile(self, identity: uuid.UUID) -> ProfileRead:
        from app.modules.users.service import UserService

        profile = self.repository.get(identity)
        if profile is None:
            raise ApiError(
                404, "PROFILE_NOT_FOUND", "Perfil personalizado não encontrado."
            )
        return self._read(
            profile,
            self.repository.grants([identity]).get(identity, []),
            UserService(self.db).profile_counts().get(identity, 0),
        )

    def save(
        self,
        data: ProfileWrite,
        *,
        actor_id: uuid.UUID,
        identity: uuid.UUID | None = None,
    ) -> ProfileRead:
        from app.modules.users.service import UserService

        try:
            self.repository.serialize_mutations()
            users = UserService(self.db)
            members = users.lock_profile_members(identity) if identity else []
            profile = (
                self.repository.get(identity, lock=True)
                if identity
                else AccessProfile()
            )
            if profile is None:
                raise ApiError(
                    404, "PROFILE_NOT_FOUND", "Perfil personalizado não encontrado."
                )
            if (
                identity
                and isinstance(data, ProfileUpdate)
                and data.version != profile.version
            ):
                raise ApiError(
                    409,
                    "PROFILE_VERSION_CONFLICT",
                    "Este perfil foi alterado. Reabra o formulário antes de salvar.",
                )
            if not data.active and members:
                raise ApiError(
                    409,
                    "PROFILE_IN_USE",
                    "Remova os usuários associados antes de desativar este perfil.",
                )
            changed = [
                field
                for field in ("name", "description", "active")
                if getattr(profile, field, None) != getattr(data, field)
            ]
            old_grants = (
                self.repository.grants([identity]).get(identity, []) if identity else []
            )
            if old_grants != data.permissions:
                changed.append("permissions")
            profile.name, profile.name_key = data.name, data.name.lower()
            if profile.name_key in {name.lower() for name in SYSTEM_LABELS.values()} | {
                role.lower() for role in SYSTEM_LABELS
            }:
                raise ApiError(
                    409,
                    "PROFILE_NAME_RESERVED",
                    "Este nome identifica um perfil protegido do sistema.",
                )
            profile.description, profile.active = data.description, data.active
            profile.version = profile.version + 1 if identity else 1
            self.db.add(profile)
            self.db.flush()
            self.repository.set_grants(profile.id, data.permissions)
            if "permissions" in changed or "active" in changed:
                users.revoke_profile_members(members)
            if changed:
                AuditService(self.db).stage_administrative_event(
                    AuditEventCreate(
                        event_type="PROFILE_UPDATED" if identity else "PROFILE_CREATED",
                        entity_type="ACCESS_PROFILE",
                        entity_id=profile.id,
                        actor_id=actor_id,
                        changed_fields=changed,
                    )
                )
            self.db.commit()
            return self.get_profile(profile.id)
        except IntegrityError:
            self.db.rollback()
            raise ApiError(
                409,
                "PROFILE_CONFLICT",
                "Já existe um perfil com este nome ou a associação é inválida.",
            ) from None
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _read(profile, permissions, count):
        return ProfileRead(
            id=profile.id,
            name=profile.name,
            description=profile.description,
            active=profile.active,
            version=profile.version,
            permissions=permissions,
            user_count=count,
            created_at=profile.created_at,
        )

    def names(self, identities):
        return self.repository.names(identities)

    def serialize_mutations(self):
        self.repository.serialize_mutations()
