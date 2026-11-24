from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.monitor import Monitor
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.schemas.monitor import (
    MonitorCreate,
    MonitorListResponse,
    MonitorResponse,
    MonitorUpdate,
)

router = APIRouter(
    prefix="/monitors",
    tags=["monitors"],
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)


def _get_owned_monitor(db: Session, monitor_id: UUID, owner_id: UUID) -> Monitor:
    monitor = db.scalar(
        select(Monitor).where(Monitor.id == monitor_id, Monitor.owner_id == owner_id)
    )
    if monitor is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found",
            code="MONITOR_NOT_FOUND",
        )
    return monitor


@router.post(
    "",
    response_model=MonitorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_monitor(
    payload: MonitorCreate,
    db: Session = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> MonitorResponse:
    monitor = Monitor(
        owner_id=current_user.id,
        name=payload.name,
        url=payload.url,
        interval_seconds=payload.interval_seconds,
        expected_status=payload.expected_status,
        is_active=payload.is_active,
    )
    db.add(monitor)
    db.commit()
    db.refresh(monitor)
    return MonitorResponse.model_validate(monitor)


@router.get("", response_model=MonitorListResponse)
def list_monitors(
    db: Session = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> MonitorListResponse:
    monitors = list(
        db.scalars(
            select(Monitor)
            .where(Monitor.owner_id == current_user.id)
            .order_by(Monitor.created_at.asc())
        )
    )
    items = [MonitorResponse.model_validate(m) for m in monitors]
    return MonitorListResponse(items=items, total=len(items))


@router.get(
    "/{monitor_id}",
    response_model=MonitorResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_monitor(
    monitor_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> MonitorResponse:
    monitor = _get_owned_monitor(db, monitor_id, current_user.id)
    return MonitorResponse.model_validate(monitor)


@router.patch(
    "/{monitor_id}",
    response_model=MonitorResponse,
    responses={404: {"model": ErrorResponse}},
)
def update_monitor(
    monitor_id: UUID,
    payload: MonitorUpdate,
    db: Session = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> MonitorResponse:
    monitor = _get_owned_monitor(db, monitor_id, current_user.id)
    updates = payload.model_dump(exclude_unset=True)
    if updates:
        for field, value in updates.items():
            setattr(monitor, field, value)
        monitor.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(monitor)
    return MonitorResponse.model_validate(monitor)


@router.delete(
    "/{monitor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
def delete_monitor(
    monitor_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> Response:
    monitor = _get_owned_monitor(db, monitor_id, current_user.id)
    db.delete(monitor)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
