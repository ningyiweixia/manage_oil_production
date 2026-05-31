from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from app.core.status_codes import SUCCESS

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = SUCCESS
    msg: str = "success"
    data: T | None = None

    model_config = ConfigDict(from_attributes=True)


def success(data: T | None = None, msg: str = "success") -> ApiResponse[T]:
    return ApiResponse(code=SUCCESS, msg=msg, data=data)
