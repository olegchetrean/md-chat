# Copyright 2026 Mega Promoting SRL
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Derived from Cronberry (Mega Promoting SRL).
"""
Self-twin agent profile generator for MD-Chat.

Converts the USER'S OWN messages (outgoing-only) into a rich agent profile
suitable for building a self-twin — i.e. an AI clone of the account owner,
NOT a clone of someone-else's contact. The user supplies a list of their
own past outgoing messages (and optional metadata); the LLM analyses voice,
tone, decision patterns, communication style.

Key adaptation from Cronberry (contact-twin):
    - Input is `own_messages` (your own outgoing texts), not `messages` with
      mixed direction.
    - No `ai_sentiment`/`ai_urgency`/`relevance_score` — those are CRM signals
      about a third party. The self-twin reads its own writing.
    - Profession/age/interests can be self-declared.
    - Output is `AgentProfile` representing the user, with optional
      `VerifiedAttestation` (eIDAS-backed authenticity claim) attached.
"""

from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..config import CONFIG  # noqa: F401  (kept for future config-driven defaults)
from ..llm.client import LLMClient

logger = logging.getLogger("md_chat_ai.agents.profile")


# ======================================================================
# Data models
# ======================================================================


@dataclass
class CommunicationStyle:
    """Detailed communication style traits derived from message analysis."""

    formality: str = "neutral"          # very_formal / formal / neutral / casual / very_casual
    directness: str = "balanced"        # very_direct / direct / balanced / indirect / very_indirect
    emotionality: str = "balanced"      # stoic / reserved / balanced / expressive / very_expressive
    response_speed: str = "normal"      # instant / quick / normal / slow / unpredictable
    typical_length: str = "medium"      # short / medium / long / variable
    emoji_usage: str = "moderate"       # none / sparse / moderate / heavy
    preferred_channel: str = "text"     # text / voice / mixed
    language_style: str = "standard"    # slang / standard / formal / technical / mixed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "formality": self.formality,
            "directness": self.directness,
            "emotionality": self.emotionality,
            "response_speed": self.response_speed,
            "typical_length": self.typical_length,
            "emoji_usage": self.emoji_usage,
            "preferred_channel": self.preferred_channel,
            "language_style": self.language_style,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CommunicationStyle":
        return cls(
            formality=d.get("formality", "neutral"),
            directness=d.get("directness", "balanced"),
            emotionality=d.get("emotionality", "balanced"),
            response_speed=d.get("response_speed", "normal"),
            typical_length=d.get("typical_length", "medium"),
            emoji_usage=d.get("emoji_usage", "moderate"),
            preferred_channel=d.get("preferred_channel", "text"),
            language_style=d.get("language_style", "standard"),
        )


@dataclass
class ResponsePattern:
    """Recurring patterns in how the user responds."""

    trigger: str
    pattern: str
    frequency: str = "sometimes"        # always / often / sometimes / rarely
    emotional_valence: str = "neutral"  # positive / neutral / negative

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger": self.trigger,
            "pattern": self.pattern,
            "frequency": self.frequency,
            "emotional_valence": self.emotional_valence,
        }


@dataclass
class DecisionFactor:
    """A factor that influences how the user makes decisions."""

    factor: str
    weight: float = 0.5
    direction: str = "positive"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor": self.factor,
            "weight": self.weight,
            "direction": self.direction,
            "notes": self.notes,
        }


@dataclass
class InfluenceEdge:
    """Represents an influence relationship with another contact or entity."""

    target_name: str
    influence_type: str
    strength: float = 0.5
    bidirectional: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_name": self.target_name,
            "influence_type": self.influence_type,
            "strength": self.strength,
            "bidirectional": self.bidirectional,
            "notes": self.notes,
        }


@dataclass
class VerifiedAttestation:
    """
    eIDAS-backed authenticity attestation for a self-twin.

    Used to mark a twin as "Verified Authentic Twin" — i.e. cryptographically
    proven to be the AI clone the owner authorised. Full attestation logic
    (qualified signature, signer DID, issuance/revocation) lives in Sprint 6;
    this is just the data carrier.
    """

    issuer: str = ""                     # eIDAS QTSP or self-attested
    subject_did: str = ""                # DID of the user the twin belongs to
    signature_alg: str = "EdDSA"
    signature: str = ""                  # base64 of the attestation signature
    issued_at: Optional[str] = None
    expires_at: Optional[str] = None
    revoked: bool = False
    revocation_reason: str = ""

    def is_valid(self) -> bool:
        """Lightweight validity check (no crypto here — Sprint 6 adds that)."""
        if self.revoked:
            return False
        if not self.signature or not self.subject_did:
            return False
        if self.expires_at:
            try:
                exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
                if exp < datetime.now(exp.tzinfo):
                    return False
            except (ValueError, AttributeError):
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issuer": self.issuer,
            "subject_did": self.subject_did,
            "signature_alg": self.signature_alg,
            "signature": self.signature,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "revoked": self.revoked,
            "revocation_reason": self.revocation_reason,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VerifiedAttestation":
        return cls(
            issuer=d.get("issuer", ""),
            subject_did=d.get("subject_did", ""),
            signature_alg=d.get("signature_alg", "EdDSA"),
            signature=d.get("signature", ""),
            issued_at=d.get("issued_at"),
            expires_at=d.get("expires_at"),
            revoked=d.get("revoked", False),
            revocation_reason=d.get("revocation_reason", ""),
        )


@dataclass
class AgentProfile:
    """
    Self-twin agent profile for MD-Chat.

    Represents the USER themselves — their voice, decision style, and habits —
    so the digital twin can speak/write in-character when the user is offline,
    in business 24/7 mode, or on vacation.
    """

    agent_id: int
    username: str
    display_name: str
    bio: str
    persona: str  # Long-form personality description (200-400 words)

    # Big Five personality traits (0.0 to 1.0)
    personality: Dict[str, float] = field(default_factory=lambda: {
        "openness": 0.5,
        "conscientiousness": 0.5,
        "extraversion": 0.5,
        "agreeableness": 0.5,
        "neuroticism": 0.5,
    })

    # Communication style
    communication_style: CommunicationStyle = field(default_factory=CommunicationStyle)

    # Observed response patterns
    response_patterns: List[ResponsePattern] = field(default_factory=list)

    # Decision-making factors
    decision_factors: List[DecisionFactor] = field(default_factory=list)

    # Social influence map (people the user trusts / follows / opposes)
    influence_map: List[InfluenceEdge] = field(default_factory=list)

    # Demographics (self-declared)
    age: Optional[int] = None
    gender: Optional[str] = None
    profession: Optional[str] = None
    interests: List[str] = field(default_factory=list)
    language: str = "ro"

    # Behavioral metrics derived from actual data
    message_count: int = 0
    avg_message_length: int = 0           # chars
    response_rate: float = 1.0            # fraction of messages that got reply
    topics_distribution: Dict[str, float] = field(default_factory=dict)
    sentiment_trend: str = "stable"
    peak_activity_hours: List[int] = field(default_factory=list)

    # Data quality
    data_confidence: float = 0.5
    last_data_update: str = field(default_factory=lambda: datetime.now().isoformat())

    # Telegram-specific
    is_premium: bool = False
    activity_level: float = 0.5

    # Source reference (the user's own account)
    source_user_id: Optional[str] = None

    # eIDAS-backed authenticity attestation (Sprint 6 will populate it)
    attestation: Optional[VerifiedAttestation] = None

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_verified(self) -> bool:
        """True iff a valid Verified Authentic Twin attestation is attached."""
        return self.attestation is not None and self.attestation.is_valid()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent_id": self.agent_id,
            "username": self.username,
            "display_name": self.display_name,
            "bio": self.bio,
            "persona": self.persona,
            "personality": self.personality,
            "communication_style": self.communication_style.to_dict(),
            "response_patterns": [rp.to_dict() for rp in self.response_patterns],
            "decision_factors": [df.to_dict() for df in self.decision_factors],
            "influence_map": [ie.to_dict() for ie in self.influence_map],
            "age": self.age,
            "gender": self.gender,
            "profession": self.profession,
            "interests": self.interests,
            "language": self.language,
            "message_count": self.message_count,
            "avg_message_length": self.avg_message_length,
            "response_rate": self.response_rate,
            "topics_distribution": self.topics_distribution,
            "sentiment_trend": self.sentiment_trend,
            "peak_activity_hours": self.peak_activity_hours,
            "data_confidence": self.data_confidence,
            "last_data_update": self.last_data_update,
            "is_premium": self.is_premium,
            "activity_level": self.activity_level,
            "source_user_id": self.source_user_id,
            "attestation": self.attestation.to_dict() if self.attestation else None,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AgentProfile":
        """Deserialize from dictionary."""
        cs = CommunicationStyle.from_dict(d.get("communication_style", {}))
        rps = [ResponsePattern(**rp) for rp in d.get("response_patterns", [])]
        dfs = [DecisionFactor(**df) for df in d.get("decision_factors", [])]
        ims = [InfluenceEdge(**ie) for ie in d.get("influence_map", [])]
        att = (
            VerifiedAttestation.from_dict(d["attestation"])
            if d.get("attestation") else None
        )
        return cls(
            agent_id=d["agent_id"],
            username=d["username"],
            display_name=d["display_name"],
            bio=d["bio"],
            persona=d["persona"],
            personality=d.get("personality", {}),
            communication_style=cs,
            response_patterns=rps,
            decision_factors=dfs,
            influence_map=ims,
            age=d.get("age"),
            gender=d.get("gender"),
            profession=d.get("profession"),
            interests=d.get("interests", []),
            language=d.get("language", "ro"),
            message_count=d.get("message_count", 0),
            avg_message_length=d.get("avg_message_length", 0),
            response_rate=d.get("response_rate", 1.0),
            topics_distribution=d.get("topics_distribution", {}),
            sentiment_trend=d.get("sentiment_trend", "stable"),
            peak_activity_hours=d.get("peak_activity_hours", []),
            data_confidence=d.get("data_confidence", 0.5),
            last_data_update=d.get("last_data_update", ""),
            is_premium=d.get("is_premium", False),
            activity_level=d.get("activity_level", 0.5),
            source_user_id=d.get("source_user_id"),
            attestation=att,
            created_at=d.get("created_at", ""),
        )


# ======================================================================
# Profile Generator (self-twin mode)
# ======================================================================


class MdChatProfileGenerator:
    """
    Generates a SELF-TWIN AgentProfile from the user's own outgoing messages.

    Two modes:
      - LLM-enriched (default): calls the LLM to analyse the user's voice
        and produce a detailed, grounded persona of themselves.
      - Rule-based: uses self-declared metadata + message-length heuristics
        (faster, less accurate, used when no LLM key is configured).

    Expected `self_data` keys:
        user_id, display_name, username, bio, language,
        own_messages (list of strings — outgoing-only),
        self_declared_profession, interests, custom_notes
    """

    PERSONA_GENERATION_PROMPT = """You are building a SELF-TWIN persona for an MD-Chat user.
The user wants their digital twin to write in their own voice when they are away.
Analyse THEIR OWN past messages and extract a faithful self-persona.

== USER DATA ==
Display name: {name}
Self-declared profession: {profession}
Self-declared interests: {interests}
Custom notes (provided by the user): {custom_notes}

Sample messages WRITTEN BY THE USER (their own outgoing texts):
{message_samples}

== TASK ==
Return a JSON object with these exact keys:

{{
    "display_name": "Their display name",
    "bio": "A short bio for this person (max 160 chars)",
    "persona": "Detailed self-persona, 200-400 words. Cover: tone, decision style, recurring vocabulary, how they handle pressure, how they greet/close messages, known opinions. Ground every claim in the messages above.",
    "personality": {{
        "openness": <0.0-1.0>,
        "conscientiousness": <0.0-1.0>,
        "extraversion": <0.0-1.0>,
        "agreeableness": <0.0-1.0>,
        "neuroticism": <0.0-1.0>
    }},
    "communication_style": {{
        "formality": "<very_formal|formal|neutral|casual|very_casual>",
        "directness": "<very_direct|direct|balanced|indirect|very_indirect>",
        "emotionality": "<stoic|reserved|balanced|expressive|very_expressive>",
        "response_speed": "<instant|quick|normal|slow|unpredictable>",
        "typical_length": "<short|medium|long|variable>",
        "emoji_usage": "<none|sparse|moderate|heavy>",
        "preferred_channel": "<text|voice|mixed>",
        "language_style": "<slang|standard|formal|technical|mixed>"
    }},
    "response_patterns": [
        {{"trigger": "...", "pattern": "...", "frequency": "<always|often|sometimes|rarely>", "emotional_valence": "<positive|neutral|negative>"}}
    ],
    "decision_factors": [
        {{"factor": "...", "weight": <0.0-1.0>, "direction": "<positive|negative|neutral>", "notes": "..."}}
    ],
    "interests": ["topic1", "topic2"],
    "activity_level": <0.0-1.0>,
    "sentiment_trend": "<rising|falling|stable|volatile>"
}}

Include at least 3 response_patterns and 3 decision_factors.
"""

    BEHAVIORAL_METRICS_PROMPT = """Analyse these {n_messages} outgoing messages WRITTEN BY THE USER.

Messages:
{message_samples}

Return JSON:
{{
    "avg_message_length": <average character count>,
    "topics_distribution": {{"topic_label": <share_0_to_1>, ...}},
    "peak_activity_hours": [<list of 0-23 hour integers when they tend to write>],
    "sentiment_trend": "<rising|falling|stable|volatile>"
}}
"""

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self._llm_client = llm_client

    @property
    def llm(self) -> LLMClient:
        """Lazily initialize the LLM client on first use."""
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_from_self(
        self,
        agent_id: int,
        self_data: Dict[str, Any],
        use_llm: bool = True,
    ) -> AgentProfile:
        """
        Generate a self-twin AgentProfile from the user's own data.

        Args:
            agent_id: Numeric agent identifier.
            self_data: Dict with the user's own data (see class docstring).
            use_llm: Whether to call the LLM for enrichment.

        Returns:
            AgentProfile representing the user themselves.
        """
        confidence = self._compute_data_confidence(self_data)
        behavioral = self._compute_behavioral_metrics(self_data, use_llm=use_llm)

        if use_llm and confidence > 0.1:
            profile = self._generate_with_llm(agent_id, self_data, behavioral)
        else:
            profile = self._generate_rule_based(agent_id, self_data)

        own_msgs = self_data.get("own_messages", [])
        profile.message_count = len(own_msgs)
        profile.avg_message_length = behavioral.get("avg_message_length", 0)
        profile.response_rate = 1.0  # self-twin always "responds" to the user
        profile.topics_distribution = behavioral.get("topics_distribution", {})
        profile.sentiment_trend = behavioral.get("sentiment_trend", profile.sentiment_trend)
        profile.peak_activity_hours = behavioral.get("peak_activity_hours", [])
        profile.data_confidence = confidence

        return profile

    def generate_batch(
        self,
        users: List[Dict[str, Any]],
        use_llm: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[AgentProfile]:
        """Generate self-twin profiles for a batch of users."""
        profiles: List[AgentProfile] = []
        total = len(users)

        for i, self_data in enumerate(users):
            name = self_data.get(
                "display_name",
                self_data.get("username", f"user_{i}"),
            )
            if progress_callback:
                progress_callback(i, total, f"Generating self-twin: {name}")

            try:
                profile = self.generate_from_self(i, self_data, use_llm=use_llm)
                profiles.append(profile)
            except Exception as exc:
                logger.error("Self-twin generation failed for %s: %s", name, exc)
                profiles.append(self._generate_rule_based(i, self_data))

        if progress_callback:
            progress_callback(total, total, f"Generated {total} self-twins")

        return profiles

    # ------------------------------------------------------------------
    # Internal: LLM path
    # ------------------------------------------------------------------

    def _generate_with_llm(
        self,
        agent_id: int,
        self_data: Dict[str, Any],
        behavioral: Dict[str, Any],
    ) -> AgentProfile:
        """Call LLM to produce a rich self-persona from the user's own messages."""
        name = self_data.get(
            "display_name",
            self_data.get("username", f"user_{agent_id}"),
        )

        own_msgs = self_data.get("own_messages", [])
        msg_samples = self._format_message_samples(own_msgs, max_count=40)

        prompt = self.PERSONA_GENERATION_PROMPT.format(
            name=name,
            profession=self_data.get("self_declared_profession", "Not declared"),
            interests=", ".join(self_data.get("interests", [])) or "Not declared",
            custom_notes=self_data.get("custom_notes", "") or "None",
            message_samples=msg_samples or "No messages available",
        )

        try:
            result = self.llm.chat_json(
                [{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=3000,
            )
        except Exception as exc:
            logger.warning("LLM self-profile generation failed for %s: %s", name, exc)
            return self._generate_rule_based(agent_id, self_data)

        cs = CommunicationStyle.from_dict(result.get("communication_style", {}))
        rps = [
            ResponsePattern(**_safe_pattern(rp))
            for rp in result.get("response_patterns", [])
        ]
        dfs = [
            DecisionFactor(**_safe_decision_factor(df))
            for df in result.get("decision_factors", [])
        ]

        username = self_data.get("username") or _make_username(name)

        return AgentProfile(
            agent_id=agent_id,
            username=username,
            display_name=result.get("display_name", name),
            bio=result.get("bio", self_data.get("bio", ""))[:160],
            persona=result.get("persona", ""),
            personality=_parse_personality(result.get("personality", {})),
            communication_style=cs,
            response_patterns=rps,
            decision_factors=dfs,
            influence_map=[],  # influence map is private to user; not auto-generated
            age=self_data.get("age"),
            gender=self_data.get("gender"),
            profession=self_data.get("self_declared_profession"),
            interests=result.get("interests", self_data.get("interests", [])),
            language=self_data.get("language", "ro"),
            activity_level=float(result.get("activity_level", 0.5)),
            sentiment_trend=behavioral.get(
                "sentiment_trend",
                result.get("sentiment_trend", "stable"),
            ),
            source_user_id=self_data.get("user_id"),
        )

    # ------------------------------------------------------------------
    # Internal: rule-based path
    # ------------------------------------------------------------------

    def _generate_rule_based(
        self,
        agent_id: int,
        self_data: Dict[str, Any],
    ) -> AgentProfile:
        """Heuristic self-profile derivation from message length only."""
        name = self_data.get(
            "display_name",
            self_data.get("username", f"user_{agent_id}"),
        )
        own_msgs = self_data.get("own_messages", [])

        avg_len = int(sum(len(m) for m in own_msgs) / len(own_msgs)) if own_msgs else 0

        if avg_len > 200:
            typical_length = "long"
            verbosity = 0.7
        elif avg_len > 80:
            typical_length = "medium"
            verbosity = 0.5
        else:
            typical_length = "short"
            verbosity = 0.3

        cs = CommunicationStyle(
            typical_length=typical_length,
            formality="neutral",
            directness="balanced",
        )

        bio_text = self_data.get("bio", "") or f"MD-Chat user: {name}"

        return AgentProfile(
            agent_id=agent_id,
            username=self_data.get("username") or _make_username(name),
            display_name=name,
            bio=bio_text[:160],
            persona=f"MD-Chat user {name}. Writes mostly {typical_length} messages.",
            personality={
                "openness": round(random.uniform(0.4, 0.6), 2),
                "conscientiousness": round(random.uniform(0.4, 0.6), 2),
                "extraversion": round(verbosity, 2),
                "agreeableness": round(random.uniform(0.4, 0.6), 2),
                "neuroticism": round(random.uniform(0.3, 0.5), 2),
            },
            communication_style=cs,
            response_patterns=[],
            decision_factors=[
                DecisionFactor(
                    factor="self-declared interests",
                    weight=0.5,
                    direction="positive",
                ),
            ],
            influence_map=[],
            profession=self_data.get("self_declared_profession"),
            interests=self_data.get("interests", []),
            language=self_data.get("language", "ro"),
            activity_level=verbosity,
            source_user_id=self_data.get("user_id"),
        )

    # ------------------------------------------------------------------
    # Internal: behavioral metrics
    # ------------------------------------------------------------------

    def _compute_behavioral_metrics(
        self,
        self_data: Dict[str, Any],
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """Calculate behavioral metrics from the user's own outgoing messages."""
        own_msgs = self_data.get("own_messages", [])
        # Accept either list of strings OR list of {date, text} dicts.
        normalised: List[Dict[str, Any]] = []
        for m in own_msgs:
            if isinstance(m, str):
                normalised.append({"text": m, "date": ""})
            elif isinstance(m, dict):
                normalised.append({
                    "text": m.get("text", ""),
                    "date": m.get("date", ""),
                })

        if normalised:
            avg_len = int(sum(len(m["text"]) for m in normalised) / len(normalised))
        else:
            avg_len = 0

        peak_hours = self._extract_peak_hours(normalised)

        metrics: Dict[str, Any] = {
            "avg_message_length": avg_len,
            "peak_activity_hours": peak_hours,
            "sentiment_trend": "stable",
            "topics_distribution": {},
        }

        if use_llm and len(normalised) >= 5:
            try:
                msg_samples = self._format_message_samples(
                    [m["text"] for m in normalised], max_count=40,
                )
                prompt = self.BEHAVIORAL_METRICS_PROMPT.format(
                    n_messages=len(normalised),
                    message_samples=msg_samples,
                )
                result = self.llm.chat_json(
                    [{"role": "user", "content": prompt}],
                    temperature=0.2,
                )
                metrics["topics_distribution"] = result.get("topics_distribution", {})
                if result.get("sentiment_trend"):
                    metrics["sentiment_trend"] = result["sentiment_trend"]
                if result.get("peak_activity_hours"):
                    metrics["peak_activity_hours"] = result["peak_activity_hours"]
            except Exception as exc:
                logger.debug("LLM behavioral metrics failed: %s", exc)

        return metrics

    @staticmethod
    def _compute_data_confidence(self_data: Dict[str, Any]) -> float:
        """
        Compute a 0.0-1.0 confidence score based on data availability.

        Self-twin rules:
          - 0 own_messages → 0.1 base
          - Each 10 own_messages → +0.05 (max +0.4)
          - bio present → +0.1
          - self_declared_profession → +0.1
          - custom_notes present → +0.1
          - interests declared → +0.1
        """
        score = 0.1
        n_messages = len(self_data.get("own_messages", []))
        score += min(0.4, n_messages / 10 * 0.05)
        if self_data.get("bio"):
            score += 0.1
        if self_data.get("self_declared_profession"):
            score += 0.1
        if self_data.get("custom_notes"):
            score += 0.1
        if self_data.get("interests"):
            score += 0.1
        return round(min(1.0, score), 3)

    @staticmethod
    def _extract_peak_hours(messages: List[Dict[str, Any]]) -> List[int]:
        """Extract the top-3 most active hours from message timestamps."""
        hour_counts: Dict[int, int] = {}
        for msg in messages:
            date_str = msg.get("date", "")
            if not date_str:
                continue
            try:
                ts = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                h = ts.hour
                hour_counts[h] = hour_counts.get(h, 0) + 1
            except (ValueError, AttributeError):
                continue
        if not hour_counts:
            return []
        sorted_hours = sorted(hour_counts, key=lambda h: hour_counts[h], reverse=True)
        return sorted_hours[:3]

    @staticmethod
    def _format_message_samples(
        messages: List[Any],
        max_count: int = 30,
    ) -> str:
        """Format outgoing messages for inclusion in a prompt."""
        sample = messages[-max_count:] if len(messages) > max_count else messages
        lines: List[str] = []
        for m in sample:
            if isinstance(m, str):
                lines.append(f"- {m[:200]}")
            elif isinstance(m, dict):
                date = (m.get("date") or "?")[:10]
                text = m.get("text", "").replace("\n", " ")[:200]
                lines.append(f"[{date}] {text}")
        return "\n".join(lines)


# ======================================================================
# Backward-compat alias
# ======================================================================

ProfileGenerator = MdChatProfileGenerator


# ======================================================================
# Private helpers
# ======================================================================


def _make_username(name: str) -> str:
    """Convert a display name into a clean username-like slug."""
    slug = re.sub(r"[^a-z0-9_]", "", name.lower().replace(" ", "_"))
    return (slug or "user")[:32]


def _parse_personality(raw: Dict[str, Any]) -> Dict[str, float]:
    """Parse and clamp Big Five personality traits."""
    traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
    result: Dict[str, float] = {}
    for t in traits:
        try:
            result[t] = round(max(0.0, min(1.0, float(raw.get(t, 0.5)))), 3)
        except (TypeError, ValueError):
            result[t] = 0.5
    return result


def _safe_pattern(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Safely convert LLM output to ResponsePattern kwargs."""
    return {
        "trigger": str(raw.get("trigger", "general situation"))[:200],
        "pattern": str(raw.get("pattern", "responds normally"))[:300],
        "frequency": raw.get("frequency", "sometimes"),
        "emotional_valence": raw.get("emotional_valence", "neutral"),
    }


def _safe_decision_factor(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Safely convert LLM output to DecisionFactor kwargs."""
    try:
        weight = round(max(0.0, min(1.0, float(raw.get("weight", 0.5)))), 3)
    except (TypeError, ValueError):
        weight = 0.5
    return {
        "factor": str(raw.get("factor", "unknown factor"))[:200],
        "weight": weight,
        "direction": raw.get("direction", "neutral"),
        "notes": str(raw.get("notes", ""))[:300],
    }
