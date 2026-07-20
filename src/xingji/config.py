"""应用配置 — 所有环境变量统一管理。"""

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    """自动加载项目根目录的 .env 文件（轻量实现，无外部依赖）。"""
    env_file = Path(__file__).parent.parent.parent / ".env"
    if not env_file.exists():
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()


@dataclass
class Settings:
    """应用配置，所有敏感值从环境变量读取。"""

    # --- LLM ---
    llm_provider: str = os.getenv("XINGJI_LLM_PROVIDER", "openai")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("XINGJI_OPENAI_MODEL", "gpt-4o-mini")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")
    llm_temperature: float = float(os.getenv("XINGJI_LLM_TEMPERATURE", "0.7"))

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
