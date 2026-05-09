from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TrainUp API"
    api_prefix: str = "/api"
    database_url: str = "postgresql://trainup_user:trainup_password@db:5432/trainup_db"
    secret_key: str = "change_this"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_timeout_seconds: float = 10.0
    llm_max_tokens: int = 500
    llm_temperature: float = 0.2
    llm_enable_enhancement: bool = False
    fuzzy_interpretation_enabled: bool = True
    it2_fuzzy_enabled: bool = True
    pose_target_fps: float = 12.0
    pose_max_width: int = 720
    pose_cache_enabled: bool = True
    backend_cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
