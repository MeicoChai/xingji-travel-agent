"""API 路由模块。"""

from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health")
async def health_check():
    """健康检查接口。"""
    return {"status": "ok"}
