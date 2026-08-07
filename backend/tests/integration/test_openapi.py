from typing import Any

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

EXPECTED_ERROR_STATUSES = {
    ("/health", "get"): {"500"},
    ("/api/v1/auth/login", "post"): {"401", "403", "422", "500"},
    ("/api/v1/auth/me", "get"): {"401", "403", "422", "500"},
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
    ("/api/v1/products", "get"): {"401", "403", "500"},
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
    ("/api/v1/trucks", "get"): {"401", "403", "500"},
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
    ("/api/v1/load-plans", "post"): {
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
}
PUBLIC_OPERATIONS = frozenset(
    {
        ("/health", "get"),
        ("/api/v1/auth/login", "post"),
    }
)
PROTECTED_OPERATIONS = frozenset(EXPECTED_ERROR_STATUSES).difference(PUBLIC_OPERATIONS)
HTTP_METHODS = frozenset({"get", "post", "patch", "put", "delete"})


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


def test_openapi_documents_bearer_authentication_for_protected_routes() -> None:
    schema = get_openapi_schema()

    bearer_scheme = schema["components"]["securitySchemes"]["BearerAuth"]
    assert bearer_scheme == {"type": "http", "scheme": "bearer"}

    for path, method in PROTECTED_OPERATIONS:
        assert schema["paths"][path][method]["security"] == [{"BearerAuth": []}]

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
