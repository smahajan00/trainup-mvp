from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TrainUp API"
    api_prefix: str = "/api"
    database_url: str = "postgresql://trainup_user:trainup_password@db:5432/trainup_db"
    secret_key: str = "change_this"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.5-flash"
    gemini_api_key: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_timeout_seconds: float = 20.0
    llm_max_tokens: int = 220
    llm_temperature: float = 0.2
    llm_enabled: bool | None = None
    llm_enable_enhancement: bool = False
    llm_debug_response_shape: bool = False
    fuzzy_interpretation_enabled: bool = True
    it2_fuzzy_enabled: bool = True
    pose_target_fps: float = 20.0
    pose_max_width: int = 720
    pose_cache_enabled: bool = True
    tts_model: str = "hexgrad/Kokoro-82M"
    tts_voice: str = "am_michael"
    tts_enabled: bool = True
    tts_warmup_on_startup: bool = False
    tts_segment_pause_ms: int = 400
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
