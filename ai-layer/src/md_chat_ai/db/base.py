"""Declarative base and shared type helpers.

Postgres-vs-SQLite portability strategy:
    * UUIDs: ``postgresql.UUID(as_uuid=True)`` on Postgres, ``String(36)`` on SQLite.
      We resolve the column type *lazily* at table-create time so tests against
      sqlite-in-memory don't require any psycopg2/postgres dialect tricks.
    * JSON: ``postgresql.JSONB`` on Postgres, ``JSON`` on SQLite.
    * TIMESTAMPTZ: ``DateTime(timezone=True)`` — SQLAlchemy maps to TIMESTAMPTZ on PG
      and naive TIMESTAMP on SQLite (acceptable for tests).
    * Arrays: ``postgresql.ARRAY(String)`` on Postgres, ``JSON`` on SQLite.

The :class:`Base` itself does not vary; portability is handled by the
:class:`GUID`, :class:`JSONB`, and :class:`StringArray` ``TypeDecorator``
classes below.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import CHAR, JSON, String, TypeDecorator
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all md-chat-ai ORM models."""


# ---------------------------------------------------------------------------
# Portable UUID column.
# ---------------------------------------------------------------------------


class GUID(TypeDecorator[uuid.UUID]):
    """Platform-independent UUID type.

    Uses Postgres :class:`postgresql.UUID` when available; falls back to
    ``CHAR(36)`` on SQLite (or any other dialect). Round-trips a Python
    :class:`uuid.UUID` either way.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value) if isinstance(value, uuid.UUID) else str(uuid.UUID(str(value)))

    def process_result_value(self, value: Any, dialect: Any) -> uuid.UUID | None:
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


# ---------------------------------------------------------------------------
# Portable JSONB column.
# ---------------------------------------------------------------------------


class JSONB(TypeDecorator[Any]):
    """JSONB on Postgres; plain JSON on every other dialect (incl. SQLite)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.JSONB())
        return dialect.type_descriptor(JSON())


# ---------------------------------------------------------------------------
# Portable string-array column.
# ---------------------------------------------------------------------------


class StringArray(TypeDecorator[list[str]]):
    """``TEXT[]`` on Postgres; JSON list on SQLite.

    Use this for short, append-only string lists (e.g. MFA backup-code hashes).
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.ARRAY(String()))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return list(value)
        return list(value)

    def process_result_value(self, value: Any, dialect: Any) -> list[str] | None:
        if value is None:
            return None
        return list(value)
