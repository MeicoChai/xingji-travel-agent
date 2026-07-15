"""pytest 全局 fixtures。"""

import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def clean_env() -> None:
    """每个测试前清理相关环境变量，避免互相影响。"""
    keys = ["OPENAI_API_KEY", "XINGJI_LLM_PROVIDER", "XINGJI_OPENAI_MODEL"]
    originals = {k: os.environ.get(k) for k in keys}
    for k in keys:
        os.environ.pop(k, None)
    yield
    for k, v in originals.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)


@pytest.fixture
def mock_llm() -> MagicMock:
    """返回一个 mock 的 ChatModel，可用于测试节点函数。"""
    llm = MagicMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def mock_agent() -> MagicMock:
    """返回一个 mock 的 TravelAgent，用于 API 层测试。"""
    agent = MagicMock()
    agent.chat = AsyncMock()
    agent.close = AsyncMock()
    return agent


@pytest.fixture
def test_client(mock_agent: MagicMock) -> TestClient:
    """创建带 mock agent 的 TestClient。"""
    from xingji.main import app

    app.state.agent = mock_agent
    return TestClient(app)
