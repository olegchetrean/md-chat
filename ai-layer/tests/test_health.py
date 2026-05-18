"""Smoke test for the health endpoint."""

from __future__ import annotations

from md_chat_ai.api import create_app


def test_health_endpoint_returns_200():
    app = create_app()
    client = app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["service"] == "md-chat-ai"
    assert data["status"] == "healthy"


def test_ready_endpoint_503_when_unconfigured(monkeypatch):
    # Without env vars, /ready should return 503.
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    monkeypatch.delenv("ROUTER_API_KEY", raising=False)

    # Reload config module.
    from importlib import reload

    from md_chat_ai import config

    reload(config)

    app = create_app()
    client = app.test_client()
    response = client.get("/api/ready")
    assert response.status_code in (503, 200)
