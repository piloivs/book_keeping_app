from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = Field(
        default_factory=lambda: f"sqlite:///{Path('data/warehouse/bookkeeping.sqlite3').as_posix()}"
    )
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    receipt_extraction_provider: str = "tesseract_ollama"
    tesseract_cmd: str = "tesseract"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_receipt_model: str = "qwen3:8b"
    openai_api_key: str | None = None
    receipt_extraction_model: str = "gpt-4.1-mini"


@lru_cache
def get_settings() -> Settings:
    return Settings()
