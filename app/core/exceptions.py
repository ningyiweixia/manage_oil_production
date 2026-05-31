from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core import status_codes
from app.schemas.response import ApiResponse


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


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessException)
    async def business_exception_handler(_: Request, exc: BusinessException) -> JSONResponse:
        return _response(exc.code, exc.msg, exc.data)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _response(status_codes.BAD_REQUEST, "参数错误", exc.errors())

    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(_: Request, __: IntegrityError) -> JSONResponse:
        return _response(status_codes.CONFLICT, "数据唯一性或关联约束冲突")

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 401:
            return _response(status_codes.UNAUTHORIZED, "身份失效")
        if exc.status_code == 403:
            return _response(status_codes.FORBIDDEN, "越权访问")
        return _response(status_codes.BAD_REQUEST, str(exc.detail))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, __: Exception) -> JSONResponse:
        return _response(status_codes.BAD_REQUEST, "系统异常")
