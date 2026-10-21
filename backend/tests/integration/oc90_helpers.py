"""Real HTTP setup shared by OC90 integration and end-to-end tests."""

import uuid
from dataclasses import dataclass, field

from fastapi.testclient import TestClient

from app.modules.orders.models import Order
from app.modules.users.models import User
from tests.integration.auth_helpers import issue_session_headers


@dataclass
class MultiFlow:
    client: TestClient
    factory: object
    manager_id: uuid.UUID
    headers: dict
    checker: dict
    admin: dict
    driver_headers: list[dict] = field(default_factory=list)
    drivers: list[dict] = field(default_factory=list)
    order: dict = field(default_factory=dict)
    distribution: dict = field(default_factory=dict)
    loadings: list[dict] = field(default_factory=list)
    trips: list[dict] = field(default_factory=list)

    def request(self, method, path, data=None, *, expected=200, headers=None):
        response = self.client.request(
            method,
            "/api/v1" + path,
            json=data,
            headers=self.headers if headers is None else headers,
        )
        assert response.status_code == expected, response.text
        return response.json()

    @property
    def parts(self):
        return sorted(self.distribution["parts"], key=lambda p: p["id"])

    def status(self):
        with self.factory() as db:
            return db.get(Order, uuid.UUID(self.order["id"])).status

    def approve(self):
        self.distribution = self.request(
            "POST", f"/load-distributions/{self.distribution['id']}/approve", {}
        )

    def create_loading(self, index):
        return self.request(
            "POST",
            "/loading-sessions",
            {"load_plan_id": self.parts[index]["load_plan"]["id"]},
            expected=201,
        )

    def prepare_loadings(self):
        self.loadings = [self.create_loading(i) for i in range(2)]

    def finish_loading(self, index):
        loading = self.loadings[index]
        prefix = f"/loading-sessions/{loading['id']}"
        self.request(
            "PATCH", prefix + "/status", {"status": "IN_PROGRESS"}, headers=self.checker
        )
        for item in loading["items"]:
            self.request(
                "PATCH",
                prefix + f"/items/{item['id']}",
                {"status": "CHECKED"},
                headers=self.checker,
            )
        return self.request(
            "PATCH", prefix + "/status", {"status": "FINISHED"}, headers=self.checker
        )

    def create_trip(self, index):
        return self.request(
            "POST",
            "/trips",
            {
                "load_plan_id": self.parts[index]["load_plan"]["id"],
                "driver_id": self.drivers[index]["id"],
            },
            expected=201,
        )

    def trip_status(self, index, status, *, expected=200):
        return self.request(
            "PATCH",
            f"/trips/{self.trips[index]['id']}/status",
            {"status": status},
            expected=expected,
        )

    def complete_delivery(self, index):
        delivery = self.trips[index]["deliveries"][0]
        self.request(
            "PATCH", f"/deliveries/{delivery['id']}/status", {"status": "IN_DELIVERY"}
        )
        return self.request("POST", f"/deliveries/{delivery['id']}/receipt", {})


def seed_multi_flow(client, factory, *, optimize=True):
    with factory() as db:
        users = [
            User(
                name="OC90 fictício",
                email=f"oc90-{uuid.uuid4().hex}@example.test",
                role=role,
                password_hash="hash-ficticio",
                active=True,
            )
            for role in ("LOGISTICS_MANAGER", "CHECKER", "ADMIN")
        ]
        db.add_all(users)
        db.commit()
        ids = [user.id for user in users]
    headers = [issue_session_headers(factory, identifier) for identifier in ids]
    s = MultiFlow(client, factory, ids[0], *headers)
    customer = s.request(
        "POST",
        "/customers",
        {
            "name": "Cliente multi fictício",
            "document": "00000000000191",
            "address": "Rua de teste, 1",
            "city": "Campinas",
            "state": "SP",
        },
        expected=201,
    )
    product = s.request(
        "POST",
        "/products",
        {
            "code": "OC90-" + uuid.uuid4().hex,
            "name": "Caixa indivisível fictícia",
            "width_cm": 10,
            "height_cm": 10,
            "length_cm": 10,
            "weight_kg": 1,
            "fragile": False,
            "stackable": False,
            "rotation_allowed": False,
        },
        expected=201,
    )
    for index in range(2):
        s.drivers.append(
            s.request(
                "POST",
                "/drivers",
                {
                    "name": "Motorista fictício",
                    "document": ("12345678909", "98765432100")[index],
                    "phone": "11900000000",
                    "license_number": ("12345678900", "98765432109")[index],
                    "license_category": "D",
                },
                expected=201,
            )
        )
        s.request(
            "POST",
            "/trucks",
            {
                "plate": uuid.uuid4().hex[:7].upper(),
                "model": "Baú unitário fictício",
                "internal_width_cm": 10,
                "internal_height_cm": 10,
                "internal_length_cm": 10,
                "max_weight_kg": 10,
            },
            expected=201,
        )
    with factory() as db:
        driver_users = [
            User(
                name="Usuário motorista fictício",
                email=f"oc90-driver-{uuid.uuid4().hex}@example.test",
                role="DRIVER",
                driver_id=uuid.UUID(driver["id"]),
                password_hash="hash-ficticio",
                active=True,
            )
            for driver in s.drivers
        ]
        db.add_all(driver_users)
        db.commit()
        driver_ids = [user.id for user in driver_users]
    s.driver_headers = [
        issue_session_headers(factory, identifier) for identifier in driver_ids
    ]
    s.order = s.request(
        "POST",
        "/orders",
        {
            "customer_id": customer["id"],
            "priority": "NORMAL",
            "delivery_address": "Destino fictício",
            "items": [
                {"product_id": product["id"], "quantity": 2, "delivery_sequence": 1}
            ],
        },
        expected=201,
    )
    s.request("PATCH", f"/orders/{s.order['id']}/status", {"status": "READY"})
    if optimize:
        s.distribution = s.request(
            "POST",
            "/load-distributions/optimize",
            {"order_ids": [s.order["id"]]},
            expected=201,
        )
        assert s.distribution["truck_count"] == 2
    return s
