"""ORM models for md-chat-ai persistence.

Schema scope
------------
This schema owns ONLY md-chat-ai concerns:

* Identity / auth (users, phone verification, MFA, PIN backup)
* eEvidence Reg 2023/1543 incoming production orders
* GDPR Art 15-22 Data Subject Requests
* Tamper-evident audit register (hash-chained) — internal admin actions
* Digital Twin audit trail (AI Act Art 50 disclosures, Art 22 automated decision logs)

Synapse owns its own Matrix database (rooms / events / devices / e2e keys).
These two databases are NEVER joined; cross-references use opaque IDs only.

Portability
-----------
All UUIDs go through :class:`md_chat_ai.db.base.GUID` (Postgres native UUID
in production, ``CHAR(36)`` on SQLite for tests). JSON columns use
:class:`md_chat_ai.db.base.JSONB` (Postgres JSONB, plain JSON on SQLite).
"""

from __future__ import annotations

import enum
import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from md_chat_ai.db.base import GUID, JSONB, Base, StringArray


def _utcnow() -> datetime:
    """Timezone-aware UTC now (avoid naive datetimes — SQLAlchemy 2.0 warns otherwise)."""
    return datetime.now(UTC)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EVerifyOrderStatus(str, enum.Enum):
    """eEvidence Reg 2023/1543 order lifecycle."""

    received = "received"
    under_review = "under_review"
    responded = "responded"
    refused = "refused"
    expired = "expired"


class EVerifyUrgency(str, enum.Enum):
    """Reg 2023/1543 Art 10 urgency tiers."""

    standard = "standard"
    expedited_8h = "expedited_8h"
    emergency_6h = "emergency_6h"


class DSRRequestType(str, enum.Enum):
    """GDPR Chapter III data-subject rights."""

    access = "access"            # Art 15
    rectification = "rectification"  # Art 16
    erasure = "erasure"          # Art 17
    restriction = "restriction"  # Art 18
    portability = "portability"  # Art 20
    objection = "objection"      # Art 21
    automated_decision = "automated_decision"  # Art 22


class DSRRequestStatus(str, enum.Enum):
    """Lifecycle for DSR ticket."""

    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    rejected = "rejected"
    extended = "extended"  # Art 12(3) extension to 90d


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class User(Base):
    """End user of MD-Chat. Phone is stored as scrypt hash only.

    Username uniqueness is enforced at the DB level. Soft delete via
    ``deleted_at`` lets us preserve audit chain references for the legal
    retention window without keeping personal data accessible.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    phone_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pin_set: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evo_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Soft delete (GDPR Art 17 — scheduled erasure with grace period for audit).
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delete_scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delete_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships — cascade-delete dependents when the user row is hard-deleted.
    phone_verifications: Mapped[list[PhoneVerification]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    mfa_settings: Mapped[MFASettings | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    pin_backups: Mapped[list[PINBackup]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    dsr_requests: Mapped[list[DSRRequest]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_users_created_at_brin", "created_at", postgresql_using="brin"),
        Index("ix_users_deleted_at", "deleted_at"),
    )


# ---------------------------------------------------------------------------
# PhoneVerification
# ---------------------------------------------------------------------------


class PhoneVerification(Base):
    """Pending phone-number verification challenge.

    Codes are stored as argon2/scrypt hashes; raw codes never touch disk.
    Rate-limit (max 5 attempts), TTL 10 min; rows expire and are pruned by
    a retention cron in ops.
    """

    __tablename__ = "phone_verifications"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phone_e164_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    user: Mapped[User] = relationship(back_populates="phone_verifications")

    __table_args__ = (
        Index("ix_phone_verifications_expires", "expires_at"),
        Index(
            "ix_phone_verifications_created_brin",
            "created_at",
            postgresql_using="brin",
        ),
    )


# ---------------------------------------------------------------------------
# MFASettings
# ---------------------------------------------------------------------------


class MFASettings(Base):
    """Per-user TOTP secret + backup codes.

    ``totp_secret_encrypted`` is sealed with a per-user KEK (key encryption key)
    derived from server master key + user salt. Backup codes are stored as
    one-way hashes; once consumed they are wiped from the list (or marked).
    """

    __tablename__ = "mfa_settings"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    totp_secret_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    backup_codes_hashes: Mapped[list[str]] = mapped_column(
        StringArray(), nullable=False, default=list
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    user: Mapped[User] = relationship(back_populates="mfa_settings")


# ---------------------------------------------------------------------------
# PINBackup
# ---------------------------------------------------------------------------


class PINBackup(Base):
    """PIN-wrapped E2E key backup (Synapse SSSS-style).

    ``wrapped_keys_blob`` is the user's cross-signing + megolm-session-key bundle
    encrypted with a KEK derived from the PIN via Argon2id. ``argon_params``
    stores the Argon2id parameters so we can verify on unlock without guessing.
    """

    __tablename__ = "pin_backups"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    wrapped_keys_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    argon_params: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    user: Mapped[User] = relationship(back_populates="pin_backups")

    __table_args__ = (
        Index("ix_pin_backups_argon_gin", "argon_params", postgresql_using="gin"),
    )


# ---------------------------------------------------------------------------
# EVerifyOrder — eEvidence Reg 2023/1543
# ---------------------------------------------------------------------------


class EVerifyOrder(Base):
    """Incoming production / preservation order under EU Reg 2023/1543.

    Captures the ticket as received, the issuing authority, the target user
    fingerprint (hash; never plaintext IDNP / phone in this table), urgency
    tier, lifecycle status, and timestamps. Full order payload is sealed in
    a separate object-store bucket; this row is the index.
    """

    __tablename__ = "everify_orders"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    ticket_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    issuing_authority: Mapped[str] = mapped_column(String(255), nullable=False)
    member_state: Mapped[str] = mapped_column(String(2), nullable=False)
    target_identifier_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    urgency: Mapped[EVerifyUrgency] = mapped_column(
        SAEnum(EVerifyUrgency, name="everify_urgency"),
        nullable=False,
        default=EVerifyUrgency.standard,
    )
    status: Mapped[EVerifyOrderStatus] = mapped_column(
        SAEnum(EVerifyOrderStatus, name="everify_order_status"),
        nullable=False,
        default=EVerifyOrderStatus.received,
    )
    legal_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_everify_orders_status", "status"),
        Index("ix_everify_orders_member_state", "member_state"),
        Index(
            "ix_everify_orders_created_brin", "created_at", postgresql_using="brin"
        ),
        Index("ix_everify_orders_payload_gin", "payload", postgresql_using="gin"),
    )


# ---------------------------------------------------------------------------
# AuditEntry — hash-chained tamper-evident log.
# ---------------------------------------------------------------------------


class AuditEntry(Base):
    """Tamper-evident audit register.

    Each row stores:
      * ``sequence_id`` — monotonically increasing 64-bit counter (Postgres
        sequence in prod; SQLite autoincrement INTEGER PK in tests).
      * ``prev_hash`` — the ``current_hash`` of the entry immediately
        preceding this one (or 64 zeros for the genesis row).
      * ``current_hash`` — ``sha256(prev_hash || sequence_id || event_type
        || canonical_json(payload_json) || created_at_iso)``.

    Use :meth:`compute_hash` to derive the hash deterministically. Use
    :meth:`append` (static helper) to insert with chain integrity preserved.
    """

    __tablename__ = "audit_entries"

    # BigInteger on Postgres for capacity headroom; Integer on SQLite because
    # only ``INTEGER PRIMARY KEY`` triggers SQLite's rowid autoincrement alias.
    sequence_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        Index(
            "ix_audit_entries_created_brin", "created_at", postgresql_using="brin"
        ),
        Index("ix_audit_entries_payload_gin", "payload_json", postgresql_using="gin"),
    )

    GENESIS_HASH: str = "0" * 64

    @staticmethod
    def _canonical_payload(payload: dict[str, Any]) -> str:
        import json

        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    @classmethod
    def compute_hash(
        cls,
        *,
        prev_hash: str,
        sequence_id: int,
        event_type: str,
        payload: dict[str, Any],
        created_at: datetime,
    ) -> str:
        """Deterministic chain hash. Mirrors verifier in ops/."""
        canon = cls._canonical_payload(payload)
        material = "|".join(
            [
                prev_hash,
                str(sequence_id),
                event_type,
                canon,
                created_at.isoformat(),
            ]
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    @classmethod
    def append(
        cls,
        session: Any,
        *,
        event_type: str,
        payload: dict[str, Any],
        actor: str | None = None,
    ) -> AuditEntry:
        """Append a new audit row, linking to the tip of the chain.

        The caller is responsible for the surrounding transaction; this method
        flushes (but does not commit) so the assigned ``sequence_id`` is
        materialized before hashing.
        """
        from sqlalchemy import select

        # Find the current tip — highest sequence_id, if any.
        tip = session.execute(
            select(cls).order_by(cls.sequence_id.desc()).limit(1)
        ).scalar_one_or_none()
        prev_hash = tip.current_hash if tip is not None else cls.GENESIS_HASH

        created_at = _utcnow()
        # Insert with placeholder hash so the autoincrement assigns sequence_id.
        row = cls(
            prev_hash=prev_hash,
            current_hash="x" * 64,  # placeholder; overwritten before commit
            event_type=event_type,
            actor=actor,
            payload_json=payload,
            created_at=created_at,
        )
        session.add(row)
        session.flush()

        row.current_hash = cls.compute_hash(
            prev_hash=prev_hash,
            sequence_id=row.sequence_id,
            event_type=event_type,
            payload=payload,
            created_at=created_at,
        )
        session.flush()
        return row


# ---------------------------------------------------------------------------
# DSRRequest — GDPR Art 15-22
# ---------------------------------------------------------------------------


class DSRRequest(Base):
    """Data Subject Request ticket (GDPR Art 15-22)."""

    __tablename__ = "dsr_requests"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request_type: Mapped[DSRRequestType] = mapped_column(
        SAEnum(DSRRequestType, name="dsr_request_type"), nullable=False
    )
    status: Mapped[DSRRequestStatus] = mapped_column(
        SAEnum(DSRRequestStatus, name="dsr_request_status"),
        nullable=False,
        default=DSRRequestStatus.pending,
    )
    requester_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    user: Mapped[User | None] = relationship(back_populates="dsr_requests")

    __table_args__ = (
        Index("ix_dsr_requests_status", "status"),
        Index(
            "ix_dsr_requests_created_brin", "created_at", postgresql_using="brin"
        ),
        Index("ix_dsr_requests_details_gin", "details", postgresql_using="gin"),
    )


# ---------------------------------------------------------------------------
# AuditTrailTwin — Digital Twin AI Act Art 50 + Art 22 log.
# ---------------------------------------------------------------------------


class AuditTrailTwin(Base):
    """Per-interaction audit log for the Digital Twin / Kallina AI agents.

    Each row records: who interacted, which twin/agent, the disclosure shown
    (Art 50), whether the decision was automated (Art 22), and the input/output
    fingerprints (NOT plaintext). Plaintext lives in the chat history (Synapse)
    and is referenced by opaque event_id.
    """

    __tablename__ = "audit_trail_twin"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    twin_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    synapse_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    disclosure_shown: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    disclosure_locale: Mapped[str] = mapped_column(String(8), nullable=False, default="ro")
    automated_decision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    input_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    output_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("synapse_event_id", name="uq_audit_trail_twin_event_id"),
        Index(
            "ix_audit_trail_twin_created_brin", "created_at", postgresql_using="brin"
        ),
        Index(
            "ix_audit_trail_twin_metadata_gin",
            "metadata_json",
            postgresql_using="gin",
        ),
    )


__all__ = [
    "EVerifyOrderStatus",
    "EVerifyUrgency",
    "DSRRequestType",
    "DSRRequestStatus",
    "User",
    "PhoneVerification",
    "MFASettings",
    "PINBackup",
    "EVerifyOrder",
    "AuditEntry",
    "DSRRequest",
    "AuditTrailTwin",
]


# Silence unused-import warnings while keeping ``text`` available for future
# migrations / data-fixup scripts.
_ = text
