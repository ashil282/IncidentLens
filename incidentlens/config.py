from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_path: Path = Path("./data/incidentlens.db")
    log_level: str = "INFO"
    max_batch_size: int = 500
    model_config = SettingsConfigDict(env_prefix="INCIDENTLENS_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
