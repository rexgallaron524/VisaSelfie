import json
from functools import lru_cache
from ipaddress import ip_network
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, HttpUrl, TypeAdapter, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def public_origin(value: str) -> str:
    """Accept a canonical HTTP(S) origin, never credentials or a URL prefix."""
    if (
        not value.startswith(("http://", "https://"))
        or any(c.isspace() for c in value)
        or any(c in value for c in "\\?#*")
        or urlsplit(value).path.strip("/")
    ):
        raise ValueError("Public URLs must be HTTP(S) origins without paths or credentials")
    parsed = TypeAdapter(HttpUrl).validate_python(value)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Public URLs must be HTTP(S) origins without paths or credentials")
    return str(parsed).rstrip("/")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    app_env: Literal["development", "test", "production"] = "production"
    frontend_public_url: str = "http://localhost:3000"
    cookie_secure: bool | None = None
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    forwarded_allow_ips: str = ""
    session_hours: int = Field(default=8, ge=1, le=24)
    s3_endpoint_url: str = "http://localhost:8333"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "visa-selfie-videos"
    s3_region: str = "us-east-1"
    max_upload_bytes: int = Field(default=30 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    max_video_seconds: int = Field(default=30, ge=3, le=60)
    ffprobe_path: str = "ffprobe"

    @field_validator("frontend_public_url")
    @classmethod
    def validate_public_url(cls, value: str) -> str:
        return public_origin(value)

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            value = json.loads(value) if value.lstrip().startswith("[") else value.split(",")
        return [public_origin(origin.strip()) for origin in value]

    @field_validator("forwarded_allow_ips")
    @classmethod
    def validate_proxy_ips(cls, value: str) -> str:
        for address in value.split(","):
            if address.strip():
                ip_network(address.strip(), strict=False)
        return value

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        if self.cookie_secure is None:
            self.cookie_secure = self.frontend_public_url.startswith("https://")
        if not self.allowed_origins:
            raise ValueError("At least one explicit allowed origin is required")
        if self.frontend_public_url not in self.allowed_origins:
            raise ValueError("ALLOWED_ORIGINS must include FRONTEND_PUBLIC_URL")
        if self.app_env == "production":
            if not self.cookie_secure:
                raise ValueError("Production requires secure cookies")
            if not self.frontend_public_url.startswith("https://"):
                raise ValueError("Production requires an HTTPS FRONTEND_PUBLIC_URL")
            if any(not origin.startswith("https://") for origin in self.allowed_origins):
                raise ValueError("Production requires HTTPS origins")
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production requires PostgreSQL")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
