"""Application configuration.

Everything is environment-driven. The development defaults make the app runnable
without external services; production deployments must set real secrets and a
PostgreSQL URL.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "POLIS API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    secret_key: str = "polis-development-only-secret-change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7
    cookie_name: str = "polis_session"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    database_url: str = f"sqlite:///{BACKEND_DIR / 'polis.db'}"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    demo_seed: bool = True
    demo_email: str = "demo@polis.health"
    demo_password: str = "PolisDemo!2026"
    demo_name: str = "Avery Chen"

    # AI: deterministic grounded synthesis is the default and always available.
    # An OpenAI-compatible endpoint can be enabled for richer prose. The system
    # falls back to deterministic synthesis on any provider failure.
    llm_provider: str = "deterministic"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"
    llm_timeout_seconds: float = 30.0
    llm_max_context_chars: int = 12000

    redis_url: str = ""
    allow_registration: bool = True
    login_rate_limit_per_minute: int = 12
    assistant_rate_limit_per_minute: int = 30

    # Federated demonstration guard rails.
    federated_dp_epsilon_per_round: float = 0.35
    federated_privacy_budget: float = 8.0

    model_config = SettingsConfigDict(
        env_file=(PROJECT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
