"""xingji-travel-agent 主入口 — FastAPI 应用与 uvicorn 启动。"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from xingji.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化 agent，关闭时清理资源。"""
    # TODO: 初始化 agent 实例
    yield
    # TODO: 清理 agent 资源


app = FastAPI(
    title="xingji-travel-agent",
    description="个人旅行规划 agent 助手",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router)


def main() -> None:
    """开发环境启动入口。"""
    uvicorn.run(
        "xingji.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
