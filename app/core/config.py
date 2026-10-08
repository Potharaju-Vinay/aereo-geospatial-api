"""Application settings.

All tunable values live here and are read from environment variables (or a
local .env file), so nothing is hard-coded in the services.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "GeoMeasure"
    database_url: str = "sqlite:///./geomeasure.db"
    upload_directory: Path = Path("uploads")

    # Upload limits. The uncompressed limit protects against zip bombs.
    max_file_size_mb: int = 25
    max_uncompressed_size_mb: int = 200
    max_zip_entries: int = 50

    allowed_extensions: list[str] = [".kml", ".zip"]
    log_level: str = "INFO"

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def max_uncompressed_bytes(self) -> int:
        return self.max_uncompressed_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
