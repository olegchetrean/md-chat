"""Tests for the sync compatibility shim on LLMClient (chat / chat_json).

The Cronberry-derived twin code calls ``self.llm.chat(...)`` and
``self.llm.chat_json(...)`` synchronously. These bridge to the async
``complete()`` and must:

1. Convert OpenAI-style messages to (prompt, system).
2. Run the async coroutine via ``asyncio.run()``.
3. Refuse to run inside an existing event loop (raises a clear error).
4. ``chat_json`` strips ```code fences``` and falls back to ``{}`` on parse failure.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from md_chat_ai.llm.client import LLMClient, LLMResponse


def _make_response(content: str) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="claude-sonnet-4-5",
        provider="router",  # type: ignore[arg-type]  -- string accepted by Enum cast
        prompt_tokens=10,
        completion_tokens=5,
        cache_read_tokens=0,
        cache_write_tokens=0,
        cost_usd_cents=1,
    )


def test_flatten_messages_extracts_system_and_concats_user():
    msgs = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
    ]
    prompt, system = LLMClient._flatten_messages(msgs)
    assert system == "You are a helpful assistant."
    assert "USER: Hello" in prompt
    assert "ASSISTANT: Hi there!" in prompt
    assert "USER: How are you?" in prompt


def test_flatten_messages_concatenates_multiple_system_turns():
    msgs = [
        {"role": "system", "content": "Be brief."},
        {"role": "system", "content": "Romanian only."},
        {"role": "user", "content": "Salut"},
    ]
    _, system = LLMClient._flatten_messages(msgs)
    assert "Be brief." in system
    assert "Romanian only." in system


def test_flatten_messages_empty_input_returns_space():
    prompt, system = LLMClient._flatten_messages([])
    assert prompt == " "
    assert system is None


def test_chat_returns_content_via_complete():
    client = LLMClient()
    fake_resp = _make_response("hello!")
    client.complete = AsyncMock(return_value=fake_resp)  # type: ignore[method-assign]

    result = client.chat([{"role": "user", "content": "hi"}])
    assert result == "hello!"

    # Verify complete() was called with the flattened prompt + system.
    client.complete.assert_awaited_once()
    kwargs = client.complete.await_args.kwargs
    assert "USER: hi" in client.complete.await_args.args[0] or kwargs.get("system") is None


def test_chat_passes_through_temperature_and_max_tokens():
    client = LLMClient()
    fake_resp = _make_response("ok")
    client.complete = AsyncMock(return_value=fake_resp)  # type: ignore[method-assign]

    client.chat(
        [{"role": "user", "content": "hi"}],
        model="claude-haiku-4-5",
        max_tokens=512,
        temperature=0.2,
    )

    kwargs = client.complete.await_args.kwargs
    assert kwargs["model"] == "claude-haiku-4-5"
    assert kwargs["max_tokens"] == 512
    assert kwargs["temperature"] == 0.2


def test_chat_json_parses_clean_json():
    client = LLMClient()
    fake_resp = _make_response('{"key": "value", "n": 42}')
    client.complete = AsyncMock(return_value=fake_resp)  # type: ignore[method-assign]

    result = client.chat_json([{"role": "user", "content": "give me JSON"}])
    assert result == {"key": "value", "n": 42}


def test_chat_json_strips_code_fence():
    client = LLMClient()
    fake_resp = _make_response('```json\n{"wrapped": true}\n```')
    client.complete = AsyncMock(return_value=fake_resp)  # type: ignore[method-assign]

    result = client.chat_json([{"role": "user", "content": "give me JSON"}])
    assert result == {"wrapped": True}


def test_chat_json_strips_bare_fence():
    client = LLMClient()
    fake_resp = _make_response('```\n{"x": 1}\n```')
    client.complete = AsyncMock(return_value=fake_resp)  # type: ignore[method-assign]

    result = client.chat_json([{"role": "user", "content": "give me JSON"}])
    assert result == {"x": 1}


def test_chat_json_returns_empty_dict_on_parse_failure():
    client = LLMClient()
    fake_resp = _make_response("this is not JSON at all, sorry")
    client.complete = AsyncMock(return_value=fake_resp)  # type: ignore[method-assign]

    result = client.chat_json([{"role": "user", "content": "give me JSON"}])
    assert result == {}


def test_chat_raises_inside_running_event_loop():
    client = LLMClient()
    client.complete = AsyncMock(return_value=_make_response("ok"))  # type: ignore[method-assign]

    async def _run_inside_loop():
        # Inside the async function — chat() should refuse.
        with pytest.raises(RuntimeError, match="cannot be used inside an async context"):
            client.chat([{"role": "user", "content": "hi"}])

    asyncio.run(_run_inside_loop())


def test_chat_json_default_temperature_is_lower():
    """JSON mode defaults to lower temperature (0.5) than free chat (0.7)."""
    client = LLMClient()
    client.complete = AsyncMock(return_value=_make_response('{"ok": true}'))  # type: ignore[method-assign]

    client.chat_json([{"role": "user", "content": "hi"}])
    kwargs = client.complete.await_args.kwargs
    assert kwargs["temperature"] == 0.5
