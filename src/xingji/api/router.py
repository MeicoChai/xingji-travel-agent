"""API 路由模块。"""

from fastapi import APIRouter, Depends

from xingji.api.deps import get_agent
from xingji.agent.core import TravelAgent
from xingji.schemas.chat import ChatRequest, ChatResponse
from xingji.schemas.common import ApiResponse

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health")
async def health_check() -> dict:
    """健康检查接口。"""
    return {"status": "ok"}


@api_router.post("/chat", response_model=ApiResponse[ChatResponse])
async def chat(
    body: ChatRequest,
    agent: TravelAgent = Depends(get_agent),
) -> ApiResponse[ChatResponse]:
    """旅行规划对话接口。

    单端点处理所有用户交互 — 新规划请求和方案修改请求。
    通过 session_id 关联多轮对话，相同 session_id 保留上下文。
    """
    result = await agent.chat(
        user_id=body.user_id,
        session_id=body.session_id,
        message=body.message,
    )
    return ApiResponse.success(
        data=ChatResponse(
            session_id=body.session_id,
            response=result["response"],
            plan=result.get("plan"),
        )
    )
