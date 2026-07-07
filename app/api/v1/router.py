from fastapi import APIRouter

from app.api.v1.endpoints import (
    a5_integration,
    approvals,
    auth,
    completions,
    contractors,
    dictionaries,
    materials,
    reports,
    rbac,
    workover_operations,
    workover_project_pools,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dictionaries.router)
api_router.include_router(rbac.router)
api_router.include_router(approvals.router)
api_router.include_router(workover_project_pools.router)
api_router.include_router(workover_operations.router)
api_router.include_router(contractors.router)
api_router.include_router(a5_integration.router)
api_router.include_router(materials.router)
api_router.include_router(completions.router)
api_router.include_router(reports.router)
