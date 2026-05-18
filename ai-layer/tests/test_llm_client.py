"""
Tests for md_chat_ai.llm.LLMClient — Router-first routing with fallback.

All HTTP traffic is intercepted via httpx.MockTransport so the tests run
fully offline. No real API keys required.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from md_chat_ai.llm import (
    ConfidentialBackend,
    LLMClient,
    LLMProvider,
    LLMResponse,
    RouterError,
    get_cost_tracker,
)
from md_chat_ai.llm.client import (
    ANTHROPIC_CACHE_MIN_CHARS,
    _compute_cost_cents,
    _lookup_pricing,
)
from md_chat_ai.llm.router_adapter import RouterAdapter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _router_ok_payload(
    *,
    content: str = "router-says-hi",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    cached_tokens: int = 0,
    cache_creation_tokens: int = 0,
    model: str = "claude-sonnet-4-5",
) -> dict[str, Any]:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "prompt_tokens_details": {"cached_tokens": cached_tokens},
            "cache_creation_input_tokens": cache_creation_tokens,
        },
    }


def _anthropic_ok_payload(
    *,
    content: str = "anthropic-says-hi",
    input_tokens: int = 80,
    output_tokens: int = 40,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> dict[str, Any]:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-4-5",
        "content": [{"type": "text", "text": content}],
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_input_tokens": cache_read_tokens,
            "cache_creation_input_tokens": cache_creation_tokens,
        },
    }


def _openai_ok_payload(content: str = "openai-says-hi") -> dict[str, Any]:
    return {
        "id": "chatcmpl-oa",
        "object": "chat.completion",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 60,
            "completion_tokens": 30,
            "total_tokens": 90,
            "prompt_tokens_details": {"cached_tokens": 0},
        },
    }


class _Recorder:
    """Captures the requests received by the MockTransport for assertions."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def append(self, req: httpx.Request) -> None:
        self.requests.append(req)

    def urls(self) -> list[str]:
        return [str(r.url) for r in self.requests]


def _make_client(handler) -> tuple[LLMClient, _Recorder]:
    """Build an LLMClient whose httpx is wired to a MockTransport handler."""
    recorder = _Recorder()

    def _handler(request: httpx.Request) -> httpx.Response:
        recorder.append(request)
        return handler(request)

    transport = httpx.MockTransport(_handler)
    http = httpx.AsyncClient(transport=transport)
    client = LLMClient(
        router_base="https://api.megapromoting.com/v1",
        router_key="router-test-key",
        anthropic_key="anthropic-test-key",
        openai_key="openai-test-key",
        http_client=http,
    )
    return client, recorder


# ---------------------------------------------------------------------------
# Pricing / cost arithmetic
# ---------------------------------------------------------------------------


def test_lookup_pricing_exact_and_unknown():
    in_c, out_c, cr_c, cw_c, family = _lookup_pricing("claude-sonnet-4-5")
    assert family == "anthropic"
    assert in_c == pytest.approx(0.450)
    assert out_c == pytest.approx(2.250)
    assert cr_c == pytest.approx(0.045)
    assert cw_c == pytest.approx(0.562)

    # Unknown model returns all-zero tuple, family "unknown".
    assert _lookup_pricing("not-a-real-model")[4] == "unknown"


def test_compute_cost_cents_with_cache_hit_uses_cache_read_rate():
    # 10_000 input tokens of which 9_000 are a cache read; 500 output.
    # Expected: 1_000 * 0.450/1000 + 500 * 2.250/1000 + 9_000 * 0.045/1000
    #         = 0.45 + 1.125 + 0.405 = 1.98 cents
    cost = _compute_cost_cents(
        "claude-sonnet-4-5",
        prompt_tokens=10_000,
        completion_tokens=500,
        cache_read_tokens=9_000,
    )
    assert cost == pytest.approx(1.98, rel=1e-3)

    # Without cache, same tokens cost much more.
    cost_nocache = _compute_cost_cents(
        "claude-sonnet-4-5",
        prompt_tokens=10_000,
        completion_tokens=500,
        cache_read_tokens=0,
    )
    assert cost_nocache > cost
    assert cost_nocache == pytest.approx(10_000 * 0.450 / 1000 + 500 * 2.250 / 1000, rel=1e-3)


# ---------------------------------------------------------------------------
# Router path — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_first_succeeds_and_records_cost():
    def handler(req: httpx.Request) -> httpx.Response:
        # Must hit the Router, not Anthropic/OpenAI direct.
        assert "api.megapromoting.com" in str(req.url)
        assert req.headers["Authorization"] == "Bearer router-test-key"
        body = json.loads(req.content)
        assert body["model"] == "claude-sonnet-4-5"
        assert body["max_tokens"] == 256
        assert body["messages"][-1]["content"] == "ping"
        return httpx.Response(200, json=_router_ok_payload())

    client, recorder = _make_client(handler)
    async with client:
        resp = await client.complete("ping", model="claude-sonnet-4-5", max_tokens=256)

    assert isinstance(resp, LLMResponse)
    assert resp.provider == LLMProvider.ROUTER
    assert resp.content == "router-says-hi"
    assert resp.prompt_tokens == 100
    assert resp.completion_tokens == 50
    assert resp.fallback_used is False
    # 100 * 0.450/1000 + 50 * 2.250/1000 = 0.045 + 0.1125 = 0.1575 cents
    assert resp.cost_usd_cents == pytest.approx(0.1575, rel=1e-3)
    # Only one HTTP call.
    assert len(recorder.requests) == 1


# ---------------------------------------------------------------------------
# Router 500 → Anthropic fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_500_falls_back_to_anthropic():
    def handler(req: httpx.Request) -> httpx.Response:
        host = req.url.host
        if "megapromoting" in host:
            return httpx.Response(500, text="boom")
        if "anthropic.com" in host:
            return httpx.Response(200, json=_anthropic_ok_payload())
        raise AssertionError(f"unexpected host {host}")

    client, recorder = _make_client(handler)
    async with client:
        resp = await client.complete("ping", model="claude-sonnet-4-5", max_tokens=256)

    assert resp.provider == LLMProvider.ANTHROPIC
    assert resp.fallback_used is True
    assert resp.content == "anthropic-says-hi"
    # Router hit + Anthropic hit.
    urls = recorder.urls()
    assert any("megapromoting" in u for u in urls)
    assert any("anthropic.com" in u for u in urls)


# ---------------------------------------------------------------------------
# Router 429 also falls back
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_429_falls_back_to_anthropic():
    def handler(req: httpx.Request) -> httpx.Response:
        if "megapromoting" in req.url.host:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, json=_anthropic_ok_payload())

    client, _ = _make_client(handler)
    async with client:
        resp = await client.complete("ping", model="claude-sonnet-4-5", max_tokens=256)
    assert resp.provider == LLMProvider.ANTHROPIC
    assert resp.fallback_used is True


# ---------------------------------------------------------------------------
# Both Router + Anthropic down → OpenAI catches it
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anthropic_failure_falls_through_to_openai():
    def handler(req: httpx.Request) -> httpx.Response:
        host = req.url.host
        if "megapromoting" in host:
            return httpx.Response(503, text="router down")
        if "anthropic.com" in host:
            return httpx.Response(500, text="anthropic down")
        if "openai.com" in host:
            return httpx.Response(200, json=_openai_ok_payload())
        raise AssertionError(host)

    client, recorder = _make_client(handler)
    async with client:
        resp = await client.complete("ping", model="gpt-4o-mini", max_tokens=256)
    assert resp.provider == LLMProvider.OPENAI
    assert resp.fallback_used is True
    # All three providers hit.
    urls = recorder.urls()
    assert sum(1 for u in urls if "megapromoting" in u) == 1
    assert sum(1 for u in urls if "anthropic.com" in u) == 1
    assert sum(1 for u in urls if "openai.com" in u) == 1


# ---------------------------------------------------------------------------
# Anthropic prompt caching — large system prompt gets cache_control
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anthropic_large_system_prompt_attaches_cache_control():
    captured: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        if "megapromoting" in req.url.host:
            return httpx.Response(500, text="force fallback")
        if "anthropic.com" in req.url.host:
            captured["body"] = json.loads(req.content)
            captured["headers"] = dict(req.headers)
            return httpx.Response(
                200,
                json=_anthropic_ok_payload(
                    input_tokens=12_000,
                    cache_creation_tokens=10_000,
                ),
            )
        raise AssertionError(req.url.host)

    big_system = "A" * (ANTHROPIC_CACHE_MIN_CHARS + 50)
    client, _ = _make_client(handler)
    async with client:
        resp = await client.complete(
            "ping",
            model="claude-sonnet-4-5",
            max_tokens=256,
            system=big_system,
        )

    body = captured["body"]
    assert isinstance(body["system"], list)
    assert body["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert captured["headers"]["anthropic-beta"] == "prompt-caching-2024-07-31"
    assert resp.cache_write_tokens == 10_000


@pytest.mark.asyncio
async def test_anthropic_small_system_prompt_is_plain_string():
    captured: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        if "megapromoting" in req.url.host:
            return httpx.Response(500, text="fallback")
        if "anthropic.com" in req.url.host:
            captured["body"] = json.loads(req.content)
            return httpx.Response(200, json=_anthropic_ok_payload())
        raise AssertionError(req.url.host)

    client, _ = _make_client(handler)
    async with client:
        await client.complete(
            "ping",
            model="claude-sonnet-4-5",
            max_tokens=256,
            system="short system",
        )
    assert captured["body"]["system"] == "short system"


# ---------------------------------------------------------------------------
# Cache hit accounting via Router
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_cache_hit_accounting():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_router_ok_payload(
                prompt_tokens=10_000,
                completion_tokens=500,
                cached_tokens=9_000,
                cache_creation_tokens=0,
            ),
        )

    client, _ = _make_client(handler)
    async with client:
        resp = await client.complete("ping", model="claude-sonnet-4-5", max_tokens=1024)

    assert resp.cache_read_tokens == 9_000
    # See test_compute_cost_cents_with_cache_hit_uses_cache_read_rate.
    assert resp.cost_usd_cents == pytest.approx(1.98, rel=1e-3)


# ---------------------------------------------------------------------------
# All providers fail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_providers_fail_raises_runtime_error():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="everything is on fire")

    client, _ = _make_client(handler)
    async with client:
        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            await client.complete("ping", model="claude-sonnet-4-5", max_tokens=64)


# ---------------------------------------------------------------------------
# Missing Router key surfaces as RouterError, then falls back
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_router_key_falls_back_to_anthropic():
    def handler(req: httpx.Request) -> httpx.Response:
        if "anthropic.com" in req.url.host:
            return httpx.Response(200, json=_anthropic_ok_payload())
        raise AssertionError(f"router should not be called; got {req.url}")

    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    client = LLMClient(
        router_base="https://api.megapromoting.com/v1",
        router_key="",  # missing!
        anthropic_key="anthropic-test-key",
        openai_key="openai-test-key",
        http_client=http,
    )
    async with client:
        resp = await client.complete("ping", model="claude-sonnet-4-5", max_tokens=64)
    assert resp.provider == LLMProvider.ANTHROPIC
    assert resp.fallback_used is True


# ---------------------------------------------------------------------------
# Confidential backend metadata passthrough
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confidential_backend_attached_to_response():
    backend = ConfidentialBackend(
        enabled=True,
        attestation="dGVzdA==",
        node_id="pcc-node-eu-west-3-7",
        enclave_type="apple-pcc",
    )

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_router_ok_payload())

    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    client = LLMClient(
        router_base="https://api.megapromoting.com/v1",
        router_key="k",
        http_client=http,
        confidential=backend,
    )
    async with client:
        resp = await client.complete("ping", model="claude-sonnet-4-5", max_tokens=64)
    assert resp.confidential.enabled is True
    assert resp.confidential.node_id == "pcc-node-eu-west-3-7"
    assert resp.confidential.enclave_type == "apple-pcc"


# ---------------------------------------------------------------------------
# Process-wide cost tracker accumulates across calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_tracker_accumulates_across_calls():
    tracker = get_cost_tracker()
    before = tracker.snapshot()

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_router_ok_payload(
                prompt_tokens=200,
                completion_tokens=100,
            ),
        )

    client, _ = _make_client(handler)
    async with client:
        await client.complete("a", model="claude-sonnet-4-5", max_tokens=64)
        await client.complete("b", model="claude-sonnet-4-5", max_tokens=64)

    after = tracker.snapshot()
    assert after["requests"] == before["requests"] + 2
    assert after["prompt_tokens"] == before["prompt_tokens"] + 400
    assert after["completion_tokens"] == before["completion_tokens"] + 200
    assert after["cost_usd_cents"] > before["cost_usd_cents"]


# ---------------------------------------------------------------------------
# RouterAdapter directly: 4xx is surfaced
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_adapter_raises_on_4xx():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="bad key")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        adapter = RouterAdapter(
            base_url="https://api.megapromoting.com/v1",
            api_key="bad",
            http_client=http,
        )
        with pytest.raises(RouterError, match="4xx"):
            await adapter.chat_completions(
                model="claude-sonnet-4-5",
                messages=[{"role": "user", "content": "x"}],
                max_tokens=8,
            )
