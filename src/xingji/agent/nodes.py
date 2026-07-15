"""Graph 节点函数 — 每个节点是一个异步函数，接收 state 返回部分 state 更新。"""

import logging
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from xingji.agent.prompts import (
    CLASSIFY_INTENT_PROMPT,
    GENERATE_PLAN_PROMPT,
    PARSE_REQUIREMENTS_PROMPT,
    REFINE_PLAN_PROMPT,
)
from xingji.agent.state import TravelPlanState
from xingji.config import settings
from xingji.exceptions import AgentException, ExternalServiceException
from xingji.schemas.travel import TravelPlan, TravelRequirements

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM 工厂
# ---------------------------------------------------------------------------

_llm: BaseChatModel | None = None


def _get_llm() -> BaseChatModel:
    """获取 LLM 实例（懒加载单例）。"""
    global _llm
    if _llm is None:
        if not settings.openai_api_key:
            raise AgentException(
                "OPENAI_API_KEY 环境变量未设置，无法创建 LLM 客户端"
            )
        if settings.llm_provider == "openai":
            _llm = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url or None,
                temperature=0.7,
            )
        else:
            raise AgentException(f"不支持的 LLM provider: {settings.llm_provider}")
    return _llm


# ---------------------------------------------------------------------------
# 结构化输出的辅助模型
# ---------------------------------------------------------------------------


class _ParseResult(BaseModel):
    """parse_requirements 节点的结构化输出。"""

    destination: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[str] = None
    travelers: Optional[int] = None
    preferences: Optional[str] = None
    requirements_complete: bool = False
    response: str = ""


# ---------------------------------------------------------------------------
# 节点函数
# ---------------------------------------------------------------------------


async def classify_intent(state: TravelPlanState) -> dict:
    """分类用户意图: new_plan 或 refine_plan。

    根据消息历史和 plan 是否存在来判断。
    """
    messages = state.get("messages", [])
    existing_plan = state.get("plan")

    # 简单启发式：如果已有 plan，大概率是 refine
    if existing_plan is not None:
        return {"intent": "refine_plan"}

    if not messages:
        return {"intent": "new_plan"}

    # 用 LLM 精确判断
    llm = _get_llm()
    try:
        result = await llm.ainvoke([
            SystemMessage(content=CLASSIFY_INTENT_PROMPT),
            HumanMessage(content=messages[-1].content),
        ])
        raw = result.content.strip().lower() if hasattr(result, "content") else str(result).strip().lower()
        intent = "refine_plan" if "refine" in raw else "new_plan"
        logger.debug("Intent classified: %s", intent)
    except Exception as e:
        logger.warning("LLM classify failed, defaulting to new_plan: %s", e)
        intent = "new_plan"

    return {"intent": intent}


async def parse_requirements(state: TravelPlanState) -> dict:
    """从用户消息中提取结构化 TravelRequirements。

    如果关键信息缺失，生成友好的追问。
    """
    messages = state.get("messages", [])
    if not messages:
        return {"requirements_complete": False, "response": "请告诉我你的旅行需求。"}

    llm = _get_llm()
    structured_llm = llm.with_structured_output(_ParseResult)

    try:
        parse_result: _ParseResult = await structured_llm.ainvoke([
            SystemMessage(content=PARSE_REQUIREMENTS_PROMPT),
            HumanMessage(content=messages[-1].content),
        ])
    except Exception as e:
        logger.exception("LLM structured output failed in parse_requirements")
        raise ExternalServiceException(f"需求解析失败: {e}") from e

    # 构建 TravelRequirements
    requirements = TravelRequirements(
        destination=parse_result.destination,
        budget=parse_result.budget,
        travelers=parse_result.travelers,
        preferences=parse_result.preferences,
    )

    return {
        "requirements": requirements,
        "requirements_complete": parse_result.requirements_complete,
        "response": parse_result.response,
    }


async def generate_plan(state: TravelPlanState) -> dict:
    """根据 TravelRequirements 生成逐日旅行方案。"""
    requirements = state.get("requirements")
    if requirements is None:
        return {"response": "无法生成方案：缺少旅行需求信息。", "plan": None}

    llm = _get_llm()
    structured_llm = llm.with_structured_output(TravelPlan)

    # 构建 prompt，把结构化需求注入
    req_text = (
        f"目的地: {requirements.destination or '待定'}\n"
        f"出行日期: {requirements.start_date or '待定'} 至 {requirements.end_date or '待定'}\n"
        f"预算级别: {requirements.budget.value if requirements.budget else '待定'}\n"
        f"出行人数: {requirements.travelers or '待定'}\n"
        f"偏好: {requirements.preferences or '无特殊偏好'}\n"
    )

    try:
        plan: TravelPlan = await structured_llm.ainvoke([
            SystemMessage(content=GENERATE_PLAN_PROMPT),
            HumanMessage(content=f"请根据以下需求生成旅行方案：\n\n{req_text}"),
        ])
    except Exception as e:
        logger.exception("LLM structured output failed in generate_plan")
        raise ExternalServiceException(f"方案生成失败: {e}") from e

    from datetime import datetime
    plan.generated_at = datetime.now()
    response_text = _format_plan_as_text(plan)

    return {"plan": plan, "response": response_text}


async def refine_plan(state: TravelPlanState) -> dict:
    """根据用户反馈修改旅行需求。"""
    messages = state.get("messages", [])
    requirements = state.get("requirements")

    if not messages:
        return {"requirements_complete": True}

    user_feedback = messages[-1].content
    current_req = requirements.model_dump_json(indent=2) if requirements else "{}"

    llm = _get_llm()
    structured_llm = llm.with_structured_output(TravelRequirements)

    refine_prompt = REFINE_PLAN_PROMPT.format(
        current_requirements=current_req,
        user_feedback=user_feedback,
    )

    try:
        updated: TravelRequirements = await structured_llm.ainvoke([
            SystemMessage(content=refine_prompt),
            HumanMessage(content=f"请更新需求: {user_feedback}"),
        ])
    except Exception as e:
        logger.exception("LLM structured output failed in refine_plan")
        raise ExternalServiceException(f"方案修改失败: {e}") from e

    return {"requirements": updated, "requirements_complete": True, "response": ""}


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _format_plan_as_text(plan: TravelPlan) -> str:
    """将结构化 TravelPlan 格式化为可读文本。"""
    lines = [
        f"## {plan.destination} 旅行方案",
        f"",
        f"- **日期**: {plan.start_date} 至 {plan.end_date}",
        f"- **预算**: {plan.budget.value}",
        f"- **人数**: {plan.travelers}人",
        f"",
        f"### 行程概览",
        f"{plan.summary}",
        f"",
    ]

    for day in plan.days:
        lines.append(f"### 第{day.day}天" + (f"（{day.day_date}）" if day.day_date else ""))
        if day.morning:
            lines.append(f"- ☀️ 上午: {day.morning}")
        if day.afternoon:
            lines.append(f"- 🌤️ 下午: {day.afternoon}")
        if day.evening:
            lines.append(f"- 🌙 晚间: {day.evening}")
        if day.meals:
            lines.append(f"- 🍽️ 餐饮: {' / '.join(day.meals)}")
        if day.estimated_cost:
            lines.append(f"- 💰 预估花费: {day.estimated_cost}")
        if day.notes:
            lines.append(f"- 📝 {day.notes}")
        lines.append("")

    if plan.total_estimated_cost:
        lines.append(f"### 总预估花费: {plan.total_estimated_cost}")

    return "\n".join(lines)
