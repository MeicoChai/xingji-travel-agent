"""xingji-travel-agent 主入口 — FastAPI 应用与 uvicorn 启动。"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from xingji.api.router import api_router
from xingji.config import settings
from xingji.exceptions import XingjiException

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化 agent，关闭时清理资源。"""
    logger.info("Initializing TravelAgent...")
    from xingji.agent.core import TravelAgent

    agent = await TravelAgent.create()
    app.state.agent = agent
    logger.info("TravelAgent initialized")
    yield
    logger.info("Shutting down TravelAgent...")
    await agent.close()
    logger.info("TravelAgent closed")


app = FastAPI(
    title="xingji-travel-agent",
    description="个人旅行规划 agent 助手",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.exception_handler(XingjiException)
async def xingji_exception_handler(request: Request, exc: XingjiException) -> JSONResponse:
    """全局业务异常处理器，转换为统一响应格式。"""
    logger.error("Business exception: %s (code=%d)", exc.message, exc.error_code)
    return JSONResponse(
        status_code=exc.http_status_code,
        content={"code": exc.error_code, "message": exc.message, "data": None},
    )


def main() -> None:
    """开发环境启动入口。"""
    uvicorn.run(
        "xingji.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
