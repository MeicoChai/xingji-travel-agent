"""Graph 节点函数 — 每个节点是一个异步函数，接收 state 返回部分 state 更新。"""

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from xingji.agent.prompts import (
    CLASSIFY_INTENT_PROMPT,
    GENERATE_PLAN_PROMPT,
    PARSE_REQUIREMENTS_PROMPT,
    REFINE_PLAN_PROMPT,
)
from xingji.agent.state import TravelPlanState
from xingji.config import settings
from xingji.exceptions import AgentException, ExternalServiceException
from xingji.schemas.travel import BudgetLevel, TravelRequirements

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
                temperature=settings.llm_temperature,
            )
        else:
            raise AgentException(f"不支持的 LLM provider: {settings.llm_provider}")
    return _llm


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _safe_enum(value: str | None, enum_cls: type) -> str | None:
    """安全转换字符串为枚举值，非法值返回 None。"""
    if not value:
        return None
    try:
        enum_cls(value)
        return value
    except ValueError:
        return None


def _extract_json(text: str) -> dict:
    """从 LLM 文本响应中提取 JSON，处理 markdown 代码块包裹。"""
    # 移除 markdown 代码块标记
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text)


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

    try:
        result = await llm.ainvoke([
            SystemMessage(content=PARSE_REQUIREMENTS_PROMPT),
            HumanMessage(content=messages[-1].content),
        ])
        raw_text = result.content if hasattr(result, "content") else str(result)
        data = _extract_json(raw_text)
    except json.JSONDecodeError as e:
        logger.warning("JSON parse failed in parse_requirements: %s", e)
        # JSON 解析失败时降级：直接追问用户
        return {
            "requirements": TravelRequirements(),
            "requirements_complete": False,
            "response": "抱歉，我没能完全理解你的需求。能再详细说说想去哪里、什么时候出发吗？",
        }
    except Exception as e:
        logger.exception("LLM call failed in parse_requirements")
        raise ExternalServiceException(f"需求解析失败: {e}") from e

    # 安全提取字段
    budget = _safe_enum(data.get("budget"), BudgetLevel)
    travelers = data.get("travelers")
    if travelers is not None and (not isinstance(travelers, int) or travelers < 1):
        travelers = None

    try:
        requirements = TravelRequirements(
            destination=data.get("destination") or None,
            budget=budget,
            travelers=travelers,
            preferences=data.get("preferences") or None,
        )
    except Exception as e:
        logger.warning("Failed to construct TravelRequirements: %s", e)
        requirements = TravelRequirements()

    return {
        "requirements": requirements,
        "requirements_complete": data.get("requirements_complete", False),
        "response": data.get("response", ""),
    }


async def generate_plan(state: TravelPlanState) -> dict:
    """根据 TravelRequirements 生成逐日旅行方案（纯文本 Markdown 输出）。"""
    requirements = state.get("requirements")
    if requirements is None:
        return {"response": "无法生成方案：缺少旅行需求信息。", "plan": None}

    llm = _get_llm()

    req_text = (
        f"目的地: {requirements.destination or '待定'}\n"
        f"出行日期: {requirements.start_date or '待定'} 至 {requirements.end_date or '待定'}\n"
        f"预算级别: {requirements.budget.value if requirements.budget else '待定'}\n"
        f"出行人数: {requirements.travelers or '待定'}\n"
        f"偏好: {requirements.preferences or '无特殊偏好'}\n"
    )

    try:
        result = await llm.ainvoke([
            SystemMessage(content=GENERATE_PLAN_PROMPT),
            HumanMessage(content=f"请根据以下需求生成旅行方案：\n\n{req_text}"),
        ])
        response_text = result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        logger.exception("LLM call failed in generate_plan")
        raise ExternalServiceException(f"方案生成失败: {e}") from e

    return {"plan": None, "response": response_text}


async def refine_plan(state: TravelPlanState) -> dict:
    """根据用户反馈修改旅行需求，然后重新生成方案。"""
    messages = state.get("messages", [])
    requirements = state.get("requirements")

    if not messages:
        return {"requirements_complete": True}

    user_feedback = messages[-1].content
    current_req = requirements.model_dump_json(indent=2) if requirements else "{}"

    llm = _get_llm()
    refine_prompt = REFINE_PLAN_PROMPT.format(
        current_requirements=current_req,
        user_feedback=user_feedback,
    )

    try:
        result = await llm.ainvoke([
            SystemMessage(content=refine_prompt),
            HumanMessage(content=f"请更新需求: {user_feedback}"),
        ])
        response_text = result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        logger.exception("LLM call failed in refine_plan")
        raise ExternalServiceException(f"方案修改失败: {e}") from e

    return {"requirements_complete": True, "response": response_text}


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
