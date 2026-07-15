"""Agent 状态定义 — TravelPlanState TypedDict。"""

from typing import TypedDict

from langchain_core.messages import BaseMessage

from xingji.schemas.travel import TravelPlan, TravelRequirements


class TravelPlanState(TypedDict, total=False):
    """旅行规划 Agent 的状态。

    使用 total=False 表示所有字段可选，节点函数只更新它们关心的字段，
    LangGraph 自动将部分返回合并到完整 state 中。
    """

    # 对话历史 (LangChain BaseMessage 列表)
    messages: list[BaseMessage]

    # 从用户消息中提取的结构化需求
    requirements: TravelRequirements | None

    # 生成的旅行方案
    plan: TravelPlan | None

    # 返回给用户的文本响应
    response: str

    # 需求信息是否足够完整（决定是否需要追问）
    requirements_complete: bool

    # 用户意图分类: "new_plan" 或 "refine_plan"
    intent: str
