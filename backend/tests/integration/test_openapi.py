from typing import Any

from fastapi.testclient import TestClient

from app.main import app

EXPECTED_ERROR_STATUSES = {
    ("/health", "get"): {"500"},
    ("/api/v1/auth/register", "post"): {"409", "422", "500"},
    ("/api/v1/auth/login", "post"): {"401", "403", "422", "500"},
    ("/api/v1/auth/me", "get"): {"401", "403", "422", "500"},
    ("/api/v1/users", "get"): {"500"},
    ("/api/v1/users", "post"): {"409", "422", "500"},
    ("/api/v1/users/{user_id}", "get"): {"404", "422", "500"},
    ("/api/v1/users/{user_id}", "patch"): {"404", "409", "422", "500"},
    ("/api/v1/customers", "get"): {"500"},
    ("/api/v1/customers", "post"): {"409", "422", "500"},
    ("/api/v1/customers/{customer_id}", "get"): {"404", "422", "500"},
    ("/api/v1/customers/{customer_id}", "patch"): {
        "404",
        "409",
        "422",
        "500",
    },
    ("/api/v1/drivers", "get"): {"500"},
    ("/api/v1/drivers", "post"): {"409", "422", "500"},
    ("/api/v1/drivers/{driver_id}", "get"): {"404", "422", "500"},
    ("/api/v1/drivers/{driver_id}", "patch"): {"404", "409", "422", "500"},
    ("/api/v1/products", "get"): {"500"},
    ("/api/v1/products", "post"): {"409", "422", "500"},
    ("/api/v1/products/{product_id}", "get"): {"404", "422", "500"},
    ("/api/v1/products/{product_id}", "patch"): {"404", "409", "422", "500"},
    ("/api/v1/trucks", "get"): {"500"},
    ("/api/v1/trucks", "post"): {"409", "422", "500"},
    ("/api/v1/trucks/{truck_id}", "get"): {"404", "422", "500"},
    ("/api/v1/trucks/{truck_id}", "patch"): {"404", "409", "422", "500"},
    ("/api/v1/orders", "get"): {"500"},
    ("/api/v1/orders", "post"): {"404", "422", "500"},
    ("/api/v1/orders/{order_id}", "get"): {"404", "422", "500"},
    ("/api/v1/orders/{order_id}", "patch"): {"404", "422", "500"},
}


def get_openapi_schema() -> dict[str, Any]:
    with TestClient(app) as client:
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
