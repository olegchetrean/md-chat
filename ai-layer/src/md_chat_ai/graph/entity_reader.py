# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Derived from Cronberry (Mega Promoting SRL).
"""
Entity reader and filter service for the MD-Chat knowledge graph.

Reads nodes from the Neo4j backend, filters them to the MD-Chat ontology
entity types, and enriches each entity with its related edges and neighbouring
nodes. Supports consent-tier filtering at every query level.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar

from ..config import CONFIG
from .neo4j_backend import Neo4jGraphBackend
from .ontology import CONSENT_TIERS, normalise_consent_tier

logger = logging.getLogger("md_chat_ai.graph.entity_reader")

T = TypeVar("T")

#: Canonical MD-Chat entity types (mirrors MDCHAT_ONTOLOGY in ontology.py).
MDCHAT_ENTITY_TYPES: Set[str] = {
    "User",
    "Contact",
    "Channel",
    "MiniApp",
    "Bot",
    "Twin",
    "Company",
    "Group",
    "Location",
    "Topic",
    # Generic fallbacks (also canonical)
    "Person",
    "Organization",
}

#: System labels that do NOT represent an MD-Chat entity type.
_SYSTEM_LABELS: Set[str] = {"Entity", "Node"}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class EntityNode:
    """
    A single entity node extracted from the MD-Chat knowledge graph.

    Attributes:
        uuid: Stable entity ID from the backend.
        name: Node name (canonical, also the merge key).
        labels: All labels assigned by the backend (system + ontology types).
        summary: Free-text summary of the entity.
        attributes: Ontology-defined attribute dict.
        consent_tier: Privacy tier (``public``/``friends``/``private``).
        related_edges: Edges where this node is source or target.
        related_nodes: Neighbouring nodes reachable through related_edges.
    """

    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    consent_tier: str = "private"
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
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

    def get_entity_type(self) -> Optional[str]:
        """Return the first non-system label, i.e. the MD-Chat entity type."""
        for label in self.labels:
            if label not in _SYSTEM_LABELS:
                return label
        return None


@dataclass
class FilteredEntities:
    """
    Collection of entities filtered by MD-Chat ontology type.

    Attributes:
        entities: Matching :class:`EntityNode` objects.
        entity_types: Set of distinct entity types found.
        total_count: Total nodes inspected (before filtering).
        filtered_count: Number of nodes that passed the filter.
    """

    entities: List[EntityNode]
    entity_types: Set[str]
    total_count: int
    filtered_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_types": sorted(self.entity_types),
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
        }


# ---------------------------------------------------------------------------
# Reader service
# ---------------------------------------------------------------------------


class MdChatEntityReader:
    """
    Reads, filters and enriches entity nodes from an MD-Chat knowledge graph.

    Operations:
      1. Retrieve all graph nodes (paginated by the backend).
      2. Filter to nodes whose labels include a known MD-Chat entity type
         and whose ``consent_tier`` is in the caller's allowlist.
      3. Optionally enrich each entity with its outgoing/incoming edges and
         the basic info of connected nodes.
    """

    def __init__(
        self,
        backend: Optional[Neo4jGraphBackend] = None,
    ) -> None:
        """
        Args:
            backend: Pre-configured :class:`Neo4jGraphBackend`. If ``None``,
                a new one is built from :data:`CONFIG`.
        """
        self.backend = backend or Neo4jGraphBackend(
            uri=CONFIG.neo4j_uri,
            user=CONFIG.neo4j_user,
            password=CONFIG.neo4j_password,
        )

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------

    def _call_with_retry(
        self,
        func: Callable[[], T],
        operation_name: str,
        max_retries: int = 3,
        initial_delay: float = 2.0,
    ) -> T:
        """
        Call *func* (a zero-argument callable) with exponential back-off.

        Args:
            func: Zero-argument callable that wraps the backend call.
            operation_name: Label for log messages.
            max_retries: Total attempts before raising.
            initial_delay: Seconds before first retry; doubles on each attempt.

        Returns:
            Return value of *func* on success.

        Raises:
            The last exception if all attempts fail.
        """
        last_exc: Optional[Exception] = None
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    logger.warning(
                        f"{operation_name} attempt {attempt + 1} failed "
                        f"({str(exc)[:80]}), retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error(
                        f"{operation_name} failed after {max_retries} attempts: {exc}"
                    )
        assert last_exc is not None
        raise last_exc

    # ------------------------------------------------------------------
    # Low-level accessors
    # ------------------------------------------------------------------

    def _allowed_tiers(self, requested: Optional[List[str]]) -> List[str]:
        """Validate & normalise a list of consent tiers."""
        if not requested:
            return list(CONSENT_TIERS)
        cleaned = [
            normalise_consent_tier(t, default="private")
            for t in requested
        ]
        # Deduplicate, keep order
        seen: List[str] = []
        for t in cleaned:
            if t not in seen:
                seen.append(t)
        return seen

    def get_all_nodes(
        self,
        graph_id: str,
        consent_tiers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return all nodes from the graph as plain dicts.

        Args:
            graph_id: Target graph ID.
            consent_tiers: Optional consent-tier allowlist.

        Returns:
            List of node dicts with keys: uuid, name, labels, summary,
            attributes, consent_tier.
        """
        logger.info(f"Fetching all nodes for graph {graph_id}...")
        tiers = self._allowed_tiers(consent_tiers)
        raw_nodes = asyncio.run(
            self.backend.get_nodes(graph_id, consent_tiers=tiers)
        )

        result: List[Dict[str, Any]] = []
        for node in raw_nodes:
            result.append({
                "uuid": node.uuid,
                "name": node.name,
                "labels": node.labels,
                "summary": node.summary,
                "attributes": node.attributes,
                "consent_tier": node.consent_tier,
            })
        logger.info(f"Retrieved {len(result)} nodes from graph {graph_id}")
        return result

    def get_all_edges(
        self,
        graph_id: str,
        consent_tiers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return all edges from the graph as plain dicts.

        Args:
            graph_id: Target graph ID.
            consent_tiers: Optional consent-tier allowlist.

        Returns:
            List of edge dicts with keys: uuid, name, fact,
            source_node_uuid, target_node_uuid, attributes, consent_tier.
        """
        logger.info(f"Fetching all edges for graph {graph_id}...")
        tiers = self._allowed_tiers(consent_tiers)
        raw_edges = asyncio.run(
            self.backend.get_edges(graph_id, consent_tiers=tiers)
        )

        result: List[Dict[str, Any]] = []
        for edge in raw_edges:
            result.append({
                "uuid": edge.uuid,
                "name": edge.name,
                "fact": edge.fact,
                "source_node_uuid": edge.source_node_uuid,
                "target_node_uuid": edge.target_node_uuid,
                "attributes": edge.attributes,
                "consent_tier": edge.consent_tier,
            })
        logger.info(f"Retrieved {len(result)} edges from graph {graph_id}")
        return result

    # ------------------------------------------------------------------
    # Filtering & enrichment
    # ------------------------------------------------------------------

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True,
        consent_tiers: Optional[List[str]] = None,
    ) -> FilteredEntities:
        """
        Filter graph nodes to those matching the MD-Chat ontology.

        Args:
            graph_id: Target graph ID.
            defined_entity_types: Optional allowlist of entity type names.
                If ``None``, all non-system-label nodes pass.
            enrich_with_edges: Whether to populate ``related_edges`` and
                ``related_nodes`` for each returned entity.
            consent_tiers: Optional consent-tier allowlist applied at the
                backend level.

        Returns:
            :class:`FilteredEntities` containing matched :class:`EntityNode`.
        """
        logger.info(f"Filtering entities in graph {graph_id}...")

        tiers = self._allowed_tiers(consent_tiers)
        all_nodes = self.get_all_nodes(graph_id, consent_tiers=tiers)
        total_count = len(all_nodes)

        all_edges = (
            self.get_all_edges(graph_id, consent_tiers=tiers)
            if enrich_with_edges
            else []
        )
        node_map: Dict[str, Dict[str, Any]] = {n["uuid"]: n for n in all_nodes}

        filtered: List[EntityNode] = []
        types_found: Set[str] = set()

        for node in all_nodes:
            labels: List[str] = node.get("labels", [])
            custom_labels = [lb for lb in labels if lb not in _SYSTEM_LABELS]

            if not custom_labels:
                continue

            if defined_entity_types:
                matching = [lb for lb in custom_labels if lb in defined_entity_types]
                if not matching:
                    continue
                entity_type = matching[0]
            else:
                entity_type = custom_labels[0]

            types_found.add(entity_type)

            entity = EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=labels,
                summary=node["summary"],
                attributes=node["attributes"],
                consent_tier=node.get("consent_tier", "private"),
            )

            if enrich_with_edges:
                outgoing: List[Dict[str, Any]] = []
                incoming: List[Dict[str, Any]] = []
                neighbour_uuids: Set[str] = set()

                for edge in all_edges:
                    if edge["source_node_uuid"] == node["uuid"]:
                        outgoing.append({
                            "direction": "outgoing",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "consent_tier": edge.get("consent_tier", "private"),
                            "target_node_uuid": edge["target_node_uuid"],
                        })
                        neighbour_uuids.add(edge["target_node_uuid"])
                    elif edge["target_node_uuid"] == node["uuid"]:
                        incoming.append({
                            "direction": "incoming",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "consent_tier": edge.get("consent_tier", "private"),
                            "source_node_uuid": edge["source_node_uuid"],
                        })
                        neighbour_uuids.add(edge["source_node_uuid"])

                entity.related_edges = outgoing + incoming
                entity.related_nodes = [
                    {
                        "uuid": node_map[uid]["uuid"],
                        "name": node_map[uid]["name"],
                        "labels": node_map[uid]["labels"],
                        "summary": node_map[uid].get("summary", ""),
                        "consent_tier": node_map[uid].get("consent_tier", "private"),
                    }
                    for uid in neighbour_uuids
                    if uid in node_map
                ]

            filtered.append(entity)

        logger.info(
            f"Filter complete: {total_count} total nodes, "
            f"{len(filtered)} matched, types: {types_found}"
        )
        return FilteredEntities(
            entities=filtered,
            entity_types=types_found,
            total_count=total_count,
            filtered_count=len(filtered),
        )

    def get_entities_by_type(
        self,
        graph_id: str,
        entity_type: str,
        enrich_with_edges: bool = True,
        consent_tiers: Optional[List[str]] = None,
    ) -> List[EntityNode]:
        """
        Return all entities of a specific ontology type.

        Args:
            graph_id: Target graph ID.
            entity_type: Ontology type label (e.g. ``"User"``, ``"Contact"``).
            enrich_with_edges: Whether to populate edge/neighbour data.
            consent_tiers: Optional consent-tier allowlist.

        Returns:
            List of matching :class:`EntityNode`.
        """
        result = self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges,
            consent_tiers=consent_tiers,
        )
        return result.entities

    def get_entity_with_context(
        self,
        graph_id: str,
        entity_uuid: str,
        consent_tiers: Optional[List[str]] = None,
    ) -> Optional[EntityNode]:
        """
        Fetch a single entity node and its full relationship context.

        Args:
            graph_id: Target graph ID.
            entity_uuid: UUID of the target entity node.
            consent_tiers: Optional consent-tier allowlist.

        Returns:
            :class:`EntityNode` on success, ``None`` if the node is not found
            or filtered out by the consent allowlist.
        """
        tiers = self._allowed_tiers(consent_tiers)
        all_nodes = self.get_all_nodes(graph_id, consent_tiers=tiers)
        node_map = {n["uuid"]: n for n in all_nodes}
        node = node_map.get(entity_uuid)
        if not node:
            return None

        edges = self.get_all_edges(graph_id, consent_tiers=tiers)
        related_edges: List[Dict[str, Any]] = []
        neighbour_uuids: Set[str] = set()

        for edge in edges:
            if edge["source_node_uuid"] == entity_uuid:
                related_edges.append({
                    "direction": "outgoing",
                    "edge_name": edge["name"],
                    "fact": edge["fact"],
                    "consent_tier": edge.get("consent_tier", "private"),
                    "target_node_uuid": edge["target_node_uuid"],
                })
                neighbour_uuids.add(edge["target_node_uuid"])
            elif edge["target_node_uuid"] == entity_uuid:
                related_edges.append({
                    "direction": "incoming",
                    "edge_name": edge["name"],
                    "fact": edge["fact"],
                    "consent_tier": edge.get("consent_tier", "private"),
                    "source_node_uuid": edge["source_node_uuid"],
                })
                neighbour_uuids.add(edge["source_node_uuid"])

        related_nodes = [
            {
                "uuid": node_map[uid]["uuid"],
                "name": node_map[uid]["name"],
                "labels": node_map[uid]["labels"],
                "summary": node_map[uid].get("summary", ""),
                "consent_tier": node_map[uid].get("consent_tier", "private"),
            }
            for uid in neighbour_uuids
            if uid in node_map
        ]

        return EntityNode(
            uuid=node["uuid"],
            name=node["name"],
            labels=node["labels"],
            summary=node.get("summary", ""),
            attributes=node.get("attributes", {}),
            consent_tier=node.get("consent_tier", "private"),
            related_edges=related_edges,
            related_nodes=related_nodes,
        )
