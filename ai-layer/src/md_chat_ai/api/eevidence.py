"""Flask blueprint exposing the eEvidence intake portal.

Endpoints
=========

Public-ish (used by issuing authorities — front of Cloudflare + WAF):

* ``POST /api/v1/legal/eevidence/submit``            — submit an EPOC.
* ``POST /api/v1/legal/eevidence/submit/emergency``  — submit + emergency flag.
* ``POST /api/v1/legal/eevidence/submit/preservation`` — submit an EPOC-PR.
* ``GET  /api/v1/legal/eevidence/ticket/<ticket_id>`` — opaque status look-up.

Internal (require ``X-MDChat-Internal-Token`` header matching
``$EEVIDENCE_INTERNAL_TOKEN``):

* ``POST /api/v1/legal/eevidence/respond``            — close ticket.
* ``POST /api/v1/legal/eevidence/emergency-mark``     — promote to emergency.
* ``GET  /api/v1/legal/eevidence/register/open``      — dashboard, open tickets.
* ``GET  /api/v1/legal/eevidence/register``           — full audit chain.

The blueprint MUST be registered on the Flask app — see runbook section
"Blueprint registration TODO".

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import os
from functools import wraps
from typing import Any, Callable

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from ..eevidence.portal import (
    DEFAULT_PORTAL,
    OrderResponse,
    PreservationOrder,
    ProductionOrder,
    ProductionOrderPortal,
)

bp = Blueprint("eevidence", __name__)


# -------------------------------------------------------- portal injection

_PORTAL: ProductionOrderPortal = DEFAULT_PORTAL


def set_portal(portal: ProductionOrderPortal) -> None:
    """Replace the active portal — used by tests and by the Flask factory."""

    global _PORTAL
    _PORTAL = portal


def _portal() -> ProductionOrderPortal:
    return _PORTAL


# -------------------------------------------------------- auth decorator


def _expected_token() -> str:
    return os.getenv("EEVIDENCE_INTERNAL_TOKEN", "")


def require_internal_token(func: Callable[..., Any]) -> Callable[..., Any]:
    """Reject requests missing or mismatched on the internal-only header."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        expected = _expected_token()
        if not expected:
            return (
                jsonify(
                    {
                        "error": "internal_token_not_configured",
                        "message": "EEVIDENCE_INTERNAL_TOKEN must be set in production.",
                    }
                ),
                503,
            )
        provided = request.headers.get("X-MDChat-Internal-Token", "")
        # Constant-time comparison to avoid timing oracles.
        import hmac

        if not hmac.compare_digest(provided, expected):
            return jsonify({"error": "unauthorized"}), 401
        return func(*args, **kwargs)

    return wrapper


# ------------------------------------------------------- helper responders


def _validation_error(exc: ValidationError):
    return (
        jsonify(
            {
                "error": "validation_failed",
                "details": exc.errors(include_url=False),
            }
        ),
        422,
    )


def _ticket_view(ticket) -> dict[str, Any]:
    return ticket.to_dict()


# ===================================================================== ROUTES


@bp.post("/v1/legal/eevidence/submit")
def submit():
    """Submit a standard / expedited production order."""

    raw = request.get_json(silent=True) or {}
    try:
        order = ProductionOrder.model_validate(raw)
    except ValidationError as exc:
        return _validation_error(exc)
    ticket = _portal().submit(order)
    return jsonify({"ticket": _ticket_view(ticket)}), 201


@bp.post("/v1/legal/eevidence/submit/emergency")
def submit_emergency():
    """Submit a production order and immediately set the 8-hour SLA timer."""

    raw = request.get_json(silent=True) or {}
    # Force the urgency_level field so we never accept emergency-grade orders
    # without explicit acknowledgement from the requester.
    raw = {**raw, "urgency_level": "emergency"}
    try:
        order = ProductionOrder.model_validate(raw)
    except ValidationError as exc:
        return _validation_error(exc)
    ticket = _portal().submit(order)
    return jsonify({"ticket": _ticket_view(ticket)}), 201


@bp.post("/v1/legal/eevidence/submit/preservation")
def submit_preservation():
    """Submit an EPOC-PR (Art. 9)."""

    raw = request.get_json(silent=True) or {}
    try:
        order = PreservationOrder.model_validate(raw)
    except ValidationError as exc:
        return _validation_error(exc)
    ticket = _portal().submit_preservation(order)
    return jsonify({"ticket": _ticket_view(ticket)}), 201


@bp.get("/v1/legal/eevidence/ticket/<ticket_id>")
def get_ticket(ticket_id: str):
    """Status look-up for the issuing authority.

    Returns a sanitised view: the payload itself is NOT included to avoid
    leaking case details over a public endpoint. Authorities authenticate the
    ticket through the case_reference / contact_email on file.
    """

    ticket = _portal().get(ticket_id)
    if ticket is None:
        return jsonify({"error": "not_found"}), 404
    view = ticket.to_dict()
    # Strip sensitive payload from the public view.
    view.pop("payload", None)
    return jsonify({"ticket": view}), 200


@bp.post("/v1/legal/eevidence/respond")
@require_internal_token
def respond():
    """Operator endpoint — closes a ticket with a response."""

    raw = request.get_json(silent=True) or {}
    ticket_id = raw.get("ticket_id")
    if not ticket_id:
        return jsonify({"error": "ticket_id_required"}), 400
    try:
        response = OrderResponse.model_validate(raw.get("response") or {})
    except ValidationError as exc:
        return _validation_error(exc)
    try:
        ticket = _portal().respond(ticket_id, response)
    except KeyError:
        return jsonify({"error": "not_found"}), 404
    except RuntimeError as exc:
        return jsonify({"error": "conflict", "message": str(exc)}), 409
    return jsonify({"ticket": _ticket_view(ticket)}), 200


@bp.post("/v1/legal/eevidence/emergency-mark")
@require_internal_token
def emergency_mark():
    """Operator endpoint — promote an existing ticket to emergency."""

    raw = request.get_json(silent=True) or {}
    ticket_id = raw.get("ticket_id")
    justification = raw.get("justification", "")
    if not ticket_id:
        return jsonify({"error": "ticket_id_required"}), 400
    try:
        ticket = _portal().mark_emergency(ticket_id, justification)
    except KeyError:
        return jsonify({"error": "not_found"}), 404
    except ValueError as exc:
        return jsonify({"error": "validation_failed", "message": str(exc)}), 422
    except RuntimeError as exc:
        return jsonify({"error": "conflict", "message": str(exc)}), 409
    return jsonify({"ticket": _ticket_view(ticket)}), 200


@bp.get("/v1/legal/eevidence/register/open")
@require_internal_token
def register_open():
    """Internal dashboard — list of open tickets."""

    tickets = _portal().list_open()
    return jsonify({"open_tickets": [t.to_dict() for t in tickets]}), 200


@bp.get("/v1/legal/eevidence/register")
@require_internal_token
def register_full():
    """Internal — return entire audit chain + chain validity check."""

    audit = _portal().audit
    return (
        jsonify(
            {
                "chain_valid": audit.verify_chain(),
                "entries": [e.to_dict() for e in audit.all()],
            }
        ),
        200,
    )
