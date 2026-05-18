"""SQLAlchemy engine + session factory.

Single source of truth for DB connectivity. The engine is constructed lazily
on first call to :func:`get_engine` so unit tests can override
``CONFIG.postgres_dsn`` before any pool is opened.

Test policy
-----------
Tests must call :func:`dispose_engine` between modules to avoid leaking a
process-wide engine when different DSNs are used (e.g. sqlite ``:memory:``).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from threading import Lock
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from md_chat_ai.config import CONFIG

_engine: Engine | None = None
_sessionmaker: sessionmaker[Session] | None = None
_lock = Lock()


def _build_engine(dsn: str | None = None, **overrides: Any) -> Engine:
    """Construct a new engine. Pool config differs for SQLite vs Postgres."""
    url = dsn or CONFIG.postgres_dsn
    kwargs: dict[str, Any] = {"future": True, "echo": CONFIG.postgres_echo}

    if url.startswith("sqlite"):
        # In-memory SQLite needs the StaticPool to share state across threads
        # within a single test process; ``check_same_thread`` is required for
        # Flask-style tests that hop threads.
        from sqlalchemy.pool import StaticPool

        kwargs.update(
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        kwargs.update(
            pool_size=CONFIG.postgres_pool_size,
            max_overflow=CONFIG.postgres_max_overflow,
            pool_timeout=CONFIG.postgres_pool_timeout,
            pool_pre_ping=True,
        )

    kwargs.update(overrides)
    engine = create_engine(url, **kwargs)

    # SQLite: foreign keys are OFF by default; enable them so ON DELETE
    # CASCADE / SET NULL behave as advertised in production (Postgres).
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_sqlite_fk(dbapi_conn: Any, _conn_record: Any) -> None:  # pragma: no cover
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_engine(dsn: str | None = None) -> Engine:
    """Return the process-global engine, building it on first call.

    Passing ``dsn`` rebuilds (and replaces) the global engine — used by tests
    to point at sqlite ``:memory:``.
    """
    global _engine, _sessionmaker
    with _lock:
        if _engine is None or dsn is not None:
            if _engine is not None:
                _engine.dispose()
            _engine = _build_engine(dsn=dsn)
            _sessionmaker = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
        return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    """Return the process-global sessionmaker; builds engine on first call."""
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


def dispose_engine() -> None:
    """Tear down the global engine — call between test modules / on shutdown."""
    global _engine, _sessionmaker
    with _lock:
        if _engine is not None:
            _engine.dispose()
        _engine = None
        _sessionmaker = None


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session: commits on success, rolls back on exception."""
    sm = get_sessionmaker()
    session = sm()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
