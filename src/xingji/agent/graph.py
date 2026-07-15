"""Graph 构建 — 定义 StateGraph 节点、边、条件路由。"""

from langgraph.graph import END, START, StateGraph

from xingji.agent.nodes import (
    classify_intent,
    generate_plan,
    parse_requirements,
    refine_plan,
)
from xingji.agent.state import TravelPlanState


def route_after_classify(state: TravelPlanState) -> str:
    """分类后的路由: new_plan → parse, refine_plan → refine。"""
    intent = state.get("intent", "new_plan")
    if intent == "refine_plan":
        return "refine_plan"
    return "parse_requirements"


def route_after_parse(state: TravelPlanState) -> str:
    """需求解析后的路由: 信息完整 → 生成方案, 不完整 → 结束（返回追问）。"""
    if state.get("requirements_complete", False):
        return "generate_plan"
    return END


def build_travel_graph() -> StateGraph:
    """构建旅行规划 StateGraph（未编译）。

    Returns:
        未编译的 StateGraph，调用者通过 .compile(checkpointer=...) 编译。
    """
    builder = StateGraph(TravelPlanState)

    # 注册节点
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("parse_requirements", parse_requirements)
    builder.add_node("generate_plan", generate_plan)
    builder.add_node("refine_plan", refine_plan)

    # 入口
    builder.add_edge(START, "classify_intent")

    # classify → parse 或 refine
    builder.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {
            "parse_requirements": "parse_requirements",
            "refine_plan": "refine_plan",
        },
    )

    # parse → generate 或 END（追问）
    builder.add_conditional_edges(
        "parse_requirements",
        route_after_parse,
        {
            "generate_plan": "generate_plan",
            END: END,
        },
    )

    # refine → generate（总是转发到生成节点）
    builder.add_edge("refine_plan", "generate_plan")

    # generate → END
    builder.add_edge("generate_plan", END)

    return builder
