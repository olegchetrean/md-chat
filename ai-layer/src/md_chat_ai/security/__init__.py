"""Security package — GDPR, prompt guard, rate limiter, AI safety.

Ported from cronberry_swarm.security for the MD-Chat AI layer. All modules
are license-compatible (Apache 2.0).

Public API:
    PromptGuard, get_guard
    RateLimiter, NamespaceLimit, RateLimitResult, get_limiter
    GDPRManager, get_manager, register_store, DataStore
    AISafetyFilter, AIDisclosure, get_disclosure
    ErrorHandler

Convenience:
    register_security(app)   — attach Flask middleware to an app.
"""

from __future__ import annotations

from .ai_safety import AIDisclosure, AISafetyFilter, get_disclosure
from .error_handler import ErrorHandler
from .gdpr import (
    DataStore,
    GDPRManager,
    get_manager,
    register_store,
    reset_manager,
    unregister_store,
)
from .prompt_guard import PromptGuard, get_guard
from .rate_limiter import (
    NamespaceLimit,
    RateLimiter,
    RateLimitResult,
    get_limiter,
    reset_limiter,
)


def register_security(app) -> None:
    """Attach security middleware to a Flask application.

    Currently registers the error handler. Rate limiting is applied per
    endpoint (via the namespaced ``RateLimiter`` directly) rather than as
    global middleware, so signup/twin-chat/briefing routes can pick their
    own bucket explicitly.
    """
    ErrorHandler(app)


__all__ = [
    "AIDisclosure",
    "AISafetyFilter",
    "DataStore",
    "ErrorHandler",
    "GDPRManager",
    "NamespaceLimit",
    "PromptGuard",
    "RateLimitResult",
    "RateLimiter",
    "get_disclosure",
    "get_guard",
    "get_limiter",
    "get_manager",
    "register_security",
    "register_store",
    "reset_limiter",
    "reset_manager",
    "unregister_store",
]
