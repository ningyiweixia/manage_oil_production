from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.core.status_codes import UNAUTHORIZED


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_token(subject: str, token_type: str, expires_delta: timedelta) -> tuple[str, str]:
    jti = uuid4().hex
    expire = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {"sub": subject, "typ": token_type, "jti": jti, "exp": expire}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    token, _ = create_token(
        subject,
        "access",
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes),
    )
    return token


def decode_token_payload(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if not payload.get("sub"):
            raise BusinessException(UNAUTHORIZED, "身份失效")
        return payload
    except JWTError as exc:
        raise BusinessException(UNAUTHORIZED, "身份失效") from exc


def decode_access_token(token: str) -> str:
    payload = decode_token_payload(token)
    if payload.get("typ") != "access":
        raise BusinessException(UNAUTHORIZED, "身份失效")
    return str(payload["sub"])
