from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime

from sqlalchemy import String, asc, desc, func, literal, select, union_all
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.access_profiles.models import AccessProfile
from app.modules.customers.models import Customer, CustomerAddress
from app.modules.deliveries.models import Delivery, Trip
from app.modules.drivers.models import Driver
from app.modules.load_planning.models import LoadPlan
from app.modules.orders.models import Order
from app.modules.products.models import Product
from app.modules.status_history.models import AuditEvent, StatusHistory
from app.modules.trucks.models import Truck
from app.modules.users.models import User


@dataclass(frozen=True, slots=True)
class AuditEntryRecord:
    id: uuid.UUID
    event_type: str
    entity_type: str
    entity_id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_name: str | None
    entity_name: str | None
    old_status: str | None
    new_status: str | None
    changed_fields: tuple[str, ...]
    created_at: datetime


class StatusHistoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self, entity_type: str | None = None, entity_id: uuid.UUID | None = None
    ) -> Sequence[StatusHistory]:
        statement = select(StatusHistory).order_by(StatusHistory.created_at.desc())
        if entity_type is not None:
            statement = statement.where(StatusHistory.entity_type == entity_type)
        if entity_id is not None:
            statement = statement.where(StatusHistory.entity_id == entity_id)
        return self.db.scalars(statement).all()

    def get(self, status_history_id: uuid.UUID) -> StatusHistory | None:
        return self.db.get(StatusHistory, status_history_id)

    def add(self, status_history: StatusHistory) -> StatusHistory:
        self.db.add(status_history)
        self.db.flush()
        self.db.refresh(status_history)
        return status_history

    def add_audit_event(self, audit_event: AuditEvent) -> AuditEvent:
        self.db.add(audit_event)
        self.db.flush()
        self.db.refresh(audit_event)
        return audit_event

    def list_audit_entries(
        self,
        pagination: PaginationParams,
        *,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        event_type: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        exclude_company: bool = False,
    ) -> PageResult[AuditEntryRecord]:
        statements = []

        if event_type in {None, "STATUS_CHANGED"}:
            status_statement = (
                select(
                    StatusHistory.id.label("id"),
                    literal("STATUS_CHANGED").label("event_type"),
                    StatusHistory.entity_type.label("entity_type"),
                    StatusHistory.entity_id.label("entity_id"),
                    StatusHistory.changed_by.label("actor_id"),
                    User.name.label("actor_name"),
                    StatusHistory.old_status.label("old_status"),
                    StatusHistory.new_status.label("new_status"),
                    literal(None, type_=String(512)).label("changed_fields"),
                    StatusHistory.created_at.label("created_at"),
                )
                .select_from(StatusHistory)
                .outerjoin(User, User.id == StatusHistory.changed_by)
            )
            if entity_type is not None:
                status_statement = status_statement.where(
                    StatusHistory.entity_type == entity_type
                )
            if entity_id is not None:
                status_statement = status_statement.where(
                    StatusHistory.entity_id == entity_id
                )
            if actor_id is not None:
                status_statement = status_statement.where(
                    StatusHistory.changed_by == actor_id
                )
            if start_at is not None:
                status_statement = status_statement.where(
                    StatusHistory.created_at >= start_at
                )
            if end_at is not None:
                status_statement = status_statement.where(
                    StatusHistory.created_at <= end_at
                )
            statements.append(status_statement)

        if event_type is None or event_type != "STATUS_CHANGED":
            audit_statement = (
                select(
                    AuditEvent.id.label("id"),
                    AuditEvent.event_type.label("event_type"),
                    AuditEvent.entity_type.label("entity_type"),
                    AuditEvent.entity_id.label("entity_id"),
                    AuditEvent.actor_id.label("actor_id"),
                    User.name.label("actor_name"),
                    literal(None, type_=String(32)).label("old_status"),
                    literal(None, type_=String(32)).label("new_status"),
                    AuditEvent.changed_fields.label("changed_fields"),
                    AuditEvent.created_at.label("created_at"),
                )
                .select_from(AuditEvent)
                .join(User, User.id == AuditEvent.actor_id)
            )
            if exclude_company:
                audit_statement = audit_statement.where(
                    AuditEvent.entity_type.not_in(
                        ["COMPANY_PROFILE", "ACCESS_PROFILE", "OUTBOX_EVENT"]
                    )
                )
            if event_type is not None:
                audit_statement = audit_statement.where(
                    AuditEvent.event_type == event_type
                )
            if entity_type is not None:
                audit_statement = audit_statement.where(
                    AuditEvent.entity_type == entity_type
                )
            if entity_id is not None:
                audit_statement = audit_statement.where(
                    AuditEvent.entity_id == entity_id
                )
            if actor_id is not None:
                audit_statement = audit_statement.where(AuditEvent.actor_id == actor_id)
            if start_at is not None:
                audit_statement = audit_statement.where(
                    AuditEvent.created_at >= start_at
                )
            if end_at is not None:
                audit_statement = audit_statement.where(AuditEvent.created_at <= end_at)
            statements.append(audit_statement)

        if not statements:
            return PageResult.create([], pagination, 0)

        combined = (
            statements[0].subquery("audit_entries")
            if len(statements) == 1
            else union_all(*statements).subquery("audit_entries")
        )
        total = self.db.scalar(select(func.count()).select_from(combined)) or 0
        direction = asc if pagination.sort_order == "asc" else desc
        rows = self.db.execute(
            select(combined)
            .order_by(direction(combined.c.created_at), direction(combined.c.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).mappings()

        items = [
            AuditEntryRecord(
                id=row["id"],
                event_type=row["event_type"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                actor_id=row["actor_id"],
                actor_name=row["actor_name"],
                entity_name=None,
                old_status=row["old_status"],
                new_status=row["new_status"],
                changed_fields=tuple(
                    field for field in (row["changed_fields"] or "").split(",") if field
                ),
                created_at=row["created_at"],
            )
            for row in rows
        ]
        return PageResult.create(self._with_entity_names(items), pagination, total)

    def _with_entity_names(
        self, items: list[AuditEntryRecord]
    ) -> list[AuditEntryRecord]:
        """Resolve rótulos em lote apenas para a página já autorizada e paginada."""

        ids_by_type: dict[str, set[uuid.UUID]] = {}
        for item in items:
            ids_by_type.setdefault(item.entity_type, set()).add(item.entity_id)

        names: dict[tuple[str, uuid.UUID], str] = {}

        simple_models = {
            "CUSTOMER": (Customer, Customer.name),
            "PRODUCT": (Product, Product.name),
            "DRIVER": (Driver, Driver.name),
            "CUSTOMER_ADDRESS": (CustomerAddress, CustomerAddress.label),
            "ACCESS_PROFILE": (AccessProfile, AccessProfile.name),
        }
        for entity_type, (model, label_column) in simple_models.items():
            entity_ids = ids_by_type.get(entity_type)
            if not entity_ids:
                continue
            for entity_id, label in self.db.execute(
                select(model.id, label_column).where(model.id.in_(entity_ids))
            ):
                names[(entity_type, entity_id)] = label

        truck_ids = ids_by_type.get("TRUCK")
        if truck_ids:
            for entity_id, plate, model in self.db.execute(
                select(Truck.id, Truck.plate, Truck.model).where(
                    Truck.id.in_(truck_ids)
                )
            ):
                names[("TRUCK", entity_id)] = f"{plate} · {model}"

        plan_ids = ids_by_type.get("LOAD_PLAN")
        if plan_ids:
            for entity_id, plate in self.db.execute(
                select(LoadPlan.id, LoadPlan.truck_snapshot_plate).where(
                    LoadPlan.id.in_(plan_ids)
                )
            ):
                names[("LOAD_PLAN", entity_id)] = f"Caminhão {plate}"

        order_ids = ids_by_type.get("ORDER")
        if order_ids:
            for entity_id, customer_name in self.db.execute(
                select(Order.id, Customer.name)
                .join(Customer, Customer.id == Order.customer_id)
                .where(Order.id.in_(order_ids))
            ):
                names[("ORDER", entity_id)] = f"Pedido de {customer_name}"

        trip_ids = ids_by_type.get("TRIP")
        if trip_ids:
            for entity_id, driver_name in self.db.execute(
                select(Trip.id, Driver.name)
                .join(Driver, Driver.id == Trip.driver_id)
                .where(Trip.id.in_(trip_ids))
            ):
                names[("TRIP", entity_id)] = f"Viagem de {driver_name}"

        delivery_ids = ids_by_type.get("DELIVERY")
        if delivery_ids:
            for entity_id, customer_name in self.db.execute(
                select(Delivery.id, Customer.name)
                .join(Order, Order.id == Delivery.order_id)
                .join(Customer, Customer.id == Order.customer_id)
                .where(Delivery.id.in_(delivery_ids))
            ):
                names[("DELIVERY", entity_id)] = f"Entrega para {customer_name}"

        return [
            replace(item, entity_name=names.get((item.entity_type, item.entity_id)))
            for item in items
        ]
