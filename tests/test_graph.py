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
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="new_plan"))

        # 模拟 parse_requirements 的 structured output
        mock_parse_result = MagicMock()
        mock_parse_result.destination = "Tokyo"
        mock_parse_result.budget = "moderate"
        mock_parse_result.travelers = 2
        mock_parse_result.preferences = "喜欢美食"
        mock_parse_result.requirements_complete = True
        mock_parse_result.response = ""

        # 模拟 generate_plan 的 structured output
        mock_plan = TravelPlan(
            destination="Tokyo",
            start_date="2026-08-01",
            end_date="2026-08-03",
            budget=BudgetLevel.MODERATE,
            travelers=2,
            summary="东京三日美食之旅",
            days=[
                ItineraryDay(
                    day=1,
                    morning="浅草寺",
                    afternoon="秋叶原",
                    evening="银座",
                    meals=["一兰拉面"],
                ),
            ],
        )

        graph = build_travel_graph()

        with patch("xingji.agent.nodes._get_llm", return_value=mock_llm):
            mock_structured = MagicMock()
            mock_structured.ainvoke = AsyncMock(
                side_effect=[mock_parse_result, mock_plan]
            )
            mock_llm.with_structured_output.return_value = mock_structured

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
        assert result["plan"] is not None
        assert result["response"] != ""

    @pytest.mark.asyncio
    async def test_graph_parse_incomplete_triggers_clarify(self) -> None:
        """当信息不完整时，graph 应该在 parse 后直接结束（返回追问）。"""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="new_plan"))

        mock_parse_result = MagicMock()
        mock_parse_result.destination = None
        mock_parse_result.budget = None
        mock_parse_result.travelers = None
        mock_parse_result.preferences = None
        mock_parse_result.requirements_complete = False
        mock_parse_result.response = "请问你想去哪里？什么时候出发？"

        graph = build_travel_graph()

        with patch("xingji.agent.nodes._get_llm", return_value=mock_llm):
            mock_structured = MagicMock()
            mock_structured.ainvoke = AsyncMock(return_value=mock_parse_result)
            mock_llm.with_structured_output.return_value = mock_structured

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
