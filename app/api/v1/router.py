from fastapi import APIRouter

from app.api.v1.endpoints import auth, dictionaries, rbac, workover_project_pools

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dictionaries.router)
api_router.include_router(rbac.router)
api_router.include_router(workover_project_pools.router)
