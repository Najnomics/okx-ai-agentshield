from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENTSHIELD_", env_file=".env", extra="ignore")

    env: str = "development"
    data_dir: str = "./data"
    api_key: str | None = None
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()

