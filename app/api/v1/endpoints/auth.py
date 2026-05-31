from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.rbac import User
from app.schemas.auth import CurrentUserOut, LoginRequest, TokenResponse
from app.schemas.response import ApiResponse, success
from app.services.auth_service import authenticate_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=ApiResponse[TokenResponse])
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> ApiResponse[TokenResponse]:
    user = authenticate_user(db, payload.username, payload.password)
    token = create_access_token(str(user.id))
    return success(TokenResponse(access_token=token), msg="登录成功")


@router.get("/me", response_model=ApiResponse[CurrentUserOut])
def current_user(user: User = Depends(get_current_user)) -> ApiResponse[CurrentUserOut]:
    return success(CurrentUserOut.model_validate(user))
