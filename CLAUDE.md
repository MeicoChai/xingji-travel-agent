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

---

## 开发规范（严格遵守）

### 1. 代码风格

- **Python 版本**：所有代码必须兼容 Python >= 3.10，使用现代语法（`X | None` 替代 `Optional[X]`，`list[X]` 替代 `List[X]`）
- **类型注解**：所有公共函数、方法必须有完整的类型注解（参数 + 返回值）。内部/私有方法如逻辑简单可省略，但建议标注
- **文档字符串**：所有模块、类、公共方法使用 Google 风格的 docstring（`"""简短描述。"""` 单行 或 `"""简短描述。\n\nArgs:\n    ...\nReturns:\n    ...\n"""` 多行）
- **代码格式化**：使用 ruff 作为 linter 和 formatter（后续集成），保持代码风格统一
- **import 顺序**：标准库 → 第三方库 → 项目内部模块，每组之间空一行
- **每行最大长度**：120 字符（docstring 除外，不超过 100 字符）
- **命名规范**：
  - 模块/文件：`snake_case`（如 `travel_agent.py`）
  - 类：`PascalCase`（如 `TravelAgent`）
  - 函数/方法/变量：`snake_case`（如 `generate_plan`）
  - 常量：`UPPER_SNAKE_CASE`（如 `MAX_RETRIES`）
  - 私有成员：前缀单下划线 `_private_method`

### 2. 项目架构约束

- **模块职责边界**：
  - `api/` — 只处理 HTTP 层：路由定义、请求参数校验、响应格式化。**不得包含业务逻辑**
  - `agent/` — 核心业务逻辑：LLM 交互、旅行规划算法、工具调用。**不得引用 FastAPI/HTTP 相关模块**
  - `main.py` — 仅负责应用创建、中间件注册、启动配置。**不得包含路由或业务逻辑**
- **依赖方向**：`api` → `agent`（api 可依赖 agent），禁止反向依赖（agent 不可 import api）
- **新增模块**：当 `agent/` 或 `api/` 下单个文件超过 300 行时，应拆分为子模块或独立文件
- **全局状态**：禁止使用模块级可变全局变量。需要共享状态时通过 FastAPI 的 `app.state` 或依赖注入传递
- **环境变量**：所有敏感配置（API Key、数据库连接串等）通过环境变量读取，不得硬编码。统一在 `xingji/config.py` 中管理配置项（后续创建）

### 3. API 设计规范

- **RESTful 风格**：URL 使用资源名词复数形式（如 `/api/v1/trips`），HTTP 方法语义正确（GET 查询、POST 创建、PUT 全量更新、PATCH 部分更新、DELETE 删除）
- **路由前缀**：所有 API 统一在 `/api/v1` 下，后续版本增加 `/api/v2`
- **请求/响应模型**：使用 Pydantic models 定义请求体和响应体，放在 `xingji/schemas/` 目录下，禁止在路由函数中直接操作裸 dict
- **响应格式**：统一返回结构：
  ```python
  # 成功
  {"code": 0, "message": "ok", "data": {...}}
  # 失败
  {"code": <error_code>, "message": "<error_message>", "data": null}
  ```
- **HTTP 状态码**：
  - 200: 成功
  - 201: 资源创建成功
  - 400: 请求参数错误
  - 404: 资源不存在
  - 422: 请求体验证失败（FastAPI 自动处理）
  - 500: 服务端内部错误
- **分页**：列表接口必须支持分页，使用 `page`（从 1 开始）和 `page_size`（默认 20，最大 100）参数

### 4. 错误处理

- **业务异常**：定义统一的异常类层次，放在 `xingji/exceptions.py`：
  - 基础异常 `XingjiException`（继承自 `Exception`）
  - 按场景细分（如 `AgentException`、`ValidationException`、`ExternalServiceException`）
- **FastAPI 异常处理器**：在 `main.py` 中注册全局 exception handler，捕获业务异常并转换为统一响应格式
- **不在代码中吞异常**：捕获异常时必须记录日志（`logger.exception(...)`)；除非有明确的降级策略，否则不得 `except: pass`
- **外部调用**：调用外部服务（LLM API、第三方 API）必须有超时设置和重试机制

### 5. 日志规范

- **日志库**：使用 Python 标准库 `logging`，通过 `logging.getLogger(__name__)` 获取 logger
- **日志级别**：
  - `DEBUG`：开发调试信息（仅本地开发环境启用）
  - `INFO`：关键业务流程节点（请求到达、agent 开始/完成规划、外部服务调用）
  - `WARNING`：可恢复的异常情况（重试成功、降级处理）
  - `ERROR`：需要关注的错误（外部调用失败、业务异常）
  - `CRITICAL`：导致服务不可用的致命错误
- **日志格式**：包含时间戳、日志级别、模块名、消息内容
- **敏感信息**：日志中**绝对不得**输出 API Key、用户密码、个人隐私数据（如电话号码、身份证号）

### 6. 测试规范

- **测试框架**：pytest
- **覆盖率**：核心业务逻辑（`agent/` 模块）测试覆盖率目标 ≥ 80%，API 路由 ≥ 60%
- **测试文件组织**：`tests/` 目录镜像 `src/xingji/` 的结构，测试文件命名 `test_<module>.py`
- **测试类型**：
  - 单元测试：测试单个函数/方法，外部依赖必须 mock
  - 集成测试：测试 API 路由和 agent 真实交互（LLM 调用除外，使用 mock）
- **每个 PR 必须包含相关测试**

### 7. Git 规范

- **分支策略**：`main` 分支保持稳定可部署。开发时从 `main` 创建 feature 分支，命名格式 `feat/<功能简述>` 或 `fix/<修复简述>`
- **Commit 信息**：使用约定式提交格式（Conventional Commits）：
  ```
  <type>(<scope>): <subject>
  
  [optional body]
  ```
  - type: `feat` | `fix` | `refactor` | `docs` | `test` | `chore`
  - scope: 变化的模块（如 `agent`、`api`、`config`）
  - subject: 中文简述，动词开头，不加句号
- **提交粒度**：每个 commit 应该是一个逻辑上独立的变更，避免把多个不相关的改动混在一个 commit
- **禁止提交**：不得提交 `.env` 文件、IDE 配置、`__pycache__/`、以及任何包含密钥/密码的文件

### 8. 异步编程规范

- **网络 IO**：所有网络请求（LLM API 调用、第三方 HTTP 请求）必须使用异步方式（`async/await` + `httpx` 异步客户端）
- **阻塞操作**：CPU 密集或同步阻塞操作应通过 `asyncio.to_thread()` 或 `run_in_executor()` 放入线程池，避免阻塞事件循环
- **FastAPI 路由**：路由处理函数使用 `async def`（除非确认不需要异步）
- **并发控制**：涉及多个独立外部调用的场景，使用 `asyncio.gather()` 并行执行，减少总耗时

### 9. 依赖管理

- **添加依赖前评估**：优先使用标准库，其次选择社区活跃、文档完善的三方库
- **版本约束**：`pyproject.toml` 中依赖版本使用兼容约束（如 `>=0.1.0,<1.0.0`），避免使用 `*` 或完全不设上限
- **锁定文件**：所有环境通过 uv.lock 锁定依赖版本，保证环境一致性

### 10. 安全规范

- **输入验证**：所有来自外部的输入（HTTP 请求参数、用户上传内容）必须校验和清洗
- **API Key 管理**：API Key 等敏感配置仅从环境变量读取，不得出现在代码、注释、日志中
- **依赖安全**：定期检查依赖漏洞（`uv sync --refresh` + `pip-audit` 或同类工具）
- **CORS**：生产环境必须限制允许的来源域名，不得使用 `allow_origins=["*"]`
- **速率限制**：对外暴露的 API 应考虑添加速率限制（后续通过中间件实现）
