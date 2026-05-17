# Copyright 2026 Mega Promoting SRL
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Derived from Cronberry (Mega Promoting SRL).
"""
Agent memory system for md-chat (self-twin mode).

Six memory types:
  - ShortTermMemory:    Rolling window of last 20 interactions in current simulation
  - LongTermMemory:     LLM-summarized history, compresses every N raw facts
  - RelationshipMemory: Per-agent sentiment/trust tracking with evolution
  - PromiseMemory:      Track promises made/received with status lifecycle
  - EmotionalState:     Current sentiment that evolves during simulation
  - TwinMemory:         Combined memory façade for Digital Twins

All memory types support add(), retrieve(), summarize(), and persist() methods.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..llm.client import LLMClient

logger = logging.getLogger("md_chat_ai.agents.memory")


# ======================================================================
# Short-Term Memory
# ======================================================================


@dataclass
class MemoryEntry:
    """A single memory entry with timestamp and metadata."""

    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = ""          # "user", "agent", "system"
    contact_id: Optional[str] = None
    round_num: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "timestamp": self.timestamp,
            "source": self.source,
            "contact_id": self.contact_id,
            "round_num": self.round_num,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        return cls(
            content=data["content"],
            timestamp=data.get("timestamp", ""),
            source=data.get("source", ""),
            contact_id=data.get("contact_id"),
            round_num=data.get("round_num", 0),
            metadata=data.get("metadata", {}),
        )


class ShortTermMemory:
    """
    Rolling-window memory that keeps the last N interactions.

    When the window is full the oldest entry is evicted. Optionally, an
    eviction callback forwards evicted entries to LongTermMemory.
    """

    def __init__(self, max_entries: int = 20) -> None:
        self.max_entries = max_entries
        self._entries: List[MemoryEntry] = []
        self._eviction_callback: Optional[Callable[[MemoryEntry], None]] = None

    # ---- Core API ---------------------------------------------------

    @property
    def entries(self) -> List[MemoryEntry]:
        """All entries, oldest first."""
        return list(self._entries)

    def add(
        self,
        content: str,
        source: str = "user",
        contact_id: Optional[str] = None,
        round_num: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[MemoryEntry]:
        """
        Add a new memory entry.

        Returns:
            The evicted entry if the window was full, else None.
        """
        entry = MemoryEntry(
            content=content,
            source=source,
            contact_id=contact_id,
            round_num=round_num,
            metadata=metadata or {},
        )

        evicted: Optional[MemoryEntry] = None
        if len(self._entries) >= self.max_entries:
            evicted = self._entries.pop(0)
            if self._eviction_callback:
                self._eviction_callback(evicted)

        self._entries.append(entry)
        return evicted

    def retrieve(
        self,
        n: int = 5,
        source: Optional[str] = None,
        contact_id: Optional[str] = None,
    ) -> List[MemoryEntry]:
        """
        Retrieve recent entries, optionally filtered.

        Args:
            n: Maximum number of entries to return.
            source: Filter by source ("user", "agent", "system").
            contact_id: Filter by associated contact.

        Returns:
            Most recent matching entries (newest last).
        """
        filtered = self._entries
        if source:
            filtered = [e for e in filtered if e.source == source]
        if contact_id:
            filtered = [e for e in filtered if e.contact_id == contact_id]
        return filtered[-n:]

    def search(self, keyword: str) -> List[MemoryEntry]:
        """Simple keyword search across entry contents."""
        kw = keyword.lower()
        return [e for e in self._entries if kw in e.content.lower()]

    def summarize(self) -> str:
        """Return a plain-text summary of all current entries."""
        if not self._entries:
            return "(no entries)"
        lines: List[str] = []
        for e in self._entries:
            prefix = f"[{e.source}]" if e.source else ""
            lines.append(f"{prefix} {e.content}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Evict all entries without callbacks."""
        self._entries.clear()

    def on_eviction(self, callback: Callable[[MemoryEntry], None]) -> None:
        """Register a callback for evicted entries."""
        self._eviction_callback = callback

    def to_context_string(self, max_entries: Optional[int] = None) -> str:
        """Format entries as a context block for LLM prompts."""
        entries = self._entries[-(max_entries or self.max_entries):]
        lines: List[str] = []
        for e in entries:
            prefix = f"[{e.source}]" if e.source else ""
            lines.append(f"{prefix} {e.content}")
        return "\n".join(lines)

    # ---- Persistence ------------------------------------------------

    def persist(self, path: str) -> None:
        """Write memory to a JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self._entries], f, ensure_ascii=False, indent=2)
        logger.debug("ShortTermMemory persisted to %s", path)

    def load(self, path: str) -> None:
        """Load memory from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self._entries = [MemoryEntry.from_dict(e) for e in raw]

    def to_json(self) -> str:
        return json.dumps([e.to_dict() for e in self._entries], ensure_ascii=False, indent=2)

    def load_json(self, data: str) -> None:
        self._entries = [MemoryEntry.from_dict(e) for e in json.loads(data)]


# ======================================================================
# Long-Term Memory
# ======================================================================


class LongTermMemory:
    """
    LLM-summarized persistent memory.

    Raw facts accumulate and are compressed into summaries every
    ``compression_threshold`` facts. Compressed summaries are kept and
    searched with simple keyword scoring.
    """

    COMPRESSION_PROMPT = """Summarize the following facts into a concise, information-dense paragraph.
Preserve: names, dates, numbers, commitments, sentiment shifts.
Remove: redundancy, filler phrases.

Facts:
{facts_text}

Return JSON:
{{"summary": "...", "key_entities": ["name1", "name2"], "key_dates": ["date1"], "sentiment_shift": "positive|negative|stable"}}"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        compression_threshold: int = 10,
    ) -> None:
        """
        Args:
            llm_client: LLM client for summarization.
            compression_threshold: Number of raw facts before triggering compression.
        """
        self._llm_client = llm_client  # may be None; lazily initialized on first use
        self.compression_threshold = compression_threshold
        self._summaries: List[Dict[str, Any]] = []
        self._raw_facts: List[str] = []
        self._fact_count: int = 0

    @property
    def llm(self) -> LLMClient:
        """Lazily initialize the LLM client on first use."""
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client

    # ---- Core API ---------------------------------------------------

    def add(self, fact: str, contact_id: Optional[str] = None) -> None:
        """
        Add a new fact. Triggers compression when threshold is reached.

        Args:
            fact: A piece of information to remember.
            contact_id: Optional contact association (stored in metadata).
        """
        self._raw_facts.append(fact)
        self._fact_count += 1
        if len(self._raw_facts) >= self.compression_threshold:
            self.compress()

    # Backward-compat alias
    def add_fact(self, fact: str, contact_id: Optional[str] = None) -> None:
        self.add(fact, contact_id=contact_id)

    def retrieve(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search compressed summaries and raw facts for relevance.

        Args:
            query: Natural language query.
            max_results: Maximum entries to return.

        Returns:
            List of matching summary dicts, most relevant first.
        """
        query_words = set(query.lower().split())
        scored: List[Tuple[int, Dict[str, Any]]] = []

        for s in self._summaries:
            text = s["summary"].lower()
            entities = [e.lower() for e in s.get("key_entities", [])]
            score = sum(1 for w in query_words if w in text)
            score += sum(2 for w in query_words if any(w in e for e in entities))
            if score > 0:
                scored.append((score, s))

        for fact in self._raw_facts:
            score = sum(1 for w in query_words if w in fact.lower())
            if score > 0:
                scored.append((score, {"summary": fact, "raw": True}))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:max_results]]

    # Backward-compat alias
    def recall(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        return self.retrieve(query, max_results)

    def summarize(self) -> str:
        """Return a human-readable overview of all retained knowledge."""
        parts: List[str] = []
        for i, s in enumerate(self._summaries, 1):
            parts.append(f"[Summary {i}] {s['summary']}")
        if self._raw_facts:
            raw_text = "\n".join(f"- {f}" for f in self._raw_facts)
            parts.append(f"[Pending facts]\n{raw_text}")
        return "\n\n".join(parts) if parts else "(no long-term memories)"

    def compress(self) -> str:
        """
        Compress raw facts into a summary using the LLM.

        Returns:
            Generated summary text (or placeholder on failure).
        """
        if not self._raw_facts:
            return ""

        facts_text = "\n".join(f"- {f}" for f in self._raw_facts)
        prompt = self.COMPRESSION_PROMPT.format(facts_text=facts_text)

        try:
            result = self.llm.chat_json(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            summary_text = result.get("summary", facts_text[:500])
        except Exception as exc:
            logger.warning("LTM compression failed: %s", exc)
            summary_text = f"[Batch of {len(self._raw_facts)} facts — LLM unavailable]"
            result = {
                "summary": summary_text,
                "key_entities": [],
                "key_dates": [],
                "sentiment_shift": "unknown",
            }

        self._summaries.append({
            "summary": result.get("summary", summary_text),
            "key_entities": result.get("key_entities", []),
            "key_dates": result.get("key_dates", []),
            "sentiment_shift": result.get("sentiment_shift", "stable"),
            "facts_compressed": len(self._raw_facts),
            "compressed_at": datetime.now().isoformat(),
        })
        self._raw_facts.clear()
        return summary_text

    def get_all_summaries(self) -> List[Dict[str, Any]]:
        return list(self._summaries)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_facts_ingested": self._fact_count,
            "summaries_count": len(self._summaries),
            "pending_raw_facts": len(self._raw_facts),
            "compression_threshold": self.compression_threshold,
        }

    # ---- Persistence ------------------------------------------------

    def persist(self, path: str) -> None:
        """Write memory to a JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._to_obj(), f, ensure_ascii=False, indent=2)
        logger.debug("LongTermMemory persisted to %s", path)

    def load(self, path: str) -> None:
        """Load memory from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            self._from_obj(json.load(f))

    def to_json(self) -> str:
        return json.dumps(self._to_obj(), ensure_ascii=False, indent=2)

    def load_json(self, data: str) -> None:
        self._from_obj(json.loads(data))

    def _to_obj(self) -> Dict[str, Any]:
        return {
            "summaries": self._summaries,
            "raw_facts": self._raw_facts,
            "fact_count": self._fact_count,
        }

    def _from_obj(self, obj: Dict[str, Any]) -> None:
        self._summaries = obj.get("summaries", [])
        self._raw_facts = obj.get("raw_facts", [])
        self._fact_count = obj.get("fact_count", 0)


# ======================================================================
# Relationship Memory
# ======================================================================


@dataclass
class RelationshipState:
    """Tracks the evolving state of a relationship with a single agent."""

    contact_id: str
    contact_name: str
    sentiment: float = 0.0          # -1.0 (hostile) to 1.0 (friendly)
    trust_score: float = 0.5        # 0.0 to 1.0
    interaction_count: int = 0
    last_interaction: Optional[str] = None
    topics_discussed: List[str] = field(default_factory=list)
    commitments_made: List[str] = field(default_factory=list)
    commitments_received: List[str] = field(default_factory=list)
    conflict_history: List[str] = field(default_factory=list)
    positive_moments: List[str] = field(default_factory=list)
    relationship_type: str = "neutral"  # ally / neutral / competitor / unknown

    # Trust score evolution log: list of {"round": N, "delta": d, "reason": "..."}
    trust_history: List[Dict[str, Any]] = field(default_factory=list)

    def apply_sentiment_delta(self, delta: float) -> None:
        """Clamp-safe sentiment update."""
        self.sentiment = round(max(-1.0, min(1.0, self.sentiment + delta)), 4)

    def apply_trust_delta(self, delta: float, round_num: int = 0, reason: str = "") -> None:
        """Clamp-safe trust update with history logging."""
        old = self.trust_score
        self.trust_score = round(max(0.0, min(1.0, self.trust_score + delta)), 4)
        self.trust_history.append({
            "round": round_num,
            "from": old,
            "to": self.trust_score,
            "delta": delta,
            "reason": reason,
        })
        # Keep only last 100 entries
        self.trust_history = self.trust_history[-100:]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contact_id": self.contact_id,
            "contact_name": self.contact_name,
            "sentiment": self.sentiment,
            "trust_score": self.trust_score,
            "interaction_count": self.interaction_count,
            "last_interaction": self.last_interaction,
            "topics_discussed": self.topics_discussed,
            "commitments_made": self.commitments_made,
            "commitments_received": self.commitments_received,
            "conflict_history": self.conflict_history,
            "positive_moments": self.positive_moments,
            "relationship_type": self.relationship_type,
            "trust_history": self.trust_history,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RelationshipState":
        return cls(
            contact_id=d["contact_id"],
            contact_name=d.get("contact_name", d["contact_id"]),
            sentiment=d.get("sentiment", 0.0),
            trust_score=d.get("trust_score", d.get("trust_level", 0.5)),
            interaction_count=d.get("interaction_count", 0),
            last_interaction=d.get("last_interaction"),
            topics_discussed=d.get("topics_discussed", []),
            commitments_made=d.get("commitments_made", []),
            commitments_received=d.get("commitments_received", []),
            conflict_history=d.get("conflict_history", []),
            positive_moments=d.get("positive_moments", []),
            relationship_type=d.get("relationship_type", "neutral"),
            trust_history=d.get("trust_history", []),
        )


class RelationshipMemory:
    """
    Tracks per-agent relationship state across all known contacts.

    Maintains sentiment and trust_score evolution, topic history,
    commitments, conflicts, and relationship type classification.
    """

    def __init__(self) -> None:
        self._relationships: Dict[str, RelationshipState] = {}

    # ---- Core API ---------------------------------------------------

    def get_or_create(self, contact_id: str, contact_name: str = "") -> RelationshipState:
        """Get existing state or create a new neutral one."""
        if contact_id not in self._relationships:
            self._relationships[contact_id] = RelationshipState(
                contact_id=contact_id,
                contact_name=contact_name or contact_id,
            )
        return self._relationships[contact_id]

    def add(
        self,
        contact_id: str,
        contact_name: str = "",
        sentiment_delta: float = 0.0,
        trust_delta: float = 0.0,
        topic: Optional[str] = None,
        commitment_made: Optional[str] = None,
        commitment_received: Optional[str] = None,
        was_positive: bool = True,
        note: Optional[str] = None,
        round_num: int = 0,
    ) -> RelationshipState:
        """Record an interaction and update the relationship state."""
        state = self.get_or_create(contact_id, contact_name)

        state.interaction_count += 1
        state.last_interaction = datetime.now().isoformat()

        state.apply_sentiment_delta(sentiment_delta)
        if trust_delta != 0:
            state.apply_trust_delta(trust_delta, round_num=round_num, reason=note or "")

        if topic and topic not in state.topics_discussed:
            state.topics_discussed.append(topic)
            state.topics_discussed = state.topics_discussed[-50:]

        if commitment_made:
            state.commitments_made.append(commitment_made)
        if commitment_received:
            state.commitments_received.append(commitment_received)

        if note:
            if was_positive:
                state.positive_moments.append(note)
                state.positive_moments = state.positive_moments[-20:]
            else:
                state.conflict_history.append(note)
                state.conflict_history = state.conflict_history[-20:]

        state.relationship_type = _classify_relationship(state)
        return state

    def retrieve(self, contact_id: str) -> Optional[RelationshipState]:
        """Get relationship state for a specific contact."""
        return self._relationships.get(contact_id)

    def summarize(self) -> str:
        """Return a text summary of the full relationship network."""
        if not self._relationships:
            return "(no relationships tracked)"
        lines: List[str] = []
        for _cid, s in self._relationships.items():
            lines.append(
                f"{s.contact_name} ({s.relationship_type}): "
                f"sentiment={s.sentiment:+.2f}, trust={s.trust_score:.2f}, "
                f"interactions={s.interaction_count}"
            )
        return "\n".join(lines)

    def get_health_report(self) -> Dict[str, Any]:
        """Generate a relationship health report across all contacts."""
        if not self._relationships:
            return {"total_contacts": 0, "summary": "No relationships tracked"}

        states = list(self._relationships.values())
        sentiments = [s.sentiment for s in states]
        trusts = [s.trust_score for s in states]
        by_sentiment = sorted(states, key=lambda s: s.sentiment, reverse=True)
        at_risk = [s for s in states if s.sentiment < -0.3 and s.interaction_count > 2]

        return {
            "total_contacts": len(states),
            "avg_sentiment": round(sum(sentiments) / len(sentiments), 3),
            "avg_trust": round(sum(trusts) / len(trusts), 3),
            "best_relationships": [
                {"name": s.contact_name, "sentiment": s.sentiment, "trust": s.trust_score}
                for s in by_sentiment[:5]
            ],
            "worst_relationships": [
                {"name": s.contact_name, "sentiment": s.sentiment, "trust": s.trust_score}
                for s in by_sentiment[-5:]
            ],
            "at_risk_contacts": [
                {"name": s.contact_name, "sentiment": s.sentiment, "interactions": s.interaction_count}
                for s in at_risk
            ],
            "relationship_types": _count_relationship_types(states),
        }

    def get_all(self) -> Dict[str, RelationshipState]:
        return dict(self._relationships)

    # ---- Persistence ------------------------------------------------

    def persist(self, path: str) -> None:
        """Write all relationship states to a JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {cid: s.to_dict() for cid, s in self._relationships.items()},
                f, ensure_ascii=False, indent=2,
            )
        logger.debug("RelationshipMemory persisted to %s", path)

    def load(self, path: str) -> None:
        """Load relationship states from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        self._relationships = {cid: RelationshipState.from_dict(s) for cid, s in obj.items()}

    def to_json(self) -> str:
        data = {cid: s.to_dict() for cid, s in self._relationships.items()}
        return json.dumps(data, ensure_ascii=False, indent=2)

    def load_json(self, data: str) -> None:
        obj = json.loads(data)
        self._relationships = {cid: RelationshipState.from_dict(s) for cid, s in obj.items()}

    # Backward-compat alias
    def record_interaction(
        self, contact_id: str, contact_name: str = "", **kwargs: Any
    ) -> RelationshipState:
        return self.add(contact_id, contact_name, **kwargs)

    def get_contact_summary(self, contact_id: str) -> Optional[Dict[str, Any]]:
        state = self._relationships.get(contact_id)
        return state.to_dict() if state else None


# ======================================================================
# Promise Memory
# ======================================================================


class PromiseStatus(str, Enum):
    PENDING = "pending"
    FULFILLED = "fulfilled"
    BROKEN = "broken"
    CANCELLED = "cancelled"


@dataclass
class Promise:
    """A tracked promise made or received between agents."""

    promise_id: str
    description: str
    direction: str                       # "made" (we promised) or "received" (they promised)
    contact_id: str
    contact_name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    due_date: Optional[str] = None
    status: PromiseStatus = PromiseStatus.PENDING
    resolved_at: Optional[str] = None
    resolution_note: str = ""
    round_created: int = 0
    round_resolved: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "promise_id": self.promise_id,
            "description": self.description,
            "direction": self.direction,
            "contact_id": self.contact_id,
            "contact_name": self.contact_name,
            "created_at": self.created_at,
            "due_date": self.due_date,
            "status": self.status.value,
            "resolved_at": self.resolved_at,
            "resolution_note": self.resolution_note,
            "round_created": self.round_created,
            "round_resolved": self.round_resolved,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Promise":
        return cls(
            promise_id=d["promise_id"],
            description=d["description"],
            direction=d.get("direction", "made"),
            contact_id=d["contact_id"],
            contact_name=d.get("contact_name", d["contact_id"]),
            created_at=d.get("created_at", ""),
            due_date=d.get("due_date"),
            status=PromiseStatus(d.get("status", "pending")),
            resolved_at=d.get("resolved_at"),
            resolution_note=d.get("resolution_note", ""),
            round_created=d.get("round_created", 0),
            round_resolved=d.get("round_resolved"),
        )


class PromiseMemory:
    """
    Tracks promises made and received with full lifecycle management.

    Status transitions: PENDING → FULFILLED / BROKEN / CANCELLED

    Trust impact is reported so callers can decide how to update RelationshipMemory.
    """

    TRUST_IMPACT: Dict[PromiseStatus, float] = {
        PromiseStatus.FULFILLED: +0.05,
        PromiseStatus.BROKEN: -0.15,
        PromiseStatus.CANCELLED: -0.03,
    }

    def __init__(self) -> None:
        self._promises: Dict[str, Promise] = {}  # promise_id → Promise
        self._counter: int = 0

    # ---- Core API ---------------------------------------------------

    def add(
        self,
        description: str,
        direction: str,
        contact_id: str,
        contact_name: str = "",
        due_date: Optional[str] = None,
        round_num: int = 0,
    ) -> Promise:
        """Record a new promise."""
        self._counter += 1
        pid = f"promise_{self._counter:06d}"
        promise = Promise(
            promise_id=pid,
            description=description,
            direction=direction,
            contact_id=contact_id,
            contact_name=contact_name or contact_id,
            due_date=due_date,
            round_created=round_num,
        )
        self._promises[pid] = promise
        logger.debug(
            "Promise recorded: [%s] %s — %s",
            direction, description[:60], contact_name,
        )
        return promise

    def retrieve(
        self,
        contact_id: Optional[str] = None,
        direction: Optional[str] = None,
        status: Optional[PromiseStatus] = None,
    ) -> List[Promise]:
        """Retrieve promises with optional filters."""
        results = list(self._promises.values())
        if contact_id:
            results = [p for p in results if p.contact_id == contact_id]
        if direction:
            results = [p for p in results if p.direction == direction]
        if status:
            results = [p for p in results if p.status == status]
        return results

    def resolve(
        self,
        promise_id: str,
        new_status: PromiseStatus,
        note: str = "",
        round_num: int = 0,
    ) -> Tuple[Promise, float]:
        """Resolve a promise and return the trust impact delta."""
        promise = self._promises.get(promise_id)
        if promise is None:
            raise KeyError(f"Unknown promise: {promise_id}")
        if promise.status != PromiseStatus.PENDING:
            raise ValueError(f"Promise {promise_id} is already {promise.status.value}")

        promise.status = new_status
        promise.resolved_at = datetime.now().isoformat()
        promise.resolution_note = note
        promise.round_resolved = round_num

        trust_delta = self.TRUST_IMPACT.get(new_status, 0.0)
        logger.debug(
            "Promise resolved: %s → %s, trust_delta=%+.2f",
            promise_id, new_status.value, trust_delta,
        )
        return promise, trust_delta

    def summarize(self) -> str:
        """Return a text summary of all promises grouped by status."""
        by_status: Dict[str, List[str]] = defaultdict(list)
        for p in self._promises.values():
            by_status[p.status.value].append(
                f"  [{p.direction}] {p.description[:80]} ← {p.contact_name}"
            )
        lines: List[str] = []
        for status, items in by_status.items():
            lines.append(f"{status.upper()}:")
            lines.extend(items)
        return "\n".join(lines) if lines else "(no promises tracked)"

    def get_pending_for_contact(self, contact_id: str) -> List[Promise]:
        """Get all pending promises involving a contact."""
        return self.retrieve(contact_id=contact_id, status=PromiseStatus.PENDING)

    def get_stats(self) -> Dict[str, Any]:
        promises = list(self._promises.values())
        return {
            "total": len(promises),
            "pending": sum(1 for p in promises if p.status == PromiseStatus.PENDING),
            "fulfilled": sum(1 for p in promises if p.status == PromiseStatus.FULFILLED),
            "broken": sum(1 for p in promises if p.status == PromiseStatus.BROKEN),
            "cancelled": sum(1 for p in promises if p.status == PromiseStatus.CANCELLED),
        }

    # ---- Persistence ------------------------------------------------

    def persist(self, path: str) -> None:
        """Write all promises to a JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "promises": [p.to_dict() for p in self._promises.values()],
                    "counter": self._counter,
                },
                f, ensure_ascii=False, indent=2,
            )

    def load(self, path: str) -> None:
        """Load promises from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        self._counter = obj.get("counter", 0)
        self._promises = {
            p["promise_id"]: Promise.from_dict(p)
            for p in obj.get("promises", [])
        }

    def to_json(self) -> str:
        return json.dumps(
            {
                "promises": [p.to_dict() for p in self._promises.values()],
                "counter": self._counter,
            },
            ensure_ascii=False, indent=2,
        )

    def load_json(self, data: str) -> None:
        obj = json.loads(data)
        self._counter = obj.get("counter", 0)
        self._promises = {
            p["promise_id"]: Promise.from_dict(p)
            for p in obj.get("promises", [])
        }


# ======================================================================
# Emotional State
# ======================================================================

class Emotion(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    CURIOUS = "curious"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    EXCITED = "excited"
    SAD = "sad"
    SUSPICIOUS = "suspicious"
    CONFIDENT = "confident"


@dataclass
class EmotionalEvent:
    """A recorded emotional shift during simulation."""
    round_num: int
    from_emotion: str
    to_emotion: str
    trigger: str
    intensity_delta: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_num": self.round_num,
            "from_emotion": self.from_emotion,
            "to_emotion": self.to_emotion,
            "trigger": self.trigger,
            "intensity_delta": self.intensity_delta,
            "timestamp": self.timestamp,
        }


class EmotionalState:
    """
    Tracks the current emotional state of an agent during simulation.

    Emotions evolve based on events, revert toward baseline over time,
    and influence how the agent behaves in subsequent rounds.

    Intensity is 0.0 (barely present) to 1.0 (overwhelming).
    """

    # Map each emotion to a reversion-toward-neutral rate per round
    REVERSION_RATE: Dict[str, float] = {
        Emotion.HAPPY.value: 0.05,
        Emotion.CURIOUS.value: 0.08,
        Emotion.FRUSTRATED.value: 0.06,
        Emotion.ANGRY.value: 0.04,
        Emotion.ANXIOUS.value: 0.07,
        Emotion.EXCITED.value: 0.1,
        Emotion.SAD.value: 0.03,
        Emotion.SUSPICIOUS.value: 0.05,
        Emotion.CONFIDENT.value: 0.06,
        Emotion.NEUTRAL.value: 0.0,
    }

    def __init__(
        self,
        baseline_emotion: str = Emotion.NEUTRAL.value,
        baseline_intensity: float = 0.5,
    ) -> None:
        self.baseline_emotion = baseline_emotion
        self.baseline_intensity = baseline_intensity
        self.current_emotion: str = baseline_emotion
        self.current_intensity: float = baseline_intensity
        self._history: List[EmotionalEvent] = []
        self._round: int = 0

    # ---- Core API ---------------------------------------------------

    def add(
        self,
        new_emotion: str,
        intensity_delta: float,
        trigger: str = "",
        round_num: Optional[int] = None,
    ) -> None:
        """Apply an emotional shift."""
        rnd = round_num if round_num is not None else self._round
        old_emotion = self.current_emotion
        old_intensity = self.current_intensity

        self.current_emotion = new_emotion
        self.current_intensity = round(max(0.0, min(1.0, old_intensity + intensity_delta)), 4)

        event = EmotionalEvent(
            round_num=rnd,
            from_emotion=old_emotion,
            to_emotion=new_emotion,
            trigger=trigger,
            intensity_delta=intensity_delta,
        )
        self._history.append(event)
        self._history = self._history[-200:]

    def retrieve(self, last_n: int = 10) -> List[EmotionalEvent]:
        """Retrieve the most recent emotional events."""
        return self._history[-last_n:]

    def tick(self, round_num: Optional[int] = None) -> None:
        """Advance one simulation round."""
        if round_num is not None:
            self._round = round_num
        else:
            self._round += 1

        # Revert intensity toward baseline
        rate = self.REVERSION_RATE.get(self.current_emotion, 0.05)
        if self.current_intensity > self.baseline_intensity:
            self.current_intensity = round(
                max(self.baseline_intensity, self.current_intensity - rate), 4
            )
        elif self.current_intensity < self.baseline_intensity:
            self.current_intensity = round(
                min(self.baseline_intensity, self.current_intensity + rate), 4
            )

        # Revert emotion toward baseline if intensity is low
        if (
            self.current_emotion != self.baseline_emotion
            and self.current_intensity <= self.baseline_intensity + 0.05
        ):
            self.current_emotion = self.baseline_emotion

    def summarize(self) -> str:
        """Return a brief text summary of the current emotional state."""
        return (
            f"Current: {self.current_emotion} (intensity={self.current_intensity:.2f}) | "
            f"Baseline: {self.baseline_emotion} ({self.baseline_intensity:.2f})"
        )

    def get_modifier(self) -> Dict[str, float]:
        """Return a dict of behavioral modifiers driven by the current emotion."""
        modifiers: Dict[str, float] = {
            "verbosity": 0.0,
            "aggressiveness": 0.0,
            "openness": 0.0,
            "compliance": 0.0,
        }
        intensity = self.current_intensity

        emotion_effects: Dict[str, Dict[str, float]] = {
            Emotion.HAPPY.value: {"verbosity": 0.2, "openness": 0.3, "compliance": 0.2},
            Emotion.EXCITED.value: {"verbosity": 0.4, "openness": 0.2, "aggressiveness": 0.1},
            Emotion.ANGRY.value: {"aggressiveness": 0.5, "verbosity": 0.3, "compliance": -0.4},
            Emotion.FRUSTRATED.value: {"aggressiveness": 0.2, "compliance": -0.2, "verbosity": -0.1},
            Emotion.SAD.value: {"verbosity": -0.3, "openness": -0.2, "compliance": 0.1},
            Emotion.ANXIOUS.value: {"verbosity": 0.1, "compliance": 0.2, "openness": -0.1},
            Emotion.SUSPICIOUS.value: {"openness": -0.3, "compliance": -0.3, "aggressiveness": 0.1},
            Emotion.CONFIDENT.value: {"verbosity": 0.1, "openness": 0.2, "compliance": -0.1},
            Emotion.CURIOUS.value: {"verbosity": 0.2, "openness": 0.4},
        }

        effects = emotion_effects.get(self.current_emotion, {})
        for key, base_effect in effects.items():
            modifiers[key] = round(base_effect * intensity, 4)

        return modifiers

    # ---- Persistence ------------------------------------------------

    def persist(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._to_obj(), f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            self._from_obj(json.load(f))

    def to_json(self) -> str:
        return json.dumps(self._to_obj(), ensure_ascii=False, indent=2)

    def load_json(self, data: str) -> None:
        self._from_obj(json.loads(data))

    def _to_obj(self) -> Dict[str, Any]:
        return {
            "baseline_emotion": self.baseline_emotion,
            "baseline_intensity": self.baseline_intensity,
            "current_emotion": self.current_emotion,
            "current_intensity": self.current_intensity,
            "round": self._round,
            "history": [e.to_dict() for e in self._history],
        }

    def _from_obj(self, obj: Dict[str, Any]) -> None:
        self.baseline_emotion = obj.get("baseline_emotion", Emotion.NEUTRAL.value)
        self.baseline_intensity = obj.get("baseline_intensity", 0.5)
        self.current_emotion = obj.get("current_emotion", self.baseline_emotion)
        self.current_intensity = obj.get("current_intensity", self.baseline_intensity)
        self._round = obj.get("round", 0)
        self._history = [
            EmotionalEvent(**e) for e in obj.get("history", [])
        ]


# ======================================================================
# Twin Memory  — combined memory façade for Digital Twins
# ======================================================================


class TwinMemory:
    """
    Combined memory façade for a Digital Twin.

    Bundles ShortTermMemory, LongTermMemory, RelationshipMemory,
    PromiseMemory, and EmotionalState into a single object.

    Short-term evictions are automatically forwarded to long-term memory
    as compressed facts so no interaction is ever fully lost.
    """

    def __init__(
        self,
        contact_id: str,
        llm_client: Optional[LLMClient] = None,
        stm_window: int = 20,
        ltm_compression_threshold: int = 10,
        baseline_emotion: str = Emotion.NEUTRAL.value,
    ) -> None:
        self.contact_id = contact_id
        self.short_term = ShortTermMemory(max_entries=stm_window)
        self.long_term = LongTermMemory(
            llm_client=llm_client,
            compression_threshold=ltm_compression_threshold,
        )
        self.relationships = RelationshipMemory()
        self.promises = PromiseMemory()
        self.emotion = EmotionalState(baseline_emotion=baseline_emotion)

        # Wire up short-term evictions into long-term
        self.short_term.on_eviction(self._on_stm_eviction)

    # ---- Convenience delegates --------------------------------------

    def record_message(
        self,
        content: str,
        source: str = "user",
        contact_id: Optional[str] = None,
        round_num: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a message into short-term memory."""
        self.short_term.add(
            content, source=source, contact_id=contact_id,
            round_num=round_num, metadata=metadata,
        )

    def update_relationship(
        self,
        other_contact_id: str,
        other_name: str = "",
        sentiment_delta: float = 0.0,
        trust_delta: float = 0.0,
        topic: Optional[str] = None,
        note: Optional[str] = None,
        was_positive: bool = True,
        round_num: int = 0,
    ) -> RelationshipState:
        """Update relationship state with another agent."""
        return self.relationships.add(
            contact_id=other_contact_id,
            contact_name=other_name,
            sentiment_delta=sentiment_delta,
            trust_delta=trust_delta,
            topic=topic,
            note=note,
            was_positive=was_positive,
            round_num=round_num,
        )

    def make_promise(
        self,
        description: str,
        other_contact_id: str,
        other_name: str = "",
        direction: str = "made",
        round_num: int = 0,
    ) -> Promise:
        """Record a new promise."""
        return self.promises.add(
            description=description,
            direction=direction,
            contact_id=other_contact_id,
            contact_name=other_name,
            round_num=round_num,
        )

    def resolve_promise(
        self, promise_id: str, status: PromiseStatus, note: str = "", round_num: int = 0
    ) -> Tuple[Promise, float]:
        """Resolve a promise and apply trust impact to the relationship."""
        promise, trust_delta = self.promises.resolve(promise_id, status, note, round_num)
        if trust_delta != 0:
            self.relationships.add(
                contact_id=promise.contact_id,
                contact_name=promise.contact_name,
                trust_delta=trust_delta,
                note=f"Promise {status.value}: {promise.description[:60]}",
                was_positive=(trust_delta > 0),
                round_num=round_num,
            )
        return promise, trust_delta

    def feel(
        self,
        emotion: str,
        intensity_delta: float,
        trigger: str = "",
        round_num: int = 0,
    ) -> None:
        """Update emotional state."""
        self.emotion.add(emotion, intensity_delta, trigger=trigger, round_num=round_num)

    def tick(self, round_num: Optional[int] = None) -> None:
        """Advance the emotional state one simulation round."""
        self.emotion.tick(round_num=round_num)

    def summarize(self) -> str:
        """Return a full text summary of all memory subsystems."""
        sections = [
            f"=== Short-term ({len(self.short_term.entries)} entries) ===",
            self.short_term.summarize(),
            "\n=== Long-term ===",
            self.long_term.summarize(),
            "\n=== Relationships ===",
            self.relationships.summarize(),
            "\n=== Promises ===",
            self.promises.summarize(),
            "\n=== Emotional state ===",
            self.emotion.summarize(),
        ]
        return "\n".join(sections)

    def to_context_block(self) -> str:
        """Generate a compact context block for inclusion in LLM prompts."""
        recent = self.short_term.to_context_string(max_entries=10)
        ltm_items = self.long_term.get_all_summaries()
        ltm_text = "\n".join(f"- {s['summary']}" for s in ltm_items[-3:]) or "(none)"
        em = self.emotion.current_emotion
        em_intensity = self.emotion.current_intensity

        pending_promises = self.promises.retrieve(status=PromiseStatus.PENDING)
        promise_lines = "\n".join(
            f"- [{p.direction}] {p.description[:60]} ← {p.contact_name}"
            for p in pending_promises[:5]
        ) or "(none)"

        return (
            f"[Recent interactions]\n{recent}\n\n"
            f"[Long-term knowledge]\n{ltm_text}\n\n"
            f"[Current emotion] {em} (intensity {em_intensity:.2f})\n\n"
            f"[Pending promises]\n{promise_lines}"
        )

    # ---- Persistence ------------------------------------------------

    def persist(self, base_path: str) -> None:
        """Persist all memory subsystems to a directory."""
        base = Path(base_path)
        base.mkdir(parents=True, exist_ok=True)
        self.short_term.persist(str(base / "stm.json"))
        self.long_term.persist(str(base / "ltm.json"))
        self.relationships.persist(str(base / "relationships.json"))
        self.promises.persist(str(base / "promises.json"))
        self.emotion.persist(str(base / "emotion.json"))
        logger.info("TwinMemory persisted to %s", base_path)

    def load(self, base_path: str) -> None:
        """Load all memory subsystems from a directory."""
        base = Path(base_path)
        for attr, filename in [
            ("short_term", "stm.json"),
            ("long_term", "ltm.json"),
            ("relationships", "relationships.json"),
            ("promises", "promises.json"),
            ("emotion", "emotion.json"),
        ]:
            file_path = base / filename
            if file_path.exists():
                getattr(self, attr).load(str(file_path))
        logger.info("TwinMemory loaded from %s", base_path)

    # ---- Private ---------------------------------------------------

    def _on_stm_eviction(self, entry: MemoryEntry) -> None:
        """Forward evicted STM entries to long-term memory."""
        fact = f"[Round {entry.round_num}][{entry.source}] {entry.content}"
        self.long_term.add(fact)


# ======================================================================
# Private helpers
# ======================================================================


def _classify_relationship(state: RelationshipState) -> str:
    if state.sentiment > 0.5 and state.trust_score > 0.6:
        return "ally"
    elif state.sentiment < -0.3:
        return "competitor"
    elif state.interaction_count < 3:
        return "unknown"
    return "neutral"


def _count_relationship_types(states: List[RelationshipState]) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for s in states:
        counts[s.relationship_type] += 1
    return dict(counts)
