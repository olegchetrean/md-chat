"""Tests for :mod:`md_chat_ai.security.web_hardening`.

These tests build a *minimal* Flask app per test (independent of the
global ``create_app`` factory) so we can exercise the middleware in
isolation, including CSRF behavior with and without exempt routes.
"""

from __future__ import annotations

import pytest
from flask import Flask, jsonify

from md_chat_ai.config import CONFIG
from md_chat_ai.security.web_hardening import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    apply_web_hardening,
    csrf_exempt,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hardened_app() -> Flask:
    """Minimal Flask app with hardening middleware + two endpoints."""
    app = Flask(__name__)
    app.config.update(TESTING=True)

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    @app.post("/api/echo")
    def echo():
        return jsonify({"ok": True})

    @app.post("/api/internal")
    @csrf_exempt
    def internal():
        return jsonify({"ok": True, "internal": True})

    apply_web_hardening(app)
    return app


@pytest.fixture
def client(hardened_app: Flask):
    return hardened_app.test_client()


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------


SECURITY_HEADER_EXPECTATIONS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site",
}


def test_all_security_headers_present_on_health(client) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    for header, expected in SECURITY_HEADER_EXPECTATIONS.items():
        assert resp.headers.get(header) == expected, f"missing/wrong {header}"
    # HSTS — has dynamic max-age from config but format is strict.
    hsts = resp.headers.get("Strict-Transport-Security", "")
    assert hsts.startswith("max-age=")
    assert "includeSubDomains" in hsts
    assert "preload" in hsts
    # CSP — must include default-src 'self'.
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp


def test_hsts_max_age_matches_config(client) -> None:
    resp = client.get("/api/health")
    hsts = resp.headers.get("Strict-Transport-Security", "")
    assert f"max-age={CONFIG.hsts_max_age}" in hsts
    # Sanity: default is 2 years (63072000) unless overridden.
    assert CONFIG.hsts_max_age >= 31536000  # at least 1 year


def test_security_headers_present_on_error_responses(client) -> None:
    resp = client.get("/api/does-not-exist")
    assert resp.status_code == 404
    # Even 404s must be non-frameable and non-sniffable.
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


def test_cors_preflight_allowed_origin(client) -> None:
    allowed = CONFIG.cors_allowed_origins[0]
    resp = client.options(
        "/api/echo",
        headers={
            "Origin": allowed,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, X-CSRF-Token",
        },
    )
    assert resp.status_code == 204
    assert resp.headers.get("Access-Control-Allow-Origin") == allowed
    assert resp.headers.get("Access-Control-Allow-Credentials") == "true"
    assert "POST" in resp.headers.get("Access-Control-Allow-Methods", "")
    assert resp.headers.get("Access-Control-Max-Age") == "3600"
    # Echoes requested headers.
    allow_headers = resp.headers.get("Access-Control-Allow-Headers", "")
    assert "X-CSRF-Token" in allow_headers


def test_cors_preflight_denied_origin(client) -> None:
    resp = client.options(
        "/api/echo",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    # No CORS headers returned — browser will block.
    assert resp.headers.get("Access-Control-Allow-Origin") is None
    assert resp.headers.get("Access-Control-Allow-Credentials") is None


def test_cors_response_adds_allow_origin_for_allowlisted(client) -> None:
    allowed = CONFIG.cors_allowed_origins[0]
    resp = client.get("/api/health", headers={"Origin": allowed})
    assert resp.headers.get("Access-Control-Allow-Origin") == allowed
    assert resp.headers.get("Access-Control-Allow-Credentials") == "true"
    assert "Origin" in resp.headers.get("Vary", "")


def test_cors_response_omits_allow_origin_for_denied(client) -> None:
    resp = client.get("/api/health", headers={"Origin": "https://attacker.test"})
    assert resp.headers.get("Access-Control-Allow-Origin") is None


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------


def test_csrf_get_mints_cookie(client) -> None:
    resp = client.get("/api/health")
    # set-cookie should contain mdchat_csrf
    set_cookies = [v for k, v in resp.headers.items() if k.lower() == "set-cookie"]
    assert any(CSRF_COOKIE_NAME in c for c in set_cookies)


def test_csrf_post_without_token_rejected(client) -> None:
    resp = client.post("/api/echo", json={})
    assert resp.status_code == 403
    body = resp.get_json()
    assert body == {"ok": False, "error": "csrf_mismatch"}


def test_csrf_post_with_mismatched_token_rejected(client) -> None:
    client.set_cookie(CSRF_COOKIE_NAME, "deadbeef" * 8, domain="localhost")
    resp = client.post(
        "/api/echo",
        json={},
        headers={CSRF_HEADER_NAME: "different-value"},
    )
    assert resp.status_code == 403


def test_csrf_post_with_matching_token_accepted(client) -> None:
    token = "a" * 64
    client.set_cookie(CSRF_COOKIE_NAME, token, domain="localhost")
    resp = client.post(
        "/api/echo",
        json={},
        headers={CSRF_HEADER_NAME: token},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


def test_csrf_exempt_endpoint_accepts_without_token(client) -> None:
    resp = client.post("/api/internal", json={})
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True, "internal": True}


def test_csrf_exempt_decorator_marks_function() -> None:
    @csrf_exempt
    def view():
        return "ok"

    assert getattr(view, "__csrf_exempt__", False) is True


# ---------------------------------------------------------------------------
# Idempotency / integration sanity
# ---------------------------------------------------------------------------


def test_apply_web_hardening_is_idempotent() -> None:
    app = Flask(__name__)

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    apply_web_hardening(app)
    apply_web_hardening(app)  # second call must be safe
    client = app.test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Frame-Options") == "DENY"


def test_csp_default_disallows_unsafe_eval(client) -> None:
    resp = client.get("/api/health")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "unsafe-eval" not in csp
