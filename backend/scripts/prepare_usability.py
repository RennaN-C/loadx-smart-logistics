"""Prepare separate, non-destructive local batches for rehearsal and recording."""

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from scripts.seed_demo import synthetic_cnh, synthetic_cpf, validate_target


def batch_number(batch: str) -> int:
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,23}", batch):
        raise ValueError("Lote deve ter 3 a 24 letras minusculas, numeros ou hifens.")
    return int.from_bytes(hashlib.sha256(batch.encode()).digest()[:4], "big")


def demo_plate(number: int) -> str:
    value = number % 26000
    return f"VD{chr(65 + value // 1000 % 26)}{value % 10}{chr(65 + value // 10 % 26)}{value // 260 % 100:02}"


def prepare(db: Session, batch: str) -> dict:
    from app.modules.customers.models import Customer
    from app.modules.customers.schemas import CustomerCreate
    from app.modules.customers.service import CustomerService
    from app.modules.drivers.models import Driver
    from app.modules.drivers.schemas import DriverCreate
    from app.modules.drivers.service import DriverService
    from app.modules.load_planning.distribution_schemas import DistributionNeedRequest
    from app.modules.load_planning.distribution_service import (
        DistributionError,
        LoadDistributionService,
    )
    from app.modules.orders.models import Order
    from app.modules.orders.schemas import OrderCreate, OrderItemCreate
    from app.modules.orders.service import OrderService
    from app.modules.products.models import Product
    from app.modules.products.schemas import ProductCreate
    from app.modules.products.service import ProductService
    from app.modules.trucks.document_schemas import DocumentCreate
    from app.modules.trucks.document_service import DocumentService
    from app.modules.trucks.models import Truck
    from app.modules.trucks.schemas import TruckCreate
    from app.modules.trucks.service import TruckService
    from app.modules.users.models import User

    number = batch_number(batch)
    prefix = f"VIDEO {batch}"
    actor = db.scalar(
        select(User)
        .where(User.role == "ADMIN", User.active.is_(True))
        .order_by(User.id)
    )
    if actor is None:
        raise ValueError("O administrador deve existir pelo bootstrap oficial.")
    customer_name = f"{prefix} Distribuidora Aurora"
    customer = db.scalar(select(Customer).where(Customer.name == customer_name))
    if customer is None:
        customer = CustomerService(db).create_customer(
            CustomerCreate(
                name=customer_name,
                document=synthetic_cpf(300 + number % 150),
                address="Rua Ficticia do Video, 100",
                city="Curitiba",
                state="PR",
                notes="Dados ficticios para avaliacao local de usabilidade.",
            ),
            changed_by=actor.id,
        )
    capacity = max([Decimal(12000), *db.scalars(select(Truck.max_weight_kg)).all()])
    trucks, drivers = [], []
    for index in range(3):
        plate = demo_plate(number + index)
        model = f"{prefix} Bau {index + 1}"
        truck = db.scalar(select(Truck).where(Truck.plate == plate))
        if truck is not None and truck.model != model:
            raise ValueError("Placa de demonstracao em uso. Escolha outro lote.")
        if truck is None:
            truck = TruckService(db).create_truck(
                TruckCreate(
                    plate=plate,
                    model=model,
                    internal_width_cm=240,
                    internal_height_cm=260,
                    internal_length_cm=640,
                    max_weight_kg=capacity,
                )
            )
            for kind in ("CRLV", "LICENSING", "INSURANCE"):
                DocumentService(db).create(
                    truck.id,
                    DocumentCreate(
                        kind=kind,
                        reference=f"FICTICIO {batch} {kind}",
                        issued_at=datetime.now(UTC) - timedelta(days=1),
                        expires_at=datetime.now(UTC) + timedelta(days=365),
                    ),
                    actor=actor.id,
                )
        trucks.append(truck)
        name = f"{prefix} Motorista {index + 1}"
        driver = db.scalar(select(Driver).where(Driver.name == name))
        if driver is None:
            offset = (number % 140) * 3 + index
            driver = DriverService(db).create_driver(
                DriverCreate(
                    name=name,
                    document=synthetic_cpf(500 + offset),
                    phone="11900000000",
                    license_number=synthetic_cnh(500 + offset),
                    license_category="D",
                    license_expires_at=datetime.now(UTC) + timedelta(days=365),
                ),
                changed_by=actor.id,
            )
        drivers.append(driver)
        DriverService(db).ensure_operational_eligibility(driver.id)
        TruckService(db).ensure_operational_eligibility(truck.id)
    products = []
    heavy_weight = (capacity / 12).quantize(Decimal("0.001"), rounding=ROUND_DOWN)
    for label, weight, side in (
        ("LEVE", Decimal(12), 40),
        ("MULTI", heavy_weight, 80),
    ):
        code = f"VID-{batch}-{label}".upper()
        product = db.scalar(select(Product).where(Product.code == code))
        if product is None:
            product = ProductService(db).create_product(
                ProductCreate(
                    code=code,
                    name=f"{prefix} Caixa {label}",
                    width_cm=side,
                    height_cm=side,
                    length_cm=side,
                    weight_kg=weight,
                    fragile=False,
                    stackable=True,
                    rotation_allowed=True,
                )
            )
        products.append(product)
    orders = []
    for label, product, quantity, ready in (
        ("SIMPLES", products[0], 6, True),
        ("MULTI", products[1], 24, True),
        ("RASCUNHO", products[0], 4, False),
    ):
        address = f"{prefix} {label} - Destino Ficticio, 100"
        order = db.scalar(select(Order).where(Order.delivery_address == address))
        if order is None:
            service = OrderService(db)
            order = service.create_order(
                OrderCreate(
                    customer_id=customer.id,
                    delivery_address=address,
                    priority="NORMAL",
                    expected_delivery_at=datetime.now(UTC) + timedelta(days=2),
                    items=[
                        OrderItemCreate(
                            product_id=product.id,
                            quantity=quantity,
                            delivery_sequence=1,
                        )
                    ],
                ),
                changed_by=actor.id,
            )
            if ready:
                order = service.change_order_status(
                    order.id, "READY", changed_by=actor.id
                )
        available = False
        if order.status == "READY":
            # Existing claimed/operational data is never reset for a retake.
            try:
                need = LoadDistributionService(db).preflight(
                    DistributionNeedRequest(order_ids=[order.id])
                )
                available = bool(need.eligible_trucks)
            except DistributionError:
                db.rollback()
        orders.append(
            {
                "task": label,
                "id": str(order.id),
                "status": order.status,
                "available_for_planning": available,
                "volumes": quantity,
            }
        )
    conflicts = TruckService(db).get_operational_conflicts(
        [truck.id for truck in trucks]
    )
    unavailable = conflicts.operations | conflicts.documents | conflicts.maintenance
    return {
        "batch": batch,
        "customer": {"id": str(customer.id), "name": customer.name},
        "trucks": [
            {
                "id": str(truck.id),
                "plate": truck.plate,
                "model": truck.model,
                "available_now": truck.active and truck.id not in unavailable,
            }
            for truck in trucks
        ],
        "drivers": [
            {
                "id": str(driver.id),
                "name": driver.name,
                "available_now": driver.active
                and not DriverService(db).has_operation_conflict(driver.id)
                and not DriverService(db).has_document_conflict(driver.id),
            }
            for driver in drivers
        ],
        "products": [
            {"id": str(product.id), "code": product.code, "name": product.name}
            for product in products
        ],
        "orders": orders,
    }


def main() -> None:
    from app.core.config import settings
    from app.database.session import SessionLocal, engine

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    args = parser.parse_args()
    batch_number(args.batch)
    target = make_url(settings.database_url)
    validate_target(settings.app_env, target.host, target.database)
    with engine.begin() as lock:
        lock.execute(text("SELECT pg_advisory_xact_lock(726334019)"))
        with SessionLocal() as db:
            print(json.dumps(prepare(db, args.batch)))


if __name__ == "__main__":
    main()
