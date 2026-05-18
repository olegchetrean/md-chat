"""GDPR compliance module — Articles 13-22 for MD-Chat AI layer.

Ported from cronberry_swarm/security/gdpr.py and adapted to MD-Chat's data
topology (Neo4j graph + tacit memory store + audit log + twin profiles).

Provides:
- Art. 15 (right of access)  → `export_user_data(user_id)`
- Art. 17 (right to erasure) → `erase_user_data(user_id, grace_period_days=90)`
- Art. 16 (rectification)    → `rectify_user_data(user_id, updates)`
- Art. 30 (RoPA)             → `log_processing(...)` + `get_processing_records()`
- Consent management         → `set_consent` / `get_consent_status`
- AI Act Art. 50 disclosure  → see `ai_safety.AIDisclosure`

Stores
------
Cronberry's GDPR DB ships with SQLite consent / processing / erasure tables.
We keep the same schema here so audit trails are portable, but the
twin/graph/memory deletions are delegated to *injected stores* so the GDPR
manager stays unit-testable without spinning up Neo4j or the memory backend.

The default `_DEFAULT_STORES` registry is populated lazily by the rest of the
ai-layer (digital_twin, memory, audit log) via `register_store(name, store)`.
Each store must expose two callables:
    store.export(user_id) -> Any
    store.erase(user_id)  -> Any

License: Apache 2.0 (Mega Promoting SRL, derived from cronberry_swarm).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import sqlite3
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from ..config import CONFIG  # noqa: F401  -- imported for future config hooks

logger = logging.getLogger("md_chat_ai.security.gdpr")


# ---------------------------------------------------------------------------
# Store protocol — injected by ai-layer subsystems
# ---------------------------------------------------------------------------


class DataStore(Protocol):
    """Minimal contract every store must satisfy for GDPR operations."""

    def export(self, user_id: str) -> Any: ...
    def erase(self, user_id: str) -> Any: ...


_DEFAULT_STORE_REGISTRY: dict[str, DataStore] = {}


def register_store(name: str, store: DataStore) -> None:
    """Plug a backing store (twin/graph/memory/audit) into the manager."""
    _DEFAULT_STORE_REGISTRY[name] = store
    logger.info("GDPR: registered store name=%s", name)


def unregister_store(name: str) -> None:
    _DEFAULT_STORE_REGISTRY.pop(name, None)


# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------

_GDPR_DB_PATH = os.environ.get(
    "GDPR_DB_PATH",
    os.path.join(os.environ.get("DATA_DIR", "data"), "gdpr.db"),
)

# Default grace period (Art. 17 allows a reasonable execution window).
DEFAULT_GRACE_PERIOD_DAYS = 90


PROCESSING_PURPOSES = {
    "analytics": "Analytical processing of communication patterns",
    "twin": "Digital twin simulation based on user history",
    "graph": "Knowledge-graph construction over user data",
    "report": "Report or briefing generation",
    "sync": "Synchronisation between MD-Chat client and AI layer",
    "memory": "Long-term tacit memory storage for personalisation",
    "data_export": "GDPR Art. 15/20 data export",
    "data_erasure": "GDPR Art. 17 right-to-erasure execution",
    "data_rectification": "GDPR Art. 16 rectification",
}


# ---------------------------------------------------------------------------
# GDPRManager
# ---------------------------------------------------------------------------


class GDPRManager:
    """Central GDPR + RoPA manager for the MD-Chat AI layer.

    Uses a dedicated SQLite database for consent, processing logs, erasure
    queue and audit trail — separate from the operational databases so the
    record-keeping survives any user-data wipe (Art. 5(2) accountability).
    """

    def __init__(
        self,
        db_path: str | None = None,
        stores: Mapping[str, DataStore] | None = None,
    ) -> None:
        self.db_path = db_path or _GDPR_DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._stores: dict[str, DataStore] = dict(stores) if stores else {}
        # Late-bound default registry — consulted on each call so new stores
        # registered after the manager is created are still picked up.
        self._init_db()

    # ------------------------------------------------------------------
    # DB bootstrap
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS consent (
                    id           TEXT PRIMARY KEY,
                    user_id      TEXT NOT NULL,
                    consent_type TEXT NOT NULL,
                    granted      INTEGER NOT NULL DEFAULT 0,
                    method       TEXT NOT NULL DEFAULT 'explicit',
                    ip_address   TEXT,
                    user_agent   TEXT,
                    granted_at   TEXT,
                    revoked_at   TEXT,
                    created_at   TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_consent_user ON consent (user_id);

                CREATE TABLE IF NOT EXISTS processing_log (
                    id              TEXT PRIMARY KEY,
                    user_id         TEXT,
                    purpose         TEXT NOT NULL,
                    legal_basis     TEXT NOT NULL DEFAULT 'legitimate_interest',
                    data_categories TEXT NOT NULL,
                    processor       TEXT NOT NULL DEFAULT 'md-chat-ai',
                    retention_days  INTEGER NOT NULL DEFAULT 365,
                    notes           TEXT,
                    created_at      TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_plog_user ON processing_log (user_id);
                CREATE INDEX IF NOT EXISTS idx_plog_purpose ON processing_log (purpose);

                CREATE TABLE IF NOT EXISTS erasure_log (
                    id              TEXT PRIMARY KEY,
                    user_id         TEXT NOT NULL,
                    requested_at    TEXT NOT NULL,
                    scheduled_at    TEXT NOT NULL,
                    executed_at     TEXT,
                    requested_by    TEXT NOT NULL DEFAULT 'user',
                    grace_days      INTEGER NOT NULL DEFAULT 90,
                    stores          TEXT NOT NULL,
                    rows_deleted    TEXT,
                    status          TEXT NOT NULL DEFAULT 'pending'
                );
                CREATE INDEX IF NOT EXISTS idx_erasure_user ON erasure_log (user_id);
                CREATE INDEX IF NOT EXISTS idx_erasure_status ON erasure_log (status);
                """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    # ------------------------------------------------------------------
    # Store resolution
    # ------------------------------------------------------------------

    def _resolve_stores(self) -> dict[str, DataStore]:
        """Merge per-instance stores with the global registry."""
        merged: dict[str, DataStore] = dict(_DEFAULT_STORE_REGISTRY)
        merged.update(self._stores)
        return merged

    # ------------------------------------------------------------------
    # Art. 15 + 20 — Data export
    # ------------------------------------------------------------------

    def export_user_data(self, user_id: str, fmt: str = "json") -> dict[str, Any]:
        """Return a JSON-serialisable dict containing every piece of data the
        MD-Chat AI layer holds about ``user_id``.

        Output schema:
            {
              "export_meta": { user_id, exported_at, regulation, format },
              "stores":       { <store_name>: <store-specific dump or error> },
              "consent":      [ ... ],
              "processing_records": [ ... ],
              "erasure_requests":   [ ... ],
              "csv_sections":       { ... }   # only when fmt == "csv"
            }
        """
        logger.info("GDPR Art.15/20 export requested user=%s", user_id)

        export: dict[str, Any] = {
            "export_meta": {
                "user_id": user_id,
                "exported_at": self._now(),
                "regulation": "GDPR Art. 15 + 20",
                "format": fmt,
            },
            "stores": {},
            "consent": [],
            "processing_records": [],
            "erasure_requests": [],
        }

        for name, store in self._resolve_stores().items():
            try:
                export["stores"][name] = store.export(user_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "GDPR export: store=%s failed for user=%s: %s",
                    name,
                    user_id,
                    exc,
                )
                export["stores"][name] = {"_error": str(exc)}

        export["consent"] = self._get_consent_rows(user_id)
        export["processing_records"] = self._get_processing_rows_for_user(user_id)
        export["erasure_requests"] = self._get_erasure_rows_for_user(user_id)

        # Always log the export itself (Art. 30 record).
        self.log_processing(
            user_id=user_id,
            purpose="data_export",
            legal_basis="gdpr_art_15_20",
            data_categories="all",
            notes="Art. 15/20 export performed via API",
        )

        if fmt == "csv":
            export["csv_sections"] = self._build_csv_sections(export)
        return export

    @staticmethod
    def _build_csv_sections(export: dict[str, Any]) -> dict[str, str]:
        sections: dict[str, str] = {}
        for key in ("consent", "processing_records", "erasure_requests"):
            rows = export.get(key, [])
            if not rows or not isinstance(rows, list):
                continue
            first = rows[0]
            if not isinstance(first, dict):
                continue
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=list(first.keys()))
            writer.writeheader()
            writer.writerows(rows)
            sections[key] = buf.getvalue()
        return sections

    # ------------------------------------------------------------------
    # Art. 17 — Right to erasure
    # ------------------------------------------------------------------

    def erase_user_data(
        self,
        user_id: str,
        grace_period_days: int = DEFAULT_GRACE_PERIOD_DAYS,
        requested_by: str = "user",
        execute_immediately: bool = False,
    ) -> dict[str, Any]:
        """Schedule (or perform) GDPR Art. 17 erasure for ``user_id``.

        Wipes everything we hold for the user across the registered stores
        (digital twin profiles, knowledge graph nodes, tacit memory, audit
        log per-user entries, queued briefings, ...).

        Args:
            user_id:              MD-Chat / matrix user identifier.
            grace_period_days:    Days between request and actual execution.
                                  Defaults to 90 days so the user can recover
                                  the account if the request was accidental.
                                  Pass 0 (with `execute_immediately=True`) to
                                  perform a hard wipe right now.
            requested_by:         "user" | "operator" | "admin" — audit info.
            execute_immediately:  If True, run the deletion now instead of
                                  scheduling it. Used by background worker
                                  when the grace period elapses.

        Returns:
            Dict describing what happened, with one of:
            - status="scheduled" → erasure queued, execute_at populated
            - status="executed"  → erasure performed, per-store counts present
        """
        logger.warning(
            "GDPR Art.17 erasure user=%s grace=%dd by=%s immediate=%s",
            user_id,
            grace_period_days,
            requested_by,
            execute_immediately,
        )

        now = datetime.now(UTC)
        scheduled_at = now + timedelta(days=max(0, grace_period_days))

        request_id = uuid.uuid4().hex
        stores = list(self._resolve_stores().keys())

        # Persist the request first so the audit trail survives a crash.
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO erasure_log
                   (id, user_id, requested_at, scheduled_at, executed_at,
                    requested_by, grace_days, stores, rows_deleted, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request_id,
                    user_id,
                    now.isoformat(),
                    scheduled_at.isoformat(),
                    None,
                    requested_by,
                    grace_period_days,
                    json.dumps(stores),
                    None,
                    "pending",
                ),
            )
            conn.commit()

        if not execute_immediately and grace_period_days > 0:
            self.log_processing(
                user_id=user_id,
                purpose="data_erasure",
                legal_basis="gdpr_art_17",
                data_categories="all",
                notes=f"Erasure scheduled in {grace_period_days}d (id={request_id})",
            )
            return {
                "request_id": request_id,
                "user_id": user_id,
                "status": "scheduled",
                "scheduled_at": scheduled_at.isoformat(),
                "grace_period_days": grace_period_days,
                "stores": stores,
            }

        # Immediate erasure path -------------------------------------------------
        return self._execute_erasure(request_id, user_id)

    def execute_due_erasures(self) -> list[dict[str, Any]]:
        """Run every erasure whose scheduled_at is in the past. Background worker."""
        now_iso = self._now()
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, user_id FROM erasure_log
                   WHERE status = 'pending' AND scheduled_at <= ?""",
                (now_iso,),
            ).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            try:
                results.append(self._execute_erasure(row["id"], row["user_id"]))
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "GDPR erasure: failed request=%s user=%s: %s",
                    row["id"],
                    row["user_id"],
                    exc,
                )
        return results

    def _execute_erasure(self, request_id: str, user_id: str) -> dict[str, Any]:
        rows_deleted: dict[str, Any] = {}
        for name, store in self._resolve_stores().items():
            try:
                rows_deleted[name] = store.erase(user_id)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "GDPR erasure: store=%s failed user=%s: %s",
                    name,
                    user_id,
                    exc,
                )
                rows_deleted[name] = {"_error": str(exc)}

        # Wipe consent rows but KEEP processing_log + erasure_log entries
        # (Art. 5(2) accountability).
        consent_deleted = self._erase_consent_rows(user_id)
        rows_deleted["consent"] = {"deleted": consent_deleted}

        with self._connect() as conn:
            conn.execute(
                """UPDATE erasure_log
                   SET executed_at = ?, status = 'executed', rows_deleted = ?
                   WHERE id = ?""",
                (self._now(), json.dumps(rows_deleted, default=str), request_id),
            )
            conn.commit()

        self.log_processing(
            user_id=user_id,
            purpose="data_erasure",
            legal_basis="gdpr_art_17",
            data_categories="all",
            notes=f"Erasure executed (id={request_id})",
        )

        logger.warning(
            "GDPR Art.17 erasure EXECUTED user=%s rows=%s",
            user_id,
            rows_deleted,
        )
        return {
            "request_id": request_id,
            "user_id": user_id,
            "status": "executed",
            "executed_at": self._now(),
            "stores": rows_deleted,
        }

    def cancel_erasure(self, request_id: str) -> bool:
        """Cancel a pending erasure (only allowed while in grace period)."""
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE erasure_log SET status = 'cancelled'
                   WHERE id = ? AND status = 'pending'""",
                (request_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def _erase_consent_rows(self, user_id: str) -> int:
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM consent WHERE user_id = ?", (user_id,)).fetchone()[0]
            conn.execute("DELETE FROM consent WHERE user_id = ?", (user_id,))
            conn.commit()
        return int(count)

    # ------------------------------------------------------------------
    # Art. 16 — Data rectification (best-effort delegate)
    # ------------------------------------------------------------------

    def rectify_user_data(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Forward a rectification request to every store that supports it."""
        results: dict[str, Any] = {}
        for name, store in self._resolve_stores().items():
            rectify: Callable[[str, dict[str, Any]], Any] | None = getattr(store, "rectify", None)
            if rectify is None:
                continue
            try:
                results[name] = rectify(user_id, updates)
            except Exception as exc:  # noqa: BLE001
                results[name] = {"_error": str(exc)}

        self.log_processing(
            user_id=user_id,
            purpose="data_rectification",
            legal_basis="gdpr_art_16",
            data_categories=",".join(sorted(updates.keys())),
            notes=f"Art. 16 rectification: {sorted(updates.keys())}",
        )
        return {
            "user_id": user_id,
            "rectified_at": self._now(),
            "stores": results,
            "fields": sorted(updates.keys()),
        }

    # ------------------------------------------------------------------
    # Consent management
    # ------------------------------------------------------------------

    def set_consent(
        self,
        user_id: str,
        consent_type: str,
        granted: bool,
        method: str = "explicit",
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        now = self._now()
        record_id = uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute(
                """UPDATE consent SET revoked_at = ?
                   WHERE user_id = ? AND consent_type = ? AND revoked_at IS NULL""",
                (now, user_id, consent_type),
            )
            conn.execute(
                """INSERT INTO consent
                   (id, user_id, consent_type, granted, method,
                    ip_address, user_agent, granted_at, revoked_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record_id,
                    user_id,
                    consent_type,
                    1 if granted else 0,
                    method,
                    ip_address,
                    user_agent,
                    now if granted else None,
                    None if granted else now,
                    now,
                ),
            )
            conn.commit()
        logger.info(
            "GDPR consent: user=%s type=%s granted=%s method=%s",
            user_id,
            consent_type,
            granted,
            method,
        )
        return {
            "id": record_id,
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": granted,
            "method": method,
            "timestamp": now,
        }

    def get_consent_status(self, user_id: str) -> dict[str, Any]:
        rows = self._get_consent_rows(user_id)
        consent_types: dict[str, Any] = {}
        for row in rows:
            ct = row["consent_type"]
            if ct in consent_types:
                continue  # keep newest only (rows are sorted DESC)
            consent_types[ct] = {
                "granted": bool(row["granted"]),
                "method": row["method"],
                "granted_at": row["granted_at"],
                "revoked_at": row["revoked_at"],
                "id": row["id"],
            }
        return {
            "user_id": user_id,
            "consent_types": consent_types,
            "last_updated": max((r["created_at"] for r in rows), default=None),
        }

    def _get_consent_rows(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM consent WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def _get_processing_rows_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM processing_log WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def _get_erasure_rows_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM erasure_log WHERE user_id = ? ORDER BY requested_at DESC",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Art. 30 — Record of Processing Activities (RoPA)
    # ------------------------------------------------------------------

    def log_processing(
        self,
        purpose: str,
        legal_basis: str,
        data_categories: str,
        user_id: str | None = None,
        processor: str = "md-chat-ai",
        retention_days: int = 365,
        notes: str = "",
    ) -> str:
        record_id = uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO processing_log
                   (id, user_id, purpose, legal_basis, data_categories,
                    processor, retention_days, notes, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record_id,
                    user_id,
                    purpose,
                    legal_basis,
                    data_categories,
                    processor,
                    retention_days,
                    notes,
                    self._now(),
                ),
            )
            conn.commit()
        return record_id

    def get_processing_records(
        self,
        limit: int = 500,
        offset: int = 0,
        purpose_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if purpose_filter:
                rows = conn.execute(
                    """SELECT * FROM processing_log WHERE purpose = ?
                       ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                    (purpose_filter, limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM processing_log
                       ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                    (limit, offset),
                ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_manager: GDPRManager | None = None


def get_manager() -> GDPRManager:
    """Return (or lazily create) the module-level GDPRManager singleton."""
    global _manager
    if _manager is None:
        _manager = GDPRManager()
    return _manager


def reset_manager() -> None:
    """Drop the singleton — used by tests to point at a temp DB."""
    global _manager
    _manager = None
