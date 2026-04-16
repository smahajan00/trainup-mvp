from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TrainUp API"
    api_prefix: str = "/api"
    database_url: str = "postgresql://trainup_user:trainup_password@db:5432/trainup_db"
    secret_key: str = "change_this"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
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
