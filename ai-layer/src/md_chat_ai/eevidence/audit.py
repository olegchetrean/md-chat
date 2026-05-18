"""Append-only audit register for the eEvidence intake portal.

This register satisfies two overlapping legal obligations:

* **GDPR Art. 33(5)** — controllers must document every personal-data breach
  *and* every access to personal data in response to a lawful request from a
  public authority. The eEvidence Regulation routes orders to operators who
  routinely process content + metadata — every such touchpoint MUST be logged
  with enough context to defend the lawfulness of the disclosure to a
  supervisory authority years later.
* **eEvidence Regulation Art. 31** — service providers must keep an internal
  record of every order received, the response sent, refusal grounds invoked
  (if any) and the timing, available for inspection by the competent
  authority that issued the order.

The register is implemented as an append-only list with **hash chaining** so
that subsequent tampering is detectable. Entries are sealed at write time:
the public API only exposes copies; mutation attempts raise.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

# Sentinel used as the previous hash for the very first entry of a register.
_GENESIS_HASH = "0" * 64


def _utcnow_iso() -> str:
    """Wall-clock UTC timestamp in ISO-8601 with millisecond precision."""

    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _stable_hash(payload: dict[str, Any], previous_hash: str) -> str:
    """Compute SHA-256 hash chaining an entry to its predecessor."""

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256()
    digest.update(previous_hash.encode("ascii"))
    digest.update(b"\x1f")  # ASCII unit separator avoids collision games.
    digest.update(canonical.encode("utf-8"))
    return digest.hexdigest()


@dataclass(frozen=True)
class AuditEntry:
    """A single immutable record in the eEvidence audit register.

    Frozen dataclass — mutation raises ``dataclasses.FrozenInstanceError``.
    """

    sequence: int
    """Monotonic counter, starting at 1."""

    timestamp: str
    """UTC ISO-8601 timestamp, set at write time."""

    event_type: str
    """One of: ``order_received``, ``preservation_received``, ``emergency_marked``,
    ``order_responded``, ``order_refused``, ``order_extended``."""

    ticket_id: str
    """The internal ticket identifier the entry refers to."""

    actor: str
    """Free-form actor description (e.g. ``portal:authority``,
    ``operator:dpo``, ``cron:sla_watchdog``)."""

    details: dict[str, Any] = field(default_factory=dict)
    """Event-specific structured details. Personal data of suspects MUST NOT
    be stored here — only the metadata of the order itself."""

    previous_hash: str = _GENESIS_HASH
    """Hash of the previous entry, forming the chain."""

    entry_hash: str = ""
    """SHA-256 of this entry's canonical JSON, prefixed by ``previous_hash``."""

    def verify(self) -> bool:
        """Recompute the hash and compare with the stored value."""

        payload = {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "ticket_id": self.ticket_id,
            "actor": self.actor,
            "details": self.details,
        }
        return _stable_hash(payload, self.previous_hash) == self.entry_hash

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict view, useful for JSON dashboards."""

        return asdict(self)


class AuditRegister:
    """Append-only audit register.

    Designed to be safe for use from multiple Flask request threads. The
    register stores entries in memory; persistence to disk / DB is left to
    callers (see runbook for the production retention rule: 5 years minimum
    after the last related criminal proceedings close, per national MLAT
    practice).
    """

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ append

    def append(
        self,
        *,
        event_type: str,
        ticket_id: str,
        actor: str,
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Record a new event. Returns the sealed :class:`AuditEntry`."""

        if not event_type:
            raise ValueError("event_type is required")
        if not ticket_id:
            raise ValueError("ticket_id is required")
        if not actor:
            raise ValueError("actor is required")

        with self._lock:
            previous_hash = self._entries[-1].entry_hash if self._entries else _GENESIS_HASH
            sequence = len(self._entries) + 1
            payload = {
                "sequence": sequence,
                "timestamp": _utcnow_iso(),
                "event_type": event_type,
                "ticket_id": ticket_id,
                "actor": actor,
                "details": dict(details or {}),
            }
            entry_hash = _stable_hash(payload, previous_hash)
            entry = AuditEntry(
                **payload,
                previous_hash=previous_hash,
                entry_hash=entry_hash,
            )
            self._entries.append(entry)
            return entry

    # -------------------------------------------------------------------- read

    def all(self) -> list[AuditEntry]:
        """Return a shallow copy of the chain (entries themselves are frozen)."""

        with self._lock:
            return list(self._entries)

    def for_ticket(self, ticket_id: str) -> list[AuditEntry]:
        """Filter chain by ticket identifier."""

        with self._lock:
            return [e for e in self._entries if e.ticket_id == ticket_id]

    # ----------------------------------------------------------- verification

    def verify_chain(self) -> bool:
        """Verify hash chain integrity end-to-end.

        Returns ``True`` iff every entry's hash recomputes correctly *and*
        the ``previous_hash`` field of each entry matches the previous
        entry's ``entry_hash``.
        """

        with self._lock:
            previous = _GENESIS_HASH
            for entry in self._entries:
                if entry.previous_hash != previous:
                    return False
                if not entry.verify():
                    return False
                previous = entry.entry_hash
            return True

    def __len__(self) -> int:  # pragma: no cover — trivial
        return len(self._entries)
