"""Application settings loaded from environment variables (.env supported)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path so the DB file is always backend/manvsmachine.db regardless of cwd.
_DEFAULT_DB = Path(__file__).resolve().parents[2] / "manvsmachine.db"


class Settings(BaseSettings):
    """Environment-driven configuration for the backend."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database (SQLite file; connection is wired up in Sprint 2)
    database_url: str = f"sqlite+aiosqlite:///{_DEFAULT_DB.as_posix()}"

    # AI providers (fallback chain: OpenAI -> Anthropic -> Ollama -> Stub)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ai_prompt_version: str = "v1.0"
    stub_provider_only: bool = False

    # Local LLM (Ollama). Optional per Scope Constraint 7: no key, no external call.
    # qwen3.5:9b won the Sprint 9 local bake-off; Ollama must send think=false for
    # qwen3-family models (they otherwise spend the token budget on hidden reasoning).
    ollama_enabled: bool = True
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3.5:9b"

    # Auth (JWT). Override jwt_secret_key via .env outside local development.
    # Default is >= 32 bytes (PyJWT/HS256 minimum) but must be overridden in any shared deployment.
    jwt_secret_key: str = "dev-insecure-secret-change-me-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 30  # 30 days: guests persist across restarts

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
