# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Derived from Cronberry (Mega Promoting SRL).
"""
Graph builder service for md-chat-ai.

Constructs a Neo4j-backed MD-Chat knowledge graph from Synapse Matrix events
using a configurable ontology. The pipeline is:

  1. Create / merge a Graph node.
  2. Apply the ontology metadata.
  3. Ingest events through :class:`SynapseEventAdapter` (was Cronberry's
     ``sqlite_import.py``).
  4. Run PageRank to score node importance.
  5. Run Louvain community detection to label clusters.

Privacy by design
-----------------
The builder respects ``consent_tier`` on every node and edge. The adapter
extracts relationship metadata only — message *content* is NOT ingested
unless the source event explicitly carries ``opt_in_content=True``.
"""

from __future__ import annotations

import logging
import threading
import uuid as _uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from ..config import CONFIG
from .neo4j_backend import Neo4jGraphBackend
from .ontology import CONSENT_TIERS, normalise_consent_tier

logger = logging.getLogger("md_chat_ai.graph.builder")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class GraphInfo:
    """Summary statistics about a constructed graph."""

    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]
    consent_breakdown: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
            "consent_breakdown": self.consent_breakdown,
        }


@dataclass
class ParsedEvent:
    """Result of parsing one Matrix event into graph fragments."""

    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Synapse Matrix event adapter
# ---------------------------------------------------------------------------


class SynapseEventAdapter:
    """
    Parse Synapse / Matrix events into graph nodes and edges.

    Replaces Cronberry's SQLite import pipeline. The adapter is intentionally
    privacy-conscious:

    * If an event lacks ``content.opt_in_content`` (or ``opt_in_content`` at
      the top level) we DO NOT persist message bodies. We only record the
      relationship metadata (``sender`` joined room ``X``, mentioned user
      ``Y``, etc.).
    * Every node and edge produced by the adapter carries a ``consent_tier``
      derived from the event (defaults to ``private``).

    Supported event types:

    * ``m.room.member`` (joins) → ``MEMBER_OF`` / ``MEMBER_OF_CHANNEL``
    * ``m.room.message`` (text)  → optional ``MENTIONED`` edges
    * ``md.chat.contact_added``  → ``RELATED`` between two users/contacts
    * ``md.chat.business_owned`` → ``OWNS_BUSINESS`` (User → Company)
    * ``md.chat.miniapp_used``   → ``USED_MINIAPP`` (User → MiniApp)
    * ``md.chat.twin_created``   → ``OWNS_TWIN`` (User → Twin)
    * ``md.chat.promise``        → ``PROMISED``
    """

    #: Room types we treat as broadcast Channels rather than Groups.
    CHANNEL_ROOM_TYPES: Tuple[str, ...] = ("m.space", "m.channel")

    def __init__(self, default_consent_tier: str = "private") -> None:
        """
        Args:
            default_consent_tier: Fallback tier when the event has no marker.
        """
        self.default_consent_tier = normalise_consent_tier(default_consent_tier)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_event(self, event: Dict[str, Any]) -> ParsedEvent:
        """
        Convert a single Matrix event into a :class:`ParsedEvent`.

        Args:
            event: Event JSON as delivered by Synapse (Application Service or
                ``/sync`` payload).

        Returns:
            A :class:`ParsedEvent` containing zero or more node/edge dicts.
            Unknown event types yield an empty result.
        """
        etype = event.get("type", "")
        method = self._DISPATCH.get(etype)
        if method is None:
            return ParsedEvent()
        return method(self, event)

    def parse_events(self, events: Iterable[Dict[str, Any]]) -> ParsedEvent:
        """
        Convert a batch of Matrix events, concatenating their results.

        Args:
            events: Iterable of Synapse event JSON dicts.

        Returns:
            One :class:`ParsedEvent` aggregating nodes/edges across the batch.
        """
        merged = ParsedEvent()
        for event in events:
            parsed = self.parse_event(event)
            merged.nodes.extend(parsed.nodes)
            merged.edges.extend(parsed.edges)
        return merged

    # ------------------------------------------------------------------
    # Per-event-type handlers
    # ------------------------------------------------------------------

    def _resolve_tier(self, event: Dict[str, Any]) -> str:
        """Pull ``consent_tier`` from event content or fall back to default."""
        content = event.get("content", {}) or {}
        tier = content.get("consent_tier") or event.get("consent_tier")
        return normalise_consent_tier(tier, default=self.default_consent_tier)

    @staticmethod
    def _opt_in(event: Dict[str, Any]) -> bool:
        """Whether the user opted in to having content ingested."""
        content = event.get("content", {}) or {}
        return bool(
            content.get("opt_in_content") or event.get("opt_in_content")
        )

    def _handle_room_member(self, event: Dict[str, Any]) -> ParsedEvent:
        """``m.room.member`` join → MEMBER_OF / MEMBER_OF_CHANNEL."""
        content = event.get("content", {}) or {}
        membership = content.get("membership")
        if membership != "join":
            return ParsedEvent()

        sender = event.get("state_key") or event.get("sender")
        room_id = event.get("room_id")
        if not sender or not room_id:
            return ParsedEvent()

        tier = self._resolve_tier(event)
        room_type = (content.get("room_type")
                     or event.get("room_type")
                     or "m.room")
        is_channel = room_type in self.CHANNEL_ROOM_TYPES
        target_type = "Channel" if is_channel else "Group"
        edge_type = "MEMBER_OF_CHANNEL" if is_channel else "MEMBER_OF"

        user_node = {
            "name": sender,
            "entity_type": "User",
            "consent_tier": tier,
            "attributes": {"matrix_id": sender},
            "summary": "",
        }
        room_node = {
            "name": room_id,
            "entity_type": target_type,
            "consent_tier": tier,
            "attributes": {},
            "summary": content.get("displayname", "") or "",
        }
        edge = {
            "source": sender,
            "target": room_id,
            "edge_type": edge_type,
            "fact": f"{sender} joined {room_id}",
            "consent_tier": tier,
            "attributes": {"joined_at": event.get("origin_server_ts", "")},
        }
        return ParsedEvent(nodes=[user_node, room_node], edges=[edge])

    def _handle_room_message(self, event: Dict[str, Any]) -> ParsedEvent:
        """``m.room.message`` → optional MENTIONED edges for tagged users."""
        content = event.get("content", {}) or {}
        sender = event.get("sender")
        room_id = event.get("room_id")
        if not sender or not room_id:
            return ParsedEvent()

        tier = self._resolve_tier(event)
        mentions: List[str] = []
        # Matrix MSC2674 mentions
        m_mentions = (
            content.get("m.mentions")
            or content.get("mentions")
            or {}
        )
        if isinstance(m_mentions, dict):
            mentions = list(m_mentions.get("user_ids") or [])

        opt_in_content = self._opt_in(event)
        body = content.get("body", "") if opt_in_content else ""

        nodes: List[Dict[str, Any]] = [{
            "name": sender,
            "entity_type": "User",
            "consent_tier": tier,
            "attributes": {"matrix_id": sender},
            "summary": "",
        }]
        edges: List[Dict[str, Any]] = []

        for target in mentions:
            nodes.append({
                "name": target,
                "entity_type": "User",
                "consent_tier": tier,
                "attributes": {"matrix_id": target},
                "summary": "",
            })
            edges.append({
                "source": sender,
                "target": target,
                "edge_type": "MENTIONED",
                "fact": body[:200] if opt_in_content else "",
                "consent_tier": tier,
                "attributes": {},
            })
        return ParsedEvent(nodes=nodes, edges=edges)

    def _handle_contact_added(self, event: Dict[str, Any]) -> ParsedEvent:
        """``md.chat.contact_added`` → RELATED edge."""
        content = event.get("content", {}) or {}
        source = event.get("sender") or content.get("source")
        target = content.get("contact") or content.get("target")
        if not source or not target:
            return ParsedEvent()

        tier = self._resolve_tier(event)
        return ParsedEvent(
            nodes=[
                {
                    "name": source,
                    "entity_type": "User",
                    "consent_tier": tier,
                    "attributes": {"matrix_id": source},
                    "summary": "",
                },
                {
                    "name": target,
                    "entity_type": "Contact",
                    "consent_tier": tier,
                    "attributes": {"full_name": content.get("display_name", "")},
                    "summary": "",
                },
            ],
            edges=[{
                "source": source,
                "target": target,
                "edge_type": "RELATED",
                "fact": content.get("note", ""),
                "consent_tier": tier,
                "attributes": {},
            }],
        )

    def _handle_business_owned(self, event: Dict[str, Any]) -> ParsedEvent:
        """``md.chat.business_owned`` → OWNS_BUSINESS edge."""
        content = event.get("content", {}) or {}
        owner = event.get("sender") or content.get("owner")
        company = content.get("company") or content.get("org_name")
        if not owner or not company:
            return ParsedEvent()
        tier = self._resolve_tier(event)
        return ParsedEvent(
            nodes=[
                {
                    "name": owner,
                    "entity_type": "User",
                    "consent_tier": tier,
                    "attributes": {"matrix_id": owner},
                    "summary": "",
                },
                {
                    "name": company,
                    "entity_type": "Company",
                    "consent_tier": tier,
                    "attributes": {"org_name": company,
                                   "industry": content.get("industry", "")},
                    "summary": "",
                },
            ],
            edges=[{
                "source": owner,
                "target": company,
                "edge_type": "OWNS_BUSINESS",
                "fact": content.get("role", "owner"),
                "consent_tier": tier,
                "attributes": {"role": content.get("role", "owner")},
            }],
        )

    def _handle_miniapp_used(self, event: Dict[str, Any]) -> ParsedEvent:
        """``md.chat.miniapp_used`` → USED_MINIAPP edge."""
        content = event.get("content", {}) or {}
        user = event.get("sender") or content.get("user")
        app = content.get("miniapp") or content.get("app_title")
        if not user or not app:
            return ParsedEvent()
        tier = self._resolve_tier(event)
        return ParsedEvent(
            nodes=[
                {
                    "name": user,
                    "entity_type": "User",
                    "consent_tier": tier,
                    "attributes": {"matrix_id": user},
                    "summary": "",
                },
                {
                    "name": app,
                    "entity_type": "MiniApp",
                    "consent_tier": tier,
                    "attributes": {"app_title": app,
                                   "category": content.get("category", "")},
                    "summary": "",
                },
            ],
            edges=[{
                "source": user,
                "target": app,
                "edge_type": "USED_MINIAPP",
                "fact": "",
                "consent_tier": tier,
                "attributes": {"last_used_at": event.get("origin_server_ts", "")},
            }],
        )

    def _handle_twin_created(self, event: Dict[str, Any]) -> ParsedEvent:
        """``md.chat.twin_created`` → OWNS_TWIN edge."""
        content = event.get("content", {}) or {}
        owner = event.get("sender") or content.get("owner")
        twin = content.get("twin") or content.get("twin_name")
        if not owner or not twin:
            return ParsedEvent()
        tier = self._resolve_tier(event)
        return ParsedEvent(
            nodes=[
                {
                    "name": owner,
                    "entity_type": "User",
                    "consent_tier": tier,
                    "attributes": {"matrix_id": owner},
                    "summary": "",
                },
                {
                    "name": twin,
                    "entity_type": "Twin",
                    "consent_tier": tier,
                    "attributes": {"twin_name": twin,
                                   "model": content.get("model", "")},
                    "summary": "",
                },
            ],
            edges=[{
                "source": owner,
                "target": twin,
                "edge_type": "OWNS_TWIN",
                "fact": "",
                "consent_tier": tier,
                "attributes": {"created_at_iso": event.get("origin_server_ts", "")},
            }],
        )

    def _handle_promise(self, event: Dict[str, Any]) -> ParsedEvent:
        """``md.chat.promise`` → PROMISED edge."""
        content = event.get("content", {}) or {}
        source = event.get("sender") or content.get("source")
        target = content.get("to") or content.get("target")
        if not source or not target:
            return ParsedEvent()
        tier = self._resolve_tier(event)
        return ParsedEvent(
            nodes=[
                {
                    "name": source,
                    "entity_type": "User",
                    "consent_tier": tier,
                    "attributes": {"matrix_id": source},
                    "summary": "",
                },
                {
                    "name": target,
                    "entity_type": "Contact",
                    "consent_tier": tier,
                    "attributes": {},
                    "summary": "",
                },
            ],
            edges=[{
                "source": source,
                "target": target,
                "edge_type": "PROMISED",
                "fact": content.get("text", "") if self._opt_in(event) else "",
                "consent_tier": tier,
                "attributes": {
                    "promise_date": event.get("origin_server_ts", ""),
                    "due_date": content.get("due_date", ""),
                },
            }],
        )

    #: Event-type → handler dispatch table. Defined after methods so it can
    #: reference them by name.
    _DISPATCH: Dict[str, Callable[["SynapseEventAdapter", Dict[str, Any]], ParsedEvent]] = {}


# Populate the dispatch table after the class is defined.
SynapseEventAdapter._DISPATCH = {
    "m.room.member":            SynapseEventAdapter._handle_room_member,
    "m.room.message":           SynapseEventAdapter._handle_room_message,
    "md.chat.contact_added":    SynapseEventAdapter._handle_contact_added,
    "md.chat.business_owned":   SynapseEventAdapter._handle_business_owned,
    "md.chat.miniapp_used":     SynapseEventAdapter._handle_miniapp_used,
    "md.chat.twin_created":     SynapseEventAdapter._handle_twin_created,
    "md.chat.promise":          SynapseEventAdapter._handle_promise,
}


# ---------------------------------------------------------------------------
# Lightweight PageRank + Louvain implementations
# ---------------------------------------------------------------------------


def _pagerank(
    nodes: List[str],
    edges: List[Tuple[str, str]],
    damping: float = 0.85,
    iterations: int = 30,
) -> Dict[str, float]:
    """
    Compute PageRank scores for a graph using power iteration.

    Pure-Python so we do not pull in networkx for a single algorithm.

    Args:
        nodes: List of node identifiers.
        edges: Directed edge tuples ``(source, target)``.
        damping: PageRank damping factor.
        iterations: Number of power-iteration steps.

    Returns:
        Dict mapping each node to its rank in [0, 1].
    """
    if not nodes:
        return {}
    n = len(nodes)
    rank: Dict[str, float] = {node: 1.0 / n for node in nodes}

    outgoing: Dict[str, List[str]] = {node: [] for node in nodes}
    for src, tgt in edges:
        if src in outgoing and tgt in rank:
            outgoing[src].append(tgt)

    for _ in range(iterations):
        new_rank: Dict[str, float] = {node: (1.0 - damping) / n for node in nodes}
        for node, outs in outgoing.items():
            if not outs:
                # distribute mass uniformly when a node has no outgoing edges
                share = damping * rank[node] / n
                for other in nodes:
                    new_rank[other] += share
            else:
                share = damping * rank[node] / len(outs)
                for tgt in outs:
                    new_rank[tgt] += share
        rank = new_rank
    return rank


def _louvain(
    nodes: List[str],
    edges: List[Tuple[str, str]],
    max_passes: int = 5,
) -> Dict[str, int]:
    """
    Detect communities with a simplified Louvain-style modularity heuristic.

    We use a label-propagation pass as a lightweight stand-in for the full
    Louvain algorithm. Each node initially has its own community label; on
    every pass, each node is reassigned to the most common label among its
    neighbours. Converges quickly on small graphs.

    Args:
        nodes: List of node identifiers.
        edges: Undirected edge tuples ``(a, b)``.
        max_passes: Maximum propagation passes.

    Returns:
        Dict mapping each node to a community integer id.
    """
    if not nodes:
        return {}

    label: Dict[str, int] = {node: idx for idx, node in enumerate(nodes)}

    neighbours: Dict[str, List[str]] = {node: [] for node in nodes}
    for a, b in edges:
        if a in neighbours and b in neighbours:
            neighbours[a].append(b)
            neighbours[b].append(a)

    for _ in range(max_passes):
        changed = False
        for node in nodes:
            counts: Dict[int, int] = {}
            for neigh in neighbours[node]:
                lbl = label[neigh]
                counts[lbl] = counts.get(lbl, 0) + 1
            if not counts:
                continue
            best = max(counts.items(), key=lambda kv: kv[1])[0]
            if best != label[node]:
                label[node] = best
                changed = True
        if not changed:
            break

    # Compact community ids so they start at 0
    remap: Dict[int, int] = {}
    for node in nodes:
        old = label[node]
        if old not in remap:
            remap[old] = len(remap)
        label[node] = remap[old]
    return label


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class GraphBuilderService:
    """
    Build an MD-Chat knowledge graph from Synapse events.

    Workflow (async):
      1. Create / merge a graph in Neo4j.
      2. Apply the ontology (entity + edge type definitions).
      3. Ingest Synapse events via :class:`SynapseEventAdapter`.
      4. Run PageRank and Louvain community detection on the resulting graph.
      5. Collect and return graph statistics.

    All heavy work runs in a daemon thread so the caller is not blocked.
    """

    def __init__(
        self,
        backend: Optional[Neo4jGraphBackend] = None,
        adapter: Optional[SynapseEventAdapter] = None,
    ) -> None:
        """
        Args:
            backend: Pre-configured :class:`Neo4jGraphBackend`. If ``None``,
                a new one is built from :data:`CONFIG`.
            adapter: Optional :class:`SynapseEventAdapter` instance.
        """
        self.backend = backend or Neo4jGraphBackend(
            uri=CONFIG.neo4j_uri,
            user=CONFIG.neo4j_user,
            password=CONFIG.neo4j_password,
        )
        self.adapter = adapter or SynapseEventAdapter()

    # ------------------------------------------------------------------
    # Async (threaded) entry point
    # ------------------------------------------------------------------

    def build_graph_async(
        self,
        events: List[Dict[str, Any]],
        ontology: Dict[str, Any],
        graph_name: str = "MD-Chat Graph",
        on_complete: Optional[Callable[[GraphInfo], None]] = None,
    ) -> str:
        """
        Launch the graph-build pipeline in a background thread.

        Args:
            events: Synapse Matrix events to ingest.
            ontology: Ontology dict (see :class:`OntologyGenerator`).
            graph_name: Human-readable name stored on the Graph node.
            on_complete: Optional callback invoked with :class:`GraphInfo`
                once the build finishes.

        Returns:
            The newly created ``graph_id``.
        """
        graph_id = f"mdchat_{_uuid.uuid4().hex[:16]}"

        thread = threading.Thread(
            target=self._build_graph_worker,
            args=(graph_id, events, ontology, graph_name, on_complete),
            daemon=True,
        )
        thread.start()
        logger.info(f"Graph build started: graph_id={graph_id}, name={graph_name!r}")
        return graph_id

    def _build_graph_worker(
        self,
        graph_id: str,
        events: List[Dict[str, Any]],
        ontology: Dict[str, Any],
        graph_name: str,
        on_complete: Optional[Callable[[GraphInfo], None]],
    ) -> None:
        """Background worker — runs the full ingestion pipeline."""
        try:
            info = self.build_graph_sync(events, ontology, graph_name, graph_id=graph_id)
            if on_complete:
                on_complete(info)
        except Exception as exc:  # pragma: no cover - background only
            import traceback
            logger.error(
                f"Graph build failed for {graph_id}: {exc}\n{traceback.format_exc()}"
            )

    # ------------------------------------------------------------------
    # Synchronous build (used by tests + the worker)
    # ------------------------------------------------------------------

    def build_graph_sync(
        self,
        events: List[Dict[str, Any]],
        ontology: Dict[str, Any],
        graph_name: str = "MD-Chat Graph",
        graph_id: Optional[str] = None,
    ) -> GraphInfo:
        """
        Synchronous build: useful for tests and CLIs.

        Args:
            events: Synapse Matrix events to ingest.
            ontology: Ontology dict.
            graph_name: Human-readable graph name.
            graph_id: Optional explicit ``graph_id``; auto-generated if absent.

        Returns:
            :class:`GraphInfo` with node/edge counts and entity-type list.
        """
        import asyncio

        graph_id = graph_id or f"mdchat_{_uuid.uuid4().hex[:16]}"

        async def _run() -> GraphInfo:
            # 1. Create graph
            await self.backend.create_graph(
                graph_id=graph_id,
                name=graph_name,
                description="MD-Chat knowledge graph — sovereign messenger intelligence",
            )

            # 2. Apply ontology
            await self.backend.set_ontology(
                graph_id=graph_id,
                entity_types=ontology.get("entity_types", []),
                edge_types=ontology.get("edge_types", []),
            )

            # 3. Ingest events
            await self._ingest_events(graph_id, events)

            # 4. Analytics (PageRank, Louvain) — best-effort, never fatal
            try:
                await self._run_analytics_async(graph_id)
            except Exception as exc:
                logger.warning(f"Analytics step skipped for {graph_id}: {exc}")

            # 5. Stats
            stats = self.backend.get_graph_stats(graph_id)
            entity_types = sorted(stats.get("entity_types", {}).keys())
            return GraphInfo(
                graph_id=graph_id,
                node_count=stats.get("node_count", 0),
                edge_count=stats.get("edge_count", 0),
                entity_types=entity_types,
                consent_breakdown=stats.get("consent_breakdown", {}),
            )

        return asyncio.run(_run())

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    async def _ingest_events(
        self,
        graph_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        """Parse events via the adapter and write nodes/edges to the backend."""
        parsed = self.adapter.parse_events(events)
        logger.info(
            f"SynapseEventAdapter: parsed {len(events)} events → "
            f"{len(parsed.nodes)} node fragments, {len(parsed.edges)} edge fragments"
        )

        # Dedupe nodes on (name, entity_type) preserving the most permissive tier.
        # ``private`` is more restrictive than ``friends`` which is more
        # restrictive than ``public`` — we keep the LEAST permissive value.
        tier_rank = {"public": 0, "friends": 1, "private": 2}
        seen: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for node in parsed.nodes:
            key = (node["name"], node["entity_type"])
            if key not in seen:
                seen[key] = dict(node)
            else:
                existing = seen[key]
                if tier_rank.get(node["consent_tier"], 2) > tier_rank.get(
                    existing["consent_tier"], 2
                ):
                    existing["consent_tier"] = node["consent_tier"]
                # Merge attributes
                merged_attrs = dict(existing.get("attributes", {}))
                merged_attrs.update(node.get("attributes", {}))
                existing["attributes"] = merged_attrs

        for node in seen.values():
            await self.backend.add_entity(
                graph_id=graph_id,
                name=node["name"],
                entity_type=node["entity_type"],
                summary=node.get("summary", ""),
                attributes=node.get("attributes", {}),
                consent_tier=node.get("consent_tier", "private"),
            )

        for edge in parsed.edges:
            await self.backend.add_edge(
                graph_id=graph_id,
                source=edge["source"],
                target=edge["target"],
                edge_type=edge["edge_type"],
                fact=edge.get("fact", ""),
                attributes=edge.get("attributes", {}),
                consent_tier=edge.get("consent_tier", "private"),
            )

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def _run_analytics_async(self, graph_id: str) -> Dict[str, Any]:
        """
        Async variant of :meth:`_run_analytics` — usable from the build worker
        which already runs inside an event loop.
        """
        nodes = await self.backend.get_nodes(graph_id)
        edges = await self.backend.get_edges(graph_id)

        node_ids = [n.uuid or n.name for n in nodes]
        edge_tuples = [(e.source_node_uuid, e.target_node_uuid) for e in edges]

        ranks = _pagerank(node_ids, edge_tuples)
        communities = _louvain(node_ids, edge_tuples)

        logger.info(
            f"Analytics for {graph_id}: pagerank computed for {len(ranks)} nodes, "
            f"{len(set(communities.values()))} communities detected"
        )
        return {"pagerank": ranks, "communities": communities}

    def _run_analytics(self, graph_id: str) -> Dict[str, Any]:
        """
        Run PageRank + Louvain on the current graph synchronously.

        Wraps :meth:`_run_analytics_async` with ``asyncio.run`` for callers
        that are not themselves inside an event loop.
        """
        import asyncio
        return asyncio.run(self._run_analytics_async(graph_id))

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def delete_graph(self, graph_id: str) -> None:
        """Delete a graph (sync wrapper around the async backend method)."""
        import asyncio
        asyncio.run(self.backend.delete_graph(graph_id))
        logger.info(f"Deleted MD-Chat graph: {graph_id}")
