"""Shared pytest fixtures.

Goal: every test should be able to import :func:`create_app` and obtain a
fully wired Flask test client *without* requiring Neo4j, Redis, Synapse,
Infobip, MPass, or any other external dependency.

Strategy:
    * Monkey-patch a safe default environment (placeholder secrets, no
      real network endpoints) at session scope.
    * Force a re-import of :mod:`md_chat_ai.config` so the patched env
      is picked up by the frozen ``CONFIG`` dataclass instance.
    * Provide a ``client`` fixture that yields a Flask test client.

The fixtures are deliberately defensive: if a blueprint depends on a
module that has not yet been written by a sibling agent, the test should
skip cleanly rather than crash the suite.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Iterator

import pytest

# ---------------------------------------------------------------------------
# Pytest markers — registered here so we don't depend on pyproject markers.
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test (boots Flask app).",
    )
    config.addinivalue_line(
        "markers",
        "compliance: mark test as a compliance/regulatory check (AI Act, GDPR).",
    )
    config.addinivalue_line(
        "markers",
        "security: mark test as a security control verification.",
    )


# ---------------------------------------------------------------------------
# Environment fixture — safe defaults for the whole session.
# ---------------------------------------------------------------------------


SAFE_ENV: dict[str, str] = {
    # Core
    "AI_LAYER_PORT": "5002",
    "LOG_LEVEL": "WARNING",
    "NODE_ENV": "test",
    # Neo4j — placeholder, will be mocked at the driver level.
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "test-password-not-real",
    # Router by MP — placeholder key, all LLM calls are mocked.
    "ROUTER_API_BASE": "https://router.test.invalid/v1",
    "ROUTER_API_KEY": "test-router-key-not-real",
    # Synapse — placeholder.
    "SYNAPSE_HS_URL": "http://synapse.test.invalid:8008",
    "SYNAPSE_AS_TOKEN": "test-synapse-token",
    # Infobip — placeholder.
    "INFOBIP_BASE_URL": "https://infobip.test.invalid",
    "INFOBIP_API_KEY": "test-infobip-key",
    "INFOBIP_SENDER_ID": "MDChatTest",
    # AI Act Art 50 disclosure — keep canonical text so compliance tests
    # can assert it is present.
    "AI_DISCLOSURE_TEXT_RO": "Sunteti in legatura cu un agent AI MD-Chat.",
    "AI_DISCLOSURE_TEXT_RU": "Vy obshchaetes s AI-agentom MD-Chat.",
    "AI_DISCLOSURE_TEXT_EN": "You are interacting with an MD-Chat AI agent.",
    # MPass / MSign — placeholder.
    "MPASS_SP_ENTITY_ID": "https://msg.md-chat.test/saml/sp",
    "MPASS_SP_ACS_URL": "https://msg.md-chat.test/api/v1/identity/saml/acs",
    "MPASS_SP_SLO_URL": "https://msg.md-chat.test/api/v1/identity/saml/slo",
    "MPASS_IDP_METADATA_URL": "https://mpass.gov.md/Metadata",
    "MPASS_RELEASE_IDNP": "false",
    "OIDC_ISSUER": "https://msg.md-chat.test",
    "MSIGN_WSDL_URL": "https://msign.gov.md/services/sign?wsdl",
    "MSIGN_CLIENT_ID": "test-client",
    "MSIGN_CLIENT_SECRET": "test-secret",
}


@pytest.fixture(scope="session", autouse=True)
def _safe_environment() -> Iterator[None]:
    """Install safe placeholder env vars for the whole session."""
    saved: dict[str, str | None] = {}
    for key, value in SAFE_ENV.items():
        saved[key] = os.environ.get(key)
        os.environ[key] = value

    # Force config reload so the frozen dataclass picks up our values.
    import md_chat_ai.config as config_module

    importlib.reload(config_module)

    yield

    for key, prev in saved.items():
        if prev is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prev


# ---------------------------------------------------------------------------
# Flask app / client fixtures.
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """Return a freshly-created Flask app for each test.

    A fresh app per test avoids cross-test pollution from blueprint state
    (rate-limit counters, in-memory caches, etc.).
    """
    from md_chat_ai.api import create_app

    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Mock fixtures — neo4j / redis / httpx so integration tests stay hermetic.
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_neo4j(monkeypatch):
    """Patch :func:`neo4j.GraphDatabase.driver` to return a no-op stub.

    Tests that simply need the import to succeed without a real DB should
    request this fixture.
    """

    class _Session:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def run(self, *a, **kw):
            class _Result:
                def single(self):
                    return None

                def data(self):
                    return []

                def __iter__(self):
                    return iter([])

            return _Result()

        def close(self):
            pass

    class _Driver:
        def session(self, *a, **kw):
            return _Session()

        def close(self):
            pass

        def verify_connectivity(self):
            return None

    try:
        import neo4j  # type: ignore

        monkeypatch.setattr(neo4j.GraphDatabase, "driver", lambda *a, **kw: _Driver())
    except ImportError:
        pytest.skip("neo4j driver not installed")

    return _Driver()


@pytest.fixture
def mock_redis(monkeypatch):
    """Patch :class:`redis.Redis` to a fake in-memory implementation."""
    store: dict[str, str] = {}

    class _FakeRedis:
        def __init__(self, *a, **kw):
            pass

        def get(self, k):
            return store.get(k)

        def set(self, k, v, *a, **kw):
            store[k] = v if isinstance(v, str) else str(v)
            return True

        def delete(self, *keys):
            for k in keys:
                store.pop(k, None)
            return len(keys)

        def incr(self, k, amount=1):
            cur = int(store.get(k, "0")) + amount
            store[k] = str(cur)
            return cur

        def expire(self, k, ttl):
            return True

        def ping(self):
            return True

        def close(self):
            pass

    try:
        import redis  # type: ignore

        monkeypatch.setattr(redis, "Redis", _FakeRedis)
        if hasattr(redis, "StrictRedis"):
            monkeypatch.setattr(redis, "StrictRedis", _FakeRedis)
    except ImportError:
        pytest.skip("redis client not installed")

    return _FakeRedis()
