"""OC95: explain actual repository queries with synthetic PostgreSQL test data."""

import argparse
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.pagination import PaginationParams
from app.modules.customers.models import Customer
from app.modules.customers.repository import CustomerRepository
from app.modules.drivers.models import Driver
from app.modules.drivers.repository import DriverRepository
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.repository import OrderRepository
from app.modules.products.models import Product
from app.modules.products.repository import ProductRepository
from app.modules.trucks.models import Truck
from app.modules.trucks.repository import TruckRepository


def seed(db: Session, rows: int) -> None:
    """Only fictitious data, all discarded by the enclosing transaction."""
    identities = [uuid.UUID(int=950000 + i) for i in range(rows)]
    stamp = datetime(2026, 10, 1, tzinfo=timezone.utc)
    customers, drivers, trucks, products, orders, items = [], [], [], [], [], []
    for i, identity in enumerate(identities):
        name = f"Fictício {'Alvo' if i % 100 == 0 else 'Base'} {i}"
        common = {
            "id": identity,
            "active": i % 7 != 0,
            "created_at": stamp + timedelta(seconds=i),
        }
        customers.append(
            {
                **common,
                "name": name,
                "document": f"{i:014}",
                "address": "Rua fictícia",
                "city": "Cidade fictícia",
                "state": "SP",
            }
        )
        drivers.append(
            {
                **common,
                "name": name,
                "document": f"{i:011}",
                "phone": "11900000000",
                "license_number": f"{100000 + i:011}",
            }
        )
        trucks.append(
            {
                **common,
                "plate": f"TEST-{i}",
                "model": name,
                "internal_width_cm": 240,
                "internal_height_cm": 260,
                "internal_length_cm": 600,
                "max_weight_kg": 8000,
            }
        )
        products.append(
            {
                **common,
                "code": f"TEST-{i}",
                "name": name,
                "width_cm": 10,
                "height_cm": 10,
                "length_cm": 10,
                "weight_kg": 1,
                "fragile": i % 3 == 0,
                "stackable": i % 5 != 1,
                "rotation_allowed": i % 6 != 0,
            }
        )
        orders.append(
            {
                "id": identity,
                "customer_id": identity,
                "status": "READY" if i % 3 == 0 else "DRAFT",
                "priority": "NORMAL",
                "delivery_address": "Destino fictício",
                "created_at": common["created_at"],
            }
        )
        for position in (0, 1):
            items.append(
                {
                    "id": uuid.UUID(int=1950000 + i * 2 + position),
                    "order_id": identity,
                    "product_id": identities[position],
                    "quantity": 2,
                    "delivery_sequence": 1,
                }
            )
    for model, values in (
        (Customer, customers),
        (Driver, drivers),
        (Truck, trucks),
        (Product, products),
        (Order, orders),
        (OrderItem, items),
    ):
        db.execute(insert(model), values)
    db.flush()
    for table in (
        "customers",
        "drivers",
        "trucks",
        "products",
        "orders",
        "order_items",
    ):
        db.connection().exec_driver_sql(f"ANALYZE {table}")


def explain(db: Session, operation: Any) -> dict[str, Any]:
    statements = []
    connection = db.connection()

    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("SELECT"):
            statements.append((statement, parameters))

    event.listen(connection, "before_cursor_execute", capture)
    try:
        result = operation()
    finally:
        event.remove(connection, "before_cursor_execute", capture)
    plans = []
    for statement, parameters in statements:
        measurements = [
            connection.exec_driver_sql(
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + statement, parameters
            ).scalar_one()[0]
            for _ in range(3)
        ]
        plans.append(
            {
                "query": statement,
                "median_execution_ms": round(
                    median(plan["Execution Time"] for plan in measurements), 3
                ),
                "planning_ms": measurements[-1]["Planning Time"],
                "plan": measurements[-1]["Plan"],
            }
        )
    return {"total": result.total, "page_items": len(result.items), "statements": plans}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=10000)
    args = parser.parse_args()
    if not 100 <= args.rows <= 100000:
        parser.error("--rows must be between 100 and 100000")
    raw_url = os.getenv("TEST_DATABASE_URL")
    if not raw_url:
        parser.error("TEST_DATABASE_URL is required")
    url = make_url(raw_url)
    if url.drivername != "postgresql+psycopg" or url.database != "loadx_test":
        parser.error("Only the exclusive loadx_test PostgreSQL database is allowed")
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            if (
                int(connection.exec_driver_sql("SHOW server_version_num").scalar_one())
                // 10000
                != 16
            ):
                parser.error("PostgreSQL 16 is required")
            # Never reset a schema or commit seeds. Refuse an occupied test database.
            for model in (Customer, Driver, Truck, Product, Order):
                if connection.scalar(select(model.id).limit(1)) is not None:
                    parser.error(
                        "Run against an empty migrated test database, outside pytest"
                    )
            connection.rollback()
            transaction = connection.begin()
            try:
                with Session(
                    connection, join_transaction_mode="create_savepoint"
                ) as db:
                    seed(db, args.rows)
                    page = PaginationParams(1, 20, "desc")
                    customers = CustomerRepository(db)
                    orders = OrderRepository(db)
                    products = ProductRepository(db)
                    cases = {
                        "orders_name": lambda: orders.list(
                            page,
                            search="Alvo",
                            customer_name_ids=customers.matching_name_ids("Alvo"),
                        ),
                        "orders_name_status": lambda: orders.list(
                            page,
                            search="Alvo",
                            status="READY",
                            customer_name_ids=customers.matching_name_ids("Alvo"),
                        ),
                        "orders_status": lambda: orders.list(page, status="READY"),
                        "orders_reference": lambda: orders.list(
                            page,
                            search=str(uuid.UUID(int=950100)),
                            customer_name_ids=customers.matching_name_ids(
                                str(uuid.UUID(int=950100))
                            ),
                        ),
                        "trucks_search": lambda: TruckRepository(db).list(
                            page, active=True, search="Alvo"
                        ),
                        "products_restricted": lambda: products.list(
                            page, active=True, search="Alvo", restriction="restricted"
                        ),
                        "products_free": lambda: products.list(
                            page, active=True, search="Alvo", restriction="free"
                        ),
                        "customers_search": lambda: customers.list(
                            page, active=True, search="Alvo"
                        ),
                        "drivers_search": lambda: DriverRepository(db).list(
                            page, active=True, search="Alvo"
                        ),
                    }
                    report = {
                        "rows_per_resource": args.rows,
                        "order_items": args.rows * 2,
                        "runs_per_query": 3,
                        "cases": {
                            name: explain(db, operation)
                            for name, operation in cases.items()
                        },
                    }
                    print(json.dumps(report, ensure_ascii=False, indent=2))
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
