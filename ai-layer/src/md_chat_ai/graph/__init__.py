# Licensed under the Apache License, Version 2.0 (the "License").
# Derived from Cronberry (Mega Promoting SRL).
"""MD-Chat knowledge graph package — Neo4j backend, ontology, builder, reader."""

from .builder import (
    GraphBuilderService,
    GraphInfo,
    ParsedEvent,
    SynapseEventAdapter,
)
from .entity_reader import (
    MDCHAT_ENTITY_TYPES,
    EntityNode as ReaderEntityNode,
    FilteredEntities,
    MdChatEntityReader,
)
from .neo4j_backend import (
    Edge,
    EntityNode,
    Neo4jGraphBackend,
    SearchResult,
)
from .ontology import (
    CONSENT_TIERS,
    MDCHAT_ONTOLOGY,
    OntologyGenerator,
    is_valid_consent_tier,
    normalise_consent_tier,
)

__all__ = [
    # Ontology
    "CONSENT_TIERS",
    "MDCHAT_ONTOLOGY",
    "OntologyGenerator",
    "is_valid_consent_tier",
    "normalise_consent_tier",
    # Backend
    "Neo4jGraphBackend",
    "EntityNode",
    "Edge",
    "SearchResult",
    # Builder
    "GraphBuilderService",
    "GraphInfo",
    "ParsedEvent",
    "SynapseEventAdapter",
    # Reader
    "MdChatEntityReader",
    "MDCHAT_ENTITY_TYPES",
    "FilteredEntities",
    "ReaderEntityNode",
]
