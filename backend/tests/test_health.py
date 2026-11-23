from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db
from app.main import create_app


def test_health_returns_ok_when_database_is_reachable(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_unavailable(test_settings: Settings) -> None:
    class _BrokenSession:
        def execute(self, *_args: object, **_kwargs: object) -> None:
            raise OperationalError("SELECT 1", {}, Exception("db down"))

    app = create_app(settings=test_settings)

    def _override_broken_db() -> Generator[Session, None, None]:
        yield _BrokenSession()  # type: ignore[misc]

    app.dependency_overrides[get_db] = _override_broken_db
    with TestClient(app) as broken_client:
        response = broken_client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Database connection unavailable",
        "code": "DATABASE_UNAVAILABLE",
    }
