"""إعدادات الـBackend من متغيرات البيئة — لا مفاتيح في الكود ولا في الواجهة."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/masadir.db"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    backend_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    api_rate_limit_per_minute: int = 30
    api_max_question_chars: int = 2000
    rag_top_k: int = 6
    rag_max_context_chars: int = 60_000
    rag_max_chunk_chars: int = 3_000

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


def get_settings() -> Settings:
    return Settings()
