"""Tests for the eEvidence intake portal."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask

from md_chat_ai.api import eevidence as eevidence_api
from md_chat_ai.eevidence import (
    AuditRegister,
    OrderResponse,
    PreservationOrder,
    ProductionOrder,
    ProductionOrderPortal,
    RefusalGround,
    TicketStatus,
    triage_order,
)


# --------------------------------------------------------------- fixtures


def _good_payload(**overrides):
    base = {
        "issuing_authority": "Tribunalul Bucuresti, Sectia Penala",
        "issuing_authority_type": "judicial",
        "member_state": "RO",
        "target_identifier": "alice@md-chat.eu",
        "target_country": "RO",
        "requested_data_category": "subscriber",
        "urgency_level": "standard",
        "legal_basis": "Cod proc. pen. art. 152 — frauda informatica",
        "case_reference": "4321/3/2026",
        "subject_flags": [],
        "contact_email": "epoc.dgcc@just.ro",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def portal() -> ProductionOrderPortal:
    return ProductionOrderPortal()


@pytest.fixture()
def app(portal):
    flask_app = Flask(__name__)
    flask_app.register_blueprint(eevidence_api.bp, url_prefix="/api")
    eevidence_api.set_portal(portal)
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def internal_token(monkeypatch):
    token = "test-internal-token-secret-123"
    monkeypatch.setenv("EEVIDENCE_INTERNAL_TOKEN", token)
    return token


# ============================================================ portal logic


def test_submit_returns_ticket_with_id(portal):
    order = ProductionOrder.model_validate(_good_payload())
    ticket = portal.submit(order)
    assert ticket.ticket_id.startswith("EE-")
    assert ticket.status == TicketStatus.UNDER_REVIEW
    assert ticket.order_kind == "production"
    # Standard urgency yields the 10-day deadline.
    assert ticket.sla_deadline is not None
    delta = ticket.sla_deadline - ticket.received_at
    assert timedelta(days=9, hours=23) <= delta <= timedelta(days=10, minutes=1)


def test_emergency_submission_sets_eight_hour_sla(portal):
    order = ProductionOrder.model_validate(_good_payload(urgency_level="emergency"))
    ticket = portal.submit(order)
    assert ticket.status == TicketStatus.EMERGENCY
    assert ticket.emergency_marked_at is not None
    delta = ticket.sla_deadline - ticket.received_at
    assert timedelta(hours=7, minutes=55) <= delta <= timedelta(hours=8, minutes=5)


def test_mark_emergency_changes_status_and_deadline(portal):
    order = ProductionOrder.model_validate(_good_payload())
    ticket = portal.submit(order)
    assert ticket.status == TicketStatus.UNDER_REVIEW

    updated = portal.mark_emergency(
        ticket.ticket_id,
        justification="Imminent threat to life — kidnapping investigation, suspect in transit.",
    )
    assert updated.status == TicketStatus.EMERGENCY
    assert updated.emergency_marked_at is not None
    delta = updated.sla_deadline - updated.emergency_marked_at
    assert timedelta(hours=7, minutes=55) <= delta <= timedelta(hours=8, minutes=5)


def test_mark_emergency_rejects_short_justification(portal):
    order = ProductionOrder.model_validate(_good_payload())
    ticket = portal.submit(order)
    with pytest.raises(ValueError):
        portal.mark_emergency(ticket.ticket_id, "too short")


def test_mark_emergency_rejects_unknown_ticket(portal):
    with pytest.raises(KeyError):
        portal.mark_emergency("EE-FAKE-0000", "Plenty long justification text here.")


def test_respond_closes_ticket(portal):
    order = ProductionOrder.model_validate(_good_payload())
    ticket = portal.submit(order)
    resp = OrderResponse(
        outcome="provided",
        delivered_artifacts=["sha256:abc123"],
        rationale="Subscriber + IP log delivered via signed S3 link.",
        responder="Oleg Chetrean / CEO",
    )
    closed = portal.respond(ticket.ticket_id, resp)
    assert closed.status == TicketStatus.RESPONDED
    assert closed.responded_at is not None
    # Reopening after close must fail.
    with pytest.raises(RuntimeError):
        portal.respond(ticket.ticket_id, resp)


def test_list_open_excludes_closed_tickets(portal):
    o1 = portal.submit(ProductionOrder.model_validate(_good_payload(case_reference="A/1")))
    o2 = portal.submit(ProductionOrder.model_validate(_good_payload(case_reference="A/2")))
    portal.respond(
        o1.ticket_id,
        OrderResponse(outcome="no_data", responder="DPO"),
    )
    open_tickets = portal.list_open()
    open_ids = {t.ticket_id for t in open_tickets}
    assert o2.ticket_id in open_ids
    assert o1.ticket_id not in open_ids


def test_submit_preservation_default_60_days(portal):
    order = PreservationOrder.model_validate(
        {
            "issuing_authority": "Procuratura Generala a Romaniei",
            "issuing_authority_type": "prosecutor",
            "member_state": "RO",
            "target_identifier": "+40712345678",
            "case_reference": "9999/P/2026",
            "legal_basis": "Cod proc. pen. art. 154 alin. (1) — pastrare date",
            "contact_email": "dno@mpublic.ro",
        }
    )
    ticket = portal.submit_preservation(order)
    assert ticket.order_kind == "preservation"
    delta = ticket.sla_deadline - ticket.received_at
    assert timedelta(days=59, hours=23) <= delta <= timedelta(days=60, minutes=1)


# ============================================================ triage logic


def test_triage_flags_non_eu_authority():
    order = ProductionOrder.model_validate(_good_payload(member_state="UA"))
    decision = triage_order(order)
    assert decision.should_refuse
    assert RefusalGround.NON_EU_AUTHORITY in decision.grounds


def test_triage_flags_administrative_for_content():
    order = ProductionOrder.model_validate(
        _good_payload(
            issuing_authority_type="administrative",
            requested_data_category="content",
        )
    )
    decision = triage_order(order)
    assert decision.should_refuse
    assert RefusalGround.DATA_CATEGORY_UNAUTHORIZED in decision.grounds


def test_triage_flags_journalist_subject():
    order = ProductionOrder.model_validate(
        _good_payload(
            requested_data_category="content",
            subject_flags=["journalist"],
        )
    )
    decision = triage_order(order)
    assert decision.should_refuse
    assert RefusalGround.PRESS_FREEDOM in decision.grounds


def test_triage_flags_lawyer_immunity():
    order = ProductionOrder.model_validate(_good_payload(subject_flags=["lawyer"]))
    decision = triage_order(order)
    assert decision.should_refuse
    assert RefusalGround.IMMUNITIES_PRIVILEGES in decision.grounds


def test_triage_clean_order_passes_with_no_grounds():
    order = ProductionOrder.model_validate(_good_payload())
    decision = triage_order(order)
    assert not decision.should_refuse
    assert decision.grounds == ()
    assert decision.requires_human_review is True


def test_triage_third_country_conflict_for_content():
    order = ProductionOrder.model_validate(
        _good_payload(
            requested_data_category="content",
            target_country="US",
        )
    )
    decision = triage_order(order)
    assert decision.should_refuse
    assert RefusalGround.THIRD_COUNTRY_CONFLICT in decision.grounds


# ============================================================ audit register


def test_audit_log_immutable_against_modify():
    audit = AuditRegister()
    entry = audit.append(event_type="order_received", ticket_id="EE-X-1", actor="portal:test")
    # AuditEntry is a frozen dataclass — assignment must raise.
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.event_type = "tampered"  # type: ignore[misc]
    # Stored chain still verifies.
    assert audit.verify_chain()


def test_audit_chain_detects_tampering_via_reconstruction():
    audit = AuditRegister()
    audit.append(event_type="order_received", ticket_id="EE-1", actor="portal:test")
    audit.append(event_type="emergency_marked", ticket_id="EE-1", actor="operator:dpo")
    entries = audit.all()
    assert audit.verify_chain()
    # Replace the middle entry with a forged copy that lies about its hash.
    forged = dataclasses.replace(entries[0], event_type="order_refused")
    # The forged entry's stored hash no longer matches its content.
    assert not forged.verify()


def test_audit_chain_links_sequentially():
    audit = AuditRegister()
    e1 = audit.append(event_type="order_received", ticket_id="EE-1", actor="portal:test")
    e2 = audit.append(event_type="order_responded", ticket_id="EE-1", actor="operator:ceo")
    assert e2.previous_hash == e1.entry_hash
    assert e2.sequence == 2
    assert audit.verify_chain()


def test_audit_logs_submit_and_respond_events(portal):
    order = ProductionOrder.model_validate(_good_payload())
    ticket = portal.submit(order)
    portal.respond(
        ticket.ticket_id,
        OrderResponse(outcome="no_data", responder="DPO"),
    )
    events = [e.event_type for e in portal.audit.for_ticket(ticket.ticket_id)]
    assert "order_received" in events
    assert "order_responded" in events


# ============================================================ HTTP endpoints


def test_endpoint_submit_returns_201(client):
    res = client.post("/api/v1/legal/eevidence/submit", json=_good_payload())
    assert res.status_code == 201
    body = res.get_json()
    assert "ticket" in body
    assert body["ticket"]["status"] == "under_review"


def test_endpoint_submit_emergency_sets_status(client):
    res = client.post("/api/v1/legal/eevidence/submit/emergency", json=_good_payload())
    assert res.status_code == 201
    assert res.get_json()["ticket"]["status"] == "emergency"


def test_endpoint_submit_validation_failure(client):
    bad = _good_payload(member_state="ROO")  # 3 chars, fails length validator
    res = client.post("/api/v1/legal/eevidence/submit", json=bad)
    assert res.status_code == 422
    assert res.get_json()["error"] == "validation_failed"


def test_endpoint_respond_requires_internal_token(client):
    # Submit one first.
    submit_res = client.post("/api/v1/legal/eevidence/submit", json=_good_payload())
    ticket_id = submit_res.get_json()["ticket"]["ticket_id"]

    payload = {
        "ticket_id": ticket_id,
        "response": {
            "outcome": "provided",
            "responder": "Oleg Chetrean / CEO",
        },
    }
    # Without env var configured -> 503.
    res = client.post("/api/v1/legal/eevidence/respond", json=payload)
    assert res.status_code in (503, 401)


def test_endpoint_respond_with_valid_token(client, internal_token):
    submit_res = client.post("/api/v1/legal/eevidence/submit", json=_good_payload())
    ticket_id = submit_res.get_json()["ticket"]["ticket_id"]

    payload = {
        "ticket_id": ticket_id,
        "response": {
            "outcome": "provided",
            "responder": "Oleg Chetrean / CEO",
            "delivered_artifacts": ["sha256:abc"],
        },
    }
    res = client.post(
        "/api/v1/legal/eevidence/respond",
        json=payload,
        headers={"X-MDChat-Internal-Token": internal_token},
    )
    assert res.status_code == 200
    assert res.get_json()["ticket"]["status"] == "responded"


def test_endpoint_respond_rejects_bad_token(client, internal_token):
    submit_res = client.post("/api/v1/legal/eevidence/submit", json=_good_payload())
    ticket_id = submit_res.get_json()["ticket"]["ticket_id"]
    res = client.post(
        "/api/v1/legal/eevidence/respond",
        json={"ticket_id": ticket_id, "response": {"outcome": "no_data", "responder": "x"}},
        headers={"X-MDChat-Internal-Token": "wrong"},
    )
    assert res.status_code == 401


def test_endpoint_ticket_lookup_strips_payload(client):
    submit_res = client.post("/api/v1/legal/eevidence/submit", json=_good_payload())
    ticket_id = submit_res.get_json()["ticket"]["ticket_id"]
    res = client.get(f"/api/v1/legal/eevidence/ticket/{ticket_id}")
    assert res.status_code == 200
    view = res.get_json()["ticket"]
    assert "payload" not in view
    assert view["ticket_id"] == ticket_id


def test_endpoint_ticket_lookup_404(client):
    res = client.get("/api/v1/legal/eevidence/ticket/EE-DOES-NOT-EXIST")
    assert res.status_code == 404


def test_endpoint_register_open_requires_token(client, internal_token):
    client.post("/api/v1/legal/eevidence/submit", json=_good_payload())
    res = client.get("/api/v1/legal/eevidence/register/open")
    assert res.status_code == 401  # no header
    res2 = client.get(
        "/api/v1/legal/eevidence/register/open",
        headers={"X-MDChat-Internal-Token": internal_token},
    )
    assert res2.status_code == 200
    assert len(res2.get_json()["open_tickets"]) >= 1


def test_endpoint_register_full_returns_chain(client, internal_token):
    client.post("/api/v1/legal/eevidence/submit", json=_good_payload())
    res = client.get(
        "/api/v1/legal/eevidence/register",
        headers={"X-MDChat-Internal-Token": internal_token},
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["chain_valid"] is True
    assert len(body["entries"]) >= 1


def test_endpoint_preservation_submission(client):
    payload = {
        "issuing_authority": "Procuratura Generala Romania",
        "issuing_authority_type": "prosecutor",
        "member_state": "RO",
        "target_identifier": "bob@md-chat.eu",
        "case_reference": "1234/P/2026",
        "legal_basis": "Cod proc. pen. art. 154 alin. (1)",
        "contact_email": "dno@mpublic.ro",
    }
    res = client.post("/api/v1/legal/eevidence/submit/preservation", json=payload)
    assert res.status_code == 201
    assert res.get_json()["ticket"]["order_kind"] == "preservation"
