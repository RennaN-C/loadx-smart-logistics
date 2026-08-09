from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.http_security import (
    API_CONTENT_SECURITY_POLICY,
    OriginValidationMiddleware,
    SecurityHeadersMiddleware,
)


def make_client() -> TestClient:
    app = FastAPI()
    app.add_middleware(
        OriginValidationMiddleware,
        allowed_origins=["https://app.example.test"],
    )

    @app.get("/api/v1/resource")
    def read_resource() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/api/v1/resource")
    def change_resource() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def test_origin_validation_allows_safe_method_without_origin() -> None:
    with make_client() as client:
        response = client.get("/api/v1/resource")

    assert response.status_code == 200


def test_origin_validation_allows_exact_origin_for_unsafe_method() -> None:
    with make_client() as client:
        response = client.post(
            "/api/v1/resource",
            headers={"Origin": "https://app.example.test"},
        )

    assert response.status_code == 200


def test_origin_validation_rejects_missing_or_unapproved_origin() -> None:
    with make_client() as client:
        missing = client.post("/api/v1/resource")
        unapproved = client.post(
            "/api/v1/resource",
            headers={"Origin": "https://attacker.example"},
        )

    assert missing.status_code == 403
    assert missing.json()["code"] == "AUTH_ORIGIN_FORBIDDEN"
    assert unapproved.status_code == 403


def make_security_headers_client(*, enable_hsts: bool) -> TestClient:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=enable_hsts)

    @app.get("/api/v1/resource")
    def read_resource() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def test_security_headers_protect_api_responses() -> None:
    with make_security_headers_client(enable_hsts=False) as client:
        response = client.get("/api/v1/resource")

    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Content-Security-Policy"] == API_CONTENT_SECURITY_POLICY
    assert response.headers["Permissions-Policy"] == (
        "camera=(), geolocation=(), microphone=()"
    )
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" not in response.headers


def test_security_headers_enable_hsts_in_production() -> None:
    with make_security_headers_client(enable_hsts=True) as client:
        response = client.get("/api/v1/resource")

    assert response.headers["Strict-Transport-Security"] == (
        "max-age=31536000; includeSubDomains"
    )
