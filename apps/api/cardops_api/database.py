from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from cardops_api.config import ROOT_DIR, get_settings
from cardops_api.models import Base

_engine: Engine | None = None
_session_local: sessionmaker[Session] | None = None


def _normalize_sqlite_url(url: str) -> str:
    if not url.startswith("sqlite:///./"):
        return url
    relative = url.removeprefix("sqlite:///./")
    absolute = ROOT_DIR / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{absolute.as_posix()}"


def configure_database(url: str | None = None) -> None:
    global _engine, _session_local
    if _engine is not None:
        _engine.dispose()
    settings = get_settings()
    database_url = _normalize_sqlite_url(url or settings.database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    _engine = create_engine(database_url, connect_args=connect_args, future=True)
    _session_local = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_engine() -> Engine:
    if _engine is None:
        configure_database()
    assert _engine is not None
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _session_local is None:
        configure_database()
    assert _session_local is not None
    return _session_local


def init_db() -> None:
    settings = get_settings()
    for path in [settings.data_dir, settings.thumbnail_dir, settings.demo_dir, settings.exports_dir]:
        Path(path).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=get_engine())


def get_session() -> Generator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
