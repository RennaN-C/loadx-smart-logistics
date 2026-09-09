from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.http_security import (
    API_CONTENT_SECURITY_POLICY,
    OriginValidationMiddleware,
    SecurityHeadersMiddleware,
)
from app.main import create_app


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


def test_application_preserves_cors_headers_and_exact_origin() -> None:
    app = create_app(
        Settings(
            app_env="local",
            backend_cors_origins_raw="https://app.example.test",
            _env_file=None,
        )
    )
    with TestClient(app) as client:
        allowed = client.get("/health", headers={"Origin": "https://app.example.test"})
        for origin in (None, "https://app.example.test.attacker.example"):
            rejected = client.post(
                "/api/v1/auth/login",
                headers={"Origin": origin} if origin else {},
            )
            assert rejected.status_code == 403
            assert rejected.json()["code"] == "AUTH_ORIGIN_FORBIDDEN"
            assert rejected.headers["X-Frame-Options"] == "DENY"
            assert "Access-Control-Allow-Origin" not in rejected.headers

    assert allowed.status_code == 200
    assert allowed.headers["Access-Control-Allow-Origin"] == "https://app.example.test"
    assert allowed.headers["Access-Control-Allow-Credentials"] == "true"
    assert allowed.headers["Content-Security-Policy"] == API_CONTENT_SECURITY_POLICY
    assert allowed.headers["Cache-Control"] == "no-store"


def test_application_cors_allows_csrf_preflight_only_for_exact_origin() -> None:
    app = create_app(
        Settings(
            app_env="local",
            backend_cors_origins_raw="https://app.example.test",
            _env_file=None,
        )
    )
    with TestClient(app) as client:
        for origin, expected_status in (
            ("https://app.example.test", 200),
            ("https://app.example.test.attacker.example", 400),
        ):
            response = client.options(
                "/api/v1/auth/login",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type, X-CSRF-Token",
                },
            )
            assert response.status_code == expected_status
            if expected_status == 200:
                assert response.headers["Access-Control-Allow-Origin"] == origin
                assert (
                    "X-CSRF-Token" in response.headers["Access-Control-Allow-Headers"]
                )
