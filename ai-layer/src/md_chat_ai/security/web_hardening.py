"""Production-grade web hardening middleware for the MD-Chat AI layer.

This module is intentionally dependency-free: no ``flask-cors``, no
``flask-wtf``. Everything is implemented with stdlib + Flask's built-in
``before_request`` / ``after_request`` hooks.

Three concerns are bundled in :func:`apply_web_hardening`:

1. **Security headers** — HSTS, CSP, X-Frame-Options, COOP/CORP, etc.
   Applied unconditionally on *every* response (including 4xx/5xx) so
   error pages cannot be framed or sniffed.
2. **CORS** — strict allowlist driven by ``CONFIG.cors_allowed_origins``.
   Preflight (``OPTIONS``) is short-circuited with a 204 before any
   blueprint sees it. Origins NOT on the allowlist receive *no*
   ``Access-Control-Allow-Origin`` header at all (browser will block).
3. **CSRF** — double-submit cookie pattern. A 32-byte hex token is
   minted on first GET and stored in cookie ``mdchat_csrf``
   (SameSite=Lax, Secure, NOT HttpOnly so frontend JS can echo it
   back). Unsafe methods (POST/PUT/DELETE/PATCH) must echo the token
   in the ``X-CSRF-Token`` header. Internal/server-to-server endpoints
   that authenticate via header bearer tokens (e.g. eEvidence
   production order webhook) can opt out with :func:`csrf_exempt`.

Integration::

    from md_chat_ai.security.web_hardening import apply_web_hardening
    app = Flask(__name__)
    apply_web_hardening(app)

The middleware is idempotent and safe to call multiple times — guarded
by an ``app.extensions`` marker.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import Flask, Response, current_app, jsonify, make_response, request

from ..config import CONFIG

__all__ = [
    "CSRF_COOKIE_NAME",
    "CSRF_HEADER_NAME",
    "apply_web_hardening",
    "csrf_exempt",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CSRF_COOKIE_NAME = "mdchat_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_TOKEN_BYTES = 32  # 32 bytes hex = 64 chars
UNSAFE_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})

CORS_ALLOWED_METHODS = "GET, POST, OPTIONS"
CORS_ALLOWED_HEADERS = "Authorization, Content-Type, X-MDChat-Internal-Token, Accept-Language, X-CSRF-Token"
CORS_MAX_AGE = "3600"

_EXT_KEY = "md_chat_web_hardening"

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Public decorator
# ---------------------------------------------------------------------------


def csrf_exempt(view_func: F) -> F:
    """Mark a view function as exempt from CSRF protection.

    Use this for internal server-to-server endpoints that authenticate
    via header tokens (e.g. ``X-MDChat-Internal-Token``) rather than
    browser cookies, so a CSRF token is meaningless.

    The middleware inspects ``view_func.__csrf_exempt__`` directly, so
    this decorator does not wrap or change behavior.
    """
    view_func.__csrf_exempt__ = True  # type: ignore[attr-defined]
    return view_func


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _origin_allowed(origin: str | None) -> bool:
    """Return True when ``origin`` is on the configured allowlist."""
    if not origin:
        return False
    return origin in CONFIG.cors_allowed_origins


def _is_view_csrf_exempt() -> bool:
    """Return True when the current view function opted out of CSRF."""
    endpoint = request.endpoint
    if not endpoint:
        return False
    view = current_app.view_functions.get(endpoint)
    if view is None:
        return False
    return bool(getattr(view, "__csrf_exempt__", False))


def _mint_token() -> str:
    return secrets.token_hex(CSRF_TOKEN_BYTES)


# ---------------------------------------------------------------------------
# Hook factories — kept as factories so they close over the app instance
# and can be safely registered multiple times in tests.
# ---------------------------------------------------------------------------


def _make_security_headers_hook() -> Callable[[Response], Response]:
    def _apply(response: Response) -> Response:
        # HSTS — 2 years, includeSubDomains + preload.
        response.headers.setdefault(
            "Strict-Transport-Security",
            f"max-age={CONFIG.hsts_max_age}; includeSubDomains; preload",
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        response.headers.setdefault("Content-Security-Policy", CONFIG.csp_policy)
        return response

    return _apply


def _make_cors_preflight_hook() -> Callable[[], Response | None]:
    def _preflight() -> Response | None:
        # Short-circuit CORS preflight before routing/CSRF.
        if request.method != "OPTIONS":
            return None
        # Only short-circuit when it's actually a CORS preflight — i.e.
        # carries ``Access-Control-Request-Method``. Otherwise let the
        # normal route handle it.
        if not request.headers.get("Access-Control-Request-Method"):
            return None
        resp = make_response("", 204)
        origin = request.headers.get("Origin")
        if _origin_allowed(origin):
            resp.headers["Access-Control-Allow-Origin"] = origin or ""
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Vary"] = "Origin"
            resp.headers["Access-Control-Allow-Methods"] = CORS_ALLOWED_METHODS
            req_headers = request.headers.get("Access-Control-Request-Headers")
            resp.headers["Access-Control-Allow-Headers"] = req_headers or CORS_ALLOWED_HEADERS
            resp.headers["Access-Control-Max-Age"] = CORS_MAX_AGE
        # Origins not on the allowlist get a bare 204 with no CORS
        # headers — the browser will treat that as a preflight failure
        # and block the actual request.
        return resp

    return _preflight


def _make_cors_response_hook() -> Callable[[Response], Response]:
    def _apply(response: Response) -> Response:
        origin = request.headers.get("Origin")
        if _origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin or ""
            response.headers["Access-Control-Allow-Credentials"] = "true"
            # Make caches origin-aware.
            existing_vary = response.headers.get("Vary")
            if existing_vary:
                if "Origin" not in existing_vary:
                    response.headers["Vary"] = f"{existing_vary}, Origin"
            else:
                response.headers["Vary"] = "Origin"
            response.headers.setdefault("Access-Control-Allow-Methods", CORS_ALLOWED_METHODS)
            response.headers.setdefault("Access-Control-Allow-Headers", CORS_ALLOWED_HEADERS)
        return response

    return _apply


def _make_csrf_before_hook() -> Callable[[], Response | None]:
    def _check() -> Response | None:
        if not CONFIG.csrf_enabled:
            return None
        if request.method not in UNSAFE_METHODS:
            return None
        if _is_view_csrf_exempt():
            return None

        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)
        if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
            resp = jsonify({"ok": False, "error": "csrf_mismatch"})
            resp.status_code = 403
            return resp
        return None

    return _check


def _make_csrf_after_hook() -> Callable[[Response], Response]:
    def _apply(response: Response) -> Response:
        if not CONFIG.csrf_enabled:
            return response
        # If the client doesn't have a token yet, mint one. Cookie is
        # readable by JS so the SPA can echo it back in the header
        # (double-submit). It is NOT HttpOnly.
        if not request.cookies.get(CSRF_COOKIE_NAME):
            response.set_cookie(
                CSRF_COOKIE_NAME,
                _mint_token(),
                max_age=60 * 60 * 24 * 7,  # 7 days
                secure=True,
                httponly=False,
                samesite="Lax",
                path="/",
            )
        return response

    return _apply


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def apply_web_hardening(app: Flask) -> None:
    """Register CORS, CSRF, and security-header middleware on ``app``.

    Idempotent — subsequent calls on the same app are no-ops, so the
    function can be safely invoked from multiple registration points
    (e.g. tests + production WSGI factory).
    """
    if app.extensions.get(_EXT_KEY):
        return

    # Order matters: preflight short-circuit MUST run before CSRF, and
    # CSRF MUST run before the route handler.
    app.before_request(_make_cors_preflight_hook())
    app.before_request(_make_csrf_before_hook())

    # after_request hooks run in REVERSE registration order. We register
    # security headers LAST so they run FIRST after the view and are
    # therefore present even if a later hook short-circuits with an
    # exception turned into a response. CORS headers run after that to
    # add Allow-Origin on top.
    app.after_request(_make_cors_response_hook())
    app.after_request(_make_csrf_after_hook())
    app.after_request(_make_security_headers_hook())

    app.extensions[_EXT_KEY] = True
