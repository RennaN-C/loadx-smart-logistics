"""Regression: non-UTC database timezones must not break MFA login cookies."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi import Response

from app.modules.auth.identity_router import trusted_cookie_expiry


@pytest.mark.parametrize(
    "expires_at",
    [
        datetime(2026, 10, 22, 11, 37, tzinfo=UTC),
        datetime(2026, 10, 22, 8, 37, tzinfo=timezone(timedelta(hours=-3))),
        datetime(2026, 10, 22, 11, 37),
    ],
)
def test_trusted_cookie_expiry_is_utc_and_serializable(expires_at):
    normalized = trusted_cookie_expiry(expires_at)
    assert normalized == datetime(2026, 10, 22, 11, 37, tzinfo=UTC)
    assert normalized.tzinfo is UTC
    response = Response()
    response.set_cookie(
        key="trusted-device-test",
        value="opaque-test-token",
        max_age=30 * 86400,
        expires=normalized,
        secure=True,
        httponly=True,
        samesite="lax",
    )
    cookie = response.headers["set-cookie"]
    assert "expires=Thu, 22 Oct 2026 11:37:00 GMT" in cookie
    assert "Max-Age=2592000" in cookie
    assert "HttpOnly" in cookie
