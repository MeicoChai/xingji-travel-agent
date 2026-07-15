"""统一 API 响应模型。"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应格式: {code, message, data}."""

    code: int = 0
    message: str = "ok"
    data: Optional[T] = None

    @classmethod
    def success(cls, data: T) -> "ApiResponse[T]":
        """构建成功响应。"""
        return cls(code=0, message="ok", data=data)

    @classmethod
    def error(cls, code: int, message: str) -> "ApiResponse[None]":
        """构建错误响应。"""
        return cls(code=code, message=message, data=None)
