from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)


def get_request_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if isinstance(settings, Settings):
        return settings
    return get_settings()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            code="UNAUTHORIZED",
        )

    user_id = decode_access_token(credentials.credentials, get_request_settings(request))
    if user_id is None:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            code="INVALID_TOKEN",
        )

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            code="INVALID_TOKEN",
        )
    return user
