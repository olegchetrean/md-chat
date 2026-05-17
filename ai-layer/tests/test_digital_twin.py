# Copyright 2026 Mega Promoting SRL
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""
Unit tests for the MD-Chat Digital Twin engine (self-twin mode).

All LLM calls are mocked — no network/router activity. Verifies:
  - TwinResponse always carries an AI Act Art 50 disclosure
  - Each new mode (auto_reply, business_24_7, vacation) works
  - revoke() prevents further chats
  - audit_log records every action
  - Verified Authentic Twin status is propagated
  - SelfProfile-based confidence scoring works
  - MdChatProfileGenerator builds a self-twin profile from own_messages
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from md_chat_ai.agents import (
    AgentProfile,
    DigitalTwin,
    MdChatProfileGenerator,
    SelfProfile,
    TwinDisclosure,
    TwinResponse,
    VerifiedAttestation,
)
from md_chat_ai.agents.digital_twin import TwinRevokedError


# ======================================================================
# Fixtures
# ======================================================================


def _make_mock_llm(
    chat_reply: str = "salut, multumesc pentru mesaj",
    chat_json_reply: Dict[str, Any] | None = None,
) -> MagicMock:
    """Build a fully-mocked LLMClient stand-in."""
    client = MagicMock()
    # Synchronous methods used by digital_twin / message_optimizer:
    client.chat.return_value = chat_reply
    client.chat_json.return_value = chat_json_reply or {
        "predicted_response": "ok, vorbim",
        "confidence": 0.7,
        "emotional_reaction": "neutral",
        "reasoning": "voice matches",
        "suggested_approach": "be direct",
        "risk_level": "low",
        "alternative_messages": ["alt1", "alt2"],
    }
    # Async method exposed by the real LLMClient.complete:
    complete_result = MagicMock()
    complete_result.content = chat_reply
    client.complete = MagicMock(return_value=complete_result)
    return client


@pytest.fixture
def self_profile() -> SelfProfile:
    """A minimally populated SelfProfile fixture."""
    return SelfProfile(
        user_id="user_oleg_42",
        name="Oleg Chetrean",
        username="oleg",
        bio="Founder MD-Chat",
        self_summary="Tehnic, direct, scurt. Romana + engleza.",
        own_messages=[
            "salut",
            "ok merge",
            "trimit acum",
            "ne vedem la 14",
            "perfect, multumesc",
            "haide ca termin azi",
            "verific si revin",
        ],
        language="ro",
        custom_notes="Prefera lowercase si mesaje sub 50 caractere.",
        interests=["AI", "Telegram", "founder ops"],
        profession="CEO",
        last_message_date=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def mock_llm() -> MagicMock:
    """Default mock LLMClient."""
    return _make_mock_llm()


@pytest.fixture
def twin(self_profile: SelfProfile, mock_llm: MagicMock) -> DigitalTwin:
    """A DigitalTwin wired to a mocked LLM."""
    return DigitalTwin(profile=self_profile, llm_client=mock_llm)


# ======================================================================
# Disclosure & free_chat
# ======================================================================


def test_free_chat_returns_twin_response_with_disclosure(twin: DigitalTwin) -> None:
    """Free chat must return a TwinResponse with an attached disclosure."""
    resp = twin.chat("salut, ce mai faci?", mode="free_chat")
    assert isinstance(resp, TwinResponse)
    assert resp.mode == "free_chat"
    assert resp.disclosure is not None
    assert isinstance(resp.disclosure, TwinDisclosure)
    assert resp.disclosure.text
    assert resp.disclosure.language in {"ro", "ru", "en"}
    assert resp.text == "salut, multumesc pentru mesaj"


def test_disclosure_defaults_to_romanian(twin: DigitalTwin) -> None:
    """By default the disclosure language is Romanian."""
    resp = twin.chat("buna", mode="free_chat")
    assert resp.disclosure.language == "ro"
    assert "MD-Chat" in resp.disclosure.text or "AI" in resp.disclosure.text


def test_disclosure_override_language(twin: DigitalTwin) -> None:
    """Caller can override disclosure language for a single call."""
    resp = twin.chat("hello", mode="free_chat", disclosure_language="en")
    assert resp.disclosure.language == "en"


def test_for_language_builder_uses_config() -> None:
    """TwinDisclosure.for_language returns config-driven text."""
    d_ro = TwinDisclosure.for_language("ro")
    d_en = TwinDisclosure.for_language("en")
    d_ru = TwinDisclosure.for_language("ru")
    assert d_ro.text != d_en.text != d_ru.text
    assert d_ro.language == "ro"
    assert d_en.language == "en"
    assert d_ru.language == "ru"


# ======================================================================
# New modes (auto_reply, business_24_7, vacation)
# ======================================================================


def test_auto_reply_mode_includes_ro_disclosure_by_default(twin: DigitalTwin) -> None:
    """auto_reply mode defaults to Romanian disclosure."""
    resp = twin.chat("vrei sa ne intalnim azi?", mode="auto_reply")
    assert resp.mode == "auto_reply"
    assert resp.disclosure.language == "ro"
    assert resp.text  # the mocked reply still propagates


def test_business_24_7_mode_works(twin: DigitalTwin) -> None:
    """business_24_7 mode produces a TwinResponse with disclosure."""
    resp = twin.chat("ce preturi aveti?", mode="business_24_7")
    assert resp.mode == "business_24_7"
    assert resp.disclosure is not None
    assert resp.text


def test_vacation_mode_uses_profile_message(self_profile: SelfProfile, mock_llm: MagicMock) -> None:
    """vacation mode returns the static profile.vacation_message verbatim."""
    self_profile.vacation_message = "Sunt in vacanta pana pe 1 iunie. Revin atunci."
    t = DigitalTwin(profile=self_profile, llm_client=mock_llm)
    resp = t.chat("orice", mode="vacation")
    assert resp.text == "Sunt in vacanta pana pe 1 iunie. Revin atunci."
    assert resp.mode == "vacation"
    assert resp.disclosure.language == "ro"


def test_vacation_mode_falls_back_to_default_text(twin: DigitalTwin) -> None:
    """vacation mode falls back to a default text when none is set."""
    resp = twin.chat("?", mode="vacation")
    assert "concediu" in resp.text.lower() or "vacanta" in resp.text.lower()


# ======================================================================
# Revocation (AI Act Art 22 hook)
# ======================================================================


def test_revoke_prevents_subsequent_chats(twin: DigitalTwin) -> None:
    """After revoke() any chat call raises TwinRevokedError."""
    twin.chat("salut", mode="free_chat")
    twin.revoke(reason="user_requested")

    assert twin.is_revoked is True
    with pytest.raises(TwinRevokedError):
        twin.chat("inca un mesaj", mode="free_chat")
    with pytest.raises(TwinRevokedError):
        twin.chat("ce zici?", mode="auto_reply")


def test_revoke_propagates_to_attestation(self_profile: SelfProfile, mock_llm: MagicMock) -> None:
    """Revoking a twin also flips the attached attestation's revoked flag."""
    agent = AgentProfile(
        agent_id=1,
        username="oleg",
        display_name="Oleg",
        bio="b",
        persona="p",
        attestation=VerifiedAttestation(
            issuer="self",
            subject_did="did:web:md-chat.eu:oleg",
            signature="sig",
            issued_at=datetime.now(timezone.utc).isoformat(),
        ),
    )
    t = DigitalTwin(profile=self_profile, agent_profile=agent, llm_client=mock_llm)
    assert t.agent_profile is not None
    assert t.agent_profile.attestation is not None
    assert t.agent_profile.attestation.revoked is False
    t.revoke(reason="user_requested")
    assert t.agent_profile.attestation.revoked is True


# ======================================================================
# Audit log
# ======================================================================


def test_audit_log_records_chat_and_revoke(twin: DigitalTwin) -> None:
    """audit_log captures every chat + the revoke event."""
    twin.chat("salut", mode="free_chat")
    twin.chat("vrei sa ne vedem?", mode="auto_reply")
    twin.revoke(reason="user_requested")

    assert len(twin.audit_log) == 3
    actions = [e.action for e in twin.audit_log]
    modes = [e.mode for e in twin.audit_log]
    assert actions == ["chat", "chat", "revoke"]
    assert modes == ["free_chat", "auto_reply", "system"]


def test_export_audit_log_is_json(twin: DigitalTwin) -> None:
    """export_audit_log returns valid JSON."""
    import json
    twin.chat("test", mode="free_chat")
    raw = twin.export_audit_log()
    parsed = json.loads(raw)
    assert isinstance(parsed, list)
    assert parsed[0]["action"] == "chat"
    assert parsed[0]["mode"] == "free_chat"


# ======================================================================
# Verified Authentic Twin
# ======================================================================


def test_verified_attestation_marks_response_verified(
    self_profile: SelfProfile, mock_llm: MagicMock
) -> None:
    """A valid attestation propagates to TwinResponse.verified=True."""
    agent = AgentProfile(
        agent_id=1, username="oleg", display_name="Oleg", bio="b", persona="p",
        attestation=VerifiedAttestation(
            issuer="eIDAS-QTSP",
            subject_did="did:web:md-chat.eu:oleg",
            signature="abc123",
            issued_at=datetime.now(timezone.utc).isoformat(),
            expires_at=(datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        ),
    )
    t = DigitalTwin(profile=self_profile, agent_profile=agent, llm_client=mock_llm)
    resp = t.chat("salut", mode="free_chat")
    assert resp.verified is True


def test_unverified_twin_sets_verified_false(twin: DigitalTwin) -> None:
    """Without attestation, TwinResponse.verified is False."""
    resp = twin.chat("salut", mode="free_chat")
    assert resp.verified is False


# ======================================================================
# Predict response (uses LLM JSON path)
# ======================================================================


def test_predict_response_uses_mocked_json(twin: DigitalTwin) -> None:
    """predict_response wraps the LLM JSON output into PredictionResult."""
    pred = twin.predict_response(
        scenario="reuniune cu un client nou",
        your_message="cand putem vorbi?",
    )
    assert pred.predicted_response == "ok, vorbim"
    assert 0.0 <= pred.confidence <= 1.0
    assert pred.risk_level in {"low", "medium", "high"}


# ======================================================================
# Profile generator (self-twin mode)
# ======================================================================


def test_profile_generator_rule_based_path(mock_llm: MagicMock) -> None:
    """Rule-based path works with very little data and no LLM call."""
    gen = MdChatProfileGenerator(llm_client=mock_llm)
    profile = gen.generate_from_self(
        agent_id=99,
        self_data={"display_name": "Test User", "own_messages": []},
        use_llm=False,
    )
    assert isinstance(profile, AgentProfile)
    assert profile.display_name == "Test User"
    assert profile.message_count == 0
    assert profile.data_confidence >= 0.1


def test_profile_generator_llm_path_uses_own_messages(mock_llm: MagicMock) -> None:
    """LLM path receives own_messages and produces a populated profile."""
    mock_llm.chat_json.return_value = {
        "display_name": "Oleg",
        "bio": "Founder",
        "persona": "Direct, scurt, tehnic.",
        "personality": {"openness": 0.8, "conscientiousness": 0.7},
        "communication_style": {
            "formality": "casual", "directness": "very_direct",
            "emotionality": "stoic", "typical_length": "short",
        },
        "response_patterns": [
            {"trigger": "task", "pattern": "lowercase + scurt"},
        ],
        "decision_factors": [
            {"factor": "viteza", "weight": 0.9, "direction": "positive"},
        ],
        "interests": ["AI", "ops"],
        "activity_level": 0.8,
        "sentiment_trend": "stable",
    }
    gen = MdChatProfileGenerator(llm_client=mock_llm)
    profile = gen.generate_from_self(
        agent_id=1,
        self_data={
            "user_id": "u1",
            "display_name": "Oleg",
            "own_messages": ["salut", "ok", "merge", "trimit", "ne vedem"],
            "self_declared_profession": "CEO",
            "language": "ro",
        },
        use_llm=True,
    )
    assert profile.persona == "Direct, scurt, tehnic."
    assert profile.communication_style.formality == "casual"
    assert profile.communication_style.typical_length == "short"
    assert profile.message_count == 5
    assert profile.source_user_id == "u1"


# ======================================================================
# Confidence
# ======================================================================


def test_confidence_score_grows_with_data(self_profile: SelfProfile, mock_llm: MagicMock) -> None:
    """confidence_score should grow as more data becomes available."""
    sparse = SelfProfile(user_id="x", name="X")
    rich = self_profile
    t_sparse = DigitalTwin(profile=sparse, llm_client=mock_llm)
    t_rich = DigitalTwin(profile=rich, llm_client=mock_llm)
    assert t_sparse.confidence_score < t_rich.confidence_score


# ======================================================================
# Attestation validity
# ======================================================================


def test_attestation_is_valid_when_signed_and_unexpired() -> None:
    """A signed, unexpired attestation is valid."""
    att = VerifiedAttestation(
        issuer="self",
        subject_did="did:web:md-chat.eu:test",
        signature="signature_bytes",
        expires_at=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    )
    assert att.is_valid() is True


def test_attestation_invalid_when_expired_or_revoked() -> None:
    """Expired or revoked attestations are invalid."""
    expired = VerifiedAttestation(
        issuer="self", subject_did="d", signature="s",
        expires_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
    )
    assert expired.is_valid() is False

    revoked = VerifiedAttestation(
        issuer="self", subject_did="d", signature="s", revoked=True,
    )
    assert revoked.is_valid() is False

    missing_sig = VerifiedAttestation(issuer="self", subject_did="d")
    assert missing_sig.is_valid() is False
