"""initial schema for md-chat-ai

Creates every table owned by md-chat-ai in one revision:

  * users
  * phone_verifications
  * mfa_settings
  * pin_backups
  * everify_orders          (eEvidence Reg 2023/1543)
  * audit_entries           (hash-chained append-only register)
  * dsr_requests            (GDPR Art 15-22)
  * audit_trail_twin        (AI Act Art 50 + Art 22)

Greenfield deploy — no data migration. Subsequent revisions must be
additive only (one ALTER per concern); see migrations/README.md.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ---------------------------------------------------------------------------
# Helpers — portable type pickers.
# ---------------------------------------------------------------------------


def _uuid_type() -> sa.types.TypeEngine:
    """UUID on Postgres, CHAR(36) elsewhere."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.CHAR(36)


def _jsonb_type() -> sa.types.TypeEngine:
    """JSONB on Postgres, JSON elsewhere."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB()
    return sa.JSON()


def _string_array_type() -> sa.types.TypeEngine:
    """TEXT[] on Postgres, JSON elsewhere."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.ARRAY(sa.String())
    return sa.JSON()


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    uuid_t = _uuid_type()
    jsonb_t = _jsonb_type()
    strarr_t = _string_array_type()

    # ----- users ----------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", uuid_t, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("phone_hash", sa.String(128), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pin_set", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("evo_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delete_scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delete_reason", sa.String(255), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_phone_hash", "users", ["phone_hash"])
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])
    if _is_postgres():
        op.create_index(
            "ix_users_created_at_brin", "users", ["created_at"], postgresql_using="brin"
        )

    # ----- phone_verifications -------------------------------------------
    op.create_table(
        "phone_verifications",
        sa.Column("id", uuid_t, primary_key=True),
        sa.Column(
            "user_id",
            uuid_t,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phone_e164_hash", sa.String(128), nullable=False),
        sa.Column("code_hash", sa.String(128), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_phone_verifications_user_id", "phone_verifications", ["user_id"])
    op.create_index(
        "ix_phone_verifications_phone_e164_hash",
        "phone_verifications",
        ["phone_e164_hash"],
    )
    op.create_index("ix_phone_verifications_expires", "phone_verifications", ["expires_at"])
    if _is_postgres():
        op.create_index(
            "ix_phone_verifications_created_brin",
            "phone_verifications",
            ["created_at"],
            postgresql_using="brin",
        )

    # ----- mfa_settings ---------------------------------------------------
    op.create_table(
        "mfa_settings",
        sa.Column("id", uuid_t, primary_key=True),
        sa.Column(
            "user_id",
            uuid_t,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("totp_secret_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("backup_codes_hashes", strarr_t, nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ----- pin_backups ----------------------------------------------------
    op.create_table(
        "pin_backups",
        sa.Column("id", uuid_t, primary_key=True),
        sa.Column(
            "user_id",
            uuid_t,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("wrapped_keys_blob", sa.LargeBinary(), nullable=False),
        sa.Column("argon_params", jsonb_t, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pin_backups_user_id", "pin_backups", ["user_id"])
    if _is_postgres():
        op.create_index(
            "ix_pin_backups_argon_gin", "pin_backups", ["argon_params"], postgresql_using="gin"
        )

    # ----- everify_orders -------------------------------------------------
    everify_urgency = sa.Enum(
        "standard", "expedited_8h", "emergency_6h", name="everify_urgency"
    )
    everify_status = sa.Enum(
        "received",
        "under_review",
        "responded",
        "refused",
        "expired",
        name="everify_order_status",
    )
    if _is_postgres():
        everify_urgency.create(op.get_bind(), checkfirst=True)
        everify_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "everify_orders",
        sa.Column("id", uuid_t, primary_key=True),
        sa.Column("ticket_id", sa.String(128), nullable=False, unique=True),
        sa.Column("issuing_authority", sa.String(255), nullable=False),
        sa.Column("member_state", sa.String(2), nullable=False),
        sa.Column("target_identifier_hash", sa.String(128), nullable=False),
        sa.Column("urgency", everify_urgency, nullable=False, server_default="standard"),
        sa.Column("status", everify_status, nullable=False, server_default="received"),
        sa.Column("legal_basis", sa.Text(), nullable=True),
        sa.Column("payload", jsonb_t, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_everify_orders_target_identifier_hash",
        "everify_orders",
        ["target_identifier_hash"],
    )
    op.create_index("ix_everify_orders_status", "everify_orders", ["status"])
    op.create_index("ix_everify_orders_member_state", "everify_orders", ["member_state"])
    if _is_postgres():
        op.create_index(
            "ix_everify_orders_created_brin",
            "everify_orders",
            ["created_at"],
            postgresql_using="brin",
        )
        op.create_index(
            "ix_everify_orders_payload_gin",
            "everify_orders",
            ["payload"],
            postgresql_using="gin",
        )

    # ----- audit_entries --------------------------------------------------
    op.create_table(
        "audit_entries",
        sa.Column(
            "sequence_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("current_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("actor", sa.String(255), nullable=True),
        sa.Column("payload_json", jsonb_t, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_entries_event_type", "audit_entries", ["event_type"])
    if _is_postgres():
        op.create_index(
            "ix_audit_entries_created_brin",
            "audit_entries",
            ["created_at"],
            postgresql_using="brin",
        )
        op.create_index(
            "ix_audit_entries_payload_gin",
            "audit_entries",
            ["payload_json"],
            postgresql_using="gin",
        )

    # ----- dsr_requests ---------------------------------------------------
    dsr_type = sa.Enum(
        "access",
        "rectification",
        "erasure",
        "restriction",
        "portability",
        "objection",
        "automated_decision",
        name="dsr_request_type",
    )
    dsr_status = sa.Enum(
        "pending",
        "in_progress",
        "completed",
        "rejected",
        "extended",
        name="dsr_request_status",
    )
    if _is_postgres():
        dsr_type.create(op.get_bind(), checkfirst=True)
        dsr_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "dsr_requests",
        sa.Column("id", uuid_t, primary_key=True),
        sa.Column(
            "user_id",
            uuid_t,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("request_type", dsr_type, nullable=False),
        sa.Column("status", dsr_status, nullable=False, server_default="pending"),
        sa.Column("requester_email", sa.String(320), nullable=True),
        sa.Column("details", jsonb_t, nullable=True),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dsr_requests_user_id", "dsr_requests", ["user_id"])
    op.create_index("ix_dsr_requests_status", "dsr_requests", ["status"])
    if _is_postgres():
        op.create_index(
            "ix_dsr_requests_created_brin",
            "dsr_requests",
            ["created_at"],
            postgresql_using="brin",
        )
        op.create_index(
            "ix_dsr_requests_details_gin",
            "dsr_requests",
            ["details"],
            postgresql_using="gin",
        )

    # ----- audit_trail_twin -----------------------------------------------
    op.create_table(
        "audit_trail_twin",
        sa.Column("id", uuid_t, primary_key=True),
        sa.Column(
            "user_id",
            uuid_t,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("twin_id", sa.String(128), nullable=False),
        sa.Column("synapse_event_id", sa.String(255), nullable=True),
        sa.Column("disclosure_shown", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("disclosure_locale", sa.String(8), nullable=False, server_default="ro"),
        sa.Column(
            "automated_decision", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("input_fingerprint", sa.String(128), nullable=True),
        sa.Column("output_fingerprint", sa.String(128), nullable=True),
        sa.Column("model_id", sa.String(128), nullable=True),
        sa.Column("metadata_json", jsonb_t, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("synapse_event_id", name="uq_audit_trail_twin_event_id"),
    )
    op.create_index("ix_audit_trail_twin_user_id", "audit_trail_twin", ["user_id"])
    op.create_index("ix_audit_trail_twin_twin_id", "audit_trail_twin", ["twin_id"])
    if _is_postgres():
        op.create_index(
            "ix_audit_trail_twin_created_brin",
            "audit_trail_twin",
            ["created_at"],
            postgresql_using="brin",
        )
        op.create_index(
            "ix_audit_trail_twin_metadata_gin",
            "audit_trail_twin",
            ["metadata_json"],
            postgresql_using="gin",
        )


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    op.drop_table("audit_trail_twin")
    op.drop_table("dsr_requests")
    op.drop_table("audit_entries")
    op.drop_table("everify_orders")
    op.drop_table("pin_backups")
    op.drop_table("mfa_settings")
    op.drop_table("phone_verifications")
    op.drop_table("users")
    if _is_postgres():
        bind = op.get_bind()
        sa.Enum(name="dsr_request_status").drop(bind, checkfirst=True)
        sa.Enum(name="dsr_request_type").drop(bind, checkfirst=True)
        sa.Enum(name="everify_order_status").drop(bind, checkfirst=True)
        sa.Enum(name="everify_urgency").drop(bind, checkfirst=True)
