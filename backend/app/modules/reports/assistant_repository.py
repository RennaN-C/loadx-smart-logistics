"""Parameterized, aggregate-only projections for the authorized assistant tools."""

import unicodedata

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.modules.customers.models import Customer
from app.modules.deliveries.models import Delivery, Trip
from app.modules.load_planning.distribution_models import LoadDistribution
from app.modules.load_planning.models import LoadPlan
from app.modules.orders.models import Order


class AssistantMetricsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def customers(self, name: str) -> list[Customer]:
        normalized = " ".join(
            "".join(
                char
                for char in unicodedata.normalize("NFKD", name.casefold())
                if not unicodedata.combining(char)
            ).split()
        )
        expression = func.regexp_replace(
            func.translate(
                func.lower(func.trim(Customer.name)),
                "áàâãäéèêëíìîïóòôõöúùûüç",
                "aaaaaeeeeiiiiooooouuuuc",
            ),
            r"\s+",
            " ",
            "g",
        )
        exact = list(
            self.db.scalars(
                select(Customer)
                .where(expression == normalized)
                .order_by(Customer.id)
                .limit(6)
            )
        )
        if exact:
            return exact
        escaped = (
            normalized.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        return list(
            self.db.scalars(
                select(Customer)
                .where(expression.ilike(f"%{escaped}%", escape="\\"))
                .order_by(Customer.name, Customer.id)
                .limit(6)
            )
        )

    def orders(self, start, end, customer_id=None, status=None) -> dict:
        query = select(Order.status, func.count(Order.id)).where(
            Order.created_at >= start, Order.created_at < end
        )
        if customer_id:
            query = query.where(Order.customer_id == customer_id)
        if status:
            query = query.where(Order.status == status)
        result = dict.fromkeys(
            ("DRAFT", "READY", "PLANNED", "IN_TRANSIT", "DELIVERED", "CANCELED"), 0
        )
        result.update(dict(self.db.execute(query.group_by(Order.status)).all()))
        return result

    def deliveries(self, start, end, customer_id=None) -> dict:
        # Current DELIVERED order plus last completed leg: never count a partial leg
        # as a fully delivered order, and count multi-truck orders only once.
        completed = (
            select(
                Delivery.order_id, func.max(Delivery.delivered_at).label("completed_at")
            )
            .where(Delivery.status == "DELIVERED")
            .group_by(Delivery.order_id)
            .subquery()
        )
        full = (
            select(Order.id)
            .join(completed, completed.c.order_id == Order.id)
            .where(
                Order.status == "DELIVERED",
                completed.c.completed_at >= start,
                completed.c.completed_at < end,
            )
        )
        dispatched = (
            select(distinct(Order.id))
            .join(Delivery, Delivery.order_id == Order.id)
            .join(Trip, Trip.id == Delivery.trip_id)
            .where(
                Trip.started_at >= start,
                Trip.started_at < end,
                Delivery.status != "CANCELED",
            )
        )
        legs = (
            select(func.count(Delivery.id))
            .join(Order, Order.id == Delivery.order_id)
            .where(
                Delivery.delivered_at >= start,
                Delivery.delivered_at < end,
                Delivery.status == "DELIVERED",
            )
        )
        if customer_id:
            full = full.where(Order.customer_id == customer_id)
            dispatched = dispatched.where(Order.customer_id == customer_id)
            legs = legs.where(Order.customer_id == customer_id)
        top = (
            select(Customer.name, func.count(Order.id))
            .join(Order, Order.customer_id == Customer.id)
            .where(Order.id.in_(full))
            .group_by(Customer.id, Customer.name)
            .order_by(func.count(Order.id).desc(), Customer.name, Customer.id)
            .limit(1)
        )
        leader = self.db.execute(top).first()
        return {
            "fully_delivered_orders": int(
                self.db.scalar(select(func.count()).select_from(full.subquery())) or 0
            ),
            "dispatched_orders": int(
                self.db.scalar(select(func.count()).select_from(dispatched.subquery()))
                or 0
            ),
            "completed_delivery_legs": int(self.db.scalar(legs) or 0),
            "top_customer_name": leader[0] if leader else None,
            "top_customer_delivered_orders": int(leader[1]) if leader else 0,
        }

    def fleet(self, start, end) -> dict:
        trips = select(Trip.id).where(Trip.started_at >= start, Trip.started_at < end)
        plan_ids = select(Trip.load_plan_id).where(Trip.id.in_(trips)).distinct()
        plans = self.db.execute(
            select(
                func.count(LoadPlan.id),
                func.avg(LoadPlan.occupancy_percent),
                func.sum(LoadPlan.loaded_count),
                func.sum(LoadPlan.unloaded_count),
                func.sum(LoadPlan.total_weight_kg),
            ).where(LoadPlan.id.in_(plan_ids))
        ).one()
        finished = select(func.count(Trip.id)).where(
            Trip.finished_at >= start, Trip.finished_at < end
        )
        return {
            "trips_started": int(
                self.db.scalar(select(func.count()).select_from(trips.subquery())) or 0
            ),
            "trips_finished": int(self.db.scalar(finished) or 0),
            "distinct_trucks_used": int(
                self.db.scalar(
                    select(func.count(distinct(LoadPlan.truck_id))).where(
                        LoadPlan.id.in_(plan_ids)
                    )
                )
                or 0
            ),
            "plans_with_started_trip": int(plans[0]),
            "average_plan_occupancy_percent": round(float(plans[1]), 2)
            if plans[1] is not None
            else None,
            "planned_loaded_volumes": int(plans[2] or 0),
            "planned_rejected_volumes": int(plans[3] or 0),
            "planned_loaded_weight_kg": float(plans[4] or 0),
        }

    def canceled(self, start, end) -> dict:
        return {
            "currently_canceled_distributions_created_in_period": int(
                self.db.scalar(
                    select(func.count(LoadDistribution.id)).where(
                        LoadDistribution.status == "CANCELED",
                        LoadDistribution.created_at >= start,
                        LoadDistribution.created_at < end,
                    )
                )
                or 0
            )
        }

    def canceled_items(self, start, end, page: int):
        return self.db.execute(
            select(LoadDistribution.id, LoadDistribution.created_at)
            .where(
                LoadDistribution.status == "CANCELED",
                LoadDistribution.created_at >= start,
                LoadDistribution.created_at < end,
            )
            .order_by(LoadDistribution.created_at.desc(), LoadDistribution.id.desc())
            .offset((page - 1) * 10)
            .limit(10)
        ).all()
