# md-chat-ai migrations

Schema lifecycle for the AI layer's PostgreSQL database. Synapse manages
its own database separately; nothing here touches Matrix tables.

## TL;DR

```bash
cd ai-layer
source .venv/bin/activate
pip install -e ".[dev]"

# 1. Make sure POSTGRES_DSN is set (or fall back to default localhost).
export POSTGRES_DSN="postgresql+psycopg2://md_chat:secret@db.internal:5432/md_chat"

# 2. Apply migrations
alembic upgrade head

# 3. Generate a new migration after editing src/md_chat_ai/db/models.py
alembic revision --autogenerate -m "add_<thing>"

# 4. Inspect generated SQL without touching the DB
alembic upgrade head --sql > /tmp/migration.sql
```

## Layout

```
migrations/
├── env.py                # online + offline runner; reads CONFIG.postgres_dsn
├── script.py.mako        # template for new revisions
├── versions/
│   └── 0001_initial.py   # creates every table for the greenfield install
└── README.md             # you are here
```

## Workflow

1. Edit `src/md_chat_ai/db/models.py` — add column / table / index.
2. Run autogen against a *clean* local DB that already matches the current
   `head` revision:
   ```bash
   alembic revision --autogenerate -m "add_foo_to_user"
   ```
3. Open the generated file under `versions/`, review carefully, and tighten
   anything autogen missed (autogen does not detect: enum value renames,
   check constraints, server defaults, BRIN/GIN index types).
4. Apply locally:
   ```bash
   alembic upgrade head
   ```
5. Verify with `alembic check` that the schema matches the models.
6. Commit both the model change and the migration in the same PR.

## Postgres-specific tuning

The initial migration deliberately *also* creates BRIN indexes on
`created_at` columns and GIN indexes on JSONB columns. These are no-ops
on SQLite (the index types collapse to btree) so tests still pass — but
on Postgres they materially reduce IO on the audit and eEvidence tables.

If you need to add a new BRIN/GIN index in a follow-up migration:

```python
op.create_index(
    "ix_my_table_created_brin",
    "my_table",
    ["created_at"],
    postgresql_using="brin",
)
```

## Rollback policy

* Always write a working `downgrade()` for additive changes (new tables /
  columns / indexes) — `op.drop_table`, `op.drop_column`, `op.drop_index`.
* Destructive `downgrade()` for column drops on populated tables is
  *forbidden* unless paired with a backup script in `ops/`. Mark such
  migrations `# IRREVERSIBLE` at the top.
* Never edit a migration that has already been applied to production.
  Roll forward with a new revision instead.

## Offline / SQL-review mode

For high-risk changes (e.g. adding a UNIQUE constraint to a populated
column), produce the SQL first, review it, and apply manually under
maintenance window:

```bash
alembic upgrade head --sql > /tmp/upgrade.sql
psql "$POSTGRES_DSN" -1 -f /tmp/upgrade.sql
```

## Testing

The test suite at `tests/test_db_models.py` uses **sqlite in-memory** —
no Postgres required. CI runs the same suite on both engines via
`POSTGRES_DSN=...` override; see `.github/workflows/`.

## Compliance hooks

The `audit_entries` table is *append-only*. A nightly verifier in
`ops/verify-audit-chain.py` walks the chain and alarms on any
`current_hash` mismatch. Do not add an `UPDATE` on this table to any
service code path.
