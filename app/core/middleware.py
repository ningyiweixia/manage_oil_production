from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.core.security import decode_access_token
from app.core.status_codes import UNAUTHORIZED
from app.schemas.response import ApiResponse


class AuthMiddleware(BaseHTTPMiddleware):
    """Global JWT gate. Route-level dependencies still enforce RBAC permissions."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if request.method == "OPTIONS" or path in settings.auth_whitelist_paths:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return JSONResponse(
                status_code=200,
                content=ApiResponse(code=UNAUTHORIZED, msg="身份失效", data=None).model_dump(),
            )

        try:
            request.state.user_id = int(decode_access_token(token))
        except (BusinessException, ValueError):
            return JSONResponse(
                status_code=200,
                content=ApiResponse(code=UNAUTHORIZED, msg="身份失效", data=None).model_dump(),
            )
        return await call_next(request)
