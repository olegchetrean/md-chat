# Copyright 2026 Mega Promoting SRL
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Derived from Cronberry (Mega Promoting SRL).
"""Branch-coverage tests for ``eevidence`` portal + triage + audit chain.

Each refusal ground (Art. 12) is exercised separately, plus:
- Preservation orders (Art. 9): default 60-day deadline, renewable.
- Emergency SLA tightening (8h, Art. 10(2)).
- Audit chain hash integrity + tamper detection.
"""

from __future__ import annotations

import dataclasses
from datetime import timedelta

import pytest

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _payload(**overrides) -> dict:
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


# ---------------------------------------------------------------------------
# Triage — every Art 12 ground (1-8) exercised separately
# ---------------------------------------------------------------------------


def test_triage_non_eu_authority_flagged():
    order = ProductionOrder.model_validate(_payload(member_state="US"))
    decision = triage_order(order)
    assert decision.should_refuse is True
    assert RefusalGround.NON_EU_AUTHORITY in decision.grounds
    assert "MLAT" in " ".join(decision.notes)


def test_triage_admin_authority_requesting_content_flagged():
    order = ProductionOrder.model_validate(
        _payload(issuing_authority_type="administrative", requested_data_category="content")
    )
    decision = triage_order(order)
    assert RefusalGround.DATA_CATEGORY_UNAUTHORIZED in decision.grounds


def test_triage_admin_authority_requesting_traffic_flagged():
    order = ProductionOrder.model_validate(
        _payload(issuing_authority_type="administrative", requested_data_category="traffic")
    )
    decision = triage_order(order)
    assert RefusalGround.DATA_CATEGORY_UNAUTHORIZED in decision.grounds


def test_triage_admin_authority_with_subscriber_is_ok():
    order = ProductionOrder.model_validate(
        _payload(issuing_authority_type="administrative", requested_data_category="subscriber")
    )
    decision = triage_order(order)
    assert RefusalGround.DATA_CATEGORY_UNAUTHORIZED not in decision.grounds


def test_triage_short_legal_basis_flagged_as_non_compliant_form():
    order = ProductionOrder.model_validate(_payload(legal_basis="too short!"))
    decision = triage_order(order)
    assert RefusalGround.NON_COMPLIANT_FORM in decision.grounds


def test_triage_extraterritorial_content_flagged():
    order = ProductionOrder.model_validate(
        _payload(member_state="RO", target_country="FR", requested_data_category="content")
    )
    decision = triage_order(order)
    assert RefusalGround.EXTRATERRITORIAL in decision.grounds


def test_triage_extraterritorial_subscriber_not_flagged():
    # Only content triggers the extraterritorial check.
    order = ProductionOrder.model_validate(
        _payload(member_state="RO", target_country="FR", requested_data_category="subscriber")
    )
    decision = triage_order(order)
    assert RefusalGround.EXTRATERRITORIAL not in decision.grounds


def test_triage_third_country_conflict_us():
    order = ProductionOrder.model_validate(
        _payload(member_state="RO", target_country="US", requested_data_category="content")
    )
    decision = triage_order(order)
    assert RefusalGround.THIRD_COUNTRY_CONFLICT in decision.grounds


def test_triage_third_country_conflict_gb():
    order = ProductionOrder.model_validate(
        _payload(member_state="RO", target_country="GB", requested_data_category="content")
    )
    decision = triage_order(order)
    assert RefusalGround.THIRD_COUNTRY_CONFLICT in decision.grounds


def test_triage_immunities_lawyer_flagged():
    order = ProductionOrder.model_validate(_payload(subject_flags=["lawyer"]))
    decision = triage_order(order)
    assert RefusalGround.IMMUNITIES_PRIVILEGES in decision.grounds


def test_triage_immunities_mep_flagged():
    order = ProductionOrder.model_validate(_payload(subject_flags=["MEP"]))
    decision = triage_order(order)
    assert RefusalGround.IMMUNITIES_PRIVILEGES in decision.grounds


def test_triage_immunities_diplomat_flagged():
    order = ProductionOrder.model_validate(_payload(subject_flags=["Diplomat"]))
    decision = triage_order(order)
    assert RefusalGround.IMMUNITIES_PRIVILEGES in decision.grounds


def test_triage_press_freedom_journalist_flagged():
    order = ProductionOrder.model_validate(_payload(subject_flags=["journalist"]))
    decision = triage_order(order)
    assert RefusalGround.PRESS_FREEDOM in decision.grounds


def test_triage_press_flag_alias():
    order = ProductionOrder.model_validate(_payload(subject_flags=["press"]))
    decision = triage_order(order)
    assert RefusalGround.PRESS_FREEDOM in decision.grounds


def test_triage_clean_order_no_grounds():
    order = ProductionOrder.model_validate(_payload())
    decision = triage_order(order)
    assert decision.should_refuse is False
    assert decision.grounds == ()
    assert decision.requires_human_review is True


def test_triage_multiple_grounds_accumulate():
    """Order with multiple violations should surface all of them."""
    order = ProductionOrder.model_validate(
        _payload(
            member_state="US",  # non-EU authority
            issuing_authority_type="administrative",
            requested_data_category="content",  # data category
            subject_flags=["lawyer"],  # immunity
        )
    )
    decision = triage_order(order)
    assert decision.should_refuse is True
    # At least 3 of the 4 checks fire (some interact).
    assert len(decision.grounds) >= 3


# ---------------------------------------------------------------------------
# Portal — submit / preservation / emergency / response
# ---------------------------------------------------------------------------


@pytest.fixture()
def portal() -> ProductionOrderPortal:
    return ProductionOrderPortal()


def test_portal_submit_standard_uses_10_day_sla(portal):
    order = ProductionOrder.model_validate(_payload(urgency_level="standard"))
    ticket = portal.submit(order)
    assert ticket.status == TicketStatus.UNDER_REVIEW
    delta = ticket.sla_deadline - ticket.received_at
    assert delta == portal.STANDARD_DEADLINE


def test_portal_submit_emergency_uses_8_hour_sla(portal):
    order = ProductionOrder.model_validate(_payload(urgency_level="emergency"))
    ticket = portal.submit(order)
    assert ticket.status == TicketStatus.EMERGENCY
    delta = ticket.sla_deadline - ticket.received_at
    assert delta == portal.EMERGENCY_DEADLINE


def test_portal_submit_emergency_marks_received_at(portal):
    order = ProductionOrder.model_validate(_payload(urgency_level="emergency"))
    ticket = portal.submit(order)
    assert ticket.emergency_marked_at == ticket.received_at


def test_portal_preservation_60_day_default(portal):
    order = PreservationOrder.model_validate(
        {
            "issuing_authority": "DG-CCI",
            "issuing_authority_type": "judicial",
            "member_state": "RO",
            "target_identifier": "bob@md-chat.eu",
            "case_reference": "case-1",
            "legal_basis": "Cod proc. pen. art. 154",
            "contact_email": "x@just.ro",
        }
    )
    ticket = portal.submit_preservation(order)
    assert ticket.order_kind == "preservation"
    assert ticket.sla_deadline is not None
    assert (ticket.sla_deadline - ticket.received_at).days == 60


def test_portal_preservation_custom_duration(portal):
    order = PreservationOrder.model_validate(
        {
            "issuing_authority": "DG-CCI",
            "issuing_authority_type": "judicial",
            "member_state": "RO",
            "target_identifier": "bob@md-chat.eu",
            "case_reference": "case-1",
            "legal_basis": "Cod proc. pen. art. 154",
            "duration_days": 30,
            "contact_email": "x@just.ro",
        }
    )
    ticket = portal.submit_preservation(order)
    assert (ticket.sla_deadline - ticket.received_at).days == 30


def test_portal_mark_emergency_promotes_standard_ticket(portal):
    order = ProductionOrder.model_validate(_payload(urgency_level="standard"))
    ticket = portal.submit(order)
    portal.mark_emergency(ticket.ticket_id, justification="suspect mass-mail abuse ongoing")
    refreshed = portal.get(ticket.ticket_id)
    assert refreshed.status == TicketStatus.EMERGENCY
    assert (refreshed.sla_deadline - refreshed.emergency_marked_at) == portal.EMERGENCY_DEADLINE


def test_portal_mark_emergency_rejects_short_justification(portal):
    order = ProductionOrder.model_validate(_payload())
    ticket = portal.submit(order)
    with pytest.raises(ValueError):
        portal.mark_emergency(ticket.ticket_id, justification="oops")


def test_portal_mark_emergency_unknown_ticket(portal):
    with pytest.raises(KeyError):
        portal.mark_emergency("EE-NOPE-00000000", justification="this is a valid length")


def test_portal_mark_emergency_on_closed_ticket_raises(portal):
    order = ProductionOrder.model_validate(_payload())
    ticket = portal.submit(order)
    response = OrderResponse(outcome="provided", responder="Oleg / CEO")
    portal.respond(ticket.ticket_id, response)
    with pytest.raises(RuntimeError):
        portal.mark_emergency(ticket.ticket_id, justification="not enough — already closed")


def test_portal_respond_with_refused_sets_status(portal):
    order = ProductionOrder.model_validate(_payload())
    ticket = portal.submit(order)
    refusal = OrderResponse(
        outcome="refused",
        refusal_grounds=["non_compliant_form"],
        rationale="Form invalid.",
        responder="Oleg / CEO",
    )
    portal.respond(ticket.ticket_id, refusal)
    refreshed = portal.get(ticket.ticket_id)
    assert refreshed.status == TicketStatus.REFUSED


def test_portal_respond_unknown_ticket_raises(portal):
    response = OrderResponse(outcome="provided", responder="Oleg / CEO")
    with pytest.raises(KeyError):
        portal.respond("EE-MISSING-00000000", response)


def test_portal_respond_twice_raises(portal):
    order = ProductionOrder.model_validate(_payload())
    ticket = portal.submit(order)
    r = OrderResponse(outcome="provided", responder="Oleg / CEO")
    portal.respond(ticket.ticket_id, r)
    with pytest.raises(RuntimeError):
        portal.respond(ticket.ticket_id, r)


def test_portal_list_open_excludes_closed(portal):
    order1 = ProductionOrder.model_validate(_payload(case_reference="111/2026"))
    order2 = ProductionOrder.model_validate(_payload(case_reference="222/2026"))
    t1 = portal.submit(order1)
    t2 = portal.submit(order2)
    portal.respond(t1.ticket_id, OrderResponse(outcome="provided", responder="Oleg / CEO"))
    open_tickets = portal.list_open()
    assert t2.ticket_id in [t.ticket_id for t in open_tickets]
    assert t1.ticket_id not in [t.ticket_id for t in open_tickets]


def test_portal_list_all_returns_every_ticket(portal):
    portal.submit(ProductionOrder.model_validate(_payload(case_reference="a/2026")))
    portal.submit(ProductionOrder.model_validate(_payload(case_reference="b/2026")))
    assert len(portal.list_all()) == 2


def test_portal_get_returns_none_for_missing(portal):
    assert portal.get("EE-MISSING-00000000") is None


def test_portal_submit_records_audit_with_redacted_target(portal):
    order = ProductionOrder.model_validate(_payload())
    portal.submit(order)
    entries = portal.audit.all()
    assert len(entries) == 1
    payload = entries[0].details["payload"]
    assert payload["target_identifier"].startswith("sha256:")


def test_ticket_to_dict_round_trip_shape(portal):
    order = ProductionOrder.model_validate(_payload(urgency_level="emergency"))
    ticket = portal.submit(order)
    d = ticket.to_dict()
    assert d["status"] == "emergency"
    assert d["order_kind"] == "production"
    assert d["sla_deadline"] is not None
    assert isinstance(d["triage"]["grounds"], list)


# ---------------------------------------------------------------------------
# Audit chain integrity
# ---------------------------------------------------------------------------


def test_audit_chain_verify_passes_after_appends():
    audit = AuditRegister()
    audit.append(event_type="order_received", ticket_id="t1", actor="portal:auth")
    audit.append(event_type="order_responded", ticket_id="t1", actor="op:dpo")
    assert audit.verify_chain() is True


def test_audit_chain_for_ticket_filters():
    audit = AuditRegister()
    audit.append(event_type="x", ticket_id="t1", actor="a")
    audit.append(event_type="x", ticket_id="t2", actor="a")
    audit.append(event_type="x", ticket_id="t1", actor="a")
    assert len(audit.for_ticket("t1")) == 2
    assert len(audit.for_ticket("t2")) == 1


def test_audit_requires_event_type():
    audit = AuditRegister()
    with pytest.raises(ValueError):
        audit.append(event_type="", ticket_id="t1", actor="a")


def test_audit_requires_ticket_id():
    audit = AuditRegister()
    with pytest.raises(ValueError):
        audit.append(event_type="x", ticket_id="", actor="a")


def test_audit_requires_actor():
    audit = AuditRegister()
    with pytest.raises(ValueError):
        audit.append(event_type="x", ticket_id="t1", actor="")


def test_audit_chain_detects_tampering():
    audit = AuditRegister()
    audit.append(event_type="x", ticket_id="t1", actor="a")
    audit.append(event_type="y", ticket_id="t1", actor="a")
    # Replace the second entry with a tampered one.
    original = audit._entries[1]
    tampered = dataclasses.replace(original, event_type="ZZZ")
    audit._entries[1] = tampered  # bypass frozen via list mutation
    assert audit.verify_chain() is False


def test_audit_entry_verify_recomputes_hash():
    audit = AuditRegister()
    e = audit.append(event_type="order_responded", ticket_id="t9", actor="op")
    assert e.verify() is True


def test_audit_first_entry_links_to_genesis():
    audit = AuditRegister()
    e = audit.append(event_type="x", ticket_id="t1", actor="a")
    assert e.previous_hash == "0" * 64
    assert e.sequence == 1
