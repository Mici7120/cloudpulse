from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _request_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if isinstance(settings, Settings):
        return settings
    return get_settings()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def register_user(
    payload: RegisterRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> UserResponse:
    existing = db.scalar(select(User).where(User.email == str(payload.email)))
    if existing is not None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
            code="EMAIL_ALREADY_EXISTS",
        )

    user = User(
        email=str(payload.email),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
            code="EMAIL_ALREADY_EXISTS",
        ) from exc
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def login_user(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),  # noqa: B008
) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == str(payload.email)))
    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    password_valid = verify_password(payload.password, password_hash)
    if user is None or not password_valid:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            code="INVALID_CREDENTIALS",
        )

    token, expires_in = create_access_token(user.id, _request_settings(request))
    return TokenResponse(access_token=token, token_type="bearer", expires_in=expires_in)
