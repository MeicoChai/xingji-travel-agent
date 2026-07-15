"""旅行规划相关数据模型。"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BudgetLevel(str, Enum):
    """预算级别。"""

    BUDGET = "budget"
    MODERATE = "moderate"
    LUXURY = "luxury"


class TravelRequirements(BaseModel):
    """用户旅行需求的结构化表示。"""

    destination: Optional[str] = Field(None, description="目的地城市/地区")
    start_date: Optional[date] = Field(None, description="出发日期")
    end_date: Optional[date] = Field(None, description="返程日期")
    budget: Optional[BudgetLevel] = Field(None, description="预算级别")
    travelers: Optional[int] = Field(None, ge=1, description="出行人数")
    preferences: Optional[str] = Field(None, description="偏好描述（自由文本）")


class ItineraryDay(BaseModel):
    """单日行程。"""

    day: int = Field(..., ge=1, description="第几天")
    day_date: Optional[date] = Field(None, description="具体日期")
    morning: str = Field("", description="上午活动")
    afternoon: str = Field("", description="下午活动")
    evening: str = Field("", description="晚间活动")
    meals: list[str] = Field(default_factory=list, description="推荐餐饮")
    estimated_cost: Optional[str] = Field(None, description="当日预估花费")
    notes: Optional[str] = Field(None, description="备注/小贴士")


class TravelPlan(BaseModel):
    """旅行规划方案。"""

    destination: str = Field(..., description="目的地")
    start_date: date = Field(..., description="出发日期")
    end_date: date = Field(..., description="返程日期")
    budget: BudgetLevel = Field(..., description="预算级别")
    travelers: int = Field(..., ge=1, description="出行人数")
    summary: str = Field("", description="行程概览")
    days: list[ItineraryDay] = Field(default_factory=list, description="逐日行程")
    total_estimated_cost: Optional[str] = Field(None, description="总预估花费")
    generated_at: Optional[datetime] = Field(None, description="方案生成时间")
