# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mega Promoting SRL
"""Tests for the md_chat_ai.reports module."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest

from md_chat_ai.reports import (
    AI_ACT_DISCLOSURES,
    TEMPLATES,
    DailyBriefing,
    Report,
    ReportAgent,
    ReportStatus,
    apply_pii_redaction,
    get_template,
    list_templates,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm():
    """Async LLM stub that echoes the section title back in the body."""
    call_count = {"n": 0}

    async def _llm(messages: list[dict[str, str]]) -> str:
        call_count["n"] += 1
        sys = next((m["content"] for m in messages if m["role"] == "system"), "")
        title = "Section"
        if "section:" in sys.lower():
            after = sys.split(":", 1)[1]
            title = after.split("\n", 1)[0].strip().strip('"')
        return f"Generated content for: {title}.\n\nDetailed analysis follows here. " + ("Lorem ipsum. " * 10)

    _llm.call_count = call_count  # type: ignore[attr-defined]
    return _llm


@pytest.fixture
def mock_conversations() -> list[dict[str, Any]]:
    today = datetime.utcnow()
    return [
        {
            "id": "c1",
            "name": "Alice",
            "urgency": 5,
            "sentiment": "positive",
            "relevance_score": 80.0,
            "last_message_date": today.strftime("%Y-%m-%d %H:%M:%S"),
        },
        {
            "id": "c2",
            "name": "Bob",
            "urgency": 1,
            "sentiment": "negative",
            "relevance_score": 65.0,
            "last_message_date": (today - timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S"),
        },
        {
            "id": "c3",
            "name": "Carol",
            "urgency": 4,
            "sentiment": "neutral",
            "relevance_score": 30.0,
            "last_message_date": today.strftime("%Y-%m-%d %H:%M:%S"),
        },
        {
            "id": "c4",
            "name": "Dan",
            "urgency": "high",
            "sentiment": "mixed",
            "relevance_score": 55.0,
            "last_message_date": (today - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
        },
    ]


@pytest.fixture
def mock_promises() -> list[dict[str, Any]]:
    today = datetime.utcnow()
    return [
        {
            "id": "p1",
            "contact_id": "c1",
            "text": "Send the contract by Friday",
            "direction": "outgoing",
            "status": "pending",
            "due_date": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
        },
        {
            "id": "p2",
            "contact_id": "c2",
            "text": "Get back on the quote",
            "direction": "incoming",
            "status": "pending",
            "due_date": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
        },
        {
            "id": "p3",
            "contact_id": "c3",
            "text": "Will happen far in the future",
            "direction": "outgoing",
            "status": "pending",
            "due_date": (today + timedelta(days=60)).strftime("%Y-%m-%d"),
        },
    ]


# ---------------------------------------------------------------------------
# Template tests
# ---------------------------------------------------------------------------


def test_template_registry_has_all_required_templates():
    """All 9 required templates are registered."""
    required_keys = {
        # ported from Cronberry
        "plan_analysis",
        "campaign_forecast",
        "negotiation_prep",
        "risk_assessment",
        "relationship_map",
        # MD-Chat additions
        "daily_digest",
        "channel_summary",
        "group_recap_after_vacation",
        "post_call_summary",
    }
    assert required_keys.issubset(set(TEMPLATES.keys()))


def test_every_template_has_ro_ru_en_variants():
    """Each registered template must have RO/RU/EN variants."""
    for key, variants in TEMPLATES.items():
        assert "ro" in variants, f"{key} missing RO variant"
        assert "ru" in variants, f"{key} missing RU variant"
        assert "en" in variants, f"{key} missing EN variant"
        for lang, tpl in variants.items():
            assert tpl.language == lang
            assert tpl.sections, f"{key}/{lang} has no sections"


def test_get_template_language_switch():
    """get_template returns the right language variant and falls back gracefully."""
    ro = get_template("daily_digest", language="ro")
    ru = get_template("daily_digest", language="ru")
    en = get_template("daily_digest", language="en")
    assert ro is not None and ro.language == "ro"
    assert ru is not None and ru.language == "ru"
    assert en is not None and en.language == "en"
    assert ro.name != ru.name and ru.name != en.name

    assert get_template("nonexistent", "ro") is None


def test_list_templates_filter_by_language():
    """list_templates can be filtered by language."""
    all_entries = list_templates()
    assert len(all_entries) == 9 * 3  # 9 keys * 3 languages

    en_only = list_templates(language="en")
    assert len(en_only) == 9
    assert all(t["language"] == "en" for t in en_only)


# ---------------------------------------------------------------------------
# ReportAgent tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_agent_generates_daily_digest(mock_llm):
    """daily_digest generates with all sections populated."""
    agent = ReportAgent(llm=mock_llm, compute_backend="router_pcc")
    report = await agent.generate(
        "daily_digest",
        context={"messages_today": 42, "active_chats": 7, "new_contacts": 2},
        language="ro",
    )
    assert isinstance(report, Report)
    assert report.status == ReportStatus.COMPLETED
    assert report.language == "ro"
    assert report.template_key == "daily_digest"

    tpl = get_template("daily_digest", "ro")
    assert tpl is not None
    assert len(report.sections) == len(tpl.sections)
    for sec in report.sections:
        assert sec.content, f"section '{sec.title}' has empty content"


@pytest.mark.asyncio
async def test_report_includes_compute_backend_metadata(mock_llm):
    """Every report carries a compute_backend marker in metadata + markdown."""
    agent = ReportAgent(llm=mock_llm, compute_backend="on_device")
    report = await agent.generate("daily_digest", context={}, language="en")

    assert report.compute_backend == "on_device"
    md = report.to_markdown()
    assert "compute backend" in md.lower()
    assert "on_device" in md

    # Override per-call
    report2 = await agent.generate("daily_digest", context={}, language="en", compute_backend="router_open")
    assert report2.compute_backend == "router_open"


@pytest.mark.asyncio
async def test_report_includes_ai_act_disclosure(mock_llm):
    """AI Act Article 50 disclosure must appear at the end of every report (all languages)."""
    agent = ReportAgent(llm=mock_llm, compute_backend="router_pcc")

    for lang in ("ro", "ru", "en"):
        report = await agent.generate("post_call_summary", context={"duration": 600}, language=lang)
        md = report.to_markdown()
        disclosure = AI_ACT_DISCLOSURES[lang]
        # disclosure is appended as a blockquote
        assert disclosure in md, f"Disclosure for {lang} missing from output"
        # confirm metadata flag is set
        assert report.metadata.get("ai_act_disclosure") is True


@pytest.mark.asyncio
async def test_multi_language_switch(mock_llm):
    """Same template key produces different localized titles."""
    agent = ReportAgent(llm=mock_llm)
    ro = await agent.generate("channel_summary", context={}, language="ro")
    ru = await agent.generate("channel_summary", context={}, language="ru")
    en = await agent.generate("channel_summary", context={}, language="en")

    assert ro.title != ru.title
    assert ru.title != en.title
    # Languages reflected in markdown header
    assert "ro" in ro.to_markdown()
    assert "ru" in ru.to_markdown()
    assert "en" in en.to_markdown()


@pytest.mark.asyncio
async def test_invalid_template_raises(mock_llm):
    agent = ReportAgent(llm=mock_llm)
    with pytest.raises(KeyError):
        await agent.generate("does_not_exist", context={}, language="ro")


@pytest.mark.asyncio
async def test_invalid_language_raises(mock_llm):
    agent = ReportAgent(llm=mock_llm)
    with pytest.raises(ValueError):
        await agent.generate("daily_digest", context={}, language="zz")  # type: ignore[arg-type]


def test_invalid_compute_backend_raises():
    with pytest.raises(ValueError):
        ReportAgent(compute_backend="cloud_us")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PII redaction tests
# ---------------------------------------------------------------------------


def test_apply_pii_redaction_phone_and_email():
    text = "Call me at +373 60 005 418 or email john.doe@example.com today."
    redacted, did = apply_pii_redaction(text)
    assert did is True
    assert "+373" not in redacted
    assert "john.doe@example.com" not in redacted
    assert "[email]" in redacted
    assert "[phone]" in redacted


def test_apply_pii_redaction_noop_on_clean_text():
    text = "This text has no personal information whatsoever."
    redacted, did = apply_pii_redaction(text)
    assert did is False
    assert redacted == text


@pytest.mark.asyncio
async def test_report_redacts_pii_in_context(mock_llm):
    """PII inside context strings should be redacted before LLM call."""

    captured: dict[str, str] = {}

    async def capturing_llm(messages):
        # Snapshot the user message that contains the context JSON
        for m in messages:
            if m["role"] == "user":
                captured["user"] = m["content"]
        return "Section content body. " * 10

    agent = ReportAgent(llm=capturing_llm, compute_backend="router_pcc", redact_pii=True)
    await agent.generate(
        "channel_summary",
        context={"raw_message": "Contact ivan@example.com or +37360001234"},
        language="en",
    )
    assert "[email]" in captured["user"]
    assert "[phone]" in captured["user"]
    assert "ivan@example.com" not in captured["user"]


# ---------------------------------------------------------------------------
# DailyBriefing tests
# ---------------------------------------------------------------------------


def test_daily_briefing_aggregates_mock_data(mock_conversations, mock_promises):
    """DailyBriefing.generate aggregates the mock conversations and promises correctly."""
    bb = DailyBriefing(compute_backend="on_device", language="en")
    rep = bb.generate(
        conversations=mock_conversations,
        promises=mock_promises,
        mentions=[
            {
                "room": "#sales",
                "sender": "@alice",
                "text": "@me can you review?",
                "timestamp": "now",
            },
        ],
    )

    # Alice (urgency=5) and Carol (4) and Dan ("high"=5) should appear as likely_inbound
    inbound_names = {c.name for c in rep.likely_inbound}
    assert "Alice" in inbound_names
    assert "Carol" in inbound_names
    assert "Dan" in inbound_names

    # Bob (20d silent, relevance 65) is cooling
    cooling_names = {c.name for c in rep.cooling_relationships}
    assert "Bob" in cooling_names

    # Expiring promises: p1 (due in 3d) and p2 (overdue, -1d). p3 (60d) is filtered out
    promise_ids = {p.promise_id for p in rep.expiring_promises}
    assert "p1" in promise_ids
    assert "p2" in promise_ids
    assert "p3" not in promise_ids

    # Bob (negative, relevance 65) is opportunity at risk
    at_risk_names = {c.name for c in rep.opportunities_at_risk}
    assert "Bob" in at_risk_names

    # Summary counts
    assert rep.summary["total_conversations"] == 4
    assert rep.summary["expiring_promises_count"] == 2
    assert rep.summary["mentions_count"] == 1

    # Compute backend is propagated
    assert rep.compute_backend == "on_device"

    # Recommendations always non-empty
    assert rep.recommendations
    assert len(rep.recommendations) <= 5


def test_daily_briefing_should_notify_on_overdue_promise(mock_conversations, mock_promises):
    bb = DailyBriefing(compute_backend="on_device", language="en")
    rep = bb.generate(conversations=mock_conversations, promises=mock_promises)
    # p2 is overdue -> should notify
    assert bb.should_notify(rep) is True


def test_daily_briefing_format_detailed_has_disclosure(mock_conversations, mock_promises):
    """Detailed Markdown ends with AI Act disclosure."""
    bb = DailyBriefing(compute_backend="router_pcc", language="ro")
    rep = bb.generate(conversations=mock_conversations, promises=mock_promises)
    md = bb.format_detailed(rep)
    assert AI_ACT_DISCLOSURES["ro"] in md
    assert "router_pcc" in md
    assert "Digest zilnic" in md  # RO title


def test_daily_briefing_format_short_under_500_chars(mock_conversations, mock_promises):
    bb = DailyBriefing(compute_backend="on_device", language="en")
    rep = bb.generate(conversations=mock_conversations, promises=mock_promises)
    short = bb.format_short(rep)
    assert short
    assert len(short) <= 500


def test_daily_briefing_multi_language_format(mock_conversations, mock_promises):
    """Briefing renders RO/RU/EN with the proper localized headings."""
    for lang, marker in [("ro", "Sumar"), ("ru", "Rezyume"), ("en", "Summary")]:
        bb = DailyBriefing(compute_backend="on_device", language=lang)
        rep = bb.generate(conversations=mock_conversations, promises=mock_promises)
        md = bb.format_detailed(rep)
        assert marker in md, f"language={lang}: heading '{marker}' missing"


def test_daily_briefing_empty_data_no_crash():
    bb = DailyBriefing(compute_backend="on_device", language="en")
    rep = bb.generate(conversations=[], promises=[], mentions=[])
    assert rep.summary["total_conversations"] == 0
    short = bb.format_short(rep)
    assert "No urgent items today." in short
    assert bb.should_notify(rep) is False
