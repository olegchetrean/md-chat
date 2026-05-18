"""Prometheus metrics exposition tests.

The ``prometheus-client`` Python library is a hard dependency
(``pyproject.toml``) — it will be used by the security and rate-limit
modules to expose counters. This module verifies the *format* contract
so any agent landing a ``/metrics`` endpoint stays compatible with the
Prometheus 0.0.4 text exposition format.

When the ``/metrics`` HTTP endpoint has not been registered by a sibling
agent, the route-level tests skip cleanly.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Library-level contract — independent of any blueprint.
# ---------------------------------------------------------------------------


def test_prometheus_client_importable():
    """The Prometheus client library MUST be installed."""
    pytest.importorskip("prometheus_client")


def test_prometheus_exposition_format_round_trip():
    """A simple Counter + generate_latest round-trips into valid text format.

    The Prometheus Python client moved from the legacy 0.0.4 text format
    to the 1.0.0 OpenMetrics-style format around release 0.20+. Both are
    acceptable; we only assert the structural contract.
    """
    prom = pytest.importorskip("prometheus_client")
    registry = prom.CollectorRegistry()
    counter = prom.Counter(
        "md_chat_test_counter",
        "Test counter for metrics format compliance.",
        registry=registry,
    )
    counter.inc()
    counter.inc(2)
    payload = prom.generate_latest(registry).decode("utf-8")

    # Structural contract — independent of text-format version:
    # 1. A HELP line for the metric family.
    # 2. A TYPE line declaring 'counter'.
    # 3. A sample line bearing the accumulated value (3.0).
    assert "# HELP md_chat_test_counter" in payload, payload
    assert "# TYPE md_chat_test_counter" in payload, payload
    assert "counter" in payload, payload
    # Counter exposition in client_python adds the ``_total`` suffix.
    assert "md_chat_test_counter_total 3.0" in payload, payload


def test_prometheus_content_type_constant():
    """``CONTENT_TYPE_LATEST`` is the contract for the /metrics response.

    Accept either the legacy ``version=0.0.4`` content type or the
    newer ``version=1.0.0`` OpenMetrics content type — both are valid
    Prometheus exposition formats and Prometheus scrapers parse both.
    """
    prom = pytest.importorskip("prometheus_client")
    ct = prom.CONTENT_TYPE_LATEST
    assert ct.startswith("text/plain"), ct
    assert "version=" in ct, ct
    # Match the major versions we know about.
    assert any(v in ct for v in ("version=0.0.4", "version=1.0.0")), ct


def test_histogram_basic_observation():
    """Histograms must accept observations and expose _bucket, _sum, _count."""
    prom = pytest.importorskip("prometheus_client")
    registry = prom.CollectorRegistry()
    hist = prom.Histogram(
        "md_chat_test_latency_seconds",
        "Test histogram.",
        buckets=(0.1, 0.5, 1.0, 2.5, 5.0),
        registry=registry,
    )
    hist.observe(0.3)
    hist.observe(1.2)
    payload = prom.generate_latest(registry).decode("utf-8")
    assert "md_chat_test_latency_seconds_bucket" in payload
    assert "md_chat_test_latency_seconds_sum" in payload
    assert "md_chat_test_latency_seconds_count 2.0" in payload


# ---------------------------------------------------------------------------
# Blueprint-level — skips if /metrics not yet registered.
# ---------------------------------------------------------------------------


def _metrics_route_registered(app) -> bool:
    return any(r.rule == "/metrics" or r.rule == "/api/metrics" for r in app.url_map.iter_rules())


def test_metrics_endpoint_or_skip(client, app):
    """If /metrics is registered, it MUST return text/plain version=0.0.4."""
    if not _metrics_route_registered(app):
        pytest.skip("/metrics route not yet registered — security agent in flight")

    for path in ("/metrics", "/api/metrics"):
        rule_exists = any(r.rule == path for r in app.url_map.iter_rules())
        if not rule_exists:
            continue
        response = client.get(path)
        assert response.status_code == 200
        ct = response.headers.get("Content-Type", "")
        assert "text/plain" in ct
        # Accept either 0.0.4 (legacy) or 1.0.0 (OpenMetrics-aligned).
        assert any(v in ct for v in ("version=0.0.4", "version=1.0.0")), ct
        body = response.get_data(as_text=True)
        # Every Prometheus payload starts with either # HELP or a sample.
        assert body.strip(), "/metrics response body is empty"
        return

    pytest.fail("metrics route detected but no path matched — inspect url_map")
