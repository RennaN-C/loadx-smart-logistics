import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.organizations.models import (
    LEGACY_ORGANIZATION_ID,
    Organization,
    OrganizationMembership,
)
from app.modules.users.models import User


class LegacyOrganizationMissingError(RuntimeError):
    pass


class OrganizationMembershipRepository:
    """Membership persistence used by the single-organization compatibility path."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def sync_legacy_membership(self, user: User) -> OrganizationMembership:
        organization = self.db.get(Organization, LEGACY_ORGANIZATION_ID)
        if organization is None or organization.status != "ACTIVE":
            raise LegacyOrganizationMissingError(
                "A organização legada ativa não foi inicializada."
            )

        membership = self.db.scalar(
            select(OrganizationMembership)
            .where(
                OrganizationMembership.organization_id == LEGACY_ORGANIZATION_ID,
                OrganizationMembership.user_id == user.id,
            )
            .with_for_update()
        )
        if membership is None:
            membership = OrganizationMembership(
                organization_id=LEGACY_ORGANIZATION_ID,
                user_id=user.id,
                role=user.role,
                custom_profile_id=user.custom_profile_id,
                driver_id=user.driver_id,
                status="ACTIVE",
            )
            self.db.add(membership)
        else:
            # Transitional mirror only: current authorization still reads User.
            # Membership status is deliberately not overwritten by user edits.
            membership.role = user.role
            membership.custom_profile_id = user.custom_profile_id
            membership.driver_id = user.driver_id
            self.db.add(membership)

        self.db.flush()
        return membership

    def active_organization_id_for_user(self, user_id: uuid.UUID) -> uuid.UUID | None:
        return self.db.scalar(
            select(OrganizationMembership.organization_id)
            .join(
                Organization,
                Organization.id == OrganizationMembership.organization_id,
            )
            .where(
                OrganizationMembership.organization_id == LEGACY_ORGANIZATION_ID,
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.status == "ACTIVE",
                Organization.status == "ACTIVE",
            )
            .order_by(
                OrganizationMembership.created_at.asc(),
                OrganizationMembership.id.asc(),
            )
            .limit(1)
        )

    def has_membership_for_user(self, user_id: uuid.UUID) -> bool:
        return (
            self.db.scalar(
                select(OrganizationMembership.id)
                .where(OrganizationMembership.user_id == user_id)
                .limit(1)
            )
            is not None
        )

    def is_active_member(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> bool:
        return (
            self.db.scalar(
                select(OrganizationMembership.id)
                .join(
                    Organization,
                    Organization.id == OrganizationMembership.organization_id,
                )
                .where(
                    OrganizationMembership.organization_id == LEGACY_ORGANIZATION_ID,
                    OrganizationMembership.user_id == user_id,
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.status == "ACTIVE",
                    Organization.status == "ACTIVE",
                )
                .limit(1)
            )
            is not None
        )
