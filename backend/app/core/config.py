from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    app_env: Literal["development", "test", "production"] = "production"
    cookie_secure: bool = True
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    session_hours: int = Field(default=8, ge=1, le=24)
    s3_endpoint_url: str = "http://localhost:8333"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "visa-selfie-videos"
    s3_region: str = "us-east-1"
    max_upload_bytes: int = Field(default=30 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    max_video_seconds: int = Field(default=30, ge=3, le=60)
    ffprobe_path: str = "ffprobe"

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        if not self.allowed_origins:
            raise ValueError("At least one explicit allowed origin is required")
        for origin in self.allowed_origins:
            parsed = urlparse(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or "*" in origin
            ):
                raise ValueError("Allowed origins must be exact HTTP(S) origins without paths")
        if self.app_env == "production":
            if not self.cookie_secure:
                raise ValueError("Production requires secure cookies")
            if any(not origin.startswith("https://") for origin in self.allowed_origins):
                raise ValueError("Production requires HTTPS origins")
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production requires PostgreSQL")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
