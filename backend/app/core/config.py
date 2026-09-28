"""Application settings loaded from environment variables (.env supported)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration for the backend."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database (SQLite file; connection is wired up in Sprint 2)
    database_url: str = "sqlite+aiosqlite:///./manvsmachine.db"

    # AI providers (fallback chain: OpenAI -> Anthropic -> Stub)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ai_prompt_version: str = "v1.0"
    stub_provider_only: bool = False

    # CORS (Vite dev server; 5174-5175 cover Vite's auto-increment when 5173 is occupied)
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ]


settings = Settings()
