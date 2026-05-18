# Copyright 2026 Mega Promoting SRL
# Licensed under the Apache License, Version 2.0 (the "License");
"""Endpoint tests for the Digital Twin Flask blueprint.

Every test uses a fully-mocked LLMClient (no network), a fresh Flask app
(no cross-test pollution) and a tightened ``twin-chat`` rate-limit
namespace so the burst test runs in milliseconds.

Coverage targets:
    * Chat returns TwinResponse with AI Act Art 50 disclosure
    * Profile create / read / update roundtrip
    * Revoke prevents subsequent chat (410 Gone)
    * Audit log gated by internal token (401 / 200)
    * Rate limit kicks in after burst (429 with Retry-After)
    * Pydantic validates mode enum strictly (400)
    * eIDAS attest stub returns 202 + flips verified
    * Mock LLMClient is honoured via ``app.config['LLM_CLIENT']``
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from md_chat_ai.api import create_app
from md_chat_ai.api.twin import _REGISTRY, _set_twin_chat_limit
from md_chat_ai.security import reset_limiter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_llm(chat_reply: str = "salut, ok, vorbim mai tarziu") -> MagicMock:
    """Build a synchronous-only mock that mirrors LLMClient's twin surface."""

    client = MagicMock()
    client.chat.return_value = chat_reply
    client.chat_json.return_value = {
        "predicted_response": "ok, vorbim",
        "confidence": 0.7,
        "emotional_reaction": "neutral",
        "reasoning": "voice matches",
        "suggested_approach": "be direct",
        "risk_level": "low",
        "alternative_messages": ["alt1", "alt2"],
        "outcome": "reached_agreement",
        "agreement_summary": "ok",
        "concessions_made": [],
        "concessions_received": [],
        "contact_position": "ok",
        "recommended_next_step": "sign",
    }
    return client


@pytest.fixture(autouse=True)
def _isolated_registry_and_limiter():
    """Reset the twin registry + rate-limiter singleton between tests."""

    _REGISTRY.clear()
    reset_limiter()
    yield
    _REGISTRY.clear()
    reset_limiter()


@pytest.fixture
def mock_llm() -> MagicMock:
    return _make_mock_llm()


@pytest.fixture
def app(mock_llm):
    """Fresh app per test with the mock LLMClient pre-wired."""

    flask_app = create_app()
    flask_app.config.update(TESTING=True, LLM_CLIENT=mock_llm)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def internal_token(monkeypatch):
    token = "twin-internal-token-test-secret"
    monkeypatch.setenv("TWIN_INTERNAL_TOKEN", token)
    return token


def _profile_payload(**overrides: Any) -> dict[str, Any]:
    base = {
        "name": "Oleg Test",
        "username": "oleg_test",
        "bio": "Founder Mega Promoting",
        "self_summary": "scrie scurt, direct, fara emoji",
        "own_messages": [
            "salut, ok",
            "vorbim maine",
            "merge, multumesc",
            "ok, hai",
            "da, sigur",
        ],
        "language": "ro",
        "custom_notes": "no formalities",
        "interests": ["AI", "SaaS"],
        "profession": "Founder",
    }
    base.update(overrides)
    return base


def _create_profile(client, user_id: str = "u-1") -> dict[str, Any]:
    resp = client.post(f"/api/v1/twin/{user_id}/profile", json=_profile_payload())
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_profile_create_returns_201_and_view(client):
    body = _create_profile(client)
    assert body["ok"] is True
    data = body["data"]
    assert data["user_id"] == "u-1"
    assert data["name"] == "Oleg Test"
    assert data["language"] == "ro"
    assert data["is_revoked"] is False
    assert data["own_messages_count"] == 5
    assert 0.0 <= data["confidence_score"] <= 1.0


def test_profile_get_after_create(client):
    _create_profile(client)
    resp = client.get("/api/v1/twin/u-1/profile")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["data"]["name"] == "Oleg Test"


def test_profile_get_404_when_missing(client):
    resp = client.get("/api/v1/twin/nobody/profile")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "twin_not_found"


def test_profile_update_returns_200_and_refreshes(client):
    _create_profile(client)
    resp = client.post(
        "/api/v1/twin/u-1/profile",
        json=_profile_payload(name="Oleg Updated", own_messages=["nou"]),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["data"]["name"] == "Oleg Updated"
    assert body["data"]["own_messages_count"] == 1


def test_chat_returns_disclosure_in_ro(client, mock_llm):
    _create_profile(client)
    resp = client.post(
        "/api/v1/twin/u-1/chat",
        json={"message": "salut, ce mai faci?", "mode": "free_chat", "language": "ro"},
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["ok"] is True
    data = body["data"]
    # Response shape
    assert data["response"]["text"]  # non-empty reply
    assert data["response"]["mode"] == "free_chat"
    # AI Act Art 50: disclosure must be present in BOTH places
    assert data["disclosure"]["eu_ai_act_art50"] is True
    assert data["disclosure"]["language"] == "ro"
    assert data["disclosure"]["text"]  # non-empty disclosure text
    assert data["response"]["disclosure"]["language"] == "ro"
    # The mock was actually called.
    assert mock_llm.chat.called


def test_chat_returns_disclosure_in_en(client):
    _create_profile(client)
    resp = client.post(
        "/api/v1/twin/u-1/chat",
        json={"message": "hello there", "mode": "free_chat", "language": "en"},
    )
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["disclosure"]["language"] == "en"
    assert "AI agent" in data["disclosure"]["text"] or data["disclosure"]["text"]


def test_chat_404_when_twin_missing(client):
    resp = client.post(
        "/api/v1/twin/ghost/chat",
        json={"message": "hi", "mode": "free_chat"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "twin_not_found"


def test_chat_rejects_invalid_mode_with_400(client):
    _create_profile(client)
    resp = client.post(
        "/api/v1/twin/u-1/chat",
        json={"message": "hi", "mode": "telepathy"},  # not in enum
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["ok"] is False
    assert body["error"] == "validation_failed"


def test_chat_rejects_empty_message(client):
    _create_profile(client)
    resp = client.post(
        "/api/v1/twin/u-1/chat",
        json={"message": "   ", "mode": "free_chat"},
    )
    assert resp.status_code == 400


def test_revoke_returns_204_and_blocks_subsequent_chat(client):
    _create_profile(client)
    resp = client.post("/api/v1/twin/u-1/revoke", json={"reason": "test"})
    assert resp.status_code == 204

    chat_resp = client.post(
        "/api/v1/twin/u-1/chat",
        json={"message": "still there?", "mode": "free_chat"},
    )
    assert chat_resp.status_code == 410
    assert chat_resp.get_json()["error"] == "twin_revoked"


def test_revoke_404_when_missing(client):
    resp = client.post("/api/v1/twin/ghost/revoke", json={})
    assert resp.status_code == 404


def test_audit_log_requires_internal_token(client):
    _create_profile(client)
    resp = client.get("/api/v1/twin/u-1/audit-log")
    # When TWIN_INTERNAL_TOKEN env is unset we get 503; when missing header
    # we get 401. Both are non-200 — we check explicitly below with token set.
    assert resp.status_code in (401, 503)


def test_audit_log_with_valid_token_returns_entries(client, internal_token):
    _create_profile(client)
    # Generate one chat so the audit log has at least one entry.
    client.post(
        "/api/v1/twin/u-1/chat",
        json={"message": "salut", "mode": "free_chat"},
    )
    resp = client.get(
        "/api/v1/twin/u-1/audit-log",
        headers={"X-MDChat-Internal-Token": internal_token},
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["ok"] is True
    assert body["data"]["count"] >= 1
    assert body["data"]["entries"][0]["action"] == "chat"


def test_audit_log_with_wrong_token_returns_401(client, internal_token):
    _create_profile(client)
    resp = client.get(
        "/api/v1/twin/u-1/audit-log",
        headers={"X-MDChat-Internal-Token": "wrong-token"},
    )
    assert resp.status_code == 401


def test_rate_limit_kicks_in_after_burst(client):
    _create_profile(client)
    # Tighten the namespace so we exhaust it deterministically.
    _set_twin_chat_limit(capacity=2, window_seconds=60.0)
    payload = {"message": "ping", "mode": "free_chat"}
    r1 = client.post("/api/v1/twin/u-1/chat", json=payload)
    r2 = client.post("/api/v1/twin/u-1/chat", json=payload)
    r3 = client.post("/api/v1/twin/u-1/chat", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.headers.get("Retry-After")
    body = r3.get_json()
    assert body["error"] == "rate_limited"
    assert body["data"]["namespace"] == "twin-chat"


def test_attest_returns_202_and_marks_verified(client):
    _create_profile(client)
    from datetime import UTC, datetime, timedelta

    expires = (datetime.now(UTC) + timedelta(days=365)).isoformat()
    resp = client.post(
        "/api/v1/twin/u-1/attest",
        json={
            "issuer": "self",
            "subject_did": "did:web:md-chat.eu:users:u-1",
            "signature": "deadbeef" * 8,
            "signature_alg": "EdDSA",
            "expires_at": expires,
        },
    )
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["ok"] is True
    assert body["data"]["verified"] is True

    # The profile read should now reflect verified=True.
    pr = client.get("/api/v1/twin/u-1/profile").get_json()
    assert pr["data"]["verified"] is True


def test_attest_validation_rejects_short_signature(client):
    _create_profile(client)
    resp = client.post(
        "/api/v1/twin/u-1/attest",
        json={"subject_did": "did:web:u-1", "signature": "x"},
    )
    assert resp.status_code == 400


def test_envelope_shape_is_consistent_across_endpoints(client):
    """All responses must carry {ok, data, error}."""

    _create_profile(client)

    # Success body.
    ok_body = client.get("/api/v1/twin/u-1/profile").get_json()
    assert set(ok_body.keys()) == {"ok", "data", "error"}

    # 404 body.
    nf_body = client.get("/api/v1/twin/ghost/profile").get_json()
    assert set(nf_body.keys()) == {"ok", "data", "error"}

    # Validation body.
    val_body = client.post(
        "/api/v1/twin/u-1/chat", json={"mode": "free_chat"}
    ).get_json()
    assert set(val_body.keys()) == {"ok", "data", "error"}
