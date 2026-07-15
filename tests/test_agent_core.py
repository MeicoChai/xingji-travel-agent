"""测试 TravelAgent 编排器。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xingji.schemas.travel import BudgetLevel, TravelPlan, TravelRequirements


def _create_mock_agent():
    """创建 mock 的 TravelAgent。"""
    from xingji.agent.core import TravelAgent

    mock_graph = MagicMock()
    mock_conn = MagicMock()
    mock_checkpointer = MagicMock()
    return TravelAgent(graph=mock_graph, db_conn=mock_conn, checkpointer=mock_checkpointer)


class TestTravelAgentInit:
    """测试 TravelAgent 初始化。"""

    def test_init_stores_resources(self) -> None:
        agent = _create_mock_agent()
        assert agent._graph is not None
        assert agent._checkpointer is not None
        assert agent._db_conn is not None

    @pytest.mark.asyncio
    async def test_close_cleans_up(self) -> None:
        agent = _create_mock_agent()
        agent._db_conn.close = AsyncMock()
        await agent.close()
        agent._db_conn.close.assert_called_once()


class TestTravelAgentChat:
    """测试 chat() 方法。"""

    @pytest.mark.asyncio
    async def test_chat_returns_response_and_plan(self) -> None:
        """模拟 graph 返回完整结果。"""
        agent = _create_mock_agent()

        mock_plan = TravelPlan(
            destination="Tokyo",
            start_date="2026-08-01",
            end_date="2026-08-03",
            budget=BudgetLevel.MODERATE,
            travelers=1,
            summary="东京三天游",
            days=[],
        )

        agent._graph.ainvoke = AsyncMock(
            return_value={
                "response": "这是您的旅行方案",
                "plan": mock_plan,
                "requirements": TravelRequirements(destination="Tokyo"),
            }
        )

        result = await agent.chat("user1", "session1", "帮我规划东京旅行")

        assert result["response"] == "这是您的旅行方案"
        assert result["plan"] is not None
        assert result["plan"].destination == "Tokyo"

    @pytest.mark.asyncio
    async def test_chat_passes_correct_thread_id(self) -> None:
        """验证 thread_id 格式正确（user_id:session_id）。"""
        agent = _create_mock_agent()
        agent._graph.ainvoke = AsyncMock(
            return_value={"response": "ok", "plan": None, "requirements": None}
        )

        await agent.chat("user_abc", "session_xyz", "hello")

        call_args = agent._graph.ainvoke.call_args
        # ainvoke(state, config) — config 是第二个位置参数
        config = call_args[0][1]
        assert config["configurable"]["thread_id"] == "user_abc:session_xyz"
