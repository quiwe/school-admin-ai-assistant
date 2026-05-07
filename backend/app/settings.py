from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


class AppSettings(BaseSettings):
    app_name: str = "高校行政 AI 回复助手"
    database_url: str = "sqlite:///./data/app.db"
    upload_dir: str = "./data/uploads"
    ai_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None
    local_model_base_url: str = "http://localhost:11434"
    local_model_name: str = "llama3.1"
    enable_ai_fallback: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()


settings = get_settings()
