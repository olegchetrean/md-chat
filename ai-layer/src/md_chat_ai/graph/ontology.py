# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Derived from Cronberry (Mega Promoting SRL).
"""
Ontology generator for the MD-Chat knowledge graph.

Two modes of operation:
  1. **Pre-defined** (default): Uses MDCHAT_ONTOLOGY, a fixed schema modelling
     MD-Chat accounts, contacts, channels, miniapps, bots and AI twins.
     No LLM call required.
  2. **LLM-driven** (optional): Calls an LLM to produce a custom ontology
     from document text, useful for one-off analyses or custom projects.

Key differences vs. the upstream Cronberry ontology:
  - **User** and **Contact** are distinct entity types: ``User`` represents an
    MD-Chat account holder (a person that has logged into the platform),
    ``Contact`` represents anybody known to a user (which may or may not be an
    MD-Chat user themselves). They overlap when a contact happens to be on the
    platform — that is modelled with a directed ``RELATED`` edge.
  - New entity types: ``Channel`` (Telegram-style broadcast), ``MiniApp`` (an
    in-platform mini application), ``Bot`` (third-party automation), ``Twin``
    (the user's AI persona / digital twin).
  - New edge types: ``MEMBER_OF_CHANNEL``, ``OWNS_BUSINESS``, ``USED_MINIAPP``,
    ``OWNS_TWIN``. The legacy ``RELATED``, ``MENTIONED``, ``MEMBER_OF`` and
    ``PROMISED`` edges from Cronberry are preserved.
  - Each entity and edge carries an optional ``consent_tier`` field
    (``public`` / ``friends`` / ``private``) so that privacy-by-design filters
    can be applied at query time. The knowledge graph is built ONLY from data
    the user explicitly consents to share — message *content* is excluded
    unless the user opts in.

Entity types (10):
  User, Contact, Channel, MiniApp, Bot, Twin, Company, Group, Location, Topic
  (with Person / Organization fallback support when running in LLM-driven mode).

Edge types (8):
  RELATED, MENTIONED, MEMBER_OF, MEMBER_OF_CHANNEL, OWNS_BUSINESS,
  USED_MINIAPP, OWNS_TWIN, PROMISED
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

#: Allowed values for the privacy-tier marker placed on every node/edge.
CONSENT_TIERS: tuple = ("public", "friends", "private")


# ---------------------------------------------------------------------------
# Pre-defined MD-Chat ontology
# ---------------------------------------------------------------------------

MDCHAT_ONTOLOGY: Dict[str, Any] = {
    "entity_types": [
        {
            "name": "User",
            "description": "An MD-Chat account holder — a person who signed up on the platform.",
            "attributes": [
                {"name": "handle", "type": "text", "description": "Public @handle"},
                {"name": "display_name", "type": "text", "description": "Display name"},
                {"name": "matrix_id", "type": "text", "description": "Synapse Matrix ID"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
            "examples": ["@oleg", "@lilia"],
        },
        {
            "name": "Contact",
            "description": "A person known to a user; may or may not be an MD-Chat User themselves.",
            "attributes": [
                {"name": "full_name", "type": "text", "description": "Full display name"},
                {"name": "phone", "type": "text", "description": "Phone number or handle"},
                {"name": "occupation", "type": "text", "description": "Job title or profession"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
            "examples": ["John Doe", "Maria Popescu"],
        },
        {
            "name": "Channel",
            "description": "A Telegram-style broadcast channel published on MD-Chat.",
            "attributes": [
                {"name": "channel_title", "type": "text", "description": "Channel display name"},
                {"name": "subscriber_count", "type": "text", "description": "Subscribers"},
                {"name": "language", "type": "text", "description": "Primary language"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
            "examples": ["MD-Chat Updates", "TechNews RO"],
        },
        {
            "name": "MiniApp",
            "description": "A mini-application embedded in MD-Chat (web-view or native).",
            "attributes": [
                {"name": "app_title", "type": "text", "description": "Mini app name"},
                {"name": "category", "type": "text", "description": "App category"},
                {"name": "publisher", "type": "text", "description": "Mini app publisher"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
            "examples": ["Wallet Mini", "Booking Mini"],
        },
        {
            "name": "Bot",
            "description": "A third-party automation bot interacting with users on MD-Chat.",
            "attributes": [
                {"name": "bot_name", "type": "text", "description": "Bot display name"},
                {"name": "purpose", "type": "text", "description": "What the bot does"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
            "examples": ["WeatherBot", "SupportBot"],
        },
        {
            "name": "Twin",
            "description": "A user's AI persona / digital twin trained on consented data.",
            "attributes": [
                {"name": "twin_name", "type": "text", "description": "Twin display name"},
                {"name": "model", "type": "text", "description": "Backing LLM model"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
            "examples": ["Oleg Twin", "Lilia Twin"],
        },
        {
            "name": "Company",
            "description": "A business or employer linked to users, contacts or channels.",
            "attributes": [
                {"name": "org_name", "type": "text", "description": "Legal or brand name"},
                {"name": "industry", "type": "text", "description": "Business sector"},
                {"name": "location", "type": "text", "description": "Primary city or country"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
            "examples": ["Mega Promoting SRL", "Acme Corp"],
        },
        {
            "name": "Group",
            "description": "A multi-user MD-Chat group conversation.",
            "attributes": [
                {"name": "group_title", "type": "text", "description": "Group chat name"},
                {"name": "member_count", "type": "text", "description": "Approximate members"},
                {"name": "topic_focus", "type": "text", "description": "Main discussion topic"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
            "examples": ["Sales Team", "Project X Chat"],
        },
        {
            "name": "Location",
            "description": "A geographic location relevant to users, contacts or events.",
            "attributes": [
                {"name": "place_name", "type": "text", "description": "City, region, or venue"},
                {"name": "country", "type": "text", "description": "Country code or name"},
                {"name": "timezone", "type": "text", "description": "IANA timezone string"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
            "examples": ["Chisinau", "Bucharest"],
        },
        {
            "name": "Topic",
            "description": "A discussion topic or theme recurring in user conversations.",
            "attributes": [
                {"name": "topic_label", "type": "text", "description": "Short topic label"},
                {"name": "sentiment", "type": "text", "description": "positive/neutral/negative"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
            "examples": ["Pricing concerns", "Technical questions"],
        },
    ],
    "edge_types": [
        {
            "name": "RELATED",
            "description": "Two entities (users/contacts) are related personally or professionally.",
            "source_targets": [
                {"source": "User", "target": "User"},
                {"source": "User", "target": "Contact"},
                {"source": "Contact", "target": "Contact"},
            ],
            "attributes": [
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
        },
        {
            "name": "MENTIONED",
            "description": "An entity was mentioned in a conversation, topic or post.",
            "source_targets": [
                {"source": "User", "target": "Contact"},
                {"source": "User", "target": "Topic"},
                {"source": "User", "target": "MiniApp"},
                {"source": "Contact", "target": "Topic"},
            ],
            "attributes": [
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
        },
        {
            "name": "MEMBER_OF",
            "description": "A user or contact is a member of a group conversation.",
            "source_targets": [
                {"source": "User", "target": "Group"},
                {"source": "Contact", "target": "Group"},
            ],
            "attributes": [
                {"name": "joined_at", "type": "text", "description": "Join timestamp"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
        },
        {
            "name": "MEMBER_OF_CHANNEL",
            "description": "A user or contact subscribed to a broadcast Channel.",
            "source_targets": [
                {"source": "User", "target": "Channel"},
                {"source": "Contact", "target": "Channel"},
            ],
            "attributes": [
                {"name": "subscribed_at", "type": "text", "description": "When they joined"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
        },
        {
            "name": "OWNS_BUSINESS",
            "description": "A user is the legal owner or operator of a Company.",
            "source_targets": [
                {"source": "User", "target": "Company"},
                {"source": "Contact", "target": "Company"},
            ],
            "attributes": [
                {"name": "role", "type": "text", "description": "CEO, founder, partner"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
        },
        {
            "name": "USED_MINIAPP",
            "description": "A user opened or interacted with a MiniApp.",
            "source_targets": [
                {"source": "User", "target": "MiniApp"},
            ],
            "attributes": [
                {"name": "last_used_at", "type": "text", "description": "Last usage timestamp"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
        },
        {
            "name": "OWNS_TWIN",
            "description": "A user owns / controls an AI Twin persona.",
            "source_targets": [
                {"source": "User", "target": "Twin"},
            ],
            "attributes": [
                {"name": "created_at_iso", "type": "text", "description": "Creation timestamp"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
        },
        {
            "name": "PROMISED",
            "description": "A user or contact made a commitment / follow-up promise.",
            "source_targets": [
                {"source": "User", "target": "Contact"},
                {"source": "Contact", "target": "User"},
                {"source": "User", "target": "User"},
            ],
            "attributes": [
                {"name": "promise_date", "type": "text", "description": "When it was promised"},
                {"name": "due_date", "type": "text", "description": "Expected fulfilment"},
                {"name": "consent_tier", "type": "text", "description": "public/friends/private"},
            ],
        },
    ],
    "analysis_summary": (
        "Pre-defined MD-Chat ontology — 10 entity types (User, Contact, Channel, "
        "MiniApp, Bot, Twin, Company, Group, Location, Topic) and 8 edge types "
        "(RELATED, MENTIONED, MEMBER_OF, MEMBER_OF_CHANNEL, OWNS_BUSINESS, "
        "USED_MINIAPP, OWNS_TWIN, PROMISED). Each node and edge carries a "
        "consent_tier marker (public/friends/private) for privacy-by-design."
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_valid_consent_tier(tier: Optional[str]) -> bool:
    """Return True if *tier* is one of ``public``, ``friends`` or ``private``."""
    return tier in CONSENT_TIERS


def normalise_consent_tier(tier: Optional[str], default: str = "private") -> str:
    """
    Return a valid consent tier or *default* if the input is missing/invalid.

    Defaults to ``private`` — the most restrictive choice — so that data
    missing an explicit tier is never accidentally over-shared.
    """
    if is_valid_consent_tier(tier):
        return tier  # type: ignore[return-value]
    return default


# ---------------------------------------------------------------------------
# LLM system prompt (used in llm_driven mode)
# ---------------------------------------------------------------------------

_LLM_SYSTEM_PROMPT = """You are an expert knowledge-graph ontology designer. Analyze the provided \
text and design entity and relationship types for an **MD-Chat sovereign messenger** intelligence graph.

**Output valid JSON only. No markdown, no text outside the JSON object.**

## Required Output Schema

```json
{
    "entity_types": [
        {
            "name": "PascalCase",
            "description": "Max 100 chars",
            "attributes": [
                {"name": "snake_case_attr", "type": "text", "description": "..."}
            ],
            "examples": ["Example1"]
        }
    ],
    "edge_types": [
        {
            "name": "UPPER_SNAKE_CASE",
            "description": "Max 100 chars",
            "source_targets": [{"source": "TypeA", "target": "TypeB"}],
            "attributes": []
        }
    ],
    "analysis_summary": "Brief summary"
}
```

## Design Rules
1. Exactly 10 entity types. The last 2 MUST be: Person (individual fallback), Organization (group fallback).
2. 6-10 edge types capturing realistic MD-Chat relationships.
3. 1-3 attributes per entity. NEVER use reserved names: name, uuid, group_id, created_at, summary.
4. All entity types must represent real-world actors, not abstract concepts.
5. Keep descriptions under 100 characters.
"""


# ---------------------------------------------------------------------------
# OntologyGenerator
# ---------------------------------------------------------------------------


class OntologyGenerator:
    """
    Returns an ontology definition suitable for ``GraphBuilderService.set_ontology()``.

    Usage:
      - :meth:`get_mdchat_ontology` returns the fixed MDCHAT_ONTOLOGY (no LLM call).
      - :meth:`generate` calls an LLM to derive a custom ontology from text.
    """

    MAX_TEXT_FOR_LLM: int = 50_000

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        """
        Args:
            llm_client: Optional LLM client. When ``None``, only
                :meth:`get_mdchat_ontology` is available.
        """
        self._llm_client = llm_client

    # ------------------------------------------------------------------
    # Pre-defined ontology
    # ------------------------------------------------------------------

    @staticmethod
    def get_mdchat_ontology() -> Dict[str, Any]:
        """
        Return the canonical MD-Chat ontology without calling an LLM.

        Returns:
            Deep copy of MDCHAT_ONTOLOGY dict.
        """
        return copy.deepcopy(MDCHAT_ONTOLOGY)

    # Backwards-compat alias for code that referenced the Cronberry name.
    @staticmethod
    def get_cronberry_ontology() -> Dict[str, Any]:
        """Deprecated alias for :meth:`get_mdchat_ontology`."""
        return OntologyGenerator.get_mdchat_ontology()

    # ------------------------------------------------------------------
    # LLM-driven ontology (custom projects)
    # ------------------------------------------------------------------

    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a custom ontology by analyzing document texts with an LLM.

        Args:
            document_texts: Source documents to analyze.
            simulation_requirement: High-level description of what the
                graph should model.
            additional_context: Optional extra instructions appended.
            system_prompt: Override the default LLM system prompt.

        Returns:
            Validated ontology dict with entity_types, edge_types,
            and analysis_summary.
        """
        if self._llm_client is None:
            raise RuntimeError(
                "OntologyGenerator: no LLM client configured for generate()"
            )

        user_message = self._build_user_message(
            document_texts, simulation_requirement, additional_context
        )
        messages = [
            {"role": "system", "content": system_prompt or _LLM_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        raw = self._llm_client.chat_json(
            messages=messages, temperature=0.3, max_tokens=4096
        )
        return self._validate_and_process(raw)

    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str],
    ) -> str:
        combined = "\n\n---\n\n".join(document_texts)
        original_len = len(combined)

        if len(combined) > self.MAX_TEXT_FOR_LLM:
            combined = combined[: self.MAX_TEXT_FOR_LLM]
            combined += (
                f"\n\n...(original {original_len} chars, "
                f"truncated to {self.MAX_TEXT_FOR_LLM} for LLM analysis)..."
            )

        msg = f"## Goal\n\n{simulation_requirement}\n\n## Document Content\n\n{combined}\n"

        if additional_context:
            msg += f"\n## Additional Instructions\n\n{additional_context}\n"

        msg += (
            "\nDesign entity and relationship types for this content.\n\n"
            "Rules:\n"
            "1. Exactly 10 entity types\n"
            "2. Last 2 must be: Person (individual fallback) and Organization (group fallback)\n"
            "3. First 8 are domain-specific\n"
            "4. All entities must be real-world actors, not abstract concepts\n"
            "5. Attribute names must not use: name, uuid, group_id, created_at, summary\n"
        )
        return msg

    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure the LLM response conforms to the expected schema."""
        result.setdefault("entity_types", [])
        result.setdefault("edge_types", [])
        result.setdefault("analysis_summary", "")

        MAX_ENTITY = 10
        MAX_EDGE = 10

        for entity in result["entity_types"]:
            entity.setdefault("attributes", [])
            entity.setdefault("examples", [])
            desc = entity.get("description", "")
            if len(desc) > 100:
                entity["description"] = desc[:97] + "..."

        for edge in result["edge_types"]:
            edge.setdefault("source_targets", [])
            edge.setdefault("attributes", [])
            desc = edge.get("description", "")
            if len(desc) > 100:
                edge["description"] = desc[:97] + "..."

        # Ensure Person / Organization fallback types exist at the end
        names = {e["name"] for e in result["entity_types"]}
        fallbacks: List[Dict[str, Any]] = []
        if "Person" not in names:
            fallbacks.append({
                "name": "Person",
                "description": "Any individual not fitting other specific person types.",
                "attributes": [
                    {"name": "full_name", "type": "text", "description": "Full name"},
                    {"name": "role", "type": "text", "description": "Role or occupation"},
                ],
                "examples": ["ordinary contact", "anonymous participant"],
            })
        if "Organization" not in names:
            fallbacks.append({
                "name": "Organization",
                "description": "Any organization not fitting other specific types.",
                "attributes": [
                    {"name": "org_name", "type": "text", "description": "Organization name"},
                    {"name": "org_type", "type": "text", "description": "Type of organization"},
                ],
                "examples": ["small business", "community group"],
            })

        if fallbacks:
            current = len(result["entity_types"])
            needed = len(fallbacks)
            if current + needed > MAX_ENTITY:
                trim = current + needed - MAX_ENTITY
                result["entity_types"] = result["entity_types"][:-trim]
            result["entity_types"].extend(fallbacks)

        result["entity_types"] = result["entity_types"][:MAX_ENTITY]
        result["edge_types"] = result["edge_types"][:MAX_EDGE]

        return result
