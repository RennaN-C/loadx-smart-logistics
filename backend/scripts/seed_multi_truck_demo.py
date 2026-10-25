"""Add a reproducible heavy-load example to the existing local demonstration."""

import json
from time import perf_counter
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.engine import make_url

from scripts.seed_demo import validate_target


def main() -> None:
    from app.core.config import settings
    from app.database.session import SessionLocal
    from app.modules.customers.models import Customer
    from app.modules.load_planning.distribution_schemas import DistributionNeedRequest
    from app.modules.load_planning.distribution_service import LoadDistributionService
    from app.modules.orders.models import Order
    from app.modules.orders.schemas import OrderCreate, OrderItemCreate
    from app.modules.orders.service import OrderService
    from app.modules.products.models import Product
    from app.modules.products.schemas import ProductCreate
    from app.modules.products.service import ProductService
    from app.modules.users.models import User

    target = make_url(settings.database_url)
    validate_target(settings.app_env, target.host, target.database)
    with SessionLocal() as db:
        actor = db.scalar(
            select(User).where(User.role == "ADMIN", User.active.is_(True))
        )
        customer = db.scalar(
            select(Customer).where(Customer.name == "DEMO Distribuidora Horizonte")
        )
        if actor is None or customer is None:
            raise ValueError(
                "Execute o bootstrap oficial e scripts.seed_demo primeiro."
            )
        code = "DEMO-MULTI-800"
        product = db.scalar(select(Product).where(Product.code == code))
        if product is None:
            product = ProductService(db).create_product(
                ProductCreate(
                    code=code,
                    name="DEMO Volume pesado multi-caminhoes",
                    width_cm=80,
                    height_cm=80,
                    length_cm=80,
                    weight_kg=800,
                    fragile=False,
                    stackable=True,
                    rotation_allowed=True,
                )
            )
        address = "DEMO MULTI — Destino ficticio da distribuicao de 24 volumes"
        order = db.scalar(select(Order).where(Order.delivery_address == address))
        if order is None:
            service = OrderService(db)
            order = service.create_order(
                OrderCreate(
                    customer_id=customer.id,
                    delivery_address=address,
                    priority="HIGH",
                    items=[
                        OrderItemCreate(
                            product_id=product.id, quantity=24, delivery_sequence=1
                        )
                    ],
                ),
                changed_by=actor.id,
            )
            order = service.change_order_status(order.id, "READY", changed_by=actor.id)
        key = uuid5(UUID("72633401-9000-4000-8000-000000000001"), str(order.id))
        start = perf_counter()
        result = LoadDistributionService(db).optimize(
            DistributionNeedRequest(order_ids=[order.id]),
            changed_by=actor.id,
            idempotency_key=key,
        )
        print(
            json.dumps(
                {
                    "distribution_id": str(result.id),
                    "status": result.status,
                    "truck_count": result.truck_count,
                    "volume_count": result.volume_count,
                    "elapsed_seconds": round(perf_counter() - start, 3),
                }
            )
        )


if __name__ == "__main__":
    main()
