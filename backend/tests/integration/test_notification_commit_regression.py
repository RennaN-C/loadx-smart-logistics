"""Regression guarantees for durable domain commits and isolated mock failures."""

import uuid

import pytest
from sqlalchemy import delete, select

from app.integrations.whatsapp import MockWhatsAppProvider, OutgoingWhatsAppMessage
from app.modules.deliveries.models import Trip
from app.modules.notifications.models import OperationalNotification
from app.modules.notifications.service import OperationalNotificationService
from app.modules.occurrences.models import Occurrence
from app.modules.occurrences.repository import OccurrenceRepository
from app.modules.occurrences.schemas import OccurrenceCreate
from app.modules.occurrences.service import OccurrenceService
from app.modules.users.models import User
from tests.integration.test_external_commands import scenario

__all__ = ("scenario",)


@pytest.mark.parametrize("provider_fails", [False, True])
def test_occurrence_is_durable_before_mock_and_survives_provider_failure_and_restart(
    scenario, provider_fails: bool
) -> None:
    observed_ids: list[uuid.UUID] = []

    class ObservingMock(MockWhatsAppProvider):
        def send_response(
            self, message: OutgoingWhatsAppMessage
        ) -> OutgoingWhatsAppMessage:
            # A separate real connection cannot see a merely released savepoint.
            with scenario.factory() as observer:
                observed_ids.extend(
                    observer.scalars(
                        select(Occurrence.id).where(
                            Occurrence.trip_id == scenario.trip_id
                        )
                    )
                )
            if provider_fails:
                raise RuntimeError("fixture mock unavailable")
            return super().send_response(message)

    provider = ObservingMock()
    try:
        with scenario.factory() as db:
            manager = db.get(User, scenario.actors["manager"])
            service = OccurrenceService(
                db, notification_service=OperationalNotificationService(provider)
            )
            occurrence = service.register_occurrence(
                OccurrenceCreate(
                    trip_id=scenario.trip_id,
                    delivery_id=scenario.delivery_id,
                    type="DELAY",
                    description="Ocorrência fictícia para regressão de commit.",
                ),
                current_user=manager,
            )
            occurrence_id = occurrence.id

        assert observed_ids == [occurrence_id]
        assert len(provider.sent_messages) == int(not provider_fails)
        # Recreate services/provider and use another connection, preserving the fact.
        with scenario.factory() as restarted:
            manager = restarted.get(User, scenario.actors["manager"])
            reloaded = OccurrenceService(
                restarted,
                notification_service=OperationalNotificationService(
                    MockWhatsAppProvider()
                ),
            ).get_occurrence_for_access(occurrence_id, current_user=manager)
            assert reloaded.trip_id == scenario.trip_id
            assert reloaded.delivery_id == scenario.delivery_id
            assert restarted.get(Trip, scenario.trip_id).status == "IN_ROUTE"
    finally:
        with scenario.factory() as cleanup:
            cleanup.execute(
                delete(OperationalNotification).where(
                    OperationalNotification.trip_id == scenario.trip_id
                )
            )
            cleanup.execute(
                delete(Occurrence).where(Occurrence.trip_id == scenario.trip_id)
            )
            cleanup.commit()


def test_occurrence_persistence_failure_rolls_back_without_mock_attempt(
    scenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = MockWhatsAppProvider()
    original_add = OccurrenceRepository.add

    def fail_after_flush(repository: OccurrenceRepository, occurrence: Occurrence):
        original_add(repository, occurrence)
        raise RuntimeError("fixture persistence failure")

    monkeypatch.setattr(OccurrenceRepository, "add", fail_after_flush)
    with scenario.factory() as db:
        service = OccurrenceService(
            db, notification_service=OperationalNotificationService(provider)
        )
        data = OccurrenceCreate(
            trip_id=scenario.trip_id,
            type="DELAY",
            description="Teste fictício de rollback.",
        )
        actor = db.get(User, scenario.actors["manager"])
        with pytest.raises(RuntimeError, match="fixture persistence failure"):
            service.register_occurrence(data, current_user=actor)
    with scenario.factory() as observer:
        assert (
            observer.scalar(
                select(Occurrence.id).where(Occurrence.trip_id == scenario.trip_id)
            )
            is None
        )
        assert observer.get(Trip, scenario.trip_id).status == "IN_ROUTE"
    assert provider.sent_messages == []
