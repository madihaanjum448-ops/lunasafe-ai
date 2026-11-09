"""Application settings, read from environment variables / .env file."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "LunaSafe AI Backend"
    app_version: str = "0.1.0"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    max_file_size_mb: int = 50
    max_image_width: int = 8192
    max_image_height: int = 8192
    upload_dir: str = "./uploads"

    # PLACEHOLDER defaults: the PRD v2.0 was not available when this was written.
    # Confirm each value against the PRD before using results for anything.
    lander_footprint_diameter_m: float = 10.0
    hazard_boulder_height_m: float = 0.5
    slope_gate_deg: float = 10.0

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
