from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _get_session_factory(settings: Settings) -> sessionmaker[Session]:
    global _engine, _session_factory
    if _session_factory is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
        _session_factory = sessionmaker(
            bind=_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    factory = _get_session_factory(get_settings())
    session = factory()
    try:
        yield session
    finally:
        session.close()
