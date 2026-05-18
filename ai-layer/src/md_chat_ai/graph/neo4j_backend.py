# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Derived from Cronberry (Mega Promoting SRL).
"""
Neo4j self-hosted graph backend for md-chat-ai.

Drop-in alternative to a cloud knowledge-graph service. Uses the official
``neo4j`` Python driver for all graph operations and (optionally)
``sentence-transformers`` for local embedding generation.

Privacy by design
-----------------
Every node and edge in the MD-Chat knowledge graph carries a ``consent_tier``
field (``public`` / ``friends`` / ``private``). The graph is built ONLY from
data the user explicitly consents to share. Message *content* is NOT ingested
unless the user opts in — by default we only persist relationship metadata.

Dependencies:
    pip install neo4j sentence-transformers numpy

Configuration is read from :data:`md_chat_ai.config.CONFIG`:
  - ``neo4j_uri``      — bolt://neo4j:7687
  - ``neo4j_user``     — neo4j
  - ``neo4j_password`` — set in environment

Schema (created automatically on first use):
  Nodes:
    (:Graph  {graph_id, name, description, created_at})
    (:Entity {graph_id, entity_id, name, entity_type, summary,
              attributes_json, embedding_json, consent_tier,
              created_at, updated_at})

  Edges:
    [:EDGE   {graph_id, edge_id, source_id, target_id, edge_type,
              fact, attributes_json, consent_tier, created_at}]
    [:IN_GRAPH] — (:Entity)-[:IN_GRAPH]->(:Graph)

  Indexes:
    entity_id (unique)
    graph_id on Entity
    consent_tier on Entity
"""

from __future__ import annotations

import json
import logging
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import UTC
from typing import Any

from ..config import CONFIG
from .ontology import CONSENT_TIERS, normalise_consent_tier

logger = logging.getLogger("md_chat_ai.graph.neo4j_backend")


# ---------------------------------------------------------------------------
# Shared data structures
# ---------------------------------------------------------------------------


@dataclass
class EntityNode:
    """
    Entity node as returned by :class:`Neo4jGraphBackend`.

    Attributes:
        uuid: Stable entity ID.
        name: Display name (used as merge key inside a graph).
        labels: All Neo4j labels (system + ontology types).
        summary: Free-text summary of the entity.
        attributes: Ontology-defined attribute dict.
        consent_tier: Privacy tier (``public``/``friends``/``private``).
        related_edges: Edges incident on this node (populated by the reader).
        related_nodes: Neighbour nodes reachable via related_edges.
    """

    uuid: str
    name: str
    labels: list[str]
    summary: str
    attributes: dict[str, Any]
    consent_tier: str = "private"
    related_edges: list[dict[str, Any]] = field(default_factory=list)
    related_nodes: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "consent_tier": self.consent_tier,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
        }

    def get_entity_type(self) -> str | None:
        """Return the first non-system label, i.e. the MD-Chat entity type."""
        system = {"Entity", "Node"}
        for label in self.labels:
            if label not in system:
                return label
        return None


@dataclass
class Edge:
    """Edge as returned by :class:`Neo4jGraphBackend`."""

    uuid: str
    name: str
    fact: str
    source_node_uuid: str
    target_node_uuid: str
    attributes: dict[str, Any]
    consent_tier: str = "private"
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "fact": self.fact,
            "source_node_uuid": self.source_node_uuid,
            "target_node_uuid": self.target_node_uuid,
            "attributes": self.attributes,
            "consent_tier": self.consent_tier,
            "created_at": self.created_at,
        }


@dataclass
class SearchResult:
    """Search result returned by :meth:`Neo4jGraphBackend.search`."""

    uuid: str
    name: str
    entity_type: str
    summary: str
    score: float
    attributes: dict[str, Any]
    consent_tier: str = "private"
    matched_edges: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "entity_type": self.entity_type,
            "summary": self.summary,
            "score": self.score,
            "attributes": self.attributes,
            "consent_tier": self.consent_tier,
            "matched_edges": self.matched_edges,
        }


# ---------------------------------------------------------------------------
# Lazy imports — only load heavy libs when actually needed
# ---------------------------------------------------------------------------


def _get_driver(uri: str, user: str, password: str):
    """Return a ``neo4j.GraphDatabase.driver()`` instance."""
    try:
        from neo4j import GraphDatabase  # type: ignore
    except ImportError as exc:  # pragma: no cover - import guard
        raise ImportError("neo4j package not found. Install it: pip install neo4j") from exc
    return GraphDatabase.driver(uri, auth=(user, password))


def _get_embedding_model(model_name: str):
    """Return a ``SentenceTransformer`` model, loaded once per process."""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError as exc:  # pragma: no cover - import guard
        raise ImportError(
            "sentence-transformers package not found. " "Install it: pip install sentence-transformers"
        ) from exc
    return SentenceTransformer(model_name)


# ---------------------------------------------------------------------------
# Main backend class
# ---------------------------------------------------------------------------


class Neo4jGraphBackend:
    """
    Self-hosted MD-Chat knowledge-graph backend backed by Neo4j.

    Provides the storage layer used by :class:`GraphBuilderService` and
    :class:`MdChatEntityReader`. The interface is intentionally a small,
    backend-agnostic subset of Cypher.

    Thread safety: the driver uses a connection pool internally. It is safe
    to share a single instance across threads.
    """

    # Cypher to create constraints and indexes on first use
    _SETUP_CYPHER = [
        "CREATE CONSTRAINT mdchat_entity_id IF NOT EXISTS " "FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
        "CREATE CONSTRAINT mdchat_graph_id IF NOT EXISTS " "FOR (g:Graph) REQUIRE g.graph_id IS UNIQUE",
        "CREATE INDEX mdchat_entity_graph IF NOT EXISTS " "FOR (e:Entity) ON (e.graph_id)",
        "CREATE INDEX mdchat_entity_consent IF NOT EXISTS " "FOR (e:Entity) ON (e.consent_tier)",
        "CREATE INDEX mdchat_edge_graph IF NOT EXISTS " "FOR ()-[r:EDGE]-() ON (r.graph_id)",
    ]

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        database: str = "neo4j",
        driver: Any | None = None,
    ) -> None:
        """
        Initialise the backend and verify connectivity.

        Args:
            uri: Neo4j bolt URI. Defaults to ``CONFIG.neo4j_uri``.
            user: Neo4j username. Defaults to ``CONFIG.neo4j_user``.
            password: Neo4j password. Defaults to ``CONFIG.neo4j_password``.
            embedding_model: sentence-transformers model name.
            database: Neo4j database name (default: ``"neo4j"``).
            driver: Optional pre-built driver — primarily for testing where
                we want to inject a mock without opening a real connection.
        """
        self.uri = uri or CONFIG.neo4j_uri
        self.user = user or CONFIG.neo4j_user
        self.password = password if password is not None else CONFIG.neo4j_password
        self.database = database
        self.embedding_model_name = embedding_model

        if driver is not None:
            self._driver = driver
        else:
            self._driver = _get_driver(self.uri, self.user, self.password)
            try:
                self._driver.verify_connectivity()
            except Exception as exc:  # pragma: no cover - depends on live DB
                logger.warning(f"Neo4j verify_connectivity failed: {exc}")

        self._embed_model = None  # lazy

        self._setup_schema()
        logger.info(
            f"Neo4jGraphBackend initialised: uri={self.uri}, db={database}, " f"embedding_model={embedding_model}"
        )

    # ------------------------------------------------------------------
    # Schema setup
    # ------------------------------------------------------------------

    def _setup_schema(self) -> None:
        """Create indexes and constraints (idempotent)."""
        with self._driver.session(database=self.database) as session:
            for cypher in self._SETUP_CYPHER:
                try:
                    session.run(cypher)
                except Exception as exc:
                    logger.debug(f"Schema setup skipped ({cypher[:60]}...): {exc}")
        logger.debug("Neo4j schema setup complete")

    # ------------------------------------------------------------------
    # Embedding helpers
    # ------------------------------------------------------------------

    def _get_embed_model(self):
        if self._embed_model is None:
            self._embed_model = _get_embedding_model(self.embedding_model_name)
        return self._embed_model

    def _embed(self, text: str) -> list[float]:
        """Embed a single string, returning a list of floats."""
        model = self._get_embed_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of strings in one batch call."""
        model = self._get_embed_model()
        vectors = model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [v.tolist() for v in vectors]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Pure-Python cosine similarity (numpy fast-path if available)."""
        try:
            import numpy as np  # type: ignore

            return float(np.dot(a, b))
        except ImportError:
            return sum(x * y for x, y in zip(a, b, strict=True))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime

        return datetime.now(UTC).isoformat()

    @staticmethod
    def _new_id() -> str:
        return _uuid.uuid4().hex

    def _run(self, cypher: str, params: dict[str, Any] | None = None) -> list[Any]:
        """Execute a Cypher query and return all records."""
        with self._driver.session(database=self.database) as session:
            result = session.run(cypher, params or {})
            return list(result)

    @staticmethod
    def _decode_attrs(attrs_json: str | None) -> dict[str, Any]:
        if not attrs_json:
            return {}
        try:
            return json.loads(attrs_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _encode_attrs(attrs: dict[str, Any]) -> str:
        return json.dumps(attrs or {}, ensure_ascii=False)

    @staticmethod
    def _resolve_tier(consent_tier: str | None) -> str:
        """Normalise a tier value, falling back to the most restrictive default."""
        return normalise_consent_tier(consent_tier, default="private")

    # ------------------------------------------------------------------
    # Graph CRUD
    # ------------------------------------------------------------------

    async def create_graph(
        self,
        graph_id: str,
        name: str,
        description: str = "",
    ) -> str:
        """
        Create or merge a Graph node.

        Args:
            graph_id: Unique graph identifier (md-chat-prefixed by convention).
            name: Human-readable graph name.
            description: Optional description.

        Returns:
            The ``graph_id`` passed in.
        """
        cypher = """
        MERGE (g:Graph {graph_id: $graph_id})
        ON CREATE SET
            g.name        = $name,
            g.description = $description,
            g.created_at  = $created_at
        RETURN g.graph_id AS gid
        """
        self._run(
            cypher,
            {
                "graph_id": graph_id,
                "name": name,
                "description": description,
                "created_at": self._now_iso(),
            },
        )
        logger.info(f"Neo4j: created graph {graph_id!r} ({name!r})")
        return graph_id

    async def set_ontology(
        self,
        graph_id: str,
        entity_types: list[dict[str, Any]],
        edge_types: list[dict[str, Any]],
    ) -> None:
        """
        Persist ontology metadata on the Graph node as JSON.

        Args:
            graph_id: Target graph.
            entity_types: Entity type dicts.
            edge_types: Edge type dicts.
        """
        ontology = {"entity_types": entity_types, "edge_types": edge_types}
        cypher = """
        MATCH (g:Graph {graph_id: $graph_id})
        SET g.ontology_json = $ontology_json
        """
        self._run(
            cypher,
            {
                "graph_id": graph_id,
                "ontology_json": json.dumps(ontology),
            },
        )
        logger.info(
            f"Neo4j: ontology set for graph {graph_id}: "
            f"{len(entity_types)} entity types, {len(edge_types)} edge types"
        )

    async def get_nodes(
        self,
        graph_id: str,
        limit: int = 1000,
        consent_tiers: list[str] | None = None,
    ) -> list[EntityNode]:
        """
        Return all Entity nodes in the graph, optionally filtered by consent tier.

        Args:
            graph_id: Target graph.
            limit: Maximum nodes to return.
            consent_tiers: If provided, only return nodes whose
                ``consent_tier`` is in this list.

        Returns:
            List of :class:`EntityNode`.
        """
        if consent_tiers:
            cypher = """
            MATCH (e:Entity {graph_id: $graph_id})
            WHERE e.consent_tier IN $tiers
            RETURN e
            ORDER BY e.created_at
            LIMIT $limit
            """
            params: dict[str, Any] = {
                "graph_id": graph_id,
                "tiers": consent_tiers,
                "limit": limit,
            }
        else:
            cypher = """
            MATCH (e:Entity {graph_id: $graph_id})
            RETURN e
            ORDER BY e.created_at
            LIMIT $limit
            """
            params = {"graph_id": graph_id, "limit": limit}

        records = self._run(cypher, params)
        nodes: list[EntityNode] = []
        for rec in records:
            e = rec["e"]
            entity_type = e.get("entity_type", "Entity") if hasattr(e, "get") else "Entity"
            nodes.append(
                EntityNode(
                    uuid=e.get("entity_id", "") if hasattr(e, "get") else "",
                    name=e.get("name", "") if hasattr(e, "get") else "",
                    labels=["Entity", entity_type] if entity_type != "Entity" else ["Entity"],
                    summary=e.get("summary", "") if hasattr(e, "get") else "",
                    attributes=self._decode_attrs(e.get("attributes_json") if hasattr(e, "get") else None),
                    consent_tier=self._resolve_tier(e.get("consent_tier") if hasattr(e, "get") else None),
                )
            )
        return nodes

    async def get_edges(
        self,
        graph_id: str,
        limit: int = 1000,
        consent_tiers: list[str] | None = None,
    ) -> list[Edge]:
        """
        Return all edges in the graph, optionally filtered by consent tier.

        Args:
            graph_id: Target graph.
            limit: Maximum edges to return.
            consent_tiers: If provided, only return edges whose
                ``consent_tier`` is in this list.

        Returns:
            List of :class:`Edge`.
        """
        if consent_tiers:
            cypher = """
            MATCH (src:Entity {graph_id: $graph_id})-[r:EDGE]->(tgt:Entity)
            WHERE r.graph_id = $graph_id AND r.consent_tier IN $tiers
            RETURN r, src.entity_id AS src_id, tgt.entity_id AS tgt_id
            ORDER BY r.created_at
            LIMIT $limit
            """
            params: dict[str, Any] = {
                "graph_id": graph_id,
                "tiers": consent_tiers,
                "limit": limit,
            }
        else:
            cypher = """
            MATCH (src:Entity {graph_id: $graph_id})-[r:EDGE]->(tgt:Entity)
            WHERE r.graph_id = $graph_id
            RETURN r, src.entity_id AS src_id, tgt.entity_id AS tgt_id
            ORDER BY r.created_at
            LIMIT $limit
            """
            params = {"graph_id": graph_id, "limit": limit}

        records = self._run(cypher, params)
        edges: list[Edge] = []
        for rec in records:
            r = rec["r"]
            edges.append(
                Edge(
                    uuid=r.get("edge_id", "") if hasattr(r, "get") else "",
                    name=r.get("edge_type", "") if hasattr(r, "get") else "",
                    fact=r.get("fact", "") if hasattr(r, "get") else "",
                    source_node_uuid=rec["src_id"],
                    target_node_uuid=rec["tgt_id"],
                    attributes=self._decode_attrs(r.get("attributes_json") if hasattr(r, "get") else None),
                    consent_tier=self._resolve_tier(r.get("consent_tier") if hasattr(r, "get") else None),
                    created_at=r.get("created_at", "") if hasattr(r, "get") else "",
                )
            )
        return edges

    async def search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
        consent_tiers: list[str] | None = None,
    ) -> list[SearchResult]:
        """
        Search entities by semantic similarity + keyword fallback.

        Args:
            graph_id: Target graph.
            query: Natural-language search query.
            limit: Maximum results to return.
            consent_tiers: Optional consent-tier allowlist.

        Returns:
            Ranked list of :class:`SearchResult`.
        """
        query_vec = self._embed(query)
        query_lower = query.lower()

        if consent_tiers:
            cypher = """
            MATCH (e:Entity {graph_id: $graph_id})
            WHERE e.embedding_json IS NOT NULL AND e.consent_tier IN $tiers
            RETURN e.entity_id AS eid,
                   e.name AS name,
                   e.entity_type AS etype,
                   e.summary AS summary,
                   e.attributes_json AS attrs_json,
                   e.embedding_json AS emb_json,
                   e.consent_tier AS tier
            """
            params: dict[str, Any] = {"graph_id": graph_id, "tiers": consent_tiers}
        else:
            cypher = """
            MATCH (e:Entity {graph_id: $graph_id})
            WHERE e.embedding_json IS NOT NULL
            RETURN e.entity_id AS eid,
                   e.name AS name,
                   e.entity_type AS etype,
                   e.summary AS summary,
                   e.attributes_json AS attrs_json,
                   e.embedding_json AS emb_json,
                   e.consent_tier AS tier
            """
            params = {"graph_id": graph_id}

        records = self._run(cypher, params)

        scored: list[tuple] = []
        for rec in records:
            emb_json = rec["emb_json"]
            if not emb_json:
                continue
            try:
                emb = json.loads(emb_json)
            except (json.JSONDecodeError, TypeError):
                continue

            cosine = self._cosine_similarity(query_vec, emb)

            name_lower = (rec["name"] or "").lower()
            summary_lower = (rec["summary"] or "").lower()
            kw_boost = sum(0.05 for word in query_lower.split() if word in name_lower or word in summary_lower)
            score = cosine + kw_boost
            scored.append((score, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:limit]

        results: list[SearchResult] = []
        for score, rec in top:
            results.append(
                SearchResult(
                    uuid=rec["eid"],
                    name=rec["name"] or "",
                    entity_type=rec["etype"] or "Entity",
                    summary=rec["summary"] or "",
                    score=round(score, 6),
                    attributes=self._decode_attrs(rec["attrs_json"]),
                    consent_tier=self._resolve_tier(rec.get("tier") if hasattr(rec, "get") else None),
                )
            )
        return results

    async def delete_graph(self, graph_id: str) -> None:
        """Permanently delete a graph and all its entities + edges."""
        self._run(
            """
            MATCH (src:Entity {graph_id: $graph_id})-[r:EDGE]->()
            DELETE r
            """,
            {"graph_id": graph_id},
        )
        self._run(
            """
            MATCH (e:Entity {graph_id: $graph_id})
            DETACH DELETE e
            """,
            {"graph_id": graph_id},
        )
        self._run(
            """
            MATCH (g:Graph {graph_id: $graph_id})
            DELETE g
            """,
            {"graph_id": graph_id},
        )
        logger.info(f"Neo4j: deleted graph {graph_id!r}")

    # ------------------------------------------------------------------
    # Direct entity/edge manipulation
    # ------------------------------------------------------------------

    async def add_entity(
        self,
        graph_id: str,
        name: str,
        entity_type: str,
        summary: str = "",
        attributes: dict[str, Any] | None = None,
        consent_tier: str = "private",
    ) -> str:
        """
        Create or merge a named entity node.

        Uses MERGE on ``(graph_id, name, entity_type)`` so identical entities
        are deduplicated automatically.

        Args:
            graph_id: Target graph.
            name: Canonical entity name (merge key).
            entity_type: Ontology label (``User``, ``Contact``, …).
            summary: Optional free-text description.
            attributes: Dict of ontology-defined attributes.
            consent_tier: ``public`` / ``friends`` / ``private``. Defaults to
                the most restrictive value.

        Returns:
            ``entity_id`` of the created or existing node.
        """
        tier = self._resolve_tier(consent_tier)
        if tier not in CONSENT_TIERS:  # defensive — should be impossible
            tier = "private"

        embedding = self._embed(f"{name} {summary}")
        now = self._now_iso()
        entity_id = self._new_id()

        cypher = """
        MATCH (g:Graph {graph_id: $graph_id})
        MERGE (e:Entity {graph_id: $graph_id, name: $name, entity_type: $entity_type})
        ON CREATE SET
            e.entity_id       = $entity_id,
            e.summary         = $summary,
            e.attributes_json = $attrs_json,
            e.embedding_json  = $embedding_json,
            e.consent_tier    = $consent_tier,
            e.created_at      = $created_at,
            e.updated_at      = $created_at
        ON MATCH SET
            e.summary         = $summary,
            e.attributes_json = $attrs_json,
            e.embedding_json  = $embedding_json,
            e.consent_tier    = $consent_tier,
            e.updated_at      = $created_at
        MERGE (e)-[:IN_GRAPH]->(g)
        RETURN e.entity_id AS eid
        """
        records = self._run(
            cypher,
            {
                "graph_id": graph_id,
                "entity_id": entity_id,
                "name": name,
                "entity_type": entity_type,
                "summary": summary,
                "attrs_json": self._encode_attrs(attributes or {}),
                "embedding_json": json.dumps(embedding),
                "consent_tier": tier,
                "created_at": now,
            },
        )
        eid = records[0]["eid"] if records else entity_id
        logger.debug(f"Neo4j: add_entity name={name!r} type={entity_type} tier={tier} eid={eid}")
        return eid

    async def add_edge(
        self,
        graph_id: str,
        source: str,
        target: str,
        edge_type: str,
        fact: str = "",
        attributes: dict[str, Any] | None = None,
        consent_tier: str = "private",
    ) -> str:
        """
        Create a directed edge between two named entities.

        Args:
            graph_id: Target graph.
            source: Name of the source entity.
            target: Name of the target entity.
            edge_type: Ontology relationship label (``RELATED``, …).
            fact: Free-text fact sentence.
            attributes: Optional relationship attributes.
            consent_tier: Privacy tier for this edge.

        Returns:
            ``edge_id`` of the created relationship.
        """
        tier = self._resolve_tier(consent_tier)
        edge_id = self._new_id()
        now = self._now_iso()

        cypher = """
        MATCH (g:Graph {graph_id: $graph_id})
        MERGE (src:Entity {graph_id: $graph_id, name: $source})
        ON CREATE SET src.entity_id = $src_id,
                      src.entity_type = 'Entity',
                      src.created_at = $now,
                      src.updated_at = $now,
                      src.summary = '',
                      src.attributes_json = '{}',
                      src.consent_tier = $tier
        MERGE (tgt:Entity {graph_id: $graph_id, name: $target})
        ON CREATE SET tgt.entity_id = $tgt_id,
                      tgt.entity_type = 'Entity',
                      tgt.created_at = $now,
                      tgt.updated_at = $now,
                      tgt.summary = '',
                      tgt.attributes_json = '{}',
                      tgt.consent_tier = $tier
        MERGE (src)-[r:EDGE {graph_id: $graph_id,
                             source_name: $source,
                             target_name: $target,
                             edge_type: $edge_type}]->(tgt)
        ON CREATE SET r.edge_id         = $edge_id,
                      r.fact            = $fact,
                      r.attributes_json = $attrs_json,
                      r.consent_tier    = $tier,
                      r.created_at      = $now
        ON MATCH  SET r.fact            = $fact,
                      r.attributes_json = $attrs_json,
                      r.consent_tier    = $tier
        MERGE (src)-[:IN_GRAPH]->(g)
        MERGE (tgt)-[:IN_GRAPH]->(g)
        RETURN r.edge_id AS rid
        """
        records = self._run(
            cypher,
            {
                "graph_id": graph_id,
                "source": source,
                "target": target,
                "src_id": self._new_id(),
                "tgt_id": self._new_id(),
                "edge_type": edge_type,
                "edge_id": edge_id,
                "fact": fact,
                "attrs_json": self._encode_attrs(attributes or {}),
                "tier": tier,
                "now": now,
            },
        )
        rid = records[0]["rid"] if records else edge_id
        logger.debug(f"Neo4j: add_edge {source!r} -[{edge_type}]-> {target!r} tier={tier} rid={rid}")
        return rid

    async def update_entity(
        self,
        graph_id: str,
        entity_id: str,
        updates: dict[str, Any],
    ) -> bool:
        """
        Update properties of an existing entity node.

        Args:
            graph_id: Target graph.
            entity_id: ``entity_id`` of the node to update.
            updates: Dict of property names → new values. Recognised keys:
                ``name``, ``entity_type``, ``summary``, ``attributes``,
                ``consent_tier``.

        Returns:
            True if the entity was found and updated, False otherwise.
        """
        fetch_cypher = """
        MATCH (e:Entity {graph_id: $graph_id, entity_id: $entity_id})
        RETURN e.name AS name, e.summary AS summary,
               e.entity_type AS etype, e.attributes_json AS attrs_json,
               e.consent_tier AS tier
        """
        rows = self._run(fetch_cypher, {"graph_id": graph_id, "entity_id": entity_id})
        if not rows:
            logger.warning(f"Neo4j: update_entity not found: {entity_id}")
            return False

        current = rows[0]
        new_name = updates.get("name", current["name"])
        new_summary = updates.get("summary", current["summary"] or "")
        new_etype = updates.get("entity_type", current["etype"] or "Entity")
        new_attrs = updates.get("attributes", self._decode_attrs(current["attrs_json"]))
        new_tier = self._resolve_tier(updates.get("consent_tier", current["tier"]))

        embedding = self._embed(f"{new_name} {new_summary}")
        now = self._now_iso()

        update_cypher = """
        MATCH (e:Entity {graph_id: $graph_id, entity_id: $entity_id})
        SET e.name            = $name,
            e.entity_type     = $etype,
            e.summary         = $summary,
            e.attributes_json = $attrs_json,
            e.embedding_json  = $embedding_json,
            e.consent_tier    = $consent_tier,
            e.updated_at      = $updated_at
        RETURN e.entity_id AS eid
        """
        result = self._run(
            update_cypher,
            {
                "graph_id": graph_id,
                "entity_id": entity_id,
                "name": new_name,
                "etype": new_etype,
                "summary": new_summary,
                "attrs_json": self._encode_attrs(new_attrs),
                "embedding_json": json.dumps(embedding),
                "consent_tier": new_tier,
                "updated_at": now,
            },
        )
        ok = bool(result)
        if ok:
            logger.debug(f"Neo4j: updated entity {entity_id}")
        return ok

    async def delete_entity(self, graph_id: str, entity_id: str) -> bool:
        """Delete an entity node and all its incident edges."""
        cypher = """
        MATCH (e:Entity {graph_id: $graph_id, entity_id: $entity_id})
        DETACH DELETE e
        RETURN count(e) AS deleted
        """
        records = self._run(cypher, {"graph_id": graph_id, "entity_id": entity_id})
        deleted = records[0]["deleted"] if records else 0
        if deleted:
            logger.debug(f"Neo4j: deleted entity {entity_id}")
        return bool(deleted)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the Neo4j driver connection pool."""
        self._driver.close()
        logger.info("Neo4j driver closed")

    def get_graph_stats(self, graph_id: str) -> dict[str, Any]:
        """
        Return basic statistics for a graph.

        Returns:
            Dict with ``node_count``, ``edge_count``, ``entity_types`` and
            ``consent_breakdown`` (counts by tier).
        """
        node_cypher = """
        MATCH (e:Entity {graph_id: $graph_id})
        RETURN e.entity_type AS etype,
               e.consent_tier AS tier,
               count(e) AS cnt
        """
        edge_cypher = """
        MATCH (:Entity {graph_id: $graph_id})-[r:EDGE {graph_id: $graph_id}]->()
        RETURN count(r) AS cnt
        """
        node_rows = self._run(node_cypher, {"graph_id": graph_id})
        edge_rows = self._run(edge_cypher, {"graph_id": graph_id})

        entity_types: dict[str, int] = {}
        consent_breakdown: dict[str, int] = {t: 0 for t in CONSENT_TIERS}
        total_nodes = 0
        for row in node_rows:
            etype = row["etype"] or "Entity"
            tier = self._resolve_tier(row["tier"])
            cnt = row["cnt"] or 0
            entity_types[etype] = entity_types.get(etype, 0) + cnt
            consent_breakdown[tier] = consent_breakdown.get(tier, 0) + cnt
            total_nodes += cnt

        total_edges = (edge_rows[0]["cnt"] if edge_rows else 0) or 0

        return {
            "graph_id": graph_id,
            "node_count": total_nodes,
            "edge_count": total_edges,
            "entity_types": entity_types,
            "consent_breakdown": consent_breakdown,
        }

    def __repr__(self) -> str:
        return f"Neo4jGraphBackend(uri={self.uri!r}, db={self.database!r}, " f"embedding={self.embedding_model_name!r})"
