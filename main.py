from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import AuthMiddleware, OperationLogMiddleware
from app.schemas.response import ApiResponse, success


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    register_exception_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(OperationLogMiddleware)
    app.add_middleware(AuthMiddleware)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    @app.get("/health", response_model=ApiResponse[dict[str, str]])
    def health() -> ApiResponse[dict[str, str]]:
        return success({"status": "ok", "service": settings.app_name})

    return app


app = create_app()
