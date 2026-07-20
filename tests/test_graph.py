"""测试 Graph 构建和条件路由逻辑。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from xingji.agent.graph import build_travel_graph, route_after_classify, route_after_parse
from xingji.agent.state import TravelPlanState
from xingji.schemas.travel import BudgetLevel, ItineraryDay, TravelPlan


class TestConditionalRouting:
    """测试条件路由函数（不依赖 LLM）。"""

    def test_route_after_classify_new_plan(self) -> None:
        state: TravelPlanState = {"intent": "new_plan"}
        assert route_after_classify(state) == "parse_requirements"

    def test_route_after_classify_refine_plan(self) -> None:
        state: TravelPlanState = {"intent": "refine_plan"}
        assert route_after_classify(state) == "refine_plan"

    def test_route_after_parse_complete(self) -> None:
        state: TravelPlanState = {"requirements_complete": True}
        assert route_after_parse(state) == "generate_plan"

    def test_route_after_parse_incomplete(self) -> None:
        state: TravelPlanState = {"requirements_complete": False}
        assert route_after_parse(state) == "__end__"


class TestGraphCompilation:
    """测试 Graph 编译。"""

    def test_build_and_compile_graph(self) -> None:
        graph = build_travel_graph()
        compiled = graph.compile(checkpointer=MemorySaver())
        assert compiled is not None

    @pytest.mark.asyncio
    async def test_graph_with_mock_llm_new_plan(self) -> None:
        """模拟 LLM 调用的完整 new_plan 流程。"""
        import json

        mock_llm = MagicMock()
        # ainvoke 调用顺序: classify_intent → parse_requirements (JSON) → generate_plan (文本)
        mock_llm.ainvoke = AsyncMock(
            side_effect=[
                MagicMock(content="new_plan"),
                MagicMock(content=json.dumps({
                    "destination": "Tokyo",
                    "start_date": "2026-08-01",
                    "end_date": "2026-08-03",
                    "budget": "moderate",
                    "travelers": 2,
                    "preferences": "喜欢美食",
                    "requirements_complete": True,
                    "response": "",
                })),
                MagicMock(content="## Tokyo 旅行方案\n\n这是一份详细的旅行方案..."),
            ]
        )

        graph = build_travel_graph()

        with patch("xingji.agent.nodes._get_llm", return_value=mock_llm):
            compiled = graph.compile(checkpointer=MemorySaver())
            state: TravelPlanState = {
                "messages": [HumanMessage(content="帮我规划一个3天的东京旅行")],
                "requirements": None,
                "plan": None,
                "response": "",
                "requirements_complete": False,
                "intent": "",
            }
            config = {"configurable": {"thread_id": "test:session1"}}
            result = await compiled.ainvoke(state, config)

        assert result["intent"] in ("new_plan", "refine_plan")
        assert result["response"] != ""

    @pytest.mark.asyncio
    async def test_graph_parse_incomplete_triggers_clarify(self) -> None:
        """当信息不完整时，graph 应该在 parse 后直接结束（返回追问）。"""
        import json

        mock_llm = MagicMock()
        # classify_intent → parse_requirements (返回不完整 JSON)
        mock_llm.ainvoke = AsyncMock(
            side_effect=[
                MagicMock(content="new_plan"),
                MagicMock(content=json.dumps({
                    "destination": None,
                    "start_date": None,
                    "end_date": None,
                    "budget": None,
                    "travelers": None,
                    "preferences": None,
                    "requirements_complete": False,
                    "response": "请问你想去哪里？什么时候出发？",
                })),
            ]
        )

        graph = build_travel_graph()

        with patch("xingji.agent.nodes._get_llm", return_value=mock_llm):

            compiled = graph.compile(checkpointer=MemorySaver())
            state: TravelPlanState = {
                "messages": [HumanMessage(content="我想出去玩")],
                "requirements": None,
                "plan": None,
                "response": "",
                "requirements_complete": False,
                "intent": "",
            }
            config = {"configurable": {"thread_id": "test:session2"}}
            result = await compiled.ainvoke(state, config)

        # requirements 不完整，不应该生成 plan
        assert result["plan"] is None
        assert result["response"] != ""  # 追问文本不为空
