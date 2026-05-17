"""
Multi-provider async LLM client for MD-Chat AI layer.

Routing order:
  1. Router by MP   — https://api.megapromoting.com/v1 (primary; OpenAI-compatible
                       gateway with 50%+ markup transparency, billed in client-facing
                       USD cents per Router by MP convention).
  2. On-device      — Llama 3.2 3B placeholder for confidential compute (stub).
  3. Anthropic      — direct via httpx (uses ``messages`` API, prompt caching).
  4. OpenAI         — direct via httpx fallback (chat completions API).

Each LLM call returns an :class:`LLMResponse` capturing token usage, cache
read/write counts, and ``cost_usd_cents`` (post-markup, client-facing).

Anthropic prompt caching is applied aggressively: any system prompt over
1024 characters is annotated with ``cache_control: {"type": "ephemeral"}``.
In Cronberry production this drives an 80-90% input-token cost reduction.

Ported and adapted from Cronberry (cronberry_swarm/llm/client.py).
Cronberry is the upstream project; this file inherits its Apache-2.0 license.

----------------------------------------------------------------------------
Copyright 2026 Mega Promoting SRL.
Portions Copyright 2025 Cronberry contributors — used under Apache License 2.0.
SPDX-License-Identifier: Apache-2.0
----------------------------------------------------------------------------
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..config import CONFIG
from .router_adapter import RouterAdapter, RouterError

logger = logging.getLogger("md_chat_ai.llm")


# ---------------------------------------------------------------------------
# Model registry — pricing in USD cents per 1k tokens (post-markup client-facing).
# Router by MP convention: prices are already marked-up; we record what the
# CLIENT pays, not raw provider cost. Markup floor is 50% by policy.
# ---------------------------------------------------------------------------
# Format: model_id: (input_cents_per_1k, output_cents_per_1k, cache_read_cents_per_1k,
#                    cache_write_cents_per_1k, family)
_MODEL_REGISTRY: Dict[str, Tuple[float, float, float, float, str]] = {
    # Anthropic Claude — cache_read = 10% of input, cache_write = 125% of input
    "claude-opus-4-5":          (2.250, 11.250, 0.225, 2.812, "anthropic"),
    "claude-opus-4-1":          (2.250, 11.250, 0.225, 2.812, "anthropic"),
    "claude-sonnet-4-5":        (0.450,  2.250, 0.045, 0.562, "anthropic"),
    "claude-sonnet-4":          (0.450,  2.250, 0.045, 0.562, "anthropic"),
    "claude-haiku-4-5":         (0.150,  0.750, 0.015, 0.187, "anthropic"),
    "claude-3-5-sonnet-latest": (0.450,  2.250, 0.045, 0.562, "anthropic"),
    "claude-3-5-haiku-latest":  (0.150,  0.750, 0.015, 0.187, "anthropic"),
    # OpenAI GPT-4o family
    "gpt-4o":                   (0.375,  1.500, 0.187, 0.0,   "openai"),
    "gpt-4o-mini":              (0.022,  0.090, 0.011, 0.0,   "openai"),
    "gpt-4.1":                  (0.300,  1.200, 0.075, 0.0,   "openai"),
    "gpt-4.1-mini":             (0.060,  0.240, 0.015, 0.0,   "openai"),
    # Google Gemini 2.5 family
    "gemini-2.5-pro":           (0.187,  1.125, 0.0,   0.0,   "google"),
    "gemini-2.5-flash":         (0.045,  0.262, 0.0,   0.0,   "google"),
    "gemini-2.5-flash-lite":    (0.015,  0.060, 0.0,   0.0,   "google"),
    # DeepSeek
    "deepseek-chat":            (0.041,  0.165, 0.010, 0.0,   "deepseek"),
    "deepseek-reasoner":        (0.082,  0.330, 0.020, 0.0,   "deepseek"),
    # Mistral
    "mistral-large-latest":     (0.300,  0.900, 0.0,   0.0,   "mistral"),
    "mistral-small-latest":     (0.030,  0.090, 0.0,   0.0,   "mistral"),
    # Meta Llama (served via Router; on-device path uses local weights)
    "llama-3.3-70b":            (0.088,  0.118, 0.0,   0.0,   "meta"),
    "llama-3.2-3b":             (0.0,    0.0,   0.0,   0.0,   "local"),  # on-device
}


def _lookup_pricing(
    model: str,
) -> Tuple[float, float, float, float, str]:
    """Return (input, output, cache_read, cache_write, family) cents-per-1k."""
    exact = _MODEL_REGISTRY.get(model)
    if exact:
        return exact
    # Prefix match — keep the longest match wins
    candidates = [k for k in _MODEL_REGISTRY if model.startswith(k) or k.startswith(model)]
    if candidates:
        best = max(candidates, key=len)
        return _MODEL_REGISTRY[best]
    return (0.0, 0.0, 0.0, 0.0, "unknown")


def _compute_cost_cents(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """Return post-markup client-facing cost in USD cents."""
    in_c, out_c, cr_c, cw_c, _ = _lookup_pricing(model)
    # Cached input tokens are billed at the cache-read rate, not full input rate.
    full_input = max(0, prompt_tokens - cache_read_tokens)
    return (
        full_input          * in_c  / 1000.0
        + completion_tokens * out_c / 1000.0
        + cache_read_tokens * cr_c  / 1000.0
        + cache_write_tokens * cw_c / 1000.0
    )


# ---------------------------------------------------------------------------
# Confidential compute hook (Apple PCC / NVIDIA H100 CC stub).
# ---------------------------------------------------------------------------

@dataclass
class ConfidentialBackend:
    """
    Placeholder for confidential-compute attestation metadata.

    Future versions will attach Apple PCC node certificates or NVIDIA H100
    confidential-compute attestation reports. For now this records intent only
    so the response shape is forward-compatible.
    """

    enabled: bool = False
    attestation: Optional[str] = None  # base64-encoded report when enabled
    node_id: Optional[str] = None      # e.g. "pcc-node-eu-west-3-7"
    enclave_type: Optional[str] = None  # "apple-pcc" | "nvidia-h100-cc" | "amd-sev"


# ---------------------------------------------------------------------------
# Provider + response dataclasses
# ---------------------------------------------------------------------------

class LLMProvider(str, Enum):
    """Identifies which backend ultimately served the request."""

    ROUTER = "router"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    ON_DEVICE = "on_device"


@dataclass
class LLMResponse:
    """Structured response from :meth:`LLMClient.complete`."""

    content: str
    model: str
    provider: LLMProvider
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd_cents: float = 0.0
    latency_ms: float = 0.0
    fallback_used: bool = False
    confidential: ConfidentialBackend = field(default_factory=ConfidentialBackend)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def cost_usd(self) -> float:
        """Convenience: cost in dollars."""
        return self.cost_usd_cents / 100.0


# ---------------------------------------------------------------------------
# Cost tracker (process-wide)
# ---------------------------------------------------------------------------

@dataclass
class CostTracker:
    """Async-safe accumulator for cost/usage stats across the process."""

    total_cost_cents: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_write_tokens: int = 0
    total_requests: int = 0
    total_fallbacks: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def record(self, response: LLMResponse) -> None:
        async with self._lock:
            self.total_cost_cents += response.cost_usd_cents
            self.total_prompt_tokens += response.prompt_tokens
            self.total_completion_tokens += response.completion_tokens
            self.total_cache_read_tokens += response.cache_read_tokens
            self.total_cache_write_tokens += response.cache_write_tokens
            self.total_requests += 1
            if response.fallback_used:
                self.total_fallbacks += 1

    def snapshot(self) -> Dict[str, Any]:
        return {
            "requests": self.total_requests,
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "cache_read_tokens": self.total_cache_read_tokens,
            "cache_write_tokens": self.total_cache_write_tokens,
            "cost_usd_cents": round(self.total_cost_cents, 4),
            "cost_usd": round(self.total_cost_cents / 100.0, 4),
            "fallbacks": self.total_fallbacks,
        }


_global_tracker = CostTracker()


def get_cost_tracker() -> CostTracker:
    """Return the process-wide cost tracker."""
    return _global_tracker


# ---------------------------------------------------------------------------
# LLMClient — async, Router-first with fallback chain
# ---------------------------------------------------------------------------

# System-prompt size threshold for Anthropic ephemeral caching (chars ≈ tokens × 4).
# 1024 tokens × ~4 chars = ~4096 chars. We trigger above 1024 tokens estimated.
ANTHROPIC_CACHE_MIN_TOKENS = 1024
ANTHROPIC_CACHE_MIN_CHARS = ANTHROPIC_CACHE_MIN_TOKENS * 4


class LLMClient:
    """
    Async multi-provider LLM client with Router-first routing and cost tracking.

    Public API (stable; downstream modules depend on it):

        async def complete(prompt, *, model, max_tokens, system=None) -> LLMResponse
    """

    def __init__(
        self,
        *,
        router_base: Optional[str] = None,
        router_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
        openai_key: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        confidential: Optional[ConfidentialBackend] = None,
        timeout_seconds: float = 60.0,
        enable_on_device: bool = False,
    ) -> None:
        self._router_base = router_base or CONFIG.router_base
        self._router_key = router_key or CONFIG.router_key
        # Direct-provider keys live outside CONFIG today; pull from env at call sites.
        import os
        self._anthropic_key = anthropic_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._openai_key = openai_key or os.getenv("OPENAI_API_KEY", "")
        self._timeout = timeout_seconds
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout_seconds)
        self._confidential = confidential or ConfidentialBackend()
        self._enable_on_device = enable_on_device

        self._router = RouterAdapter(
            base_url=self._router_base,
            api_key=self._router_key,
            http_client=self._http,
            timeout_seconds=timeout_seconds,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> "LLMClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int,
        system: Optional[str] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Run a single completion. Routes through Router by MP first; on failure
        falls back through on-device → Anthropic → OpenAI.
        """
        attempts: List[Tuple[LLMProvider, Any]] = [
            (LLMProvider.ROUTER, self._call_router),
        ]
        if self._enable_on_device:
            attempts.append((LLMProvider.ON_DEVICE, self._call_on_device))
        attempts.append((LLMProvider.ANTHROPIC, self._call_anthropic))
        attempts.append((LLMProvider.OPENAI, self._call_openai))

        last_error: Optional[Exception] = None
        for idx, (provider, fn) in enumerate(attempts):
            try:
                t0 = time.monotonic()
                resp = await fn(
                    prompt=prompt,
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    temperature=temperature,
                )
                resp.latency_ms = (time.monotonic() - t0) * 1000.0
                resp.fallback_used = idx > 0
                resp.confidential = self._confidential
                await _global_tracker.record(resp)
                return resp
            except Exception as exc:  # noqa: BLE001 — we re-raise after exhausting
                last_error = exc
                logger.warning(
                    "LLM provider %s failed: %s — trying next",
                    provider.value, exc,
                )

        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    # ------------------------------------------------------------------
    # Provider call paths
    # ------------------------------------------------------------------

    async def _call_router(
        self,
        *,
        prompt: str,
        model: str,
        max_tokens: int,
        system: Optional[str],
        temperature: float,
    ) -> LLMResponse:
        if not self._router_key:
            raise RouterError("ROUTER_API_KEY not configured")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        data = await self._router.chat_completions(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        usage = data.get("usage", {}) or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        # Router exposes cache stats via OpenAI's prompt_tokens_details / cached_tokens.
        details = usage.get("prompt_tokens_details", {}) or {}
        cache_read = int(details.get("cached_tokens", 0))
        cache_write = int(usage.get("cache_creation_input_tokens", 0))

        content = data["choices"][0]["message"]["content"] or ""
        cost = _compute_cost_cents(
            model, prompt_tokens, completion_tokens, cache_read, cache_write
        )
        return LLMResponse(
            content=content,
            model=model,
            provider=LLMProvider.ROUTER,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_tokens=cache_read,
            cache_write_tokens=cache_write,
            cost_usd_cents=cost,
        )

    async def _call_anthropic(
        self,
        *,
        prompt: str,
        model: str,
        max_tokens: int,
        system: Optional[str],
        temperature: float,
    ) -> LLMResponse:
        if not self._anthropic_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")

        # Anthropic system prompts go in a top-level `system` field; we pass it as
        # an array of blocks so we can attach cache_control on large prompts.
        payload: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            if len(system) >= ANTHROPIC_CACHE_MIN_CHARS:
                payload["system"] = [
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                payload["system"] = system

        headers = {
            "x-api-key": self._anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        # Cache-control header is auto-enabled in newer API versions, but we
        # opt in explicitly to keep compatibility with older accounts.
        if isinstance(payload.get("system"), list):
            headers["anthropic-beta"] = "prompt-caching-2024-07-31"

        r = await self._http.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers,
            timeout=self._timeout,
        )
        r.raise_for_status()
        data = r.json()

        # Anthropic returns content as an array of blocks; concat text blocks.
        content = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )
        usage = data.get("usage", {}) or {}
        prompt_tokens = int(usage.get("input_tokens", 0))
        completion_tokens = int(usage.get("output_tokens", 0))
        cache_read = int(usage.get("cache_read_input_tokens", 0))
        cache_write = int(usage.get("cache_creation_input_tokens", 0))

        cost = _compute_cost_cents(
            model, prompt_tokens, completion_tokens, cache_read, cache_write
        )
        return LLMResponse(
            content=content,
            model=model,
            provider=LLMProvider.ANTHROPIC,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_tokens=cache_read,
            cache_write_tokens=cache_write,
            cost_usd_cents=cost,
        )

    async def _call_openai(
        self,
        *,
        prompt: str,
        model: str,
        max_tokens: int,
        system: Optional[str],
        temperature: float,
    ) -> LLMResponse:
        if not self._openai_key:
            raise RuntimeError("OPENAI_API_KEY not configured")

        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # GPT-5 / o-series have different param names (Cronberry pattern preserved).
        restricted = any(k in model.lower() for k in ("gpt-5", "o1-", "o3", "o4"))
        token_key = "max_completion_tokens" if restricted else "max_tokens"

        payload: Dict[str, Any] = {"model": model, "messages": messages, token_key: max_tokens}
        if not restricted:
            payload["temperature"] = temperature

        r = await self._http.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {self._openai_key}",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
        )
        r.raise_for_status()
        data = r.json()

        content = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {}) or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        details = usage.get("prompt_tokens_details", {}) or {}
        cache_read = int(details.get("cached_tokens", 0))

        cost = _compute_cost_cents(
            model, prompt_tokens, completion_tokens, cache_read, 0
        )
        return LLMResponse(
            content=content,
            model=model,
            provider=LLMProvider.OPENAI,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_tokens=cache_read,
            cost_usd_cents=cost,
        )

    async def _call_on_device(
        self,
        *,
        prompt: str,
        model: str,
        max_tokens: int,
        system: Optional[str],
        temperature: float,
    ) -> LLMResponse:
        """
        Placeholder for on-device inference (Llama 3.2 3B via llama.cpp or MLX).

        Today this always raises NotImplementedError so the chain advances to
        Anthropic. The interface is in place so a future PR can wire up a
        local runtime without touching the surrounding fallback logic.
        """
        raise NotImplementedError("on-device backend not yet wired up")


__all__ = [
    "LLMClient",
    "LLMResponse",
    "LLMProvider",
    "CostTracker",
    "ConfidentialBackend",
    "get_cost_tracker",
]
