from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, *, status_code: int, detail: str, code: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        if errors:
            first = errors[0]
            loc = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
            msg = str(first.get("msg", "Invalid request payload"))
            detail = f"{loc}: {msg}" if loc else msg
        else:
            detail = "Invalid request payload"
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": detail, "code": "VALIDATION_ERROR"},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detail, "code": f"HTTP_{exc.status_code}"},
            headers=exc.headers,
        )
