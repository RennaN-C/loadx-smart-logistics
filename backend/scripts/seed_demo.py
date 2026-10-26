"""Populate the local demonstration database through existing domain services."""

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.modules.customers.schemas import CustomerCreate
from app.modules.drivers.schemas import DriverCreate


def validate_target(environment: str, host: str | None, database: str | None) -> None:
    """Never seed remote, production, or integration-test databases."""
    if (
        environment != "local"
        or host not in {"db", "localhost", "127.0.0.1", "::1"}
        or database != "loadx"
    ):
        raise ValueError("Seed permitido somente no banco loadx local.")


def synthetic_cpf(index: int) -> str:
    digits = f"823500{index:03d}"
    for length in (9, 10):
        remainder = (
            sum(int(d) * w for d, w in zip(digits, range(length + 1, 1, -1))) % 11
        )
        digits += str(0 if remainder < 2 else 11 - remainder)
    return digits


def synthetic_cnh(index: int) -> str:
    digits = f"735200{index:03d}"
    first = sum(int(d) * w for d, w in zip(digits, range(9, 0, -1))) % 11
    discount = 2 if first == 10 else 0
    second = (sum(int(d) * w for d, w in zip(digits, range(1, 10))) - discount) % 11
    return (
        digits + str(0 if first == 10 else first) + str(0 if second == 10 else second)
    )


def demo_customers() -> list[CustomerCreate]:
    cities = [
        ("Curitiba", "PR"),
        ("São Paulo", "SP"),
        ("Joinville", "SC"),
        ("Londrina", "PR"),
    ]
    names = [
        "Horizonte",
        "Aurora",
        "Vale Azul",
        "Estrela",
        "Pioneira",
        "Solar",
        "Central",
        "Serra",
    ]
    return [
        CustomerCreate(
            name=f"DEMO Distribuidora {name}",
            document=synthetic_cpf(100 + index),
            address=f"Rua Fictícia de Demonstração, {100 + index}",
            city=cities[index % 4][0],
            state=cities[index % 4][1],
            notes="Dados fictícios para demonstração local do LoadX.",
        )
        for index, name in enumerate(names)
    ]


def demo_drivers() -> list[DriverCreate]:
    return [
        DriverCreate(
            name=f"DEMO Motorista {index + 1:02d}",
            document=synthetic_cpf(200 + index),
            phone="11900000000",
            license_number=synthetic_cnh(index),
            license_category="D",
        )
        for index in range(6)
    ]


def seed_database(db: Session) -> dict[str, int]:
    from app.modules.customers.models import Customer
    from app.modules.customers.service import CustomerService
    from app.modules.deliveries.models import Trip
    from app.modules.deliveries.schemas import TripCreate
    from app.modules.deliveries.service import TripService
    from app.modules.drivers.models import Driver
    from app.modules.drivers.service import DriverService
    from app.modules.load_planning.models import LoadPlan, LoadPlanOrder
    from app.modules.load_planning.schemas import LoadPlanCreate
    from app.modules.load_planning.service import LoadPlanningService
    from app.modules.loading.service import LoadingService
    from app.modules.occurrences.models import Occurrence
    from app.modules.occurrences.schemas import OccurrenceCreate
    from app.modules.occurrences.service import OccurrenceService
    from app.modules.orders.models import Order
    from app.modules.orders.schemas import OrderCreate, OrderItemCreate
    from app.modules.orders.service import OrderService
    from app.modules.products.models import Product
    from app.modules.products.schemas import ProductCreate
    from app.modules.products.service import ProductService
    from app.modules.trucks.models import Truck
    from app.modules.trucks.schemas import TruckCreate
    from app.modules.trucks.service import TruckService
    from app.modules.users.models import User

    actor = db.scalar(
        select(User)
        .where(User.role == "ADMIN", User.active.is_(True))
        .order_by(User.id)
    )
    if actor is None:
        raise ValueError("Crie primeiro o administrador pelo bootstrap oficial.")
    trucks, products, customers, drivers = [], [], [], []
    for index in range(8):
        plate = f"DMO{index}A{index + 10}"
        truck = db.scalar(select(Truck).where(Truck.plate == plate))
        if truck is None:
            truck = TruckService(db).create_truck(
                TruckCreate(
                    plate=plate,
                    model=f"DEMO Baú logístico {index + 1:02d}",
                    internal_width_cm=240,
                    internal_height_cm=260,
                    internal_length_cm=600 + index * 20,
                    max_weight_kg=10000 + index * 500,
                )
            )
        trucks.append(truck)
    for index in range(12):
        code = f"DEMO-CX-{index + 1:03d}"
        product = db.scalar(select(Product).where(Product.code == code))
        if product is None:
            product = ProductService(db).create_product(
                ProductCreate(
                    code=code,
                    name=f"DEMO Caixa {index + 1:02d}",
                    description="Embalagem fictícia de demonstração.",
                    width_cm=30 + index * 2,
                    height_cm=25 + index,
                    length_cm=40 + index * 2,
                    weight_kg=5 + index,
                    fragile=index % 4 == 0,
                    stackable=index % 4 != 0,
                    rotation_allowed=index % 3 != 0,
                )
            )
        products.append(product)
    for data in demo_customers():
        existing = db.scalar(select(Customer).where(Customer.document == data.document))
        if existing is not None and existing.name != data.name:
            raise ValueError("Documento de demonstração já pertence a outro cadastro.")
        customers.append(
            existing or CustomerService(db).create_customer(data, changed_by=actor.id)
        )
    for data in demo_drivers():
        existing = db.scalar(select(Driver).where(Driver.document == data.document))
        if existing is not None and existing.name != data.name:
            raise ValueError("Documento de demonstração já pertence a outro cadastro.")
        drivers.append(
            existing or DriverService(db).create_driver(data, changed_by=actor.id)
        )

    orders = []
    for index in range(24):
        address = f"DEMO LoadX {index + 1:02d} — Rua Fictícia, {index + 100}"
        order = db.scalar(select(Order).where(Order.delivery_address == address))
        if order is None:
            order = OrderService(db).create_order(
                OrderCreate(
                    customer_id=customers[index % 8].id,
                    delivery_address=address,
                    priority=("LOW", "NORMAL", "HIGH", "URGENT")[index % 4],
                    expected_delivery_at=datetime.now(UTC)
                    + timedelta(days=1 + index % 5),
                    items=[
                        OrderItemCreate(
                            product_id=products[index % 12].id,
                            quantity=3 + index % 5,
                            delivery_sequence=1,
                        )
                    ],
                ),
                changed_by=actor.id,
            )
            target = "READY" if index < 16 else "CANCELED" if index >= 20 else "DRAFT"
            if target != "DRAFT":
                order = OrderService(db).change_order_status(
                    order.id, target, changed_by=actor.id
                )
        orders.append(order)

    targets = ("calculated", "loading", "scheduled", "in_route", "partial", "finished")
    for index, target in enumerate(targets):
        pair = orders[index * 2 : index * 2 + 2]
        plan = db.scalar(
            select(LoadPlan)
            .join(LoadPlanOrder)
            .where(
                LoadPlanOrder.order_id == pair[0].id,
            )
            .order_by(LoadPlan.created_at.desc())
        )
        planning = LoadPlanningService(db)
        if plan is None:
            plan = planning.create_load_plan(
                LoadPlanCreate(
                    truck_id=trucks[index].id,
                    order_ids=[order.id for order in pair],
                ),
                changed_by=actor.id,
            )
        if target == "calculated":
            continue
        if plan.status == "CALCULATED":
            plan = planning.approve_load_plan(plan.id, changed_by=actor.id)
        loading = LoadingService(db)
        session = loading.create_session(plan.id)
        if session.status == "PENDING":
            session = loading.change_status(session.id, "IN_PROGRESS")
        if session.status == "IN_PROGRESS":
            items = list(session.items)
            for item in (
                items[: max(1, len(items) // 2)] if target == "loading" else items
            ):
                if item.status != "CHECKED":
                    loading.change_item_status(session.id, item.id, "CHECKED")
            if target != "loading":
                loading.change_status(session.id, "FINISHED")
        if target == "loading":
            continue
        trips = TripService(db)
        trip = db.scalar(select(Trip).where(Trip.load_plan_id == plan.id))
        if trip is None:
            trip = trips.create_trip(
                TripCreate(load_plan_id=plan.id, driver_id=drivers[index].id),
                changed_by=actor.id,
            )
        if target == "scheduled" or trip.status == "FINISHED":
            continue
        if trip.status == "SCHEDULED":
            trip = trips.change_trip_status(trip.id, "IN_ROUTE", current_user=actor)
        deliveries = sorted(trip.deliveries, key=lambda item: item.sequence)
        for number, delivery in enumerate(deliveries):
            if target == "in_route" and number > 0:
                break
            if delivery.status == "PENDING":
                trips.change_delivery_status(
                    delivery.id, "IN_DELIVERY", current_user=actor
                )
            if (
                target == "finished" or (target == "partial" and number == 0)
            ) and delivery.status != "DELIVERED":
                trips.register_delivery_receipt(delivery.id, current_user=actor)
        if target == "finished":
            trips.change_trip_status(trip.id, "FINISHED", current_user=actor)
        else:
            description = f"DEMO: acompanhamento fictício da operação {index + 1}."
            exists = db.scalar(
                select(Occurrence.id).where(
                    Occurrence.trip_id == trip.id, Occurrence.description == description
                )
            )
            if exists is None:
                OccurrenceService(db).register_occurrence(
                    OccurrenceCreate(
                        trip_id=trip.id,
                        type="DELAY",
                        description=description,
                    ),
                    current_user=actor,
                )
    return {
        model.__tablename__: db.scalar(select(func.count()).select_from(model)) or 0
        for model in (
            Truck,
            Product,
            Customer,
            Driver,
            Order,
            LoadPlan,
            Trip,
            Occurrence,
        )
    }


def main() -> None:
    from app.core.config import settings
    from app.database.session import SessionLocal, engine

    target = make_url(settings.database_url)
    validate_target(settings.app_env, target.host, target.database)
    # The dedicated transaction keeps the lock while domain services commit.
    with engine.begin() as lock:
        lock.execute(text("SELECT pg_advisory_xact_lock(726334019)"))
        with SessionLocal() as db:
            print(json.dumps({"environment": "local", "totals": seed_database(db)}))


if __name__ == "__main__":
    main()
