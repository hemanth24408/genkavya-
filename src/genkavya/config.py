"""Central environment-backed application configuration."""

from typing import Literal

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: Literal["ollama"] = "ollama"
    ollama_base_url: AnyUrl = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    request_timeout_seconds: float = Field(default=180.0, gt=0)
    generation_max_attempts_per_candidate: int = Field(default=3, gt=0)


def get_settings() -> Settings:
    """Return settings loaded from the environment and optional local .env."""
    return Settings()

