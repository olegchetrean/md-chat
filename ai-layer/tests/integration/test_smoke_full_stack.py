"""Full-stack smoke tests.

These tests verify that the Flask application can be constructed, that
the canonical health endpoints answer, and that every blueprint the
sibling agents are expected to register is wired up at the documented
URL prefix.

A blueprint that has NOT yet been registered (because the agent
implementing it has not landed their PR) results in a *skip*, not a
failure — this lets the integration suite live on ``main`` while the
parallel feature branches catch up.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


def test_app_factory_returns_flask_app(app):
    """``create_app`` returns a Flask instance with the expected name."""
    from flask import Flask
    assert isinstance(app, Flask)


def test_health_endpoint_200(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["service"] == "md-chat-ai"
    assert data["status"] == "healthy"
    # AI Act Art 50 disclosure surface MUST be flagged on health payload.
    assert data.get("ai_act_disclosure") is True


def test_ready_endpoint_responds(client):
    """``/api/ready`` is always reachable; status may be 200 or 503."""
    response = client.get("/api/ready")
    assert response.status_code in (200, 503)
    data = response.get_json()
    assert "ready" in data


def test_health_payload_includes_version(client):
    response = client.get("/api/health")
    data = response.get_json()
    assert "version" in data
    # Semver-ish — at least major.minor.patch.
    parts = data["version"].split(".")
    assert len(parts) >= 3


def test_health_payload_includes_config_flags(client):
    response = client.get("/api/health")
    data = response.get_json()
    cfg = data.get("config") or {}
    # All three config flags MUST be exposed (bool); their value depends
    # on the env at test time — sibling tests may reload config and
    # transiently clear vars, so we assert the *shape*, not the value.
    assert "neo4j_configured" in cfg
    assert "router_configured" in cfg
    assert "infobip_configured" in cfg
    for key in ("neo4j_configured", "router_configured", "infobip_configured"):
        assert isinstance(cfg[key], bool)


# ---------------------------------------------------------------------------
# Blueprint registration
# ---------------------------------------------------------------------------


# Map: blueprint name -> at least one URL prefix that MUST exist if the
# blueprint is registered. These are the contracts the sibling agents are
# expected to fulfil. Missing blueprints SKIP rather than FAIL.
EXPECTED_BLUEPRINTS: dict[str, list[str]] = {
    "health": ["/api/health", "/api/ready"],
    "auth": ["/api/auth"],
    "identity": ["/api/v1/identity"],
    "eevidence": ["/api/eevidence"],
}


def _has_route_prefix(app, prefix: str) -> bool:
    return any(r.rule.startswith(prefix) for r in app.url_map.iter_rules())


def test_health_blueprint_registered(app):
    assert "health" in app.blueprints, "health blueprint MUST be registered"


@pytest.mark.parametrize("bp_name,prefixes", list(EXPECTED_BLUEPRINTS.items()))
def test_expected_blueprint_present_or_skip(app, bp_name, prefixes):
    """Each contracted blueprint either exists or the test skips cleanly.

    This keeps CI green while the sibling agents are still pushing code.
    """
    if bp_name not in app.blueprints and not any(
        _has_route_prefix(app, p) for p in prefixes
    ):
        pytest.skip(f"blueprint '{bp_name}' not yet registered — owning agent in flight")
    assert any(_has_route_prefix(app, p) for p in prefixes), (
        f"blueprint '{bp_name}' claims to be registered but exposes none of {prefixes}"
    )


def test_404_for_unknown_route(client):
    response = client.get("/api/__definitely_not_a_route__")
    assert response.status_code == 404


def test_health_endpoint_returns_json(client):
    response = client.get("/api/health")
    assert response.content_type.startswith("application/json")
