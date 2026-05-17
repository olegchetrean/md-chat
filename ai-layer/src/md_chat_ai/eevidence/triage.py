"""Triage logic for eEvidence production / preservation orders.

Implements a deterministic decision tree based on **Article 12** of the
eEvidence Regulation (refusal grounds for service providers). Each ground
maps to a :class:`RefusalGround` enum value carrying the article reference
and a short human-readable rationale.

The triage is intentionally rule-based and side-effect free so that:

1. Outcomes are auditable and reviewable by the DPO and EU Representative.
2. The same payload can be replayed deterministically across versions.
3. Operators can extend the rule list without touching the portal core.

The decision tree is conservative — when a check matches, the order is
flagged for *human review* (``should_refuse=True``). It does **NOT** auto-
refuse; per the runbook, only the CEO + DPO + EU Rep jointly may file a
formal refusal with the issuing authority.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid circular import at module load
    from .portal import ProductionOrder


class RefusalGround(str, Enum):
    """Closed list of grounds we may invoke per Art. 12 eEvidence."""

    EXTRATERRITORIAL = "extraterritorial"
    """Order targets data of a person not subject to the issuing state's
    jurisdiction in a way Art. 12(1)(a) considers manifest."""

    FUNDAMENTAL_RIGHTS = "fundamental_rights"
    """Compliance would violate Charter rights (Art. 12(1)(b))."""

    IMMUNITIES_PRIVILEGES = "immunities_privileges"
    """Targeted person enjoys immunity / privilege under EU or national law
    (Art. 12(1)(c)) — e.g. lawyer-client privilege, MEPs, journalists."""

    NON_COMPLIANT_FORM = "non_compliant_form"
    """EPOC / EPOC-PR not issued in the prescribed form or not validated by
    an issuing authority defined in Art. 4."""

    THIRD_COUNTRY_CONFLICT = "third_country_conflict"
    """Compliance would force a conflict with the laws of a third country
    (Art. 17 review mechanism applies)."""

    PRESS_FREEDOM = "press_freedom"
    """Order would compromise journalistic sources (subset of fundamental
    rights, flagged separately for transparency reporting)."""

    DATA_CATEGORY_UNAUTHORIZED = "data_category_unauthorized"
    """Authority is not competent for the requested data category — e.g.
    administrative authority requesting traffic / content data which
    Art. 5(4) reserves for judicial authority + serious crime list."""

    NON_EU_AUTHORITY = "non_eu_authority"
    """Issuing authority is not a Member State of the eEvidence Regulation.
    Such orders must be re-routed via MLAT / E-EVIDENCE Convention, not
    accepted at the Art. 7 portal."""


# Closed list of EU Member States the Regulation applies to. Excludes IE & DK
# which have an opt-out under the Treaties (verify before each deployment).
_REGULATION_MEMBER_STATES: frozenset[str] = frozenset(
    {
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IT",
        "LV",
        "LT",
        "LU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
    }
)

# Administrative-only authorities cannot request traffic / content data.
_CONTENT_TRAFFIC_CATEGORIES: frozenset[str] = frozenset({"traffic", "content"})


@dataclass(frozen=True)
class TriageDecision:
    """Outcome of running the triage decision tree on an order."""

    should_refuse: bool
    """``True`` if at least one refusal ground was matched."""

    grounds: tuple[RefusalGround, ...] = ()
    """All matched refusal grounds, in detection order."""

    notes: tuple[str, ...] = ()
    """Free-text rationale for each ground, parallel to ``grounds``."""

    requires_human_review: bool = True
    """We never auto-refuse — flag for human review always."""

    extra: dict[str, str] = field(default_factory=dict)
    """Optional structured details for the audit register."""


def _check_authority_state(order: "ProductionOrder") -> tuple[RefusalGround, str] | None:
    state = (order.member_state or "").upper()
    if state and state not in _REGULATION_MEMBER_STATES:
        return (
            RefusalGround.NON_EU_AUTHORITY,
            f"Issuing state {state!r} is not bound by EU 2023/1543; "
            "re-route through MLAT / Budapest Convention.",
        )
    return None


def _check_authority_competence(order: "ProductionOrder") -> tuple[RefusalGround, str] | None:
    if (
        order.issuing_authority_type == "administrative"
        and order.requested_data_category in _CONTENT_TRAFFIC_CATEGORIES
    ):
        return (
            RefusalGround.DATA_CATEGORY_UNAUTHORIZED,
            "Administrative authority requesting traffic/content data; "
            "Art. 5(4) reserves these to judicial authorities + serious-crime list.",
        )
    return None


def _check_form_compliance(order: "ProductionOrder") -> tuple[RefusalGround, str] | None:
    if not order.legal_basis or len(order.legal_basis.strip()) < 16:
        return (
            RefusalGround.NON_COMPLIANT_FORM,
            "Legal basis missing or too short to assess; EPOC must cite the "
            "national criminal procedure article + offence.",
        )
    if not order.case_reference:
        return (
            RefusalGround.NON_COMPLIANT_FORM,
            "Case reference missing — Annex I EPOC form requires it.",
        )
    return None


def _check_extraterritorial(order: "ProductionOrder") -> tuple[RefusalGround, str] | None:
    target_country = (order.target_country or "").upper()
    state = (order.member_state or "").upper()
    if target_country and state and target_country != state and target_country != "EU":
        if order.requested_data_category == "content":
            return (
                RefusalGround.EXTRATERRITORIAL,
                f"Content order from {state} targeting a user located in "
                f"{target_country} — manifest extraterritorial reach.",
            )
    return None


def _check_third_country_conflict(order: "ProductionOrder") -> tuple[RefusalGround, str] | None:
    if order.target_country and order.target_country.upper() in {"US", "GB", "CH"}:
        if order.requested_data_category == "content":
            return (
                RefusalGround.THIRD_COUNTRY_CONFLICT,
                "Content disclosure may conflict with third-country law (e.g. ECPA, "
                "UK IPA); trigger Art. 17 review.",
            )
    return None


def _check_immunities(order: "ProductionOrder") -> tuple[RefusalGround, str] | None:
    flags = {f.lower() for f in order.subject_flags}
    if "lawyer" in flags or "attorney" in flags:
        return (
            RefusalGround.IMMUNITIES_PRIVILEGES,
            "Target flagged as legal counsel — attorney-client privilege.",
        )
    if "mep" in flags or "diplomat" in flags:
        return (
            RefusalGround.IMMUNITIES_PRIVILEGES,
            "Target enjoys parliamentary / diplomatic immunity.",
        )
    return None


def _check_press(order: "ProductionOrder") -> tuple[RefusalGround, str] | None:
    flags = {f.lower() for f in order.subject_flags}
    if "journalist" in flags or "press" in flags:
        return (
            RefusalGround.PRESS_FREEDOM,
            "Target identified as journalist; protection of sources applies.",
        )
    return None


_CHECKS = (
    _check_authority_state,
    _check_authority_competence,
    _check_form_compliance,
    _check_extraterritorial,
    _check_third_country_conflict,
    _check_immunities,
    _check_press,
)


def triage_order(order: "ProductionOrder") -> TriageDecision:
    """Run the Art. 12 decision tree against ``order``.

    The returned :class:`TriageDecision` is purely advisory — the portal
    records it in the audit register and forwards the order to the human
    review queue (CEO + DPO + EU Rep) regardless of the outcome.
    """

    grounds: list[RefusalGround] = []
    notes: list[str] = []
    for check in _CHECKS:
        result = check(order)
        if result is not None:
            ground, note = result
            grounds.append(ground)
            notes.append(note)

    return TriageDecision(
        should_refuse=bool(grounds),
        grounds=tuple(grounds),
        notes=tuple(notes),
        requires_human_review=True,
    )
