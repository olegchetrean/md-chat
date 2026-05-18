"""Database persistence layer for md-chat-ai.

Schema is owned by *this* service; Synapse manages its own Postgres database
separately (matrix.synapse.* tables). The two databases are NEVER cross-joined.
Inter-service references use opaque IDs only.

Public API:
    * :class:`Base` — SQLAlchemy 2.0 declarative base.
    * :func:`get_engine` — singleton SQLAlchemy engine bound to ``CONFIG.postgres_dsn``.
    * :func:`get_sessionmaker` — sessionmaker factory.
    * :func:`session_scope` — context manager yielding a transactional session.
    * Model classes from :mod:`md_chat_ai.db.models`.
"""

from __future__ import annotations

from md_chat_ai.db.base import Base
from md_chat_ai.db.engine import (
    dispose_engine,
    get_engine,
    get_sessionmaker,
    session_scope,
)
from md_chat_ai.db.models import (
    AuditEntry,
    AuditTrailTwin,
    DSRRequest,
    EVerifyOrder,
    MFASettings,
    PhoneVerification,
    PINBackup,
    User,
)

__all__ = [
    "Base",
    "get_engine",
    "get_sessionmaker",
    "session_scope",
    "dispose_engine",
    "User",
    "PhoneVerification",
    "MFASettings",
    "PINBackup",
    "EVerifyOrder",
    "AuditEntry",
    "DSRRequest",
    "AuditTrailTwin",
]
