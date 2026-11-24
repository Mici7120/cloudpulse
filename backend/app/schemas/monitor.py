from datetime import datetime
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)

_HTTP_URL_ADAPTER: TypeAdapter[AnyHttpUrl] = TypeAdapter(AnyHttpUrl)


def _validate_http_url(value: str) -> str:
    stripped = value.strip()
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in stripped):
        raise ValueError("URL must not contain control characters")
    _HTTP_URL_ADAPTER.validate_python(stripped)
    return stripped


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=1, max_length=2048)
    interval_seconds: int = Field(default=60, ge=30, le=86400)
    expected_status: int = Field(default=200, ge=100, le=599)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Monitor name must not be blank")
        return stripped

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return _validate_http_url(value)


class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    interval_seconds: int | None = Field(default=None, ge=30, le=86400)
    expected_status: int | None = Field(default=None, ge=100, le=599)
    is_active: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_nulls(cls, data: object) -> object:
        if isinstance(data, dict):
            for key in cls.model_fields:
                if key in data and data[key] is None:
                    raise ValueError(f"{key} must not be null")
        return data

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Monitor name must not be blank")
        return stripped

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_http_url(value)


class MonitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str
    interval_seconds: int
    expected_status: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MonitorListResponse(BaseModel):
    items: list[MonitorResponse]
    total: int
