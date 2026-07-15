"""聊天接口请求/响应模型。"""

from typing import Optional

from pydantic import BaseModel, Field

from xingji.schemas.travel import TravelPlan


class ChatRequest(BaseModel):
    """聊天请求体。"""

    user_id: str = Field(..., min_length=1, max_length=64, description="用户标识")
    session_id: str = Field(..., min_length=1, max_length=64, description="会话标识")
    message: str = Field(..., min_length=1, max_length=4000, description="用户消息")


class ChatResponse(BaseModel):
    """聊天响应数据。"""

    session_id: str = Field(..., description="会话标识")
    response: str = Field(..., description="Agent 回复文本")
    plan: Optional[TravelPlan] = Field(None, description="旅行方案（生成/更新后返回）")
