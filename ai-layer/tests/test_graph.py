# Licensed under the Apache License, Version 2.0 (the "License").
# Derived from Cronberry (Mega Promoting SRL).
"""
Tests for the MD-Chat knowledge graph package.

The Neo4j driver is fully mocked — no real database is touched. We exercise
the public surface of :mod:`md_chat_ai.graph` end to end: ontology shape,
adapter parsing, builder ingestion, and consent-tier propagation.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from md_chat_ai.graph import (
    CONSENT_TIERS,
    MDCHAT_ENTITY_TYPES,
    MDCHAT_ONTOLOGY,
    GraphBuilderService,
    MdChatEntityReader,
    Neo4jGraphBackend,
    OntologyGenerator,
    ParsedEvent,
    SynapseEventAdapter,
    is_valid_consent_tier,
    normalise_consent_tier,
)


# ---------------------------------------------------------------------------
# Driver mock fixtures
# ---------------------------------------------------------------------------


class _StubResult:
    """Mimics a neo4j ``Result`` iterable of dict-like records."""

    def __init__(self, records: List[Dict[str, Any]]):
        self._records = [
            _StubRecord(r) if not isinstance(r, _StubRecord) else r for r in records
        ]

    def __iter__(self):
        return iter(self._records)


class _StubRecord:
    """A dict-like neo4j record."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data.get(key)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self._data


class _StubSession:
    """Mimics ``neo4j.Session``; records every ``run`` call."""

    def __init__(self, driver: "_StubDriver"):
        self._driver = driver

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, cypher: str, params: Dict[str, Any] | None = None) -> _StubResult:
        self._driver.calls.append((cypher, params or {}))
        # Honour the next-result queue, fall back to []
        if self._driver.next_results:
            return _StubResult(self._driver.next_results.pop(0))
        return _StubResult([])


class _StubDriver:
    """In-memory replacement for ``neo4j.GraphDatabase.driver()``."""

    def __init__(self):
        self.calls: List[tuple] = []
        self.next_results: List[List[Dict[str, Any]]] = []
        self.closed = False

    def session(self, database: str = "neo4j") -> _StubSession:
        return _StubSession(self)

    def verify_connectivity(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def stub_driver() -> _StubDriver:
    return _StubDriver()


@pytest.fixture
def backend(stub_driver: _StubDriver) -> Neo4jGraphBackend:
    """A Neo4jGraphBackend wired to the stub driver with embeddings mocked."""
    bk = Neo4jGraphBackend(
        uri="bolt://stub:7687",
        user="neo4j",
        password="stub",
        driver=stub_driver,
    )
    # Bypass sentence-transformers entirely.
    bk._embed = MagicMock(return_value=[0.0] * 8)  # type: ignore[method-assign]
    bk._embed_batch = MagicMock(side_effect=lambda texts: [[0.0] * 8 for _ in texts])  # type: ignore[method-assign]
    return bk


# ---------------------------------------------------------------------------
# 1. Ontology tests
# ---------------------------------------------------------------------------


def test_ontology_has_mdchat_specific_types():
    """User, Channel, MiniApp, Bot, Twin must all be defined."""
    ontology = OntologyGenerator.get_mdchat_ontology()
    names = {e["name"] for e in ontology["entity_types"]}
    for required in ("User", "Contact", "Channel", "MiniApp", "Bot", "Twin"):
        assert required in names, f"missing required entity type {required}"
    # Cronberry's deprecated alias should also work
    legacy = OntologyGenerator.get_cronberry_ontology()
    assert legacy == ontology


def test_ontology_edge_types_include_new_relationships():
    """MEMBER_OF_CHANNEL, OWNS_BUSINESS, USED_MINIAPP, OWNS_TWIN must exist."""
    ontology = MDCHAT_ONTOLOGY
    edge_names = {e["name"] for e in ontology["edge_types"]}
    for required in (
        "RELATED",
        "MENTIONED",
        "MEMBER_OF",
        "PROMISED",
        "MEMBER_OF_CHANNEL",
        "OWNS_BUSINESS",
        "USED_MINIAPP",
        "OWNS_TWIN",
    ):
        assert required in edge_names, f"missing edge type {required}"


def test_consent_tier_helpers():
    """Validation and normalisation behave as documented."""
    assert set(CONSENT_TIERS) == {"public", "friends", "private"}
    for tier in CONSENT_TIERS:
        assert is_valid_consent_tier(tier)
    assert not is_valid_consent_tier("secret")
    # Unknown values fall back to the most restrictive default.
    assert normalise_consent_tier(None) == "private"
    assert normalise_consent_tier("public") == "public"
    assert normalise_consent_tier("bogus") == "private"
    assert normalise_consent_tier("bogus", default="friends") == "friends"


def test_mdchat_entity_types_set_matches_ontology():
    """The reader's allowlist must include every type from the ontology."""
    ontology_names = {e["name"] for e in MDCHAT_ONTOLOGY["entity_types"]}
    assert ontology_names.issubset(MDCHAT_ENTITY_TYPES)


# ---------------------------------------------------------------------------
# 2. Neo4j backend tests (driver mocked)
# ---------------------------------------------------------------------------


def test_backend_schema_setup_runs_expected_cyphers(stub_driver, backend):
    """Init should run the constraint + index Cyphers exactly once each."""
    # Index/constraint statements all start with CREATE
    create_calls = [c for c, _ in stub_driver.calls if c.startswith("CREATE")]
    assert len(create_calls) == len(Neo4jGraphBackend._SETUP_CYPHER)
    assert any("e.consent_tier" in c for c, _ in stub_driver.calls), \
        "consent_tier index must be created"


def test_add_entity_writes_consent_tier(stub_driver, backend):
    """add_entity must persist the consent_tier parameter."""
    stub_driver.next_results = [[{"eid": "abc123"}]]
    eid = asyncio.run(backend.add_entity(
        graph_id="g1",
        name="@oleg",
        entity_type="User",
        summary="MD-Chat founder",
        attributes={"handle": "oleg"},
        consent_tier="friends",
    ))
    assert eid == "abc123"

    # Find the add_entity call (the MERGE on Entity)
    merge_calls = [
        (c, p) for c, p in stub_driver.calls if "MERGE (e:Entity" in c
    ]
    assert merge_calls, "add_entity must issue a MERGE"
    _, params = merge_calls[-1]
    assert params["consent_tier"] == "friends"
    assert params["name"] == "@oleg"
    assert params["entity_type"] == "User"


def test_add_entity_invalid_tier_falls_back_to_private(stub_driver, backend):
    """An unknown consent_tier value must be coerced to 'private'."""
    stub_driver.next_results = [[{"eid": "xyz"}]]
    asyncio.run(backend.add_entity(
        graph_id="g1",
        name="Maria",
        entity_type="Contact",
        consent_tier="leaky",  # invalid
    ))
    _, params = [
        (c, p) for c, p in stub_driver.calls if "MERGE (e:Entity" in c
    ][-1]
    assert params["consent_tier"] == "private"


def test_add_edge_writes_consent_tier(stub_driver, backend):
    """add_edge must persist consent_tier on the relationship."""
    stub_driver.next_results = [[{"rid": "rel_42"}]]
    rid = asyncio.run(backend.add_edge(
        graph_id="g1",
        source="@oleg",
        target="@lilia",
        edge_type="RELATED",
        fact="co-founders",
        consent_tier="public",
    ))
    assert rid == "rel_42"
    edge_calls = [(c, p) for c, p in stub_driver.calls if "MERGE (src)-[r:EDGE" in c]
    assert edge_calls
    _, params = edge_calls[-1]
    assert params["tier"] == "public"
    assert params["edge_type"] == "RELATED"


def test_get_nodes_with_consent_tier_filters_query(stub_driver, backend):
    """Filtering by tier must add a WHERE clause and pass the tier list."""
    asyncio.run(backend.get_nodes("g1", consent_tiers=["public", "friends"]))
    filtered_calls = [
        (c, p) for c, p in stub_driver.calls
        if "MATCH (e:Entity {graph_id: $graph_id})" in c and "consent_tier" in c
    ]
    assert filtered_calls, "consent_tiers must trigger a filtered query"
    _, params = filtered_calls[-1]
    assert params["tiers"] == ["public", "friends"]


# ---------------------------------------------------------------------------
# 3. SynapseEventAdapter tests
# ---------------------------------------------------------------------------


def test_adapter_parses_room_member_join_event():
    """m.room.member → MEMBER_OF (or MEMBER_OF_CHANNEL for spaces)."""
    adapter = SynapseEventAdapter()
    event = {
        "type": "m.room.member",
        "sender": "@oleg:md-chat.eu",
        "state_key": "@oleg:md-chat.eu",
        "room_id": "!room123:md-chat.eu",
        "origin_server_ts": 1700000000000,
        "content": {
            "membership": "join",
            "displayname": "Oleg",
            "room_type": "m.room",
            "consent_tier": "friends",
        },
    }
    parsed = adapter.parse_event(event)
    assert isinstance(parsed, ParsedEvent)
    assert any(n["entity_type"] == "User" for n in parsed.nodes)
    assert any(n["entity_type"] == "Group" for n in parsed.nodes)
    assert any(e["edge_type"] == "MEMBER_OF" for e in parsed.edges)
    assert all(e["consent_tier"] == "friends" for e in parsed.edges)


def test_adapter_parses_channel_join_event():
    """A space/channel room → MEMBER_OF_CHANNEL edge with Channel node."""
    adapter = SynapseEventAdapter()
    event = {
        "type": "m.room.member",
        "sender": "@oleg:md-chat.eu",
        "state_key": "@oleg:md-chat.eu",
        "room_id": "!broadcast:md-chat.eu",
        "content": {
            "membership": "join",
            "room_type": "m.space",
            "consent_tier": "public",
        },
    }
    parsed = adapter.parse_event(event)
    assert any(n["entity_type"] == "Channel" for n in parsed.nodes)
    assert any(e["edge_type"] == "MEMBER_OF_CHANNEL" for e in parsed.edges)


def test_adapter_message_without_opt_in_strips_body():
    """Without opt_in_content the message body must NOT propagate."""
    adapter = SynapseEventAdapter()
    event = {
        "type": "m.room.message",
        "sender": "@oleg:md-chat.eu",
        "room_id": "!r:md-chat.eu",
        "content": {
            "body": "Secret plan details",
            "m.mentions": {"user_ids": ["@lilia:md-chat.eu"]},
            "consent_tier": "private",
        },
    }
    parsed = adapter.parse_event(event)
    mentions = [e for e in parsed.edges if e["edge_type"] == "MENTIONED"]
    assert mentions, "mentions must produce edges"
    assert mentions[0]["fact"] == "", \
        "without opt_in_content the fact body must be empty"


def test_adapter_message_with_opt_in_keeps_body():
    """opt_in_content=True permits message-content ingestion."""
    adapter = SynapseEventAdapter()
    event = {
        "type": "m.room.message",
        "sender": "@oleg:md-chat.eu",
        "room_id": "!r:md-chat.eu",
        "content": {
            "body": "Hi @lilia, ready for the meeting?",
            "m.mentions": {"user_ids": ["@lilia:md-chat.eu"]},
            "consent_tier": "friends",
            "opt_in_content": True,
        },
    }
    parsed = adapter.parse_event(event)
    mentions = [e for e in parsed.edges if e["edge_type"] == "MENTIONED"]
    assert mentions
    assert "Hi @lilia" in mentions[0]["fact"]


def test_adapter_supports_custom_md_chat_events():
    """OWNS_BUSINESS / USED_MINIAPP / OWNS_TWIN / PROMISED must be parsed."""
    adapter = SynapseEventAdapter()
    business = adapter.parse_event({
        "type": "md.chat.business_owned",
        "sender": "@oleg:md-chat.eu",
        "content": {"company": "MEGA Promoting SRL", "role": "CEO",
                    "consent_tier": "public"},
    })
    assert any(e["edge_type"] == "OWNS_BUSINESS" for e in business.edges)
    assert any(n["entity_type"] == "Company" for n in business.nodes)

    miniapp = adapter.parse_event({
        "type": "md.chat.miniapp_used",
        "sender": "@oleg:md-chat.eu",
        "content": {"miniapp": "Wallet", "category": "finance",
                    "consent_tier": "friends"},
    })
    assert any(e["edge_type"] == "USED_MINIAPP" for e in miniapp.edges)
    assert any(n["entity_type"] == "MiniApp" for n in miniapp.nodes)

    twin = adapter.parse_event({
        "type": "md.chat.twin_created",
        "sender": "@oleg:md-chat.eu",
        "content": {"twin": "Oleg Twin", "model": "claude-opus-4-7"},
    })
    assert any(e["edge_type"] == "OWNS_TWIN" for e in twin.edges)
    assert any(n["entity_type"] == "Twin" for n in twin.nodes)


def test_adapter_unknown_event_yields_empty_result():
    """Unknown event types must produce zero nodes and zero edges."""
    parsed = SynapseEventAdapter().parse_event({"type": "m.unknown.event"})
    assert parsed.nodes == []
    assert parsed.edges == []


# ---------------------------------------------------------------------------
# 4. Builder pipeline test (driver mocked)
# ---------------------------------------------------------------------------


def test_builder_ingests_synapse_events_end_to_end(stub_driver, backend):
    """build_graph_sync must call the backend with consent-aware writes."""
    # Pre-load the next_results for every Cypher call the backend will make.
    # Each add_entity returns one record with `eid`, each add_edge returns
    # `rid`, and the final stats query returns aggregates.
    stub_driver.next_results = (
        # create_graph MERGE
        [[{"gid": "test_graph"}]]
        # set_ontology SET (no records returned)
        + [[]]
        # add_entity x3 (deduped: @oleg User, !r room Group, Maria Contact)
        + [[{"eid": f"eid_{i}"}] for i in range(3)]
        # add_edge x2 (MEMBER_OF, RELATED)
        + [[{"rid": f"rid_{i}"}] for i in range(2)]
        # _run_analytics_async → get_nodes
        + [[]]
        # _run_analytics_async → get_edges
        + [[]]
        # get_graph_stats — node_cypher
        + [[{"etype": "User", "tier": "friends", "cnt": 1},
            {"etype": "Group", "tier": "friends", "cnt": 1},
            {"etype": "Contact", "tier": "public", "cnt": 1}]]
        # get_graph_stats — edge_cypher
        + [[{"cnt": 2}]]
    )

    builder = GraphBuilderService(backend=backend)
    events = [
        {
            "type": "m.room.member",
            "sender": "@oleg:md-chat.eu",
            "state_key": "@oleg:md-chat.eu",
            "room_id": "!r:md-chat.eu",
            "content": {"membership": "join", "consent_tier": "friends"},
        },
        {
            "type": "md.chat.contact_added",
            "sender": "@oleg:md-chat.eu",
            "content": {"contact": "Maria Popescu", "consent_tier": "public"},
        },
    ]
    ontology = OntologyGenerator.get_mdchat_ontology()
    info = builder.build_graph_sync(
        events=events,
        ontology=ontology,
        graph_name="Test Graph",
        graph_id="test_graph",
    )

    assert info.graph_id == "test_graph"
    # The stats came from the mocked node/edge cypher results.
    assert info.node_count == 3
    assert info.edge_count == 2
    assert "User" in info.entity_types
    # Verify the ontology JSON was passed to set_ontology
    ontology_calls = [
        p for c, p in stub_driver.calls if "g.ontology_json" in c
    ]
    assert ontology_calls
    persisted = json.loads(ontology_calls[-1]["ontology_json"])
    assert any(e["name"] == "MiniApp" for e in persisted["entity_types"])


# ---------------------------------------------------------------------------
# 5. Entity reader test (driver mocked)
# ---------------------------------------------------------------------------


def test_entity_reader_filters_to_mdchat_entity_types(stub_driver, backend):
    """filter_defined_entities must keep only known MD-Chat types."""
    # First call: get_nodes
    stub_driver.next_results = [
        [
            {"e": _StubRecord({
                "entity_id": "n1",
                "name": "@oleg",
                "entity_type": "User",
                "summary": "founder",
                "attributes_json": "{}",
                "consent_tier": "public",
            })},
            {"e": _StubRecord({
                "entity_id": "n2",
                "name": "junk",
                "entity_type": "Entity",  # generic system label only
                "summary": "",
                "attributes_json": "{}",
                "consent_tier": "private",
            })},
        ],
        # second call: get_edges
        [],
    ]
    reader = MdChatEntityReader(backend=backend)
    result = reader.filter_defined_entities(
        graph_id="g1",
        defined_entity_types=["User"],
        enrich_with_edges=True,
        consent_tiers=["public", "friends"],
    )
    assert result.total_count == 2
    assert result.filtered_count == 1
    assert result.entities[0].name == "@oleg"
    assert result.entities[0].consent_tier == "public"
    assert "User" in result.entity_types
