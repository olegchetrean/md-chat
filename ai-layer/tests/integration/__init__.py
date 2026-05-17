"""Integration tests for md-chat-ai.

These tests exercise the Flask application end-to-end (within a single
process) without relying on Neo4j, Redis, or external network services.
External dependencies are mocked or monkey-patched via fixtures in
``tests/conftest.py``.

All tests in this package SHOULD be marked with ``@pytest.mark.integration``
so that they can be selectively skipped on lightweight CI runners.
"""
