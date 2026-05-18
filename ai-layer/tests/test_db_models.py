"""Schema + relationship tests for md_chat_ai.db.

Strategy: every test runs against a fresh sqlite ``:memory:`` engine to keep
the suite hermetic. Postgres-specific column types (UUID, JSONB, BRIN/GIN
indexes) gracefully degrade on SQLite via the TypeDecorators in
``db.base`` — what we exercise here is shape + cascade behaviour, not
dialect-specific features.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from md_chat_ai.db import (
    AuditEntry,
    AuditTrailTwin,
    Base,
    DSRRequest,
    EVerifyOrder,
    MFASettings,
    PhoneVerification,
    PINBackup,
    User,
    dispose_engine,
    get_engine,
)
from md_chat_ai.db.models import (
    DSRRequestStatus,
    DSRRequestType,
    EVerifyOrderStatus,
    EVerifyUrgency,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine() -> Iterator[Engine]:
    """Fresh in-memory SQLite engine with all tables created."""
    eng = get_engine(dsn="sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    dispose_engine()


@pytest.fixture()
def session(engine: Engine) -> Iterator[Session]:
    sm = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = sm()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def user(session: Session) -> User:
    u = User(
        username="alice",
        phone_hash="scrypt$placeholder$" + "0" * 64,
        email="alice@example.com",
    )
    session.add(u)
    session.commit()
    return u


# ---------------------------------------------------------------------------
# Engine + schema sanity
# ---------------------------------------------------------------------------


def test_engine_creates_all_tables(engine: Engine) -> None:
    """All 8 owned tables exist after metadata.create_all()."""
    expected = {
        "users",
        "phone_verifications",
        "mfa_settings",
        "pin_backups",
        "everify_orders",
        "audit_entries",
        "dsr_requests",
        "audit_trail_twin",
    }
    actual = set(inspect(engine).get_table_names())
    assert expected.issubset(actual), f"Missing: {expected - actual}"


def test_user_has_required_fields(engine: Engine) -> None:
    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    required = {
        "id",
        "username",
        "phone_hash",
        "email",
        "created_at",
        "updated_at",
        "mfa_enabled",
        "pin_set",
        "evo_verified",
        "deleted_at",
        "delete_scheduled_at",
        "delete_reason",
    }
    assert required.issubset(cols)


def test_user_username_unique(session: Session) -> None:
    session.add(User(username="bob", phone_hash="h1"))
    session.commit()
    session.add(User(username="bob", phone_hash="h2"))
    with pytest.raises(Exception):  # IntegrityError on unique constraint
        session.commit()
    session.rollback()


def test_user_uuid_primary_key(user: User) -> None:
    assert isinstance(user.id, uuid.UUID)


def test_timestamps_populated(user: User) -> None:
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)


# ---------------------------------------------------------------------------
# Relationship cascade
# ---------------------------------------------------------------------------


def test_cascade_deletes_phone_verifications(session: Session, user: User) -> None:
    pv = PhoneVerification(
        user_id=user.id,
        phone_e164_hash="h-+37360000000",
        code_hash="h-code",
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    session.add(pv)
    session.commit()
    assert session.execute(select(PhoneVerification)).scalars().first() is not None

    session.delete(user)
    session.commit()
    assert session.execute(select(PhoneVerification)).scalars().first() is None


def test_cascade_deletes_mfa(session: Session, user: User) -> None:
    mfa = MFASettings(
        user_id=user.id,
        totp_secret_encrypted=b"\x00" * 32,
        backup_codes_hashes=["h1", "h2"],
    )
    session.add(mfa)
    session.commit()
    assert session.execute(select(MFASettings)).scalars().first() is not None

    session.delete(user)
    session.commit()
    assert session.execute(select(MFASettings)).scalars().first() is None


def test_cascade_deletes_pin_backup(session: Session, user: User) -> None:
    pb = PINBackup(
        user_id=user.id,
        wrapped_keys_blob=b"\x01\x02\x03",
        argon_params={"t": 3, "m": 65536, "p": 4},
    )
    session.add(pb)
    session.commit()
    assert session.execute(select(PINBackup)).scalars().first() is not None

    session.delete(user)
    session.commit()
    assert session.execute(select(PINBackup)).scalars().first() is None


def test_mfa_per_user_unique(session: Session, user: User) -> None:
    """A user can have only one MFASettings row (unique on user_id)."""
    session.add(MFASettings(user_id=user.id, totp_secret_encrypted=b"a", backup_codes_hashes=[]))
    session.commit()
    session.add(MFASettings(user_id=user.id, totp_secret_encrypted=b"b", backup_codes_hashes=[]))
    with pytest.raises(Exception):
        session.commit()
    session.rollback()


# ---------------------------------------------------------------------------
# eEvidence orders
# ---------------------------------------------------------------------------


def test_everify_order_roundtrip(session: Session) -> None:
    o = EVerifyOrder(
        ticket_id="EU-2026-001",
        issuing_authority="Tribunal de Paris",
        member_state="FR",
        target_identifier_hash="h" + "0" * 63,
        urgency=EVerifyUrgency.expedited_8h,
        status=EVerifyOrderStatus.received,
        payload={"crime_type": "fraud", "art": "Art 3 Reg 2023/1543"},
    )
    session.add(o)
    session.commit()
    loaded = session.execute(select(EVerifyOrder)).scalar_one()
    assert loaded.ticket_id == "EU-2026-001"
    assert loaded.urgency == EVerifyUrgency.expedited_8h
    assert loaded.payload == {"crime_type": "fraud", "art": "Art 3 Reg 2023/1543"}


def test_everify_ticket_id_unique(session: Session) -> None:
    o1 = EVerifyOrder(
        ticket_id="DUP-001",
        issuing_authority="X",
        member_state="DE",
        target_identifier_hash="h",
    )
    session.add(o1)
    session.commit()
    session.add(
        EVerifyOrder(
            ticket_id="DUP-001",
            issuing_authority="Y",
            member_state="DE",
            target_identifier_hash="h2",
        )
    )
    with pytest.raises(Exception):
        session.commit()
    session.rollback()


# ---------------------------------------------------------------------------
# Audit chain integrity
# ---------------------------------------------------------------------------


def test_audit_chain_first_entry_uses_genesis_hash(session: Session) -> None:
    e = AuditEntry.append(
        session, event_type="user.created", payload={"id": "u-1"}, actor="system"
    )
    session.commit()
    assert e.prev_hash == AuditEntry.GENESIS_HASH
    assert len(e.current_hash) == 64
    assert e.sequence_id >= 1


def test_audit_chain_links_sequential(session: Session) -> None:
    e1 = AuditEntry.append(session, event_type="evt.a", payload={"n": 1})
    e2 = AuditEntry.append(session, event_type="evt.b", payload={"n": 2})
    e3 = AuditEntry.append(session, event_type="evt.c", payload={"n": 3})
    session.commit()

    assert e1.sequence_id < e2.sequence_id < e3.sequence_id
    assert e2.prev_hash == e1.current_hash
    assert e3.prev_hash == e2.current_hash


def test_audit_chain_hash_is_deterministic(session: Session) -> None:
    e = AuditEntry.append(session, event_type="evt.x", payload={"foo": "bar"})
    session.commit()

    recomputed = AuditEntry.compute_hash(
        prev_hash=e.prev_hash,
        sequence_id=e.sequence_id,
        event_type=e.event_type,
        payload=e.payload_json,
        created_at=e.created_at,
    )
    assert recomputed == e.current_hash


def test_audit_chain_detects_tamper(session: Session) -> None:
    """If anyone mutates payload_json, recomputed hash != stored hash."""
    e = AuditEntry.append(session, event_type="evt.x", payload={"foo": "bar"})
    session.commit()

    tampered = AuditEntry.compute_hash(
        prev_hash=e.prev_hash,
        sequence_id=e.sequence_id,
        event_type=e.event_type,
        payload={"foo": "EVIL"},
        created_at=e.created_at,
    )
    assert tampered != e.current_hash


def test_audit_current_hash_unique(session: Session) -> None:
    """Two entries must never share a current_hash."""
    e1 = AuditEntry.append(session, event_type="x", payload={"a": 1})
    e2 = AuditEntry.append(session, event_type="x", payload={"a": 2})
    session.commit()
    assert e1.current_hash != e2.current_hash


# ---------------------------------------------------------------------------
# DSR + Audit Trail Twin
# ---------------------------------------------------------------------------


def test_dsr_request_roundtrip(session: Session, user: User) -> None:
    r = DSRRequest(
        user_id=user.id,
        request_type=DSRRequestType.access,
        status=DSRRequestStatus.pending,
        requester_email="alice@example.com",
        details={"channel": "email", "ip": "192.0.2.1"},
        sla_due_at=datetime.now(UTC) + timedelta(days=30),
    )
    session.add(r)
    session.commit()
    loaded = session.execute(select(DSRRequest)).scalar_one()
    assert loaded.request_type == DSRRequestType.access
    assert loaded.status == DSRRequestStatus.pending
    assert loaded.details == {"channel": "email", "ip": "192.0.2.1"}


def test_dsr_request_user_setnull_on_user_delete(session: Session, user: User) -> None:
    """When the user is hard-deleted, dsr_requests survive with user_id=NULL.

    GDPR Art 17 — we keep the ticket trail for accountability, but unlink the
    identifier so PII is purged.
    """
    r = DSRRequest(user_id=user.id, request_type=DSRRequestType.erasure)
    session.add(r)
    session.commit()

    # Detach the relationship cascade explicitly: dsr_requests is configured
    # with cascade="all, delete-orphan" on the ORM side, but the FK uses
    # ON DELETE SET NULL. Direct ORM delete cascades; to test SET NULL we
    # do a raw delete that bypasses the ORM cascade.
    from sqlalchemy import delete

    session.execute(delete(User).where(User.id == user.id))
    session.commit()
    session.expire_all()

    loaded = session.execute(select(DSRRequest)).scalar_one()
    assert loaded.user_id is None


def test_audit_trail_twin_unique_event_id(session: Session, user: User) -> None:
    t1 = AuditTrailTwin(
        user_id=user.id,
        twin_id="kallina-voice-v1",
        synapse_event_id="$event_1:msg.md-chat.eu",
        disclosure_locale="ro",
    )
    session.add(t1)
    session.commit()
    session.add(
        AuditTrailTwin(
            user_id=user.id,
            twin_id="kallina-voice-v1",
            synapse_event_id="$event_1:msg.md-chat.eu",
        )
    )
    with pytest.raises(Exception):
        session.commit()
    session.rollback()


def test_audit_trail_twin_defaults(session: Session, user: User) -> None:
    t = AuditTrailTwin(user_id=user.id, twin_id="kallina-v1")
    session.add(t)
    session.commit()
    loaded = session.execute(select(AuditTrailTwin)).scalar_one()
    assert loaded.disclosure_shown is True
    assert loaded.disclosure_locale == "ro"
    assert loaded.automated_decision is False


# ---------------------------------------------------------------------------
# Soft-delete sanity
# ---------------------------------------------------------------------------


def test_user_soft_delete_fields_default_null(user: User) -> None:
    assert user.deleted_at is None
    assert user.delete_scheduled_at is None
    assert user.delete_reason is None
