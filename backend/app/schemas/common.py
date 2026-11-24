from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str
    code: str


class HealthResponse(BaseModel):
    status: str
    database: str
