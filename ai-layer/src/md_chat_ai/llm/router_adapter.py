"""
Router by MP adapter — talks to Mega Promoting's internal AI gateway.

Router by MP is an OpenAI-compatible aggregator at
``https://api.megapromoting.com/v1`` with a 50%+ markup policy applied at
the gateway. Client-facing prices are USD (cents); raw upstream provider
costs are intentionally hidden from MD-Chat (Router by MP convention).

Endpoint shape:
    POST /v1/chat/completions
    Authorization: Bearer <ROUTER_API_KEY>
    Body: standard OpenAI ChatCompletion request.

This adapter is intentionally thin — heavy lifting (fallback chain, cost
tracking, cache accounting) lives in :class:`md_chat_ai.llm.client.LLMClient`.

----------------------------------------------------------------------------
Copyright 2026 Mega Promoting SRL.
SPDX-License-Identifier: Apache-2.0
----------------------------------------------------------------------------
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("md_chat_ai.llm.router")


class RouterError(RuntimeError):
    """Raised when the Router gateway returns a non-2xx response or is unreachable."""


class RouterAdapter:
    """Async adapter for the Router by MP chat-completions endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        http_client: httpx.AsyncClient,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http_client
        self._timeout = timeout_seconds

    @property
    def base_url(self) -> str:
        return self._base_url

    async def chat_completions(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float = 0.7,
        extra_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        POST /v1/chat/completions through Router by MP.

        Returns the parsed JSON response (OpenAI-compatible shape).
        Raises :class:`RouterError` on any non-2xx status or transport error.
        """
        if not self._api_key:
            raise RouterError("Router API key is empty")

        # GPT-5 / o-series use max_completion_tokens at the OpenAI layer.
        restricted = any(k in model.lower() for k in ("gpt-5", "o1-", "o3", "o4"))
        token_key = "max_completion_tokens" if restricted else "max_tokens"

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            token_key: max_tokens,
        }
        if not restricted:
            payload["temperature"] = temperature
        if extra_body:
            payload.update(extra_body)

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-MD-Chat-Adapter": "router-by-mp/1.0",
        }

        try:
            r = await self._http.post(url, json=payload, headers=headers, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise RouterError(f"Router transport error: {exc}") from exc

        if r.status_code >= 500:
            raise RouterError(f"Router 5xx: status={r.status_code} body={r.text[:200]!r}")
        if r.status_code == 429:
            raise RouterError(f"Router rate-limited (429): {r.text[:200]!r}")
        if r.status_code >= 400:
            # 4xx is a permanent client error — surface as RouterError so the
            # caller can decide whether to fall back or fail loudly.
            raise RouterError(f"Router 4xx: status={r.status_code} body={r.text[:200]!r}")

        try:
            return r.json()
        except ValueError as exc:
            raise RouterError(f"Router returned non-JSON: {exc}") from exc


__all__ = ["RouterAdapter", "RouterError"]
