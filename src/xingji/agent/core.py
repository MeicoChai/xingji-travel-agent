"""Agent 核心逻辑 — TravelAgent 编排器。

将编译好的 LangGraph 封装为面向 API 层的统一接口。
"""

import logging
from pathlib import Path

import aiosqlite
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from xingji.agent.graph import build_travel_graph
from xingji.agent.state import TravelPlanState
from xingji.config import settings

logger = logging.getLogger(__name__)


class TravelAgent:
    """旅行规划 Agent。

    封装 LangGraph 编译后的图，提供 chat() 作为唯一的公开接口。
    API 层无需感知 LangGraph 内部细节。

    通过 TravelAgent.create() 异步工厂方法创建实例。
    """

    def __init__(
        self,
        graph: CompiledStateGraph,
        db_conn: aiosqlite.Connection,
        checkpointer: AsyncSqliteSaver,
    ) -> None:
        self._graph = graph
        self._db_conn = db_conn
        self._checkpointer = checkpointer

    @classmethod
    async def create(cls) -> "TravelAgent":
        """异步工厂方法：初始化数据库和 checkpointer，编译 graph。

        在 FastAPI lifespan 中调用。
        """
        db_path = settings.checkpoint_db_path

        # 确保 checkpoint 文件的父目录存在
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Initializing SQLite checkpoint at: %s", db_path)

        db_conn = await aiosqlite.connect(db_path)
        checkpointer = AsyncSqliteSaver(db_conn)
        await checkpointer.setup()

        graph: CompiledStateGraph = build_travel_graph().compile(
            checkpointer=checkpointer
        )

        logger.info("TravelAgent created (model=%s)", settings.openai_model)
        return cls(graph=graph, db_conn=db_conn, checkpointer=checkpointer)

    async def chat(
        self, user_id: str, session_id: str, message: str
    ) -> dict:
        """处理用户消息，返回 agent 响应。

        Args:
            user_id: 用户标识（用于隔离不同用户的会话）。
            session_id: 会话标识（同一会话的多轮对话共享状态）。
            message: 用户消息文本。

        Returns:
            dict: {"response": str, "plan": TravelPlan | None,
                   "requirements": TravelRequirements | None}
        """
        thread_id = f"{user_id}:{session_id}"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state: TravelPlanState = {
            "messages": [HumanMessage(content=message)],
            "requirements": None,
            "plan": None,
            "response": "",
            "requirements_complete": False,
            "intent": "",
        }

        logger.debug("Invoking graph for thread=%s", thread_id)
        result = await self._graph.ainvoke(initial_state, config)

        return {
            "response": result.get("response", ""),
            "plan": result.get("plan"),
            "requirements": result.get("requirements"),
        }

    async def close(self) -> None:
        """清理资源（关闭数据库连接）。"""
        if self._db_conn:
            await self._db_conn.close()
            logger.info("SQLite connection closed")
        logger.info("TravelAgent closed")
