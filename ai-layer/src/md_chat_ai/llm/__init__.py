"""
Multi-provider async LLM client for MD-Chat AI layer.

Ported from Cronberry (Apache-2.0). Routes through Router by MP as the
primary backend with fallback chain on-device → Anthropic → OpenAI.

Public surface:

    from md_chat_ai.llm import LLMClient, LLMResponse

    async with LLMClient() as llm:
        resp = await llm.complete(
            "Hello", model="claude-sonnet-4-5", max_tokens=256,
        )
        print(resp.content, resp.cost_usd_cents)
"""

from .client import (
    ConfidentialBackend,
    CostTracker,
    LLMClient,
    LLMProvider,
    LLMResponse,
    get_cost_tracker,
)
from .router_adapter import RouterAdapter, RouterError

__all__ = [
    "LLMClient",
    "LLMResponse",
    "LLMProvider",
    "CostTracker",
    "ConfidentialBackend",
    "RouterAdapter",
    "RouterError",
    "get_cost_tracker",
]
