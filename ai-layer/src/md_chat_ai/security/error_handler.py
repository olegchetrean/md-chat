"""Production-safe error handler — Flask error middleware.

Ported from cronberry_swarm/security/error_handler.py with no behavioural
changes (logger renamed, DEBUG env var aligned with MD-Chat's `NODE_ENV`).

Behaviour:
  - No stack traces in responses (logged server-side at ERROR level).
  - Every error response uses the same structured JSON shape:
      {
          "error":      "<human-readable message>",
          "code":       <HTTP status code int>,
          "request_id": "<UUID>"
      }
  - In debug mode the exception type + message is included in the response
    body (still no traceback frames).

License: Apache 2.0 (Mega Promoting SRL, derived from cronberry_swarm).
"""

from __future__ import annotations

import logging
import traceback
import uuid

from flask import Flask, g, jsonify
from werkzeug.exceptions import HTTPException

from ..config import CONFIG

logger = logging.getLogger("md_chat_ai.security.error_handler")


_GENERIC_MESSAGES = {
    400: "Bad request",
    401: "Authentication required",
    403: "Access denied",
    404: "Resource not found",
    405: "Method not allowed",
    413: "Request payload too large",
    422: "Unprocessable request",
    429: "Too many requests",
    500: "An unexpected error occurred. Please try again later.",
    502: "Bad gateway",
    503: "Service temporarily unavailable",
    504: "Gateway timeout",
}


def _request_id() -> str:
    try:
        return g.get("request_id") or str(uuid.uuid4())
    except RuntimeError:
        return str(uuid.uuid4())


def _make_error_response(status_code: int, message: str | None = None):
    body = {
        "error": message or _GENERIC_MESSAGES.get(status_code, "An error occurred"),
        "code": status_code,
        "request_id": _request_id(),
    }
    response = jsonify(body)
    response.status_code = status_code
    return response


class ErrorHandler:
    """Register error handlers on a Flask app for all common HTTP codes."""

    def __init__(self, app: Flask) -> None:
        self.app = app
        self._register(app)

    @staticmethod
    def _register(app: Flask) -> None:
        debug_mode = CONFIG.dev_mode

        @app.errorhandler(HTTPException)
        def handle_http_exception(exc: HTTPException):
            status = exc.code or 500
            logger.warning(
                "HTTPException status=%d description=%s request_id=%s",
                status,
                exc.description,
                _request_id(),
            )
            response = _make_error_response(status)
            if status == 429 and hasattr(exc, "response") and exc.response:
                retry = exc.response.headers.get("Retry-After")
                if retry:
                    response.headers["Retry-After"] = retry
            return response

        for code in (400, 401, 403, 404, 405, 413, 422, 429):

            def _make_handler(c):
                def _handler(exc):
                    logger.info("HTTP %d request_id=%s", c, _request_id())
                    return _make_error_response(c)

                _handler.__name__ = f"handle_{c}"
                return _handler

            app.register_error_handler(code, _make_handler(code))

        @app.errorhandler(Exception)
        def handle_exception(exc: Exception):
            tb = traceback.format_exc()
            logger.error(
                "Unhandled exception request_id=%s type=%s: %s\n%s",
                _request_id(),
                type(exc).__name__,
                str(exc),
                tb,
            )
            if debug_mode:
                message = f"{type(exc).__name__}: {exc}"
            else:
                message = _GENERIC_MESSAGES[500]
            return _make_error_response(500, message)
