"""测试 Pydantic 数据模型。"""

from datetime import date

import pytest
from pydantic import ValidationError

from xingji.schemas.chat import ChatRequest, ChatResponse
from xingji.schemas.common import ApiResponse
from xingji.schemas.travel import (
    BudgetLevel,
    ItineraryDay,
    TravelPlan,
    TravelRequirements,
)


class TestApiResponse:
    """统一响应模型测试。"""

    def test_success_response(self) -> None:
        resp = ApiResponse.success(data={"key": "value"})
        assert resp.code == 0
        assert resp.message == "ok"
        assert resp.data == {"key": "value"}

    def test_error_response(self) -> None:
        resp = ApiResponse.error(code=40000, message="Bad request")
        assert resp.code == 40000
        assert resp.data is None


class TestTravelRequirements:
    """TravelRequirements 模型测试。"""

    def test_empty_requirements(self) -> None:
        req = TravelRequirements()
        assert req.destination is None
        assert req.travelers is None

    def test_partial_requirements(self) -> None:
        req = TravelRequirements(destination="Tokyo", budget=BudgetLevel.MODERATE)
        assert req.destination == "Tokyo"
        assert req.budget == BudgetLevel.MODERATE
        assert req.start_date is None

    def test_travelers_validation(self) -> None:
        with pytest.raises(ValidationError):
            TravelRequirements(travelers=0)

    def test_full_requirements(self) -> None:
        req = TravelRequirements(
            destination="Paris",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 5),
            budget=BudgetLevel.LUXURY,
            travelers=2,
            preferences="喜欢博物馆和美食",
        )
        assert req.destination == "Paris"
        assert req.travelers == 2


class TestTravelPlan:
    """TravelPlan 模型测试。"""

    def test_minimal_plan(self) -> None:
        plan = TravelPlan(
            destination="Tokyo",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 3),
            budget=BudgetLevel.MODERATE,
            travelers=1,
        )
        assert plan.days == []
        assert plan.summary == ""

    def test_plan_with_days(self) -> None:
        day = ItineraryDay(
            day=1,
            day_date=date(2026, 8, 1),
            morning="参观浅草寺",
            afternoon="秋叶原购物",
            evening="银座晚餐",
            meals=["一兰拉面", "寿司大"],
        )
        plan = TravelPlan(
            destination="Tokyo",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 2),
            budget=BudgetLevel.BUDGET,
            travelers=1,
            summary="东京紧凑一日游",
            days=[day],
        )
        assert len(plan.days) == 1
        assert plan.days[0].morning == "参观浅草寺"


class TestChatModels:
    """聊天接口模型测试。"""

    def test_valid_chat_request(self) -> None:
        req = ChatRequest(
            user_id="user1",
            session_id="sess1",
            message="帮我规划一个3天的东京旅行",
        )
        assert req.user_id == "user1"

    def test_empty_message_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest(user_id="u1", session_id="s1", message="")

    def test_message_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest(user_id="u1", session_id="s1", message="x" * 4001)
