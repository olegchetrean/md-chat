"""Intake portal for European Production / Preservation Orders.

Public entry-point: :class:`ProductionOrderPortal`. The portal is instance-
based so the Flask blueprint (and the test-suite) can construct independent
copies. A module-level *default* portal is exposed so the running app shares
state across requests; tests should always inject their own.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .audit import AuditRegister
from .triage import TriageDecision, triage_order

# -------------------------------------------------------------------- typing


UrgencyLevel = Literal["standard", "expedited", "emergency"]
DataCategory = Literal["subscriber", "traffic", "content"]
AuthorityType = Literal["judicial", "administrative", "prosecutor"]


# --------------------------------------------------------------- Pydantic IO


class ProductionOrder(BaseModel):
    """EU Production Order payload (Annex I EPOC, simplified for intake).

    Fields map directly to the boxes of the official EPOC form. Free-text
    description of the offence is kept short — full PDFs are referenced via
    :attr:`attachment_url` (signed S3-style links).
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    issuing_authority: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Full name of the issuing court / prosecutor's office.",
    )
    issuing_authority_type: AuthorityType = Field(
        ...,
        description="Authority type — administrative authorities cannot request "
        "traffic/content data without judicial validation.",
    )
    member_state: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="ISO-3166 alpha-2 code of the issuing EU Member State.",
    )
    target_identifier: str = Field(
        ...,
        min_length=1,
        max_length=320,
        description="MD-Chat user identifier (username / phone / email / matrix id).",
    )
    target_country: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=2,
        description="ISO-3166 alpha-2 of the country where the target is located, "
        "if known to the issuing authority.",
    )
    requested_data_category: DataCategory = Field(
        ...,
        description="One of subscriber / traffic / content.",
    )
    urgency_level: UrgencyLevel = Field(
        default="standard",
        description="standard (10 days), expedited (≤72 h voluntary), "
        "emergency (8 h, Art. 10(2)).",
    )
    legal_basis: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Cite the national criminal-procedure articles + offence.",
    )
    case_reference: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Case file reference at the issuing authority.",
    )
    subject_flags: list[str] = Field(
        default_factory=list,
        description="Free-form flags (e.g. 'lawyer', 'journalist', 'mep', 'minor'). "
        "Used by the triage to surface immunities / privileges.",
    )
    notification_deferral_requested: bool = Field(
        default=False,
        description="Art. 13 — if true and lawful, MD-Chat must not notify the user.",
    )
    contact_email: str = Field(
        ...,
        min_length=5,
        max_length=320,
        description="Operational contact of the issuing authority for clarifications.",
    )
    attachment_url: Optional[str] = Field(
        default=None,
        description="Signed link to the full EPOC PDF / structured XML.",
    )

    @field_validator("member_state", "target_country")
    @classmethod
    def _upper_country_code(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value


class PreservationOrder(BaseModel):
    """EU Preservation Order payload (Art. 9, Annex II EPOC-PR).

    Preservation is data-conservation only — no disclosure. A subsequent
    Production Order is required to obtain the preserved data.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    issuing_authority: str = Field(..., min_length=3, max_length=200)
    issuing_authority_type: AuthorityType
    member_state: str = Field(..., min_length=2, max_length=2)
    target_identifier: str = Field(..., min_length=1, max_length=320)
    case_reference: str = Field(..., min_length=1, max_length=120)
    legal_basis: str = Field(..., min_length=10, max_length=2000)
    duration_days: int = Field(
        default=60,
        ge=1,
        le=60,
        description="Art. 9(1): up to 60 days; renewable once for another 60 (Art. 9(6)).",
    )
    contact_email: str = Field(..., min_length=5, max_length=320)
    attachment_url: Optional[str] = None

    @field_validator("member_state")
    @classmethod
    def _upper_member_state(cls, value: str) -> str:
        return value.upper()


class OrderResponse(BaseModel):
    """Response sent back to the issuing authority."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    outcome: Literal["provided", "partial", "refused", "no_data"] = Field(
        ...,
        description="provided = full data set delivered; partial = subset only; "
        "refused = Art. 12 invoked; no_data = MD-Chat does not hold matching data.",
    )
    delivered_artifacts: list[str] = Field(
        default_factory=list,
        description="Identifiers / hashes of delivered files (encrypted at rest).",
    )
    refusal_grounds: list[str] = Field(
        default_factory=list,
        description="Refusal ground identifiers (see "
        ":class:`~md_chat_ai.eevidence.triage.RefusalGround`).",
    )
    rationale: str = Field(
        default="",
        max_length=4000,
        description="Free-text rationale to accompany the response.",
    )
    responder: str = Field(
        ...,
        min_length=3,
        max_length=120,
        description="Internal operator name + role (e.g. 'Oleg Chetrean / CEO').",
    )


# -------------------------------------------------------------- domain types


class TicketStatus(str, Enum):
    """Lifecycle of an intake ticket."""

    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    EMERGENCY = "emergency"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    RESPONDED = "responded"
    REFUSED = "refused"


@dataclass
class OrderTicket:
    """Lightweight container tracking an order through its lifecycle."""

    ticket_id: str
    received_at: datetime
    order_kind: Literal["production", "preservation"]
    payload: dict[str, Any]
    triage: TriageDecision
    status: TicketStatus = TicketStatus.RECEIVED
    sla_deadline: Optional[datetime] = None
    """Deadline after which the order is in SLA breach. Set on emergency
    marking or at ticket creation for standard orders (10 days, Art. 10(1))."""

    emergency_marked_at: Optional[datetime] = None
    emergency_justification: Optional[str] = None
    response: Optional[OrderResponse] = None
    responded_at: Optional[datetime] = None

    history: list[str] = field(default_factory=list)
    """Free-form lifecycle events, mirrored verbosely in the audit register."""

    # ------------------------------------------------------------ helpers

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "received_at": self.received_at.isoformat(),
            "order_kind": self.order_kind,
            "status": self.status.value,
            "sla_deadline": self.sla_deadline.isoformat() if self.sla_deadline else None,
            "emergency_marked_at": (
                self.emergency_marked_at.isoformat() if self.emergency_marked_at else None
            ),
            "emergency_justification": self.emergency_justification,
            "triage": {
                "should_refuse": self.triage.should_refuse,
                "grounds": [g.value for g in self.triage.grounds],
                "notes": list(self.triage.notes),
                "requires_human_review": self.triage.requires_human_review,
            },
            "history": list(self.history),
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "response": self.response.model_dump() if self.response else None,
        }


# ------------------------------------------------------------------ portal


def _generate_ticket_id() -> str:
    """Cryptographically random, human-typeable ticket ID."""

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = secrets.token_hex(4).upper()
    return f"EE-{stamp}-{suffix}"


def _redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``payload`` with the target identifier coarse-hashed.

    The audit register stores order metadata for years; storing raw target
    identifiers (e.g. phone numbers) would be disproportionate. We keep a
    short SHA-256 prefix to allow correlation with the case file held by the
    issuing authority without storing the plaintext.
    """

    import hashlib

    redacted = dict(payload)
    if (tid := redacted.get("target_identifier")) is not None:
        digest = hashlib.sha256(str(tid).encode("utf-8")).hexdigest()[:12]
        redacted["target_identifier"] = f"sha256:{digest}"
    return redacted


class ProductionOrderPortal:
    """Stateful intake portal for EU eEvidence orders.

    Thread-safe enough for Flask's default thread-pool: ticket allocation is
    serialised under a per-portal lock. The portal does not persist anything
    to disk — wiring to PostgreSQL is left for the operator (see runbook).
    """

    #: Default execution deadline for standard production orders (Art. 10(1)).
    STANDARD_DEADLINE = timedelta(days=10)

    #: Emergency execution deadline (Art. 10(2)).
    EMERGENCY_DEADLINE = timedelta(hours=8)

    def __init__(self, audit: Optional[AuditRegister] = None) -> None:
        import threading

        self._audit = audit or AuditRegister()
        self._tickets: dict[str, OrderTicket] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------ accessors

    @property
    def audit(self) -> AuditRegister:
        return self._audit

    # ----------------------------------------------------------- submission

    def submit(self, order: ProductionOrder) -> OrderTicket:
        """Accept an EPOC, run triage, assign ticket, log."""

        triage = triage_order(order)
        now = datetime.now(timezone.utc)
        deadline = now + self.STANDARD_DEADLINE
        if order.urgency_level == "emergency":
            deadline = now + self.EMERGENCY_DEADLINE

        with self._lock:
            ticket_id = _generate_ticket_id()
            ticket = OrderTicket(
                ticket_id=ticket_id,
                received_at=now,
                order_kind="production",
                payload=order.model_dump(),
                triage=triage,
                status=(
                    TicketStatus.EMERGENCY
                    if order.urgency_level == "emergency"
                    else TicketStatus.UNDER_REVIEW
                ),
                sla_deadline=deadline,
                emergency_marked_at=now if order.urgency_level == "emergency" else None,
            )
            ticket.history.append(f"received:{order.urgency_level}")
            if triage.should_refuse:
                ticket.history.append(
                    "triage:flagged:" + ",".join(g.value for g in triage.grounds)
                )
            self._tickets[ticket_id] = ticket

        self._audit.append(
            event_type="order_received",
            ticket_id=ticket.ticket_id,
            actor=f"portal:authority:{order.member_state}",
            details={
                "order_kind": "production",
                "urgency_level": order.urgency_level,
                "data_category": order.requested_data_category,
                "issuing_authority": order.issuing_authority,
                "issuing_authority_type": order.issuing_authority_type,
                "case_reference": order.case_reference,
                "payload": _redact_payload(order.model_dump()),
                "triage_flagged": triage.should_refuse,
                "triage_grounds": [g.value for g in triage.grounds],
                "sla_deadline": deadline.isoformat(),
            },
        )
        return ticket

    def submit_preservation(self, order: PreservationOrder) -> OrderTicket:
        """Accept an EPOC-PR (Art. 9)."""

        now = datetime.now(timezone.utc)
        with self._lock:
            ticket_id = _generate_ticket_id()
            ticket = OrderTicket(
                ticket_id=ticket_id,
                received_at=now,
                order_kind="preservation",
                payload=order.model_dump(),
                triage=TriageDecision(
                    should_refuse=False,
                    grounds=(),
                    notes=(
                        "Preservation only — no disclosure. Refusal grounds limited "
                        "to Art. 10(4) (manifestly unfounded).",
                    ),
                ),
                status=TicketStatus.UNDER_REVIEW,
                sla_deadline=now + timedelta(days=order.duration_days),
            )
            ticket.history.append(f"preservation_received:{order.duration_days}d")
            self._tickets[ticket_id] = ticket

        self._audit.append(
            event_type="preservation_received",
            ticket_id=ticket.ticket_id,
            actor=f"portal:authority:{order.member_state}",
            details={
                "order_kind": "preservation",
                "duration_days": order.duration_days,
                "issuing_authority": order.issuing_authority,
                "case_reference": order.case_reference,
                "payload": _redact_payload(order.model_dump()),
            },
        )
        return ticket

    # --------------------------------------------------------- emergency

    def mark_emergency(
        self,
        ticket_id: str,
        justification: str,
        *,
        actor: str = "operator:dpo",
    ) -> OrderTicket:
        """Promote a ticket to emergency status — starts the 8-hour SLA."""

        if not justification or len(justification.strip()) < 12:
            raise ValueError("emergency justification too short — needs >= 12 chars")
        now = datetime.now(timezone.utc)
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                raise KeyError(f"unknown ticket {ticket_id!r}")
            if ticket.status in {TicketStatus.RESPONDED, TicketStatus.REFUSED}:
                raise RuntimeError(
                    f"ticket {ticket_id} already closed with status {ticket.status.value}"
                )
            ticket.status = TicketStatus.EMERGENCY
            ticket.emergency_marked_at = now
            ticket.emergency_justification = justification.strip()
            ticket.sla_deadline = now + self.EMERGENCY_DEADLINE
            ticket.history.append("emergency_marked")

        self._audit.append(
            event_type="emergency_marked",
            ticket_id=ticket_id,
            actor=actor,
            details={
                "justification": justification.strip(),
                "new_deadline": ticket.sla_deadline.isoformat()
                if ticket.sla_deadline
                else None,
            },
        )
        return ticket

    # ---------------------------------------------------------- response

    def respond(
        self,
        ticket_id: str,
        response: OrderResponse,
        *,
        actor: Optional[str] = None,
    ) -> OrderTicket:
        """Close a ticket with the operator's response."""

        now = datetime.now(timezone.utc)
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                raise KeyError(f"unknown ticket {ticket_id!r}")
            if ticket.status in {TicketStatus.RESPONDED, TicketStatus.REFUSED}:
                raise RuntimeError(
                    f"ticket {ticket_id} already closed with status {ticket.status.value}"
                )
            ticket.response = response
            ticket.responded_at = now
            ticket.status = (
                TicketStatus.REFUSED if response.outcome == "refused" else TicketStatus.RESPONDED
            )
            ticket.history.append(f"responded:{response.outcome}")

        self._audit.append(
            event_type="order_refused" if response.outcome == "refused" else "order_responded",
            ticket_id=ticket_id,
            actor=actor or f"operator:{response.responder}",
            details={
                "outcome": response.outcome,
                "refusal_grounds": list(response.refusal_grounds),
                "delivered_artifacts": list(response.delivered_artifacts),
                "rationale_present": bool(response.rationale),
            },
        )
        return ticket

    # ----------------------------------------------------------- queries

    def get(self, ticket_id: str) -> Optional[OrderTicket]:
        with self._lock:
            return self._tickets.get(ticket_id)

    def list_open(self) -> list[OrderTicket]:
        """Tickets not yet closed (responded / refused)."""

        with self._lock:
            return [
                t
                for t in self._tickets.values()
                if t.status not in {TicketStatus.RESPONDED, TicketStatus.REFUSED}
            ]

    def list_all(self) -> list[OrderTicket]:
        with self._lock:
            return list(self._tickets.values())


# --------------------------------------------------------- module default

#: Application-wide default portal. Tests must inject their own instance via
#: :func:`md_chat_ai.api.eevidence.set_portal`. Do NOT mutate this directly.
DEFAULT_PORTAL: ProductionOrderPortal = ProductionOrderPortal()
