import json

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.core.security import decode_token_payload
from app.core.status_codes import UNAUTHORIZED
from app.db.session import SessionLocal
from app.models.rbac import OperationLog
from app.schemas.response import ApiResponse
from app.services.auth_service import is_access_token_revoked


def _unauthorized_response() -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content=ApiResponse(code=UNAUTHORIZED, msg="身份失效", data=None).model_dump(),
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Global JWT gate for APP-zone APIs."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if request.method == "OPTIONS" or path in settings.auth_whitelist_paths:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return _unauthorized_response()

        try:
            payload = decode_token_payload(token)
            if payload.get("typ") != "access":
                return _unauthorized_response()
            if is_access_token_revoked(payload.get("jti")):
                return _unauthorized_response()
            request.state.user_id = int(payload["sub"])
            request.state.token_jti = payload.get("jti")
        except (BusinessException, ValueError):
            return _unauthorized_response()
        return await call_next(request)


class OperationLogMiddleware(BaseHTTPMiddleware):
    """Best-effort operation log; failures never block business APIs."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        if (
            request.method == "OPTIONS"
            or request.url.path in settings.auth_whitelist_paths
        ):
            return response

        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            status_code: int | None = None
            response_message: str | None = None
            if body:
                payload = json.loads(body.decode("utf-8"))
                status_code = payload.get("code")
                response_message = payload.get("msg")

            with SessionLocal() as db:
                db.add(
                    OperationLog(
                        user_id=getattr(request.state, "user_id", None),
                        username=None,
                        ip_address=request.client.host if request.client else None,
                        method=request.method,
                        path=request.url.path,
                        operation=getattr(request.state, "permission_code", None),
                        status_code=status_code,
                        response_message=response_message,
                    )
                )
                db.commit()
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        except Exception:
            return response
