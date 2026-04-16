from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """
    Helix Runtime 配置管理
    """
    # 应用基本配置
    app_name: str = "Helix Runtime"
    debug: bool = True

    # 运行时约束
    max_recent_turns: int = 5
    max_history_turns: int = 5
    max_workflow_steps: int = 3
    max_prompt_tokens: int = 4096
    max_workflow_retry: int = 2

    # Redis 配置（可选）
    redis_url: Optional[str] = None

    # PostgreSQL 配置（可选）
    database_url: Optional[str] = None

    @property
    def config_file(self) -> Path:
        """配置文件路径"""
        return Path.home() / ".config" / "helix" / "config.json"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
