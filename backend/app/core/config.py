from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TrainUp API"
    api_prefix: str = "/api"
    database_url: str = "postgresql://trainup_user:trainup_password@db:5432/trainup_db"
    secret_key: str = "change_this"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    llm_provider: str = "llama_cpp"
    llm_model: str = "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_timeout_seconds: float = 10.0
    llm_max_tokens: int = 360
    llm_temperature: float = 0.2
    llm_enabled: bool | None = None
    llm_enable_enhancement: bool = False
    llm_model_path: str = "models/Qwen2.5-7B-Instruct-Q4_K_M.gguf"
    llm_model_repo_id: str = "bartowski/Qwen2.5-7B-Instruct-GGUF"
    llm_model_filename: str = "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
    llm_context_size: int = 4096
    llm_gpu_layers: int = 0
    llm_batch_size: int = 128
    llm_warmup_on_startup: bool = False
    fuzzy_interpretation_enabled: bool = True
    it2_fuzzy_enabled: bool = True
    pose_target_fps: float = 12.0
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
