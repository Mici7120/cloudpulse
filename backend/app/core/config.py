from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_SECRET = "replace-with-a-long-random-secret-key-at-least-32-chars"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg://cloudpulse:cloudpulse@localhost:5432/cloudpulse",
        alias="DATABASE_URL",
    )
    jwt_secret_key: SecretStr = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = Field(
        default="HS256",
        alias="JWT_ALGORITHM",
    )
    jwt_expire_minutes: int = Field(default=60, ge=1, alias="JWT_EXPIRE_MINUTES")

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value().strip()
        if len(raw) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        if raw == _PLACEHOLDER_SECRET:
            raise ValueError("JWT_SECRET_KEY must not use the example placeholder value")
        return SecretStr(raw)


@lru_cache
def get_settings() -> Settings:
    return Settings()
