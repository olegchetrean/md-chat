"""Coverage tests for agents.message_optimizer — pre-send message optimisation.

Tests use only the public dataclasses + public methods. Internal heuristics
(``_select_winner``, ``_calculate_confidence``) are exercised through the
public ``optimize`` path or via direct calls with synthetic ``VariantTestResult``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from md_chat_ai.agents.message_optimizer import (
    MessageOptimizer,
    MessageVariant,
    OptimizationResult,
    VariantTestResult,
)


def _make_fake_llm() -> MagicMock:
    fake = MagicMock()
    fake_resp = MagicMock()
    fake_resp.content = '{"variants": ["v1", "v2", "v3"]}'
    fake_resp.cost_usd_cents = 5
    fake.complete = AsyncMock(return_value=fake_resp)
    return fake


def _variant(text: str = "hi") -> MessageVariant:
    return MessageVariant(text=text, tone="friendly", approach="direct", rationale="warm opener")


def _variant_result(text: str = "hi", success: float = 0.6) -> VariantTestResult:
    return VariantTestResult(
        variant=_variant(text),
        twin_response="ok!",
        success_score=success,
        naturalness_score=0.7,
        risk_score=0.2,
        predicted_outcome="will_respond_positively",
        reasoning="solid match",
    )


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_optimizer_constructs_with_explicit_llm():
    opt = MessageOptimizer(llm_client=_make_fake_llm())
    assert opt.llm is not None


def test_optimizer_constructs_lazy():
    opt = MessageOptimizer()
    assert opt is not None


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


def test_message_variant_fields_round_trip():
    v = MessageVariant(text="hello", tone="formal", approach="indirect", rationale="careful")
    assert v.text == "hello"
    assert v.tone == "formal"
    assert v.approach == "indirect"
    assert v.rationale == "careful"


def test_variant_test_result_to_dict_shape():
    r = _variant_result("greet")
    d = r.to_dict()
    assert d["twin_response"] == "ok!"
    assert d["success_score"] == 0.6
    assert d["variant"]["text"] == "greet"
    assert d["predicted_outcome"] == "will_respond_positively"


def test_optimization_result_to_dict_includes_variants():
    r1 = _variant_result("A", 0.4)
    r2 = _variant_result("B", 0.8)
    opt_result = OptimizationResult(
        user_id="@u:md",
        user_name="Test",
        objective="get a reply",
        original_message="hi",
        variants_tested=[r1, r2],
        winner=r2,
        runner_up=r1,
        confidence=0.7,
        estimated_success_rate=0.8,
    )
    d = opt_result.to_dict()
    assert d["user_id"] == "@u:md"
    assert d["original_message"] == "hi"
    assert len(d["variants_tested"]) == 2
    assert d["winner"]["variant"]["text"] == "B"


# ---------------------------------------------------------------------------
# History / record_outcome
# ---------------------------------------------------------------------------


def test_record_outcome_appends_to_history():
    opt = MessageOptimizer(llm_client=_make_fake_llm())
    opt.record_outcome(
        user_id="@oleg:md-chat.eu",
        message_sent="hi 👋",
        actual_response="oh hey!",
        was_successful=True,
    )
    history = opt.get_history(user_id="@oleg:md-chat.eu")
    assert len(history) == 1
    assert history[0]["user_id"] == "@oleg:md-chat.eu"


def test_get_history_returns_empty_for_unknown_user():
    opt = MessageOptimizer(llm_client=_make_fake_llm())
    assert opt.get_history(user_id="@nobody:md") == []


def test_get_history_without_user_id_returns_all():
    opt = MessageOptimizer(llm_client=_make_fake_llm())
    opt.record_outcome(user_id="@a:md", message_sent="m1", actual_response="r1", was_successful=True)
    opt.record_outcome(user_id="@b:md", message_sent="m2", actual_response="r2", was_successful=False)
    assert len(opt.get_history()) == 2


# ---------------------------------------------------------------------------
# Internal scoring helpers (smoke + edge cases)
# ---------------------------------------------------------------------------


def test_select_winner_empty_list_returns_none_pair():
    opt = MessageOptimizer(llm_client=_make_fake_llm())
    winner, runner_up = opt._select_winner([])
    assert winner is None
    assert runner_up is None


def test_select_winner_with_multiple_picks_higher_success():
    opt = MessageOptimizer(llm_client=_make_fake_llm())
    low = _variant_result("low", success=0.3)
    high = _variant_result("high", success=0.9)
    mid = _variant_result("mid", success=0.6)
    winner, runner_up = opt._select_winner([low, mid, high])
    assert winner is not None
    assert winner.variant.text == "high"
    # Runner-up should be one of the others.
    assert runner_up in (low, mid)


def test_select_winner_with_single_result():
    opt = MessageOptimizer(llm_client=_make_fake_llm())
    only = _variant_result("only", 0.5)
    winner, runner_up = opt._select_winner([only])
    assert winner is only
    assert runner_up is None


def test_calculate_confidence_zero_when_no_winner():
    opt = MessageOptimizer(llm_client=_make_fake_llm())
    score = opt._calculate_confidence(results=[], winner=None)
    assert score == 0.0


def test_calculate_confidence_returns_float_in_range():
    opt = MessageOptimizer(llm_client=_make_fake_llm())
    r1 = _variant_result("A", 0.4)
    r2 = _variant_result("B", 0.8)
    score = opt._calculate_confidence(results=[r1, r2], winner=r2)
    assert 0.0 <= score <= 1.0
