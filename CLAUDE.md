# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

xingji-travel-agent 是一个个人旅行规划 agent 助手，基于 Python + FastAPI + Uvicorn 构建。

## 技术栈

| 领域 | 选型 |
|------|------|
| 语言 | Python >= 3.10 |
| 包管理 | uv + pyproject.toml |
| Web 框架 | FastAPI |
| 服务进程 | Uvicorn（开发环境 hot-reload） |

## 常用命令

```bash
# 安装依赖
uv sync

# 添加新依赖
uv add <package>

# 启动开发服务器（hot-reload）
uv run uvicorn xingji.main:app --host 127.0.0.1 --port 8000 --reload

# 或通过入口脚本启动
uv run xingji

# 运行测试（待添加测试框架后补充）
uv run pytest
```

## 目录结构

```
src/xingji/
├── __init__.py
├── main.py          # FastAPI 应用实例 + uvicorn 启动入口
├── api/
│   ├── __init__.py
│   └── router.py    # API 路由（REST 接口）
└── agent/
    ├── __init__.py
    └── core.py      # Agent 核心逻辑（TravelAgent 类）
tests/               # 测试用例
```

## 架构要点

- **FastAPI 应用** 在 `main.py` 中创建，使用 `lifespan` 管理 agent 实例的生命周期
- **API 路由** 统一挂载在 `/api/v1` 前缀下，由 `api/router.py` 定义
- **Agent 核心** 封装在 `TravelAgent` 类中，负责接收旅行需求并生成规划方案
- **开发模式** 通过 `uv run uvicorn` 启动，默认开启 `--reload` 热加载
