from fastapi import APIRouter

from app.api.v1.endpoints import (
    a5_integration,
    auth,
    contractors,
    dictionaries,
    engineering,
    rbac,
    workover_project_pools,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dictionaries.router)
api_router.include_router(rbac.router)
api_router.include_router(workover_project_pools.router)
api_router.include_router(contractors.router)
api_router.include_router(a5_integration.router)
api_router.include_router(engineering.router)
