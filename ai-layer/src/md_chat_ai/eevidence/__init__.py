"""eEvidence Regulation (EU 2023/1543) production-order portal.

Provides the 24/7 intake portal that Article 7 of the eEvidence Regulation
requires every service provider offering services in the EU to operate.

Operative obligations covered here:

- **Article 4**  — designation of an addressee for receiving European
  Production Orders (EPOC) and European Preservation Orders (EPOC-PR).
- **Article 7**  — service providers' obligation to receive orders at any time
  and from any Member State; the portal accepts machine-readable JSON forms in
  addition to the official decentralised IT system once it is available.
- **Article 9**  — preservation orders (60-day default, renewable once).
- **Article 10** — production-order execution deadlines: 10 days standard,
  **8 hours** for emergency cases threatening life or critical infrastructure.
- **Article 12** — refusal grounds (manifestly extraterritorial reach,
  fundamental-rights violation, immunities/privileges, etc.). Triage is
  implemented in :mod:`md_chat_ai.eevidence.triage`.
- **Article 28** — confidentiality obligations toward the user (notification
  delay where the issuing authority requests it).
- **Article 31** — internal logging of every order received.
- **Article 33(5) GDPR / Art. 31 eEvidence** — append-only audit register;
  see :mod:`md_chat_ai.eevidence.audit`.

Operational runbook: ``docs/eevidence-runbook.md``.

The portal is licensed under Apache License 2.0 (SPDX-License-Identifier:
Apache-2.0) as the rest of the MD-Chat AI organising layer.
"""

from __future__ import annotations

from .audit import AuditEntry, AuditRegister
from .portal import (
    OrderResponse,
    OrderTicket,
    PreservationOrder,
    ProductionOrder,
    ProductionOrderPortal,
    TicketStatus,
)
from .triage import RefusalGround, TriageDecision, triage_order

__all__ = [
    "AuditEntry",
    "AuditRegister",
    "OrderResponse",
    "OrderTicket",
    "PreservationOrder",
    "ProductionOrder",
    "ProductionOrderPortal",
    "RefusalGround",
    "TicketStatus",
    "TriageDecision",
    "triage_order",
]
