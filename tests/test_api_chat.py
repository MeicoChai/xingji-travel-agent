"""测试 POST /api/v1/chat 接口。"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from xingji.agent.core import TravelAgent
from xingji.schemas.travel import BudgetLevel, TravelPlan


def _create_mock_agent() -> TravelAgent:
    """创建 mock 的 TravelAgent 用于测试。"""
    mock_graph = MagicMock()
    mock_conn = MagicMock()
    mock_checkpointer = MagicMock()
    return TravelAgent(graph=mock_graph, db_conn=mock_conn, checkpointer=mock_checkpointer)


@pytest.fixture
def client() -> TestClient:
    """创建 TestClient，依赖覆盖为 mock TravelAgent。"""
    from xingji.main import app

    agent = _create_mock_agent()
    agent._graph.ainvoke = AsyncMock(
        return_value={
            "response": "这是您的东京旅行方案",
            "plan": TravelPlan(
                destination="Tokyo",
                start_date="2026-08-01",
                end_date="2026-08-03",
                budget=BudgetLevel.MODERATE,
                travelers=1,
                summary="三日游",
            ),
            "requirements": None,
        }
    )
    app.state.agent = agent
    return TestClient(app)


class TestHealthEndpoint:
    """健康检查接口。"""

    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestChatEndpoint:
    """POST /api/v1/chat 接口测试。"""

    def test_chat_valid_request(self, client: TestClient) -> None:
        body = {
            "user_id": "user1",
            "session_id": "session1",
            "message": "帮我规划一个3天的东京旅行",
        }
        response = client.post("/api/v1/chat", json=body)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "ok"
        assert data["data"]["response"] != ""
        assert data["data"]["plan"] is not None
        assert data["data"]["session_id"] == "session1"

    def test_chat_missing_required_fields(self, client: TestClient) -> None:
        response = client.post("/api/v1/chat", json={})
        assert response.status_code == 422

    def test_chat_empty_message(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/chat",
            json={"user_id": "u1", "session_id": "s1", "message": ""},
        )
        assert response.status_code == 422

    def test_chat_message_too_long(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/chat",
            json={"user_id": "u1", "session_id": "s1", "message": "x" * 4001},
        )
        assert response.status_code == 422


class TestExceptionHandler:
    """测试全局异常处理器。"""

    def test_business_exception_handled(self) -> None:
        """验证业务异常被正确转换为统一响应格式。"""
        from xingji.main import app
        from xingji.exceptions import ValidationException

        agent = _create_mock_agent()
        agent._graph.ainvoke = AsyncMock(
            side_effect=ValidationException("目的地不能为空")
        )
        app.state.agent = agent

        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"user_id": "u1", "session_id": "s1", "message": "测试"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 40000
        assert "目的地" in data["message"]
