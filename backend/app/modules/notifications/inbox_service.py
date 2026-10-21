import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PaginationParams
from app.modules.access_profiles.catalog import Permission, has_permission
from app.modules.deliveries.reference_service import DeliveryReferenceService
from app.modules.drivers.service import DriverNotFoundError, DriverService
from app.modules.notifications.inbox_repository import InboxRepository
from app.modules.notifications.schemas import (
    EVENT_CATEGORIES,
    NotificationPage,
    NotificationRead,
    PreferenceRead,
    PreferencesRead,
    PreferencesWrite,
)
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService
from app.modules.users.models import User
from app.modules.users.service import UserService


class InboxService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = InboxRepository(db)

    def stage_recipients(self, notification) -> None:
        codes = (Permission.TRIPS_READ,)
        if notification.event_type == "OCCURRENCE_REGISTERED":
            codes += (Permission.OCCURRENCES_READ,)
        eligible = UserService(self.db).notification_recipient_ids(
            codes, notification.recipient_driver_id
        )
        self.repository.stage_recipients(
            notification.id, EVENT_CATEGORIES[notification.event_type], eligible
        )

    def _visible(self, user: User):
        events = []
        if has_permission(user, Permission.TRIPS_READ):
            events.append("TRIP_STARTED")
            if has_permission(user, Permission.OCCURRENCES_READ):
                events.append("OCCURRENCE_REGISTERED")
            return self.repository.visible(user.id, events)
        if has_permission(user, Permission.TRIPS_OWN) and user.driver_id:
            try:
                driver = DriverService(self.db).get_driver(user.driver_id)
            except DriverNotFoundError:
                driver = None
            if driver is not None and driver.active:
                return self.repository.visible(
                    user.id,
                    tuple(EVENT_CATEGORIES),
                    driver_id=driver.id,
                    trip_ids=DeliveryReferenceService(self.db).trip_ids_for_driver(
                        driver.id
                    ),
                )
        return self.repository.visible(user.id, ())

    @staticmethod
    def _read(row) -> NotificationRead:
        titles = {
            "TRIP_STARTED": "Viagem iniciada",
            "OCCURRENCE_REGISTERED": "Nova ocorrência",
        }
        return NotificationRead(
            id=row["id"],
            event_type=row["event_type"],
            category=EVENT_CATEGORIES[row["event_type"]],
            title=titles[row["event_type"]],
            summary=f"Atualização operacional na viagem {str(row['trip_id'])[:8]}.",
            created_at=row["created_at"],
            received_at=row["received_at"],
            read_at=row["read_at"],
        )

    def list_notifications(
        self,
        user: User,
        pagination: PaginationParams,
        *,
        event_type=None,
        category=None,
        read=None,
    ) -> NotificationPage:
        if category is not None:
            matching = [
                event for event, value in EVENT_CATEGORIES.items() if value == category
            ]
            if not matching or (event_type is not None and event_type not in matching):
                event_type = "NO_APPROVED_EVENT"
            else:
                event_type = matching[0]
        all_visible = self._visible(user)
        rows, total, unread = self.repository.page(
            all_visible, pagination, event_type=event_type, read=read
        )
        return NotificationPage(
            items=[self._read(row) for row in rows],
            page=pagination.page,
            page_size=pagination.page_size,
            total=total,
            total_pages=(total + pagination.page_size - 1) // pagination.page_size,
            unread_count=unread,
        )

    def unread_count(self, user: User) -> int:
        return self.repository.unread_count(self._visible(user))

    def _get(self, user: User, identifier: uuid.UUID):
        row = self.repository.get(self._visible(user), identifier)
        if row is None:
            raise ApiError(
                404,
                "NOTIFICATION_NOT_FOUND",
                "Notificação não encontrada ou indisponível.",
            )
        return row

    def mark_read(self, user: User, identifier: uuid.UUID) -> NotificationRead:
        self._get(user, identifier)
        try:
            self.repository.mark_read(self._visible(user), user.id, identifier)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self._read(self._get(user, identifier))

    def mark_all_read(self, user: User) -> int:
        try:
            updated = self.repository.mark_read(self._visible(user), user.id)
            self.db.commit()
            return updated
        except Exception:
            self.db.rollback()
            raise

    def source(self, user: User, identifier: uuid.UUID) -> str:
        from app.modules.deliveries.service import (
            TripAccessForbiddenError,
            TripNotFoundError,
            TripService,
        )
        from app.modules.occurrences.service import (
            OccurrenceAccessForbiddenError,
            OccurrenceNotFoundError,
            OccurrenceService,
        )

        row = self._get(user, identifier)
        try:
            TripService(self.db).get_trip(row["trip_id"], current_user=user)
            if row["occurrence_id"]:
                OccurrenceService(self.db).get_occurrence_for_access(
                    row["occurrence_id"], current_user=user
                )
        except (
            TripAccessForbiddenError,
            TripNotFoundError,
            OccurrenceAccessForbiddenError,
            OccurrenceNotFoundError,
        ):
            raise ApiError(
                404, "NOTIFICATION_NOT_FOUND", "Origem indisponível para sua conta."
            ) from None
        return f"/trips/{row['trip_id']}"

    def preferences(self, user: User) -> PreferencesRead:
        current = self.repository.preferences(user.id)
        return PreferencesRead(
            items=[
                PreferenceRead(
                    category=category,
                    enabled=current.get(category, True),
                    mandatory=category == "SECURITY",
                )
                for category in ("TRIPS", "OCCURRENCES", "SECURITY")
            ]
        )

    def save_preferences(self, user: User, data: PreferencesWrite) -> PreferencesRead:
        try:
            changed = self.repository.save_preferences(
                user.id, sorted(data.items, key=lambda item: item.category)
            )
            if changed:
                AuditService(self.db).stage_administrative_event(
                    AuditEventCreate(
                        event_type="USER_UPDATED",
                        entity_type="USER",
                        entity_id=user.id,
                        actor_id=user.id,
                        changed_fields=[
                            f"notification_preferences.{category}"
                            for category in changed
                        ],
                    )
                )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.preferences(user)
