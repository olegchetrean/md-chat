# Copyright 2026 Mega Promoting SRL
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Derived from Cronberry (Mega Promoting SRL).
"""Branch-coverage tests for ``agents.memory``.

Targets:
- ShortTermMemory eviction → LongTermMemory forwarding (memory pruning)
- LongTermMemory compression threshold + LLM-failure fallback
- RelationshipMemory state transitions / classification
- PromiseMemory lifecycle: PENDING → FULFILLED / BROKEN / CANCELLED + trust delta
- EmotionalState transitions + reversion + modifier matrix
- TwinMemory façade wiring (eviction routing, promise resolution updates trust)
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from md_chat_ai.agents.memory import (
    Emotion,
    EmotionalState,
    LongTermMemory,
    MemoryEntry,
    Promise,
    PromiseMemory,
    PromiseStatus,
    RelationshipMemory,
    RelationshipState,
    ShortTermMemory,
    TwinMemory,
    _classify_relationship,
    _count_relationship_types,
)


# ---------------------------------------------------------------------------
# ShortTermMemory eviction & pruning
# ---------------------------------------------------------------------------


def test_stm_evicts_oldest_when_window_full():
    stm = ShortTermMemory(max_entries=3)
    assert stm.add("a", source="user") is None
    assert stm.add("b", source="user") is None
    assert stm.add("c", source="user") is None
    evicted = stm.add("d", source="user")
    assert evicted is not None and evicted.content == "a"
    assert [e.content for e in stm.entries] == ["b", "c", "d"]


def test_stm_eviction_callback_invoked():
    stm = ShortTermMemory(max_entries=2)
    captured = []
    stm.on_eviction(lambda e: captured.append(e.content))
    stm.add("x")
    stm.add("y")
    stm.add("z")  # evicts "x"
    assert captured == ["x"]


def test_stm_retrieve_filters_by_source_and_contact():
    stm = ShortTermMemory(max_entries=10)
    stm.add("u1", source="user", contact_id="c1")
    stm.add("a1", source="agent", contact_id="c1")
    stm.add("u2", source="user", contact_id="c2")
    by_source = stm.retrieve(n=10, source="user")
    assert {e.content for e in by_source} == {"u1", "u2"}
    by_contact = stm.retrieve(n=10, contact_id="c1")
    assert {e.content for e in by_contact} == {"u1", "a1"}


def test_stm_search_case_insensitive():
    stm = ShortTermMemory()
    stm.add("Buna ziua", source="user")
    stm.add("hello there", source="user")
    assert len(stm.search("BUNA")) == 1
    assert len(stm.search("hello")) == 1


def test_stm_summarize_and_to_context_string():
    stm = ShortTermMemory()
    assert stm.summarize() == "(no entries)"
    stm.add("hi", source="user")
    stm.add("hey", source="agent")
    s = stm.summarize()
    assert "[user]" in s and "[agent]" in s
    ctx = stm.to_context_string(max_entries=1)
    assert ctx.count("\n") == 0  # only last entry


def test_stm_persist_load_roundtrip(tmp_path):
    stm = ShortTermMemory()
    stm.add("hello", source="user", round_num=2)
    path = tmp_path / "stm.json"
    stm.persist(str(path))

    other = ShortTermMemory()
    other.load(str(path))
    assert [e.content for e in other.entries] == ["hello"]
    # JSON round-trip via string also OK.
    stm2 = ShortTermMemory()
    stm2.load_json(stm.to_json())
    assert [e.content for e in stm2.entries] == ["hello"]


def test_stm_clear_removes_all():
    stm = ShortTermMemory()
    stm.add("x")
    stm.clear()
    assert stm.entries == []


def test_memory_entry_from_dict_round_trip():
    e = MemoryEntry(content="hello", source="user", round_num=1, metadata={"k": "v"})
    d = e.to_dict()
    rebuilt = MemoryEntry.from_dict(d)
    assert rebuilt.content == "hello"
    assert rebuilt.metadata == {"k": "v"}


# ---------------------------------------------------------------------------
# LongTermMemory compression + LLM fallback
# ---------------------------------------------------------------------------


def test_ltm_compresses_when_threshold_reached():
    fake = MagicMock()
    fake.chat_json = MagicMock(
        return_value={
            "summary": "Compressed summary",
            "key_entities": ["Alice"],
            "key_dates": ["2026-05-17"],
            "sentiment_shift": "positive",
        }
    )
    ltm = LongTermMemory(llm_client=fake, compression_threshold=3)
    for i in range(3):
        ltm.add(f"fact-{i}")
    summaries = ltm.get_all_summaries()
    assert len(summaries) == 1
    assert summaries[0]["summary"] == "Compressed summary"
    # raw_facts cleared after compression.
    stats = ltm.get_stats()
    assert stats["pending_raw_facts"] == 0
    assert stats["summaries_count"] == 1


def test_ltm_compress_fallback_on_llm_failure():
    fake = MagicMock()
    fake.chat_json = MagicMock(side_effect=RuntimeError("llm down"))
    ltm = LongTermMemory(llm_client=fake, compression_threshold=2)
    ltm.add("fact A")
    ltm.add("fact B")
    summaries = ltm.get_all_summaries()
    assert len(summaries) == 1
    assert "LLM unavailable" in summaries[0]["summary"]


def test_ltm_compress_returns_empty_when_no_facts():
    fake = MagicMock()
    ltm = LongTermMemory(llm_client=fake, compression_threshold=10)
    assert ltm.compress() == ""
    fake.chat_json.assert_not_called()


def test_ltm_retrieve_scores_entity_matches_higher():
    fake = MagicMock()
    fake.chat_json = MagicMock(
        return_value={
            "summary": "discussion topic",
            "key_entities": ["Oleg"],
            "key_dates": [],
            "sentiment_shift": "stable",
        }
    )
    ltm = LongTermMemory(llm_client=fake, compression_threshold=1)
    ltm.add("Some fact about something")
    results = ltm.retrieve("Oleg discussion", max_results=5)
    assert len(results) >= 1
    # Top result should be summary (entity hit), not raw.
    assert "summary" in results[0]


def test_ltm_retrieve_returns_empty_when_no_match():
    ltm = LongTermMemory(llm_client=MagicMock(), compression_threshold=10)
    ltm.add("an irrelevant fact")
    assert ltm.retrieve("nonexistent xyzzy") == []


def test_ltm_summarize_empty():
    ltm = LongTermMemory(llm_client=MagicMock())
    assert ltm.summarize() == "(no long-term memories)"


def test_ltm_persist_and_load_roundtrip(tmp_path):
    ltm = LongTermMemory(llm_client=MagicMock(), compression_threshold=100)
    ltm.add("fact-1")
    path = tmp_path / "ltm.json"
    ltm.persist(str(path))
    other = LongTermMemory(llm_client=MagicMock())
    other.load(str(path))
    assert other.get_stats()["pending_raw_facts"] == 1


def test_ltm_recall_alias_works():
    ltm = LongTermMemory(llm_client=MagicMock())
    ltm.add_fact("matchable keyword")
    results = ltm.recall("keyword")
    assert results and "summary" in results[0]


# ---------------------------------------------------------------------------
# RelationshipMemory transitions + classification
# ---------------------------------------------------------------------------


def test_relationship_get_or_create_returns_same_instance():
    rm = RelationshipMemory()
    s1 = rm.get_or_create("c1", "Alice")
    s2 = rm.get_or_create("c1", "Different")
    assert s1 is s2


def test_relationship_apply_sentiment_clamps():
    s = RelationshipState(contact_id="c1", contact_name="A")
    s.apply_sentiment_delta(5.0)
    assert s.sentiment == 1.0
    s.apply_sentiment_delta(-50.0)
    assert s.sentiment == -1.0


def test_relationship_trust_history_records_delta():
    s = RelationshipState(contact_id="c1", contact_name="A")
    s.apply_trust_delta(0.2, round_num=3, reason="kept promise")
    assert s.trust_score == 0.7
    assert s.trust_history[0]["reason"] == "kept promise"
    assert s.trust_history[0]["delta"] == 0.2


def test_relationship_classify_ally():
    s = RelationshipState(contact_id="c1", contact_name="A", sentiment=0.6, trust_score=0.7)
    assert _classify_relationship(s) == "ally"


def test_relationship_classify_competitor():
    s = RelationshipState(contact_id="c1", contact_name="A", sentiment=-0.5)
    assert _classify_relationship(s) == "competitor"


def test_relationship_classify_unknown_when_few_interactions():
    s = RelationshipState(contact_id="c1", contact_name="A", interaction_count=1)
    assert _classify_relationship(s) == "unknown"


def test_relationship_classify_neutral_default():
    s = RelationshipState(contact_id="c1", contact_name="A", interaction_count=5)
    assert _classify_relationship(s) == "neutral"


def test_relationship_add_records_topic_and_commitments():
    rm = RelationshipMemory()
    state = rm.add(
        contact_id="c1",
        contact_name="A",
        sentiment_delta=0.5,
        trust_delta=0.1,
        topic="weather",
        commitment_made="I will call",
        commitment_received="They will email",
        note="positive note",
        was_positive=True,
        round_num=1,
    )
    assert "weather" in state.topics_discussed
    assert state.commitments_made == ["I will call"]
    assert state.commitments_received == ["They will email"]
    assert state.positive_moments == ["positive note"]


def test_relationship_add_records_conflict():
    rm = RelationshipMemory()
    state = rm.add(
        contact_id="c1",
        contact_name="A",
        note="they were rude",
        was_positive=False,
    )
    assert state.conflict_history == ["they were rude"]
    assert state.positive_moments == []


def test_relationship_health_report_aggregates():
    rm = RelationshipMemory()
    rm.add("a", "A", sentiment_delta=0.8, trust_delta=0.2)
    rm.add("a", "A", sentiment_delta=0.0, trust_delta=0.0)
    rm.add("a", "A")  # third interaction
    rm.add("b", "B", sentiment_delta=-0.5, trust_delta=-0.2)
    rm.add("b", "B", sentiment_delta=-0.2, trust_delta=0.0)
    rm.add("b", "B", sentiment_delta=0.0, trust_delta=0.0)  # third
    report = rm.get_health_report()
    assert report["total_contacts"] == 2
    assert any(c["name"] == "B" for c in report["at_risk_contacts"])


def test_relationship_health_report_empty():
    rm = RelationshipMemory()
    report = rm.get_health_report()
    assert report["total_contacts"] == 0


def test_relationship_summarize_text():
    rm = RelationshipMemory()
    assert rm.summarize() == "(no relationships tracked)"
    rm.add("c1", "Alice", sentiment_delta=0.4, trust_delta=0.2)
    text = rm.summarize()
    assert "Alice" in text


def test_relationship_persist_roundtrip(tmp_path):
    rm = RelationshipMemory()
    rm.add("c1", "Alice", sentiment_delta=0.3, trust_delta=0.1)
    path = tmp_path / "rm.json"
    rm.persist(str(path))
    other = RelationshipMemory()
    other.load(str(path))
    assert other.retrieve("c1") is not None


def test_relationship_to_from_dict_roundtrip():
    s = RelationshipState(
        contact_id="c1",
        contact_name="A",
        sentiment=0.4,
        trust_score=0.6,
        interaction_count=3,
    )
    rebuilt = RelationshipState.from_dict(s.to_dict())
    assert rebuilt.sentiment == 0.4
    assert rebuilt.trust_score == 0.6


def test_count_relationship_types_groups_states():
    states = [
        RelationshipState(contact_id="a", contact_name="A", relationship_type="ally"),
        RelationshipState(contact_id="b", contact_name="B", relationship_type="ally"),
        RelationshipState(contact_id="c", contact_name="C", relationship_type="competitor"),
    ]
    counts = _count_relationship_types(states)
    assert counts == {"ally": 2, "competitor": 1}


# ---------------------------------------------------------------------------
# PromiseMemory lifecycle
# ---------------------------------------------------------------------------


def test_promise_status_lifecycle_fulfilled_returns_positive_trust():
    pm = PromiseMemory()
    p = pm.add("call back", direction="made", contact_id="c1", contact_name="A")
    assert p.status == PromiseStatus.PENDING
    promise, delta = pm.resolve(p.promise_id, PromiseStatus.FULFILLED, note="done")
    assert promise.status == PromiseStatus.FULFILLED
    assert delta == 0.05


def test_promise_status_lifecycle_broken_returns_negative_trust():
    pm = PromiseMemory()
    p = pm.add("call back", direction="received", contact_id="c1")
    _, delta = pm.resolve(p.promise_id, PromiseStatus.BROKEN)
    assert delta == -0.15


def test_promise_cancelled_minor_trust_penalty():
    pm = PromiseMemory()
    p = pm.add("x", direction="made", contact_id="c1")
    _, delta = pm.resolve(p.promise_id, PromiseStatus.CANCELLED)
    assert delta == -0.03


def test_promise_resolve_unknown_raises_keyerror():
    pm = PromiseMemory()
    with pytest.raises(KeyError):
        pm.resolve("promise_nonexistent", PromiseStatus.FULFILLED)


def test_promise_resolve_already_closed_raises():
    pm = PromiseMemory()
    p = pm.add("x", "made", "c1")
    pm.resolve(p.promise_id, PromiseStatus.FULFILLED)
    with pytest.raises(ValueError):
        pm.resolve(p.promise_id, PromiseStatus.BROKEN)


def test_promise_retrieve_filters():
    pm = PromiseMemory()
    p1 = pm.add("a", "made", "c1")
    pm.add("b", "received", "c1")
    pm.add("c", "made", "c2")
    pm.resolve(p1.promise_id, PromiseStatus.FULFILLED)
    by_contact = pm.retrieve(contact_id="c1")
    assert len(by_contact) == 2
    pending = pm.retrieve(status=PromiseStatus.PENDING)
    assert len(pending) == 2
    made_only = pm.retrieve(direction="made")
    assert all(p.direction == "made" for p in made_only)


def test_promise_get_pending_for_contact():
    pm = PromiseMemory()
    pm.add("x", "made", "c1")
    pm.add("y", "made", "c1")
    p3 = pm.add("z", "made", "c1")
    pm.resolve(p3.promise_id, PromiseStatus.FULFILLED)
    pending = pm.get_pending_for_contact("c1")
    assert len(pending) == 2


def test_promise_stats_aggregates():
    pm = PromiseMemory()
    p1 = pm.add("a", "made", "c1")
    p2 = pm.add("b", "made", "c1")
    pm.add("c", "made", "c2")
    pm.resolve(p1.promise_id, PromiseStatus.FULFILLED)
    pm.resolve(p2.promise_id, PromiseStatus.BROKEN)
    stats = pm.get_stats()
    assert stats["total"] == 3
    assert stats["pending"] == 1
    assert stats["fulfilled"] == 1
    assert stats["broken"] == 1


def test_promise_summarize_text():
    pm = PromiseMemory()
    assert pm.summarize() == "(no promises tracked)"
    pm.add("call me", "made", "c1", "Alice")
    text = pm.summarize()
    assert "PENDING" in text
    assert "Alice" in text


def test_promise_persist_roundtrip(tmp_path):
    pm = PromiseMemory()
    p = pm.add("call", "made", "c1", "A")
    pm.resolve(p.promise_id, PromiseStatus.FULFILLED)
    path = tmp_path / "promises.json"
    pm.persist(str(path))
    other = PromiseMemory()
    other.load(str(path))
    assert other.get_stats()["fulfilled"] == 1


def test_promise_from_dict_roundtrip():
    p = Promise(
        promise_id="promise_000001",
        description="x",
        direction="made",
        contact_id="c1",
        contact_name="A",
        due_date="2026-12-31",
    )
    d = p.to_dict()
    rebuilt = Promise.from_dict(d)
    assert rebuilt.due_date == "2026-12-31"
    assert rebuilt.status == PromiseStatus.PENDING


# ---------------------------------------------------------------------------
# EmotionalState transitions, ticks, modifiers
# ---------------------------------------------------------------------------


def test_emotion_add_changes_current_state():
    es = EmotionalState()
    es.add(Emotion.HAPPY.value, intensity_delta=0.3, trigger="good news")
    assert es.current_emotion == Emotion.HAPPY.value
    assert es.current_intensity == 0.8


def test_emotion_intensity_clamps_at_one():
    es = EmotionalState(baseline_intensity=0.9)
    es.add(Emotion.EXCITED.value, intensity_delta=0.5)
    assert es.current_intensity == 1.0


def test_emotion_intensity_clamps_at_zero():
    es = EmotionalState(baseline_intensity=0.2)
    es.add(Emotion.SAD.value, intensity_delta=-1.0)
    assert es.current_intensity == 0.0


def test_emotion_tick_reverts_toward_baseline():
    es = EmotionalState()
    es.add(Emotion.EXCITED.value, intensity_delta=0.4)  # 0.9 intensity
    starting = es.current_intensity
    es.tick()
    assert es.current_intensity < starting
    # Tick many to push down below threshold → emotion reverts to baseline.
    for _ in range(20):
        es.tick()
    assert es.current_emotion == Emotion.NEUTRAL.value


def test_emotion_tick_with_specific_round_num():
    es = EmotionalState()
    es.add(Emotion.ANGRY.value, 0.1)
    es.tick(round_num=42)
    assert es._round == 42


def test_emotion_modifier_for_angry():
    es = EmotionalState()
    es.add(Emotion.ANGRY.value, 0.5)
    mods = es.get_modifier()
    assert mods["aggressiveness"] > 0
    assert mods["compliance"] < 0


def test_emotion_modifier_for_neutral_is_zero():
    es = EmotionalState()
    mods = es.get_modifier()
    assert all(v == 0 for v in mods.values())


def test_emotion_retrieve_recent_events():
    es = EmotionalState()
    for label in (Emotion.HAPPY, Emotion.SAD, Emotion.ANGRY, Emotion.CURIOUS):
        es.add(label.value, 0.1)
    last3 = es.retrieve(last_n=3)
    assert len(last3) == 3
    assert last3[-1].to_emotion == Emotion.CURIOUS.value


def test_emotion_persist_roundtrip(tmp_path):
    es = EmotionalState()
    es.add(Emotion.HAPPY.value, 0.2)
    path = tmp_path / "emotion.json"
    es.persist(str(path))
    other = EmotionalState()
    other.load(str(path))
    assert other.current_emotion == Emotion.HAPPY.value


def test_emotion_summarize_human_readable():
    es = EmotionalState()
    es.add(Emotion.CURIOUS.value, 0.1)
    assert "curious" in es.summarize()


# ---------------------------------------------------------------------------
# TwinMemory façade — eviction routing & promise→relationship
# ---------------------------------------------------------------------------


def test_twin_memory_short_term_eviction_routes_to_long_term():
    tm = TwinMemory(contact_id="@u:md", stm_window=2, ltm_compression_threshold=100)
    tm.record_message("first", source="user")
    tm.record_message("second", source="user")
    tm.record_message("third", source="user")
    # "first" was evicted to LTM as a raw fact.
    assert tm.long_term.get_stats()["pending_raw_facts"] == 1


def test_twin_memory_resolve_promise_updates_trust():
    tm = TwinMemory(contact_id="@u:md")
    p = tm.make_promise("call me back", other_contact_id="@oleg:md", other_name="Oleg")
    promise, delta = tm.resolve_promise(p.promise_id, PromiseStatus.FULFILLED)
    assert promise.status == PromiseStatus.FULFILLED
    rel = tm.relationships.retrieve("@oleg:md")
    assert rel is not None
    assert rel.trust_score > 0.5


def test_twin_memory_summarize_combines_all_sections():
    tm = TwinMemory(contact_id="@u:md")
    tm.record_message("hi", source="user")
    tm.update_relationship("@oleg:md", "Oleg", sentiment_delta=0.3)
    tm.make_promise("call back", "@oleg:md", "Oleg")
    tm.feel(Emotion.HAPPY.value, 0.2, trigger="positive interaction")
    full = tm.summarize()
    assert "Short-term" in full and "Long-term" in full
    assert "Relationships" in full and "Promises" in full
    assert "Emotional state" in full


def test_twin_memory_to_context_block_has_required_sections():
    tm = TwinMemory(contact_id="@u:md")
    tm.record_message("hello", source="user")
    tm.make_promise("call back tomorrow", "@oleg:md")
    block = tm.to_context_block()
    assert "[Recent interactions]" in block
    assert "[Long-term knowledge]" in block
    assert "[Current emotion]" in block
    assert "[Pending promises]" in block


def test_twin_memory_persist_load_roundtrip(tmp_path):
    tm = TwinMemory(contact_id="@u:md")
    tm.record_message("hi", source="user")
    tm.feel(Emotion.HAPPY.value, 0.1, trigger="warm welcome")
    tm.persist(str(tmp_path / "twin"))

    other = TwinMemory(contact_id="@u:md")
    other.load(str(tmp_path / "twin"))
    assert other.emotion.current_emotion == Emotion.HAPPY.value
