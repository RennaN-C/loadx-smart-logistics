from collections.abc import Callable, Generator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.modules.customers.models import Customer
from app.modules.customers.schemas import CustomerCreate
from app.modules.customers.service import CustomerService
from app.modules.drivers.models import Driver
from app.modules.drivers.schemas import DriverCreate
from app.modules.drivers.service import DriverService
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.schemas import OrderCreate
from app.modules.orders.service import OrderService
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate
from app.modules.products.service import ProductService
from app.modules.trucks.models import Truck
from app.modules.trucks.schemas import TruckCreate
from app.modules.trucks.service import TruckService
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService

SessionFactory = Callable[[], Session]
ALL_ROLES = ("ADMIN", "LOGISTICS_MANAGER", "CHECKER", "DRIVER")
ALL_ROLE_SET = frozenset(ALL_ROLES)
ADMIN_ONLY = frozenset({"ADMIN"})
OPERATION_READERS = frozenset({"ADMIN", "LOGISTICS_MANAGER", "CHECKER"})
PERSONAL_DATA_READERS = frozenset({"ADMIN", "LOGISTICS_MANAGER"})
MANAGER_ONLY = frozenset({"LOGISTICS_MANAGER"})


@dataclass(frozen=True)
class AuthorizationCase:
    name: str
    method: str
    path: str
    allowed_roles: frozenset[str]
    success_status: int
    payload_name: str | None = None


AUTHORIZATION_CASES = (
    AuthorizationCase("auth_me", "GET", "/api/v1/auth/me", ALL_ROLE_SET, 200),
    AuthorizationCase("users_list", "GET", "/api/v1/users", ADMIN_ONLY, 200),
    AuthorizationCase(
        "users_create", "POST", "/api/v1/users", ADMIN_ONLY, 201, "user_create"
    ),
    AuthorizationCase("users_get", "GET", "/api/v1/users/{user_id}", ADMIN_ONLY, 200),
    AuthorizationCase(
        "users_update",
        "PATCH",
        "/api/v1/users/{user_id}",
        ADMIN_ONLY,
        200,
        "user_update",
    ),
    AuthorizationCase(
        "customers_list", "GET", "/api/v1/customers", PERSONAL_DATA_READERS, 200
    ),
    AuthorizationCase(
        "customers_create",
        "POST",
        "/api/v1/customers",
        MANAGER_ONLY,
        201,
        "customer_create",
    ),
    AuthorizationCase(
        "customers_get",
        "GET",
        "/api/v1/customers/{customer_id}",
        PERSONAL_DATA_READERS,
        200,
    ),
    AuthorizationCase(
        "customers_update",
        "PATCH",
        "/api/v1/customers/{customer_id}",
        MANAGER_ONLY,
        200,
        "customer_update",
    ),
    AuthorizationCase(
        "drivers_list", "GET", "/api/v1/drivers", PERSONAL_DATA_READERS, 200
    ),
    AuthorizationCase(
        "drivers_create",
        "POST",
        "/api/v1/drivers",
        MANAGER_ONLY,
        201,
        "driver_create",
    ),
    AuthorizationCase(
        "drivers_get",
        "GET",
        "/api/v1/drivers/{driver_id}",
        PERSONAL_DATA_READERS,
        200,
    ),
    AuthorizationCase(
        "drivers_update",
        "PATCH",
        "/api/v1/drivers/{driver_id}",
        MANAGER_ONLY,
        200,
        "driver_update",
    ),
    AuthorizationCase("trucks_list", "GET", "/api/v1/trucks", OPERATION_READERS, 200),
    AuthorizationCase(
        "trucks_create",
        "POST",
        "/api/v1/trucks",
        MANAGER_ONLY,
        201,
        "truck_create",
    ),
    AuthorizationCase(
        "trucks_get",
        "GET",
        "/api/v1/trucks/{truck_id}",
        OPERATION_READERS,
        200,
    ),
    AuthorizationCase(
        "trucks_update",
        "PATCH",
        "/api/v1/trucks/{truck_id}",
        MANAGER_ONLY,
        200,
        "truck_update",
    ),
    AuthorizationCase(
        "products_list", "GET", "/api/v1/products", OPERATION_READERS, 200
    ),
    AuthorizationCase(
        "products_create",
        "POST",
        "/api/v1/products",
        MANAGER_ONLY,
        201,
        "product_create",
    ),
    AuthorizationCase(
        "products_get",
        "GET",
        "/api/v1/products/{product_id}",
        OPERATION_READERS,
        200,
    ),
    AuthorizationCase(
        "products_update",
        "PATCH",
        "/api/v1/products/{product_id}",
        MANAGER_ONLY,
        200,
        "product_update",
    ),
    AuthorizationCase("orders_list", "GET", "/api/v1/orders", OPERATION_READERS, 200),
    AuthorizationCase(
        "orders_create",
        "POST",
        "/api/v1/orders",
        MANAGER_ONLY,
        201,
        "order_create",
    ),
    AuthorizationCase(
        "orders_get",
        "GET",
        "/api/v1/orders/{order_id}",
        OPERATION_READERS,
        200,
    ),
    AuthorizationCase(
        "orders_update",
        "PATCH",
        "/api/v1/orders/{order_id}",
        MANAGER_ONLY,
        200,
        "order_update",
    ),
)


@pytest.fixture
def session_factory() -> Generator[SessionFactory, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        User.__table__,
        Customer.__table__,
        Driver.__table__,
        Truck.__table__,
        Product.__table__,
        Order.__table__,
        OrderItem.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        yield testing_session_local
    finally:
        Base.metadata.drop_all(engine, tables=list(reversed(tables)))


@pytest.fixture
def client(session_factory: SessionFactory) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def create_user(
    session_factory: SessionFactory,
    email: str,
    role: str,
) -> User:
    db = session_factory()
    try:
        return UserService(db).create_user(
            UserCreate(
                name="Usuário de Auditoria",
                email=email,
                password="senha-local",
                role=role,
            )
        )
    finally:
        db.close()


def seed_resources(session_factory: SessionFactory) -> dict[str, str]:
    db = session_factory()
    try:
        target_user = UserService(db).create_user(
            UserCreate(
                name="Usuário Alvo",
                email="target@example.test",
                password="senha-local",
                role="CHECKER",
            )
        )
        customer = CustomerService(db).create_customer(
            CustomerCreate(
                name="Cliente de Auditoria",
                document="00000000000191",
                phone="5500000000000",
                address="Rua Exemplo, 100",
                city="Sao Paulo",
                state="SP",
            )
        )
        driver = DriverService(db).create_driver(
            DriverCreate(
                name="Motorista de Auditoria",
                document="00000000000",
                phone="5500000000000",
                license_number="CNH0001",
                license_category="D",
            )
        )
        truck = TruckService(db).create_truck(
            TruckCreate(
                plate="ABC1D23",
                model="Bau medio",
                internal_width_cm=240,
                internal_height_cm=260,
                internal_length_cm=600,
                max_weight_kg="8000.00",
            )
        )
        product = ProductService(db).create_product(
            ProductCreate(
                code="CX-A",
                name="Produto de Auditoria",
                width_cm=60,
                height_cm=50,
                length_cm=40,
                weight_kg="12.500",
            )
        )
        order = OrderService(db).create_order(
            OrderCreate.model_validate(
                {
                    "customer_id": str(customer.id),
                    "priority": "normal",
                    "delivery_address": "Rua Exemplo, 100",
                    "items": [
                        {
                            "product_id": str(product.id),
                            "quantity": 1,
                            "delivery_sequence": 1,
                        }
                    ],
                }
            )
        )
        return {
            "user_id": str(target_user.id),
            "customer_id": str(customer.id),
            "driver_id": str(driver.id),
            "truck_id": str(truck.id),
            "product_id": str(product.id),
            "order_id": str(order.id),
        }
    finally:
        db.close()


def get_payload(payload_name: str | None, resource_ids: dict[str, str]):
    payloads = {
        "user_create": {
            "name": "Novo Usuário",
            "email": "new-user@example.test",
            "password": "senha-local",
            "role": "checker",
        },
        "user_update": {"name": "Usuário Atualizado"},
        "customer_create": {
            "name": "Novo Cliente",
            "document": "00000000000272",
            "phone": "5511000000000",
            "address": "Rua Exemplo, 200",
            "city": "Campinas",
            "state": "SP",
        },
        "customer_update": {"city": "Campinas"},
        "driver_create": {
            "name": "Novo Motorista",
            "document": "00000000001",
            "phone": "5511000000000",
            "license_number": "CNH0002",
            "license_category": "E",
        },
        "driver_update": {"phone": "5511999999999"},
        "truck_create": {
            "plate": "DEF4G56",
            "model": "Bau pequeno",
            "internal_width_cm": 220,
            "internal_height_cm": 240,
            "internal_length_cm": 500,
            "max_weight_kg": "6000.00",
        },
        "truck_update": {"model": "Bau atualizado"},
        "product_create": {
            "code": "CX-B",
            "name": "Novo Produto",
            "width_cm": 30,
            "height_cm": 20,
            "length_cm": 40,
            "weight_kg": "5.000",
        },
        "product_update": {"name": "Produto Atualizado"},
        "order_create": {
            "customer_id": resource_ids["customer_id"],
            "priority": "high",
            "delivery_address": "Rua Exemplo, 300",
            "items": [
                {
                    "product_id": resource_ids["product_id"],
                    "quantity": 2,
                    "delivery_sequence": 1,
                }
            ],
        },
        "order_update": {"priority": "high"},
    }
    return payloads.get(payload_name)


@pytest.mark.parametrize("role", ALL_ROLES)
@pytest.mark.parametrize(
    "case",
    AUTHORIZATION_CASES,
    ids=lambda case: case.name,
)
def test_complete_authorization_matrix(
    client: TestClient,
    session_factory: SessionFactory,
    case: AuthorizationCase,
    role: str,
) -> None:
    resource_ids = seed_resources(session_factory)
    current_user = create_user(
        session_factory,
        f"caller-{role.lower()}@example.test",
        role,
    )
    token = create_access_token(str(current_user.id), {"role": role})
    path = case.path.format(**resource_ids)
    payload = get_payload(case.payload_name, resource_ids)
    request_options: dict[str, object] = {
        "headers": {"Authorization": f"Bearer {token}"}
    }
    if payload is not None:
        request_options["json"] = payload

    response = client.request(case.method, path, **request_options)

    if role in case.allowed_roles:
        assert response.status_code == case.success_status
    else:
        assert response.status_code == 403
        assert response.json()["code"] == "AUTH_FORBIDDEN"
