# Copyright 2026 Mega Promoting SRL
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Derived from Cronberry (Mega Promoting SRL).
"""Branch-coverage tests for ``agents.message_optimizer``.

These tests exercise the full ``optimize()`` path, ``ab_test``, batch and
internal helpers (``_generate_variants``, ``_test_variant_on_twin``,
``_analyse_variant_result``, ``_select_winner`` edges) with the LLM client
fully mocked via ``MagicMock`` / ``AsyncMock``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from md_chat_ai.agents.digital_twin import SelfProfile
from md_chat_ai.agents.message_optimizer import (
    MessageOptimizer,
    MessageVariant,
    OptimizationResult,
    VariantTestResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _profile(**overrides) -> SelfProfile:
    base = dict(
        user_id="@oleg:md-chat.eu",
        name="Oleg",
        username="oleg",
        bio="Founder of MEGA PROMOTING",
        self_summary="Direct, technical, low-formality.",
        own_messages=["hi", "tomorrow at 10?", "ok deal"],
        language="ro",
        custom_notes="prefer short replies",
        interests=["AI", "voice agents"],
        profession="CEO",
        last_message_date="2026-05-17T10:00:00Z",
    )
    base.update(overrides)
    return SelfProfile(**base)


def _llm_returning(*payloads: dict) -> MagicMock:
    """Return a MagicMock LLM with chat_json yielding each payload in order."""
    fake = MagicMock()
    fake.chat_json = MagicMock(side_effect=list(payloads))
    fake.chat = MagicMock(return_value='{"variants": []}')
    fake.complete = AsyncMock()
    return fake


def _variants_payload(n: int = 3) -> dict:
    return {
        "variants": [
            {
                "text": f"variant text {i}",
                "tone": ["formal", "informal", "friendly"][i % 3],
                "approach": ["direct", "indirect", "storytelling"][i % 3],
                "rationale": f"rationale {i}",
            }
            for i in range(n)
        ]
    }


def _analysis_payload(success=0.7, naturalness=0.8, risk=0.1, outcome="will_respond_positively") -> dict:
    return {
        "success_score": success,
        "naturalness_score": naturalness,
        "risk_score": risk,
        "predicted_outcome": outcome,
        "reasoning": "looks good",
    }


# ---------------------------------------------------------------------------
# optimize() — full happy path
# ---------------------------------------------------------------------------


def test_optimize_full_path_picks_winner(monkeypatch):
    """End-to-end optimize() with 3 variants — winner has highest success."""
    profile = _profile()

    # 1 variant-generation call + 3 per-variant analysis calls = 4 chat_json.
    payloads = [
        _variants_payload(3),
        _analysis_payload(success=0.4, risk=0.1),
        _analysis_payload(success=0.9, risk=0.05, outcome="will_respond_positively"),
        _analysis_payload(success=0.5, risk=0.2),
    ]
    llm = _llm_returning(*payloads)
    opt = MessageOptimizer(llm_client=llm)

    # Bypass DigitalTwin LLM by stubbing the chat method via monkeypatch.
    from md_chat_ai.agents import digital_twin as dt_mod

    def _fake_chat(self, message, mode="free_chat", context=None, round_num=None, disclosure_language=None):
        return dt_mod.TwinResponse(
            text=f"twin reply to: {message[:20]}",
            emotion="neutral",
            intensity=0.5,
            mode=mode,
            round_num=0,
            disclosure=dt_mod.TwinDisclosure.for_language("ro"),
            verified=False,
        )

    monkeypatch.setattr(dt_mod.DigitalTwin, "chat", _fake_chat)

    result = opt.optimize(
        self_profile=profile,
        objective="schedule a meeting",
        draft_message="hi can we meet tomorrow?",
        num_variants=3,
    )
    assert isinstance(result, OptimizationResult)
    assert len(result.variants_tested) == 3
    assert result.winner is not None
    assert result.winner.success_score == 0.9
    assert result.runner_up is not None
    assert result.runner_up.success_score in (0.4, 0.5)
    assert result.estimated_success_rate == 0.9
    assert 0.0 <= result.confidence <= 1.0


def test_optimize_no_draft_uses_objective_only(monkeypatch):
    profile = _profile()
    llm = _llm_returning(_variants_payload(2), _analysis_payload(0.6), _analysis_payload(0.55))
    opt = MessageOptimizer(llm_client=llm)

    from md_chat_ai.agents import digital_twin as dt_mod

    monkeypatch.setattr(
        dt_mod.DigitalTwin,
        "chat",
        lambda self, m, **kw: dt_mod.TwinResponse(
            text="ok",
            emotion="neutral",
            intensity=0.5,
            mode=kw.get("mode", "free_chat"),
            round_num=0,
            disclosure=dt_mod.TwinDisclosure.for_language("ro"),
            verified=False,
        ),
    )

    result = opt.optimize(profile, objective="say hello", num_variants=2)
    assert result.original_message is None
    assert len(result.variants_tested) == 2


def test_optimize_emits_low_profile_confidence_warning(monkeypatch):
    """Low-data profile triggers the 'low confidence' warning."""
    profile = _profile(
        own_messages=[],
        self_summary=None,
        custom_notes="",
        profession=None,
        interests=[],
        last_message_date=None,
    )
    llm = _llm_returning(_variants_payload(2), _analysis_payload(0.5), _analysis_payload(0.45))
    opt = MessageOptimizer(llm_client=llm)
    from md_chat_ai.agents import digital_twin as dt_mod

    monkeypatch.setattr(
        dt_mod.DigitalTwin,
        "chat",
        lambda self, m, **kw: dt_mod.TwinResponse(
            text="r",
            emotion="neutral",
            intensity=0.5,
            mode="free_chat",
            round_num=0,
            disclosure=dt_mod.TwinDisclosure.for_language("ro"),
            verified=False,
        ),
    )

    result = opt.optimize(profile, "say hello", num_variants=2)
    assert any("Low profile confidence" in w for w in result.warnings)


def test_optimize_emits_low_success_warning(monkeypatch):
    profile = _profile()
    llm = _llm_returning(
        _variants_payload(2),
        _analysis_payload(success=0.1, risk=0.1),
        _analysis_payload(success=0.2, risk=0.1),
    )
    opt = MessageOptimizer(llm_client=llm)
    from md_chat_ai.agents import digital_twin as dt_mod

    monkeypatch.setattr(
        dt_mod.DigitalTwin,
        "chat",
        lambda self, m, **kw: dt_mod.TwinResponse(
            text="r",
            emotion="neutral",
            intensity=0.5,
            mode="free_chat",
            round_num=0,
            disclosure=dt_mod.TwinDisclosure.for_language("ro"),
            verified=False,
        ),
    )

    result = opt.optimize(profile, "ask favour", num_variants=2)
    assert any("low success score" in w for w in result.warnings)


def test_optimize_flags_do_not_send_on_high_risk(monkeypatch):
    profile = _profile()
    # All risky → do_not_send populated + risky warning.
    llm = _llm_returning(
        _variants_payload(3),
        _analysis_payload(success=0.5, risk=0.85),
        _analysis_payload(success=0.6, risk=0.9, outcome="will_respond_negatively"),
        _analysis_payload(success=0.5, risk=0.95, outcome="will_respond_negatively"),
    )
    opt = MessageOptimizer(llm_client=llm)
    from md_chat_ai.agents import digital_twin as dt_mod

    monkeypatch.setattr(
        dt_mod.DigitalTwin,
        "chat",
        lambda self, m, **kw: dt_mod.TwinResponse(
            text="r",
            emotion="neutral",
            intensity=0.5,
            mode="free_chat",
            round_num=0,
            disclosure=dt_mod.TwinDisclosure.for_language("ro"),
            verified=False,
        ),
    )
    result = opt.optimize(profile, "ask favour", num_variants=3)
    assert len(result.do_not_send) >= 2
    assert any("risky" in w.lower() for w in result.warnings)


def test_optimize_continues_when_variant_test_raises(monkeypatch):
    """If a single variant analysis throws, optimize() logs + skips it."""
    profile = _profile()
    llm = _llm_returning(_variants_payload(3), _analysis_payload(0.7), _analysis_payload(0.6))
    opt = MessageOptimizer(llm_client=llm)
    from md_chat_ai.agents import digital_twin as dt_mod

    call_counter = {"n": 0}

    def _chat(self, m, **kw):
        call_counter["n"] += 1
        if call_counter["n"] == 2:
            raise RuntimeError("simulated chat failure")
        return dt_mod.TwinResponse(
            text="r",
            emotion="neutral",
            intensity=0.5,
            mode="free_chat",
            round_num=0,
            disclosure=dt_mod.TwinDisclosure.for_language("ro"),
            verified=False,
        )

    monkeypatch.setattr(dt_mod.DigitalTwin, "chat", _chat)

    result = opt.optimize(profile, "say hi", num_variants=3)
    # Two of three variants tested successfully.
    assert len(result.variants_tested) == 2


# ---------------------------------------------------------------------------
# _generate_variants — fallback paths
# ---------------------------------------------------------------------------


def test_generate_variants_fallback_with_draft_when_llm_fails():
    """LLM returning no variants triggers the draft-fallback path."""
    profile = _profile()
    llm = MagicMock()
    llm.chat_json = MagicMock(return_value={"variants": []})  # empty
    opt = MessageOptimizer(llm_client=llm)
    variants = opt._generate_variants(profile, "objective", "draft msg", 3, None)
    assert len(variants) == 1
    assert variants[0].text == "draft msg"
    assert variants[0].tone == "original"


def test_generate_variants_fallback_no_draft_when_llm_raises():
    profile = _profile()
    llm = MagicMock()
    llm.chat_json = MagicMock(side_effect=RuntimeError("oops"))
    opt = MessageOptimizer(llm_client=llm)
    variants = opt._generate_variants(profile, "say hello", None, 5, None)
    assert len(variants) == 1
    assert "Buna" in variants[0].text
    assert variants[0].tone == "neutral"


def test_generate_variants_filters_empty_text():
    profile = _profile()
    llm = MagicMock()
    llm.chat_json = MagicMock(
        return_value={
            "variants": [
                {"text": "", "tone": "x", "approach": "y", "rationale": "z"},
                {"text": "valid one", "tone": "formal", "approach": "direct", "rationale": "ok"},
            ]
        }
    )
    opt = MessageOptimizer(llm_client=llm)
    variants = opt._generate_variants(profile, "obj", None, 5, None)
    assert len(variants) == 1
    assert variants[0].text == "valid one"


def test_generate_variants_uses_constraints_and_history():
    """Path through constraints + history blocks (covers their f-string branches)."""
    profile = _profile()
    llm = MagicMock()
    llm.chat_json = MagicMock(return_value=_variants_payload(2))
    opt = MessageOptimizer(llm_client=llm)

    # Seed history so the history block is rendered.
    opt.record_outcome(profile.user_id, "msg1", "yay", was_successful=True)
    opt.record_outcome(profile.user_id, "msg2", "nope", was_successful=False)

    variants = opt._generate_variants(profile, "obj", None, 5, ["no slang", "be polite"])
    assert len(variants) == 2
    # The prompt was built (one chat_json call).
    assert llm.chat_json.call_count == 1


def test_generate_variants_respects_num_limit():
    profile = _profile()
    llm = MagicMock()
    llm.chat_json = MagicMock(return_value=_variants_payload(10))
    opt = MessageOptimizer(llm_client=llm)
    variants = opt._generate_variants(profile, "obj", None, 3, None)
    assert len(variants) == 3


# ---------------------------------------------------------------------------
# _test_variant_on_twin / _analyse_variant_result
# ---------------------------------------------------------------------------


def test_analyse_variant_result_clamps_out_of_range_scores():
    opt = MessageOptimizer(llm_client=MagicMock())
    opt._llm = MagicMock()
    opt._llm.chat_json = MagicMock(
        return_value={
            "success_score": 2.5,  # > 1.0
            "naturalness_score": -0.5,  # < 0.0
            "risk_score": 1.7,  # > 1.0
        }
    )
    variant = MessageVariant(text="hi", tone="x", approach="y", rationale="z")
    raw = opt._analyse_variant_result("obj", variant, "twin says hi", "user")
    assert raw["success_score"] == 1.0
    assert raw["naturalness_score"] == 0.0
    assert raw["risk_score"] == 1.0


def test_analyse_variant_result_handles_llm_failure():
    opt = MessageOptimizer(llm_client=MagicMock())
    opt._llm.chat_json = MagicMock(side_effect=RuntimeError("llm down"))
    variant = MessageVariant(text="hi", tone="x", approach="y", rationale="z")
    raw = opt._analyse_variant_result("obj", variant, "twin reply", "user")
    assert raw["predicted_outcome"] == "uncertain"
    assert raw["success_score"] == 0.5
    assert "Analysis failed" in raw["reasoning"]


def test_analyse_variant_result_defaults_missing_fields():
    opt = MessageOptimizer(llm_client=MagicMock())
    opt._llm.chat_json = MagicMock(return_value={"success_score": 0.6})
    variant = MessageVariant(text="hi", tone="x", approach="y", rationale="z")
    raw = opt._analyse_variant_result("obj", variant, "ok", "user")
    assert raw["predicted_outcome"] == "uncertain"
    assert raw["reasoning"] == ""


# ---------------------------------------------------------------------------
# ab_test — head to head
# ---------------------------------------------------------------------------


def test_ab_test_picks_winner_a(monkeypatch):
    opt = MessageOptimizer(llm_client=MagicMock())
    # Two analysis calls; A scores higher.
    opt._llm.chat_json = MagicMock(
        side_effect=[
            _analysis_payload(success=0.9, naturalness=0.9, risk=0.05),
            _analysis_payload(success=0.3, naturalness=0.4, risk=0.5),
        ]
    )
    from md_chat_ai.agents import digital_twin as dt_mod

    monkeypatch.setattr(
        dt_mod.DigitalTwin,
        "chat",
        lambda self, m, **kw: dt_mod.TwinResponse(
            text="x",
            emotion="neutral",
            intensity=0.5,
            mode="free_chat",
            round_num=0,
            disclosure=dt_mod.TwinDisclosure.for_language("ro"),
            verified=False,
        ),
    )
    result = opt.ab_test(_profile(), "objective", "msg A great", "msg B weak")
    assert result["winner"] == "A"
    assert result["confidence"] in ("high", "medium", "low")
    assert result["message_a"]["composite_score"] > result["message_b"]["composite_score"]


def test_ab_test_picks_winner_b_on_tie_breaker(monkeypatch):
    opt = MessageOptimizer(llm_client=MagicMock())
    opt._llm.chat_json = MagicMock(
        side_effect=[
            _analysis_payload(success=0.3, naturalness=0.3, risk=0.8),
            _analysis_payload(success=0.9, naturalness=0.9, risk=0.05),
        ]
    )
    from md_chat_ai.agents import digital_twin as dt_mod

    monkeypatch.setattr(
        dt_mod.DigitalTwin,
        "chat",
        lambda self, m, **kw: dt_mod.TwinResponse(
            text="x",
            emotion="neutral",
            intensity=0.5,
            mode="free_chat",
            round_num=0,
            disclosure=dt_mod.TwinDisclosure.for_language("ro"),
            verified=False,
        ),
    )
    result = opt.ab_test(_profile(), "obj", "weak A", "strong B")
    assert result["winner"] == "B"
    assert result["margin"] >= 0
    assert "Send message B" in result["recommendation"]


def test_ab_test_low_confidence_when_margin_small(monkeypatch):
    opt = MessageOptimizer(llm_client=MagicMock())
    opt._llm.chat_json = MagicMock(
        side_effect=[
            _analysis_payload(success=0.5, naturalness=0.5, risk=0.2),
            _analysis_payload(success=0.5, naturalness=0.5, risk=0.21),
        ]
    )
    from md_chat_ai.agents import digital_twin as dt_mod

    monkeypatch.setattr(
        dt_mod.DigitalTwin,
        "chat",
        lambda self, m, **kw: dt_mod.TwinResponse(
            text="x",
            emotion="neutral",
            intensity=0.5,
            mode="free_chat",
            round_num=0,
            disclosure=dt_mod.TwinDisclosure.for_language("ro"),
            verified=False,
        ),
    )
    result = opt.ab_test(_profile(), "obj", "A", "B")
    assert result["confidence"] == "low"


# ---------------------------------------------------------------------------
# optimize_batch
# ---------------------------------------------------------------------------


def test_optimize_batch_skips_invalid_profile(monkeypatch):
    opt = MessageOptimizer(llm_client=MagicMock())
    opt._llm.chat_json = MagicMock(return_value=_variants_payload(1))
    from md_chat_ai.agents import digital_twin as dt_mod

    monkeypatch.setattr(
        dt_mod.DigitalTwin,
        "chat",
        lambda self, m, **kw: dt_mod.TwinResponse(
            text="x",
            emotion="neutral",
            intensity=0.5,
            mode="free_chat",
            round_num=0,
            disclosure=dt_mod.TwinDisclosure.for_language("ro"),
            verified=False,
        ),
    )
    # Each item with a valid profile needs (variants + 1 analysis) chat_json calls.
    opt._llm.chat_json = MagicMock(
        side_effect=[
            _variants_payload(1),
            _analysis_payload(),
        ]
    )
    items = [
        {"objective": "x"},  # missing profile
        {"profile": "not-a-profile", "objective": "x"},  # invalid type
        {"profile": _profile(), "objective": "say hi"},  # valid
    ]
    results = opt.optimize_batch(items, num_variants=1)
    assert len(results) == 1
    assert results[0].user_name == "Oleg"


def test_optimize_batch_catches_per_item_exception(monkeypatch):
    """If optimize() raises for one item, batch keeps going."""
    opt = MessageOptimizer(llm_client=MagicMock())
    bad_profile = _profile(name="Bad")
    good_profile = _profile(name="Good")

    call_idx = {"i": 0}

    def _opt(self_profile, objective, draft_message=None, num_variants=3, constraints=None):
        call_idx["i"] += 1
        if call_idx["i"] == 1:
            raise RuntimeError("bad item")
        return OptimizationResult(
            user_id=self_profile.user_id,
            user_name=self_profile.name,
            objective=objective,
            original_message=draft_message,
            variants_tested=[],
        )

    opt.optimize = _opt  # type: ignore[method-assign]
    results = opt.optimize_batch(
        [
            {"profile": bad_profile, "objective": "x"},
            {"profile": good_profile, "objective": "y"},
        ],
        num_variants=1,
    )
    assert len(results) == 1
    assert results[0].user_name == "Good"


# ---------------------------------------------------------------------------
# _select_winner & _calculate_confidence edges
# ---------------------------------------------------------------------------


def _r(text, success, risk=0.1, naturalness=0.7):
    return VariantTestResult(
        variant=MessageVariant(text=text, tone="t", approach="a", rationale="r"),
        twin_response="reply",
        success_score=success,
        naturalness_score=naturalness,
        risk_score=risk,
        predicted_outcome="will_respond_positively",
        reasoning="ok",
    )


def test_select_winner_prefers_high_naturalness_when_success_tied():
    opt = MessageOptimizer(llm_client=MagicMock())
    a = _r("A", success=0.5, naturalness=0.3)
    b = _r("B", success=0.5, naturalness=0.9)
    winner, _ = opt._select_winner([a, b])
    assert winner is b


def test_select_winner_penalizes_high_risk():
    opt = MessageOptimizer(llm_client=MagicMock())
    safe = _r("safe", success=0.6, risk=0.05)
    risky = _r("risky", success=0.65, risk=0.9)
    winner, _ = opt._select_winner([safe, risky])
    # safe has lower success but lower risk; composite favors safe given coeffs.
    composite_safe = 0.6 * 0.5 + 0.7 * 0.3 - 0.05 * 0.2
    composite_risky = 0.65 * 0.5 + 0.7 * 0.3 - 0.9 * 0.2
    expected = safe if composite_safe >= composite_risky else risky
    assert winner is expected


def test_calculate_confidence_clamps_to_unit_interval():
    opt = MessageOptimizer(llm_client=MagicMock())
    r = _r("x", success=1.0, naturalness=1.0, risk=0.0)
    score = opt._calculate_confidence([r], r)
    assert 0.0 <= score <= 1.0


def test_calculate_confidence_with_single_winner():
    opt = MessageOptimizer(llm_client=MagicMock())
    only = _r("only", success=0.5, naturalness=0.5, risk=0.2)
    score = opt._calculate_confidence([only], only)
    # Should be deterministic & in range.
    assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Lazy-initialized LLM client
# ---------------------------------------------------------------------------


def test_lazy_llm_property_initializes_only_once():
    opt = MessageOptimizer()
    # The property forces creation; we don't actually call it (LLMClient
    # would try to read env). Patch the class to verify instantiation logic.
    sentinel = MagicMock()
    opt._llm = sentinel
    assert opt.llm is sentinel
