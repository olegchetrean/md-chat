"""Alembic environment.

Reads the DB URL from :data:`md_chat_ai.config.CONFIG.postgres_dsn` so that
the same env-var-driven config powers app code and migrations.

Online mode (default): connects through the SQLAlchemy engine.
Offline mode: emits SQL to stdout for review without touching a database
(useful for ops review of irreversible changes).
"""

from __future__ import annotations

import logging
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make ``src/`` importable without installing the package — useful in CI.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from md_chat_ai.config import CONFIG  # noqa: E402
from md_chat_ai.db.base import Base  # noqa: E402
from md_chat_ai.db import models  # noqa: E402,F401  -- ensure tables are registered

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

target_metadata = Base.metadata


def _resolve_url() -> str:
    """Resolve the DB URL — CLI ``-x url=...`` wins, else CONFIG.postgres_dsn."""
    x_args = context.get_x_argument(as_dictionary=True)
    return x_args.get("url") or CONFIG.postgres_dsn


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL without a DBAPI connection."""
    url = _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connect and apply against the DB."""
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _resolve_url()

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
