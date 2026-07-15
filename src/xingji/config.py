"""应用配置 — 所有环境变量统一管理。"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """应用配置，所有敏感值从环境变量读取。"""

    # --- LLM ---
    llm_provider: str = os.getenv("XINGJI_LLM_PROVIDER", "openai")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("XINGJI_OPENAI_MODEL", "gpt-4o-mini")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")

    # --- Checkpoint 持久化 ---
    checkpoint_db_path: str = os.getenv(
        "XINGJI_CHECKPOINT_DB", "data/checkpoints.db"
    )

    # --- 服务 ---
    host: str = os.getenv("XINGJI_HOST", "127.0.0.1")
    port: int = int(os.getenv("XINGJI_PORT", "8000"))

    # --- 日志 ---
    log_level: str = os.getenv("XINGJI_LOG_LEVEL", "INFO")


settings = Settings()
