"""API 依赖注入 — 从 app.state 获取共享资源。"""

from fastapi import Request

from xingji.agent.core import TravelAgent


def get_agent(request: Request) -> TravelAgent:
    """从应用状态获取 TravelAgent 单例。"""
    return request.app.state.agent
