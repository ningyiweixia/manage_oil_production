import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core import status_codes
from app.schemas.response import ApiResponse

logger = logging.getLogger(__name__)


class BusinessException(Exception):
    def __init__(self, code: int, msg: str, data: object | None = None) -> None:
        self.code = code
        self.msg = msg
        self.data = data


def _response(code: int, msg: str, data: object | None = None, http_status: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content=ApiResponse(code=code, msg=msg, data=data).model_dump(),
    )


def _http_status_for_code(code: int) -> int:
    if code == status_codes.BAD_REQUEST:
        return 400
    if code == status_codes.UNAUTHORIZED:
        return 401
    if code == status_codes.FORBIDDEN:
        return 403
    if code == status_codes.CONFLICT:
        return 409
    if code == status_codes.TOO_MANY_REQUESTS:
        return 429
    if code >= 50000:
        return 502
    return 200


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessException)
    async def business_exception_handler(_: Request, exc: BusinessException) -> JSONResponse:
        return _response(exc.code, exc.msg, exc.data, http_status=_http_status_for_code(exc.code))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _response(status_codes.BAD_REQUEST, "Invalid request parameters", exc.errors(), http_status=400)

    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(_: Request, exc: IntegrityError) -> JSONResponse:
        logger.exception("Database integrity error", exc_info=exc)
        return _response(status_codes.CONFLICT, "Data uniqueness or relationship constraint conflict", http_status=409)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 401:
            return _response(status_codes.UNAUTHORIZED, "Authentication failed", http_status=401)
        if exc.status_code == 403:
            return _response(status_codes.FORBIDDEN, "Forbidden", http_status=403)
        return _response(status_codes.BAD_REQUEST, str(exc.detail), http_status=exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled application error", exc_info=exc)
        return _response(status_codes.BAD_REQUEST, "System error", http_status=500)
