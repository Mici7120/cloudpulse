from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.monitors import router as monitors_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    app = FastAPI(
        title="CloudPulse API",
        version="0.1.0",
        description="Uptime, deploys, and alerts monitor API.",
    )
    app.state.settings = active_settings
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(monitors_router)
    return app
