from typing import Any

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

EXPECTED_ERROR_STATUSES = {
    ("/api/v1/deliveries/{delivery_id}/communications", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    **{
        (path, method): {"400", "401", "403", "422", "429", "503", "500"}
        for path, method in [
            ("/api/v1/auth/password-recovery", "post"),
            ("/api/v1/auth/password-recovery/confirm", "post"),
            ("/api/v1/auth/mfa/setup", "post"),
            ("/api/v1/auth/mfa/verify", "post"),
            ("/api/v1/auth/me/mfa", "get"),
            ("/api/v1/auth/me/trusted-devices", "get"),
            ("/api/v1/auth/me/trusted-devices/current", "delete"),
            ("/api/v1/auth/me/trusted-devices/{device_id}", "delete"),
            ("/api/v1/auth/me/trusted-devices/revoke-all", "post"),
            ("/api/v1/auth/me/mfa/enroll", "post"),
            ("/api/v1/auth/me/mfa/recovery-codes", "post"),
            ("/api/v1/auth/me/mfa/disable", "post"),
        ]
    },
    ("/api/v1/outbox-events", "get"): {"401", "403", "404", "409", "422", "500"},
    ("/api/v1/outbox-events/summary", "get"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/outbox-events/{event_id}", "get"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/outbox-events/{event_id}/attempts", "get"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/outbox-events/{event_id}/source", "get"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/outbox-events/{event_id}/retry", "post"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/notifications", "get"): {"401", "403", "422", "500"},
    ("/api/v1/notifications/unread-count", "get"): {"401", "403", "422", "500"},
    ("/api/v1/notifications/preferences", "get"): {"401", "403", "422", "500"},
    ("/api/v1/notifications/preferences", "put"): {"401", "403", "422", "500"},
    ("/api/v1/notifications/read-all", "post"): {"401", "403", "422", "500"},
    ("/api/v1/notifications/{notification_id}/read", "post"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/notifications/{notification_id}/source", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/access-profiles", "get"): {"401", "403", "404", "409", "422", "500"},
    ("/api/v1/access-profiles", "post"): {"401", "403", "404", "409", "422", "500"},
    ("/api/v1/access-profiles/permissions", "get"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/access-profiles/{profile_id}", "get"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/access-profiles/{profile_id}", "patch"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/search", "get"): {"401", "403", "422", "500"},
    ("/api/v1/auth/me", "patch"): {
        "400",
        "401",
        "403",
        "409",
        "422",
        "429",
        "503",
        "500",
    },
    ("/api/v1/auth/me/password", "post"): {"400", "401", "403", "422", "429", "500"},
    ("/api/v1/auth/me/sessions", "get"): {"401", "403", "422", "500"},
    ("/api/v1/auth/me/sessions/{session_id}", "delete"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/auth/me/sessions/revoke-others", "post"): {"401", "403", "422", "500"},
    ("/api/v1/integration-health", "get"): {"401", "403", "422", "500"},
    ("/api/v1/company-profile", "get"): {"401", "403", "422", "500"},
    ("/api/v1/company-profile", "put"): {"401", "403", "422", "500"},
    ("/health", "get"): {"500"},
    ("/ready", "get"): {"500", "503"},
    ("/api/v1/auth/login", "post"): {"401", "403", "422", "429", "500", "503"},
    ("/api/v1/auth/me", "get"): {"401", "403", "422", "500"},
    ("/api/v1/auth/logout", "post"): {"401", "403", "422", "500"},
    ("/api/v1/audit", "get"): {"401", "403", "422", "500"},
    ("/api/v1/users", "get"): {"401", "403", "422", "500"},
    ("/api/v1/users", "post"): {"401", "403", "409", "422", "500"},
    ("/api/v1/users/{user_id}", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/users/{user_id}", "patch"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/customers", "get"): {"401", "403", "422", "500"},
    ("/api/v1/customers", "post"): {"401", "403", "409", "422", "500"},
    ("/api/v1/customers/cep/{cep}", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
        "502",
        "503",
        "504",
    },
    ("/api/v1/customers/{customer_id}", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/customers/{customer_id}", "patch"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/drivers", "get"): {"401", "403", "422", "500"},
    ("/api/v1/drivers/operational-status", "get"): {"401", "403", "422", "500"},
    ("/api/v1/drivers", "post"): {"401", "403", "409", "422", "500"},
    ("/api/v1/drivers/{driver_id}", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/drivers/{driver_id}", "patch"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/products", "get"): {"401", "403", "422", "500"},
    ("/api/v1/products", "post"): {"401", "403", "409", "422", "500"},
    ("/api/v1/products/{product_id}", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/products/{product_id}", "patch"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/trucks", "get"): {"401", "403", "422", "500"},
    ("/api/v1/trucks/operational-status", "get"): {"401", "403", "422", "500"},
    ("/api/v1/trucks", "post"): {"401", "403", "409", "422", "500"},
    ("/api/v1/trucks/{truck_id}", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/trucks/{truck_id}", "patch"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/orders", "get"): {"401", "403", "422", "500"},
    ("/api/v1/orders", "post"): {"401", "403", "404", "422", "500"},
    ("/api/v1/orders/{order_id}", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/orders/{order_id}", "patch"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/orders/{order_id}/status", "patch"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/load-plans", "get"): {"401", "403", "422", "500"},
    ("/api/v1/load-plans/{load_plan_id}/continuity", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/load-plans", "post"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/load-plans/compare-trucks", "post"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/load-plans/{load_plan_id}", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/load-plans/{load_plan_id}/explain", "post"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/load-plans/{load_plan_id}/visualization", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/load-plans/{load_plan_id}/approve", "post"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/load-plans/{load_plan_id}/recalculate", "post"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/trips", "post"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/trips", "get"): {
        "401",
        "403",
        "422",
        "500",
    },
    ("/api/v1/trips/{trip_id}", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/trips/{trip_id}/status", "patch"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/deliveries/{delivery_id}/status", "patch"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/deliveries/{delivery_id}/receipt", "post"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/deliveries/{delivery_id}/receipt", "get"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/deliveries/{delivery_id}/evidences", "post"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
        "503",
    },
    ("/api/v1/deliveries/{delivery_id}/evidences", "get"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
        "503",
    },
    ("/api/v1/deliveries/{delivery_id}/evidences/{evidence_id}", "get"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
        "503",
    },
    ("/api/v1/deliveries/{delivery_id}/evidences/{evidence_id}/content", "get"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
        "503",
    },
    ("/api/v1/deliveries/{delivery_id}/evidences/{evidence_id}/revoke", "post"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
        "503",
    },
    ("/api/v1/loading-sessions", "post"): {
        "401",
        "403",
        "409",
        "422",
        "500",
    },
    ("/api/v1/loading-sessions/{session_id}", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/loading-sessions/{session_id}/status", "patch"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/loading-sessions/{session_id}/scan", "post"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/loading-sessions/{session_id}/items/{item_id}", "patch"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/messages/interpret", "post"): {"401", "403", "422", "500"},
    ("/api/v1/occurrences", "post"): {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/trips/{trip_id}/occurrences", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/reports/load-plans/{load_plan_id}", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/reports/trips/{trip_id}", "get"): {
        "401",
        "403",
        "404",
        "422",
        "500",
    },
    ("/api/v1/operational-indicators", "get"): {"401", "403", "500"},
}
for distribution_path, methods in {
    "/api/v1/load-distributions": ("post",),
    "/api/v1/load-distributions/preflight": ("post",),
    "/api/v1/load-distributions/optimize": ("post",),
    "/api/v1/load-distributions/{distribution_id}": ("get",),
    "/api/v1/load-distributions/{distribution_id}/approve": ("post",),
    "/api/v1/load-distributions/{distribution_id}/cancel": ("post",),
    "/api/v1/load-distributions/{distribution_id}/parts/{part_id}/approve": ("post",),
    "/api/v1/load-distributions/{distribution_id}/parts/{part_id}/cancel": ("post",),
    "/api/v1/load-distributions/{distribution_id}/parts/{part_id}/reprocess": ("post",),
}.items():
    for distribution_method in methods:
        EXPECTED_ERROR_STATUSES[(distribution_path, distribution_method)] = {
            "401",
            "403",
            "404",
            "409",
            "422",
            "500",
        }

for address_path, address_method in (
    ("/api/v1/customers/{customer_id}/addresses", "get"),
    ("/api/v1/customers/{customer_id}/addresses", "post"),
    ("/api/v1/customers/{customer_id}/addresses/{address_id}", "patch"),
):
    EXPECTED_ERROR_STATUSES[(address_path, address_method)] = {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    }

for maintenance_path, maintenance_method in (
    ("/api/v1/drivers/{driver_id}/documents", "get"),
    ("/api/v1/drivers/{driver_id}/documents", "post"),
    ("/api/v1/drivers/{driver_id}/documents/{document_id}/renew", "post"),
    ("/api/v1/drivers/{driver_id}/document-policies", "get"),
    ("/api/v1/drivers/{driver_id}/document-policies/{document_type_id}", "patch"),
    ("/api/v1/trucks/{truck_id}/documents", "get"),
    ("/api/v1/trucks/{truck_id}/documents", "post"),
    ("/api/v1/trucks/{truck_id}/documents/{document_id}/renew", "post"),
    ("/api/v1/trucks/{truck_id}/document-policies", "get"),
    ("/api/v1/trucks/{truck_id}/document-policies/{kind}", "patch"),
    ("/api/v1/trucks/{truck_id}/maintenances", "get"),
    ("/api/v1/trucks/{truck_id}/maintenances", "post"),
    ("/api/v1/trucks/{truck_id}/maintenances/{maintenance_id}/close", "post"),
):
    EXPECTED_ERROR_STATUSES[(maintenance_path, maintenance_method)] = {
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    }

for method in ("get", "post"):
    EXPECTED_ERROR_STATUSES[("/api/v1/driver-document-types", method)] = {
        "401",
        "403",
        "409",
        "422",
        "500",
    }

for attachment_suffix, attachment_method in (
    ("", "get"),
    ("", "post"),
    ("/{attachment_id}", "get"),
    ("/{attachment_id}/content", "get"),
    ("/{attachment_id}/revoke", "post"),
):
    EXPECTED_ERROR_STATUSES[
        (
            f"/api/v1/attachments/{{resource_type}}/{{resource_id}}{attachment_suffix}",
            attachment_method,
        )
    ] = {"401", "403", "404", "409", "422", "500", "503"}

for import_suffix, import_method in (
    ("", "get"),
    ("/{import_id}", "get"),
    ("/{entity_type}/template", "get"),
    ("/{entity_type}/preview", "post"),
    ("/{entity_type}/confirm", "post"),
):
    EXPECTED_ERROR_STATUSES[
        (f"/api/v1/registration-imports{import_suffix}", import_method)
    ] = {"401", "403", "404", "409", "422", "500"}

SIGNED_OPERATIONS = frozenset({("/api/v1/webhooks/controlled-events", "post")})
EXPECTED_ERROR_STATUSES[("/api/v1/webhooks/controlled-events", "post")] = {
    "400",
    "401",
    "403",
    "408",
    "409",
    "410",
    "413",
    "415",
    "422",
    "429",
    "500",
    "503",
}

PUBLIC_OPERATIONS = frozenset(
    {
        ("/health", "get"),
        ("/ready", "get"),
        ("/api/v1/auth/login", "post"),
        ("/api/v1/auth/password-recovery", "post"),
        ("/api/v1/auth/password-recovery/confirm", "post"),
        ("/api/v1/auth/mfa/setup", "post"),
        ("/api/v1/auth/mfa/verify", "post"),
    }
)
PROTECTED_OPERATIONS = frozenset(EXPECTED_ERROR_STATUSES).difference(
    PUBLIC_OPERATIONS, SIGNED_OPERATIONS
)
HTTP_METHODS = frozenset({"get", "post", "patch", "put", "delete"})


def test_openapi_documents_loading_scan_contract() -> None:
    schema = get_openapi_schema()
    operation = schema["paths"]["/api/v1/loading-sessions/{session_id}/scan"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LoadingItemScan"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LoadingSessionRead"
    }
    components = schema["components"]["schemas"]
    assert components["LoadingItemScan"]["additionalProperties"] is False
    code_schema = components["LoadingItemScan"]["properties"]["code"]
    assert code_schema["minLength"] == code_schema["maxLength"] == 55
    assert components["LoadingSessionItemRead"]["properties"]["code"]["readOnly"]


def get_openapi_schema() -> dict[str, Any]:
    local_app = create_app(Settings(app_env="local", _env_file=None))
    with TestClient(local_app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


def test_openapi_defines_standard_error_response_schema() -> None:
    schema = get_openapi_schema()

    assert "HTTPValidationError" not in schema["components"]["schemas"]
    error_schema = schema["components"]["schemas"]["ErrorResponse"]
    assert set(error_schema["required"]) == {"code", "message", "details"}
    assert error_schema["properties"]["code"]["type"] == "string"
    assert error_schema["properties"]["message"]["type"] == "string"
    assert error_schema["properties"]["details"]["type"] == "array"


def test_openapi_declares_all_public_decimal_fields_as_numbers() -> None:
    schema = get_openapi_schema()
    components = schema["components"]["schemas"]
    decimal_fields = {
        "TruckCreate": ("max_weight_kg",),
        "TruckRead": ("max_weight_kg",),
        "TruckUpdate": ("max_weight_kg",),
        "ProductCreate": ("weight_kg",),
        "ProductRead": ("weight_kg",),
        "ProductUpdate": ("weight_kg",),
        "LoadPlanItemRead": ("weight_kg",),
        "PlacedLoadPlanItemRead": ("weight_kg",),
        "UnloadedLoadPlanItemRead": ("weight_kg",),
        "LoadPlanRead": ("occupancy_percent", "total_weight_kg"),
        "LoadPlanListRead": ("occupancy_percent", "total_weight_kg"),
        "TruckComparisonRead": ("occupancy_percent", "total_weight_kg"),
        "TruckSnapshotRead": ("max_weight_kg",),
    }

    for component_name, field_names in decimal_fields.items():
        properties = components[component_name]["properties"]
        for field_name in field_names:
            field_schema = properties[field_name]
            allowed_types = (
                {variant["type"] for variant in field_schema["anyOf"]}
                if "anyOf" in field_schema
                else {field_schema["type"]}
            )
            assert allowed_types <= {"number", "null"}
            assert "number" in allowed_types


def test_openapi_uses_standard_schema_for_each_documented_error() -> None:
    schema = get_openapi_schema()

    for (path, method), expected_statuses in EXPECTED_ERROR_STATUSES.items():
        responses = schema["paths"][path][method]["responses"]
        actual_error_statuses = {
            status_code for status_code in responses if int(status_code) >= 400
        }
        assert actual_error_statuses == expected_statuses

        for status_code in expected_statuses:
            response_schema = responses[status_code]["content"]["application/json"][
                "schema"
            ]
            assert response_schema == {"$ref": "#/components/schemas/ErrorResponse"}


def test_openapi_documents_cookie_authentication_for_protected_routes() -> None:
    schema = get_openapi_schema()

    cookie_scheme = schema["components"]["securitySchemes"]["SessionCookie"]
    assert cookie_scheme == {
        "type": "apiKey",
        "in": "cookie",
        "name": "loadx_session",
    }

    for path, method in PROTECTED_OPERATIONS:
        assert schema["paths"][path][method]["security"] == [{"SessionCookie": []}]

    for path, method in PUBLIC_OPERATIONS:
        assert "security" not in schema["paths"][path][method]


def test_openapi_exposes_only_the_approved_public_and_protected_operations() -> None:
    schema = get_openapi_schema()
    documented_operations = frozenset(
        (path, method)
        for path, path_item in schema["paths"].items()
        for method in path_item
        if method in HTTP_METHODS
    )

    assert documented_operations == frozenset(EXPECTED_ERROR_STATUSES)


def test_openapi_does_not_expose_public_registration() -> None:
    schema = get_openapi_schema()

    assert "/api/v1/auth/register" not in schema["paths"]


def test_openapi_cep_lookup_exposes_existing_address_schema_with_text_limits() -> None:
    schema = get_openapi_schema()
    response_schema = schema["paths"]["/api/v1/customers/cep/{cep}"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]

    assert response_schema == {"$ref": "#/components/schemas/ViaCEPAddress"}
    properties = schema["components"]["schemas"]["ViaCEPAddress"]["properties"]
    assert set(properties) == {
        "cep",
        "street",
        "neighborhood",
        "complement",
        "city",
        "state",
    }
    assert properties["city"]["maxLength"] == 120
    for field in ("street", "neighborhood", "complement"):
        text_schema = next(
            variant
            for variant in properties[field]["anyOf"]
            if variant["type"] == "string"
        )
        assert text_schema["maxLength"] == 255


def test_openapi_documents_truck_operational_status_contract() -> None:
    schema = get_openapi_schema()

    operation = schema["paths"]["/api/v1/trucks/operational-status"]["get"]
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]

    page_component_name = response_schema["$ref"].split("/")[-1]
    page_schema = schema["components"]["schemas"][page_component_name]

    item_schema = page_schema["properties"]["items"]["items"]
    assert item_schema == {"$ref": "#/components/schemas/TruckOperationalStatusRead"}

    status_schema = schema["components"]["schemas"]["TruckOperationalStatusRead"]
    expected_fields = {
        "id",
        "plate",
        "model",
        "active",
        "has_operation_conflict",
        "has_maintenance_conflict",
        "has_document_conflict",
        "available",
    }

    assert set(status_schema["properties"]) == expected_fields
    assert set(status_schema["required"]) == expected_fields


def test_openapi_documents_operational_indicators_contract() -> None:
    schema = get_openapi_schema()

    response_schema = schema["paths"]["/api/v1/operational-indicators"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]

    assert response_schema == {"$ref": "#/components/schemas/OperationalIndicatorsRead"}

    components = schema["components"]["schemas"]

    assert set(components["OperationalIndicatorsRead"]["properties"]) == {
        "fleet",
        "trips",
        "deliveries",
        "occurrences",
    }

    assert set(components["FleetIndicatorsRead"]["properties"]) == {
        "period",
        "total",
        "active",
        "inactive",
        "available",
        "unavailable",
        "with_operation_conflict",
    }

    assert set(components["TripIndicatorsRead"]["properties"]) == {
        "period",
        "total",
        "scheduled",
        "in_route",
        "finished",
    }

    assert set(components["DeliveryIndicatorsRead"]["properties"]) == {
        "period",
        "total",
        "pending",
        "in_delivery",
        "delivered",
    }

    assert set(components["OccurrenceIndicatorsRead"]["properties"]) == {
        "period",
        "total",
    }


def test_openapi_documents_driver_operational_status_contract() -> None:
    schema = get_openapi_schema()

    operation = schema["paths"]["/api/v1/drivers/operational-status"]["get"]
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]

    page_component_name = response_schema["$ref"].split("/")[-1]
    page_schema = schema["components"]["schemas"][page_component_name]
    item_schema = page_schema["properties"]["items"]["items"]

    assert item_schema == {"$ref": "#/components/schemas/DriverOperationalStatusRead"}

    status_schema = schema["components"]["schemas"]["DriverOperationalStatusRead"]
    expected_fields = {
        "id",
        "name",
        "license_category",
        "active",
        "has_document_conflict",
        "has_operation_conflict",
        "available",
    }
    assert set(status_schema["properties"]) == expected_fields
    assert set(status_schema["required"]) == expected_fields


def test_driver_documents_preserve_oc101_schema_names():
    schema = get_openapi_schema()
    assert "DocumentRead" in schema["components"]["schemas"]
    assert "DriverDocumentRead" in schema["components"]["schemas"]
    assert schema["paths"]["/api/v1/trucks/{truck_id}/documents"]["post"]["responses"][
        "201"
    ]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/DocumentRead"
    }
    assert schema["paths"]["/api/v1/drivers/{driver_id}/documents"]["post"][
        "responses"
    ]["201"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/DriverDocumentRead"
    }


def test_oc95_explicit_filter_whitelist_preserves_privacy() -> None:
    schema = create_app(Settings(app_env="local")).openapi()
    expected = {
        "orders": {"search", "status"},
        "trucks": {"search", "archive_status"},
        "products": {"search", "restriction", "archive_status"},
        "customers": {"search", "archive_status"},
        "drivers": {"search", "archive_status"},
    }
    for resource, filters in expected.items():
        parameters = schema["paths"][f"/api/v1/{resource}"]["get"]["parameters"]
        query = {p["name"]: p for p in parameters if p["in"] == "query"}
        assert set(query) == {"page", "page_size", "sort_order"} | filters
        assert query["search"]["schema"]["anyOf"][0]["maxLength"] == 120
        if resource == "orders":
            assert set(query["status"]["schema"]["anyOf"][0]["enum"]) == {
                "DRAFT",
                "READY",
                "PLANNED",
                "IN_TRANSIT",
                "DELIVERED",
                "CANCELED",
            }
        if resource == "products":
            assert set(query["restriction"]["schema"]["anyOf"][0]["enum"]) == {
                "restricted",
                "free",
            }
    for resource in ("trucks", "drivers"):
        parameters = schema["paths"][f"/api/v1/{resource}/operational-status"]["get"][
            "parameters"
        ]
        assert {p["name"] for p in parameters} == {"page", "page_size", "sort_order"}


def test_oc86_admin_list_documents_identity_fields_and_safe_filters() -> None:
    schema = get_openapi_schema()
    operation = schema["paths"]["/api/v1/users"]["get"]
    query = {
        item["name"]: item for item in operation["parameters"] if item["in"] == "query"
    }
    assert set(query) == {"page", "page_size", "sort_order", "search", "role", "active"}
    assert query["search"]["schema"]["anyOf"][0]["maxLength"] == 120
    assert set(query["role"]["schema"]["anyOf"][0]["enum"]) == {
        "ADMIN",
        "LOGISTICS_MANAGER",
        "CHECKER",
        "DRIVER",
        "CUSTOM",
    }
    assert operation["security"] == [{"SessionCookie": []}]
    fields = schema["components"]["schemas"]["UserListRead"]["properties"]
    assert set(fields) == {
        "id",
        "name",
        "email",
        "role",
        "active",
        "driver_id",
        "driver_name",
        "custom_profile_id",
        "custom_profile_name",
        "created_at",
    }
    assert "password_hash" not in fields


def test_openapi_documents_inbound_signature_without_session_cookie():
    schema = get_openapi_schema()
    operation = schema["paths"]["/api/v1/webhooks/controlled-events"]["post"]
    assert "security" not in operation
    signature = next(
        item for item in operation["parameters"] if item["name"] == "X-LoadX-Signature"
    )
    assert signature["required"] is True
    assert signature["schema"]["pattern"] == "^[0-9a-f]{64}$"
    body = operation["requestBody"]["content"]["application/json"]["schema"]
    assert body["additionalProperties"] is False
    assert set(body["properties"]["command"]["enum"]) == {
        "START_TRIP",
        "START_DELIVERY",
        "FINISH_DELIVERY",
    }


def test_notification_contract_is_personal_and_excludes_channel_secrets() -> None:
    schema = get_openapi_schema()
    listing = schema["paths"]["/api/v1/notifications"]["get"]
    parameters = {item["name"] for item in listing["parameters"]}
    assert parameters == {
        "page",
        "page_size",
        "sort_order",
        "read",
        "event_type",
        "category",
    }
    properties = schema["components"]["schemas"]["NotificationRead"]["properties"]
    assert set(properties) == {
        "id",
        "event_type",
        "category",
        "title",
        "summary",
        "created_at",
        "received_at",
        "read_at",
    }
    assert listing["security"] == [{"SessionCookie": []}]


def test_oc90_delivery_leg_context_is_additive_and_not_client_assignable():
    schema = get_openapi_schema()
    schemas = schema["components"]["schemas"]
    field = schemas["DeliveryRead"]["properties"]["distribution_part_id"]
    assert {"type": "string", "format": "uuid"} in field["anyOf"]
    assert {"type": "null"} in field["anyOf"]
    assert "distribution_part_id" not in schemas["DeliveryRead"]["required"]
    assert set(schemas["TripCreate"]["properties"]) == {"load_plan_id", "driver_id"}
    assert schemas["TripCreate"]["additionalProperties"] is False
    audit = schema["paths"]["/api/v1/audit"]["get"]["parameters"]
    entity = next(p for p in audit if p["name"] == "entity_type")
    assert {"LOAD_DISTRIBUTION", "LOAD_DISTRIBUTION_PART"} <= set(
        entity["schema"]["anyOf"][0]["enum"]
    )


def test_oc81_communication_is_read_only_bounded_and_sanitized():
    schema = get_openapi_schema()
    path = schema["paths"]["/api/v1/deliveries/{delivery_id}/communications"]
    assert set(path) == {"get"}
    listing = path["get"]
    assert listing["security"] == [{"SessionCookie": []}]
    assert {p["name"] for p in listing["parameters"]} == {
        "delivery_id",
        "page",
        "page_size",
        "sort_order",
    }
    properties = schema["components"]["schemas"]["DeliveryCommunicationRead"][
        "properties"
    ]
    assert set(properties) == {
        "id",
        "occurrence_id",
        "event_type",
        "created_at",
        "channel",
        "simulation_status",
        "processing_status",
    }
