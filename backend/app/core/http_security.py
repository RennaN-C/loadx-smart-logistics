from collections.abc import Sequence

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.responses import error_response

UNSAFE_HTTP_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


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
