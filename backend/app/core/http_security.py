from collections.abc import Sequence

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.responses import error_response

UNSAFE_HTTP_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
API_CONTENT_SECURITY_POLICY = (
    "default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, enable_hsts: bool) -> None:
        super().__init__(app)
        self.enable_hsts = enable_hsts

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = API_CONTENT_SECURITY_POLICY
        response.headers["Permissions-Policy"] = (
            "camera=(), geolocation=(), microphone=()"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


class OriginValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, allowed_origins: Sequence[str]) -> None:
        super().__init__(app)
        self.allowed_origins = frozenset(allowed_origins)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if (
            request.url.path.startswith("/api/v1/")
            and request.method in UNSAFE_HTTP_METHODS
            and request.headers.get("origin") not in self.allowed_origins
        ):
            return error_response(
                403,
                "AUTH_ORIGIN_FORBIDDEN",
                "Origem da requisição não autorizada.",
            )
        return await call_next(request)
