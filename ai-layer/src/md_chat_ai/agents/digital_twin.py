# Copyright 2026 Mega Promoting SRL
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Derived from Cronberry (Mega Promoting SRL).
"""
Digital Twin system for MD-Chat (self-twin mode).

Each DigitalTwin is an LLM-powered agent that models the USER themselves
(the account owner), NOT a third-party contact. The self-twin is useful for:
  - Replying on the user's behalf while they are offline (auto_reply)
  - Running a corporate agent 24/7 in the user's voice (business_24_7)
  - Sending a custom away message (vacation)
  - Free-chatting as the user (free_chat)
  - Predicting how the user would respond to a hypothetical message (predict_response)
  - Rehearsing negotiations from the user's own seat (negotiate)

Every reply ships with an AI Act Art 50 disclosure (RO / RU / EN) and is
recorded in the per-twin audit_log. The twin can be revoked at any time
(AI Act Art 22 consideration) — after revoke() further chats raise.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..config import CONFIG
from ..llm.client import LLMClient
from .memory import (
    Emotion,
    TwinMemory,
)
from .profile_generator import AgentProfile, VerifiedAttestation

logger = logging.getLogger("md_chat_ai.agents.twin")


# Allowed top-level interaction modes.
TwinMode = Literal[
    "free_chat",
    "predict_response",
    "negotiate",
    "auto_reply",
    "business_24_7",
    "vacation",
]

# Allowed disclosure languages (AI Act Art 50).
DisclosureLanguage = Literal["ro", "ru", "en"]


# ======================================================================
# Pydantic response models
# ======================================================================


class TwinDisclosure(BaseModel):
    """
    AI Act Article 50 disclosure attached to every twin reply.

    The text wording is loaded from ``CONFIG.ai_disclosure_*`` (overridable
    via env vars) and falls back to sensible defaults.
    """

    language: DisclosureLanguage = Field(
        default="ro",
        description="ISO 639-1 language code of the disclosure text",
    )
    text: str = Field(..., description="The disclosure text shown to the recipient")
    timestamp: datetime = Field(default_factory=datetime.now)

    @classmethod
    def for_language(cls, language: DisclosureLanguage) -> TwinDisclosure:
        """Build the canonical disclosure for the given language."""
        text_map: dict[str, str] = {
            "ro": CONFIG.ai_disclosure_ro,
            "ru": CONFIG.ai_disclosure_ru,
            "en": CONFIG.ai_disclosure_en,
        }
        return cls(language=language, text=text_map[language])


class TwinResponse(BaseModel):
    """Response from DigitalTwin.chat()."""

    text: str = Field(..., description="The twin's reply in character")
    emotion: str = Field("neutral", description="Detected emotional state during this response")
    intensity: float = Field(0.5, ge=0.0, le=1.0, description="Emotion intensity")
    mode: TwinMode = Field("free_chat", description="Interaction mode used")
    round_num: int = Field(0, description="Simulation round number")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    # AI Act Art 50 disclosure (always present)
    disclosure: TwinDisclosure = Field(
        ...,
        description="AI Act Art 50 disclosure shown alongside the reply",
    )

    # Verified Authentic Twin status (mirrored from the underlying AgentProfile)
    verified: bool = Field(
        default=False,
        description="True iff the twin carries a valid eIDAS attestation",
    )


class PredictionResult(BaseModel):
    """Result from DigitalTwin.predict_response()."""

    predicted_response: str = Field(..., description="How the user would actually reply")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")
    emotional_reaction: str = Field(..., description="Emotion this message would trigger")
    reasoning: str = Field(..., description="Why they would respond this way")
    suggested_approach: str = Field(..., description="Better phrasing for a positive outcome")
    risk_level: str = Field("medium", description="low / medium / high — risk of negative reaction")
    alternative_messages: list[str] = Field(
        default_factory=list,
        description="Two alternative phrasings to consider",
    )


class Concession(BaseModel):
    """A single concession made or received during negotiation."""

    party: str = Field(..., description="who / them")
    description: str
    value_estimate: float = Field(0.0, description="Estimated deal value impact, normalised 0-1")
    round_num: int = 0


class NegotiationResult(BaseModel):
    """Result from DigitalTwin.negotiate()."""

    objective: str = Field(..., description="Original negotiation objective")
    outcome: str = Field(..., description="reached_agreement / partial_agreement / stalemate / rejected")
    agreement_summary: str = Field("", description="What was agreed (if anything)")
    concessions_made: list[Concession] = Field(default_factory=list)
    concessions_received: list[Concession] = Field(default_factory=list)
    contact_position: str = Field("", description="The user's final stated position")
    recommended_next_step: str = Field("", description="What to do next")
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    rounds_taken: int = 0


class AccuracyStats(BaseModel):
    """Accuracy tracking for a DigitalTwin across interactions."""

    total_predictions: int = 0
    confirmed_correct: int = 0
    confirmed_incorrect: int = 0
    pending_confirmation: int = 0
    accuracy_rate: float = Field(0.0, ge=0.0, le=1.0)
    confidence_calibration: float = Field(
        0.0,
        description="Correlation between stated confidence and accuracy",
    )
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())


# ======================================================================
# Self profile data container
# ======================================================================


@dataclass
class SelfProfile:
    """
    Lightweight self-profile data container for DigitalTwin construction.

    This is the ContactProfile equivalent from Cronberry, adapted for
    self-twin mode: the fields describe the USER themselves, and the
    `own_messages` list holds the user's own outgoing texts.
    """

    user_id: str
    name: str
    username: str | None = None
    bio: str | None = None
    self_summary: str | None = None
    own_messages: list[str] = field(default_factory=list)
    language: str = "ro"
    custom_notes: str = ""
    interests: list[str] = field(default_factory=list)
    profession: str | None = None
    last_message_date: str | None = None

    # Optional pre-written vacation message used by the `vacation` mode.
    vacation_message: str | None = None


# ======================================================================
# Audit log entry
# ======================================================================


@dataclass
class AuditLogEntry:
    """A single entry in the per-twin audit log."""

    action: str
    mode: str
    user_message: str
    twin_reply: str
    disclosure_language: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    audit_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "action": self.action,
            "mode": self.mode,
            "user_message": self.user_message,
            "twin_reply": self.twin_reply,
            "disclosure_language": self.disclosure_language,
            "timestamp": self.timestamp,
        }


# ======================================================================
# Custom exceptions
# ======================================================================


class TwinRevokedError(RuntimeError):
    """Raised when an operation is attempted on a revoked twin."""


# ======================================================================
# Digital Twin
# ======================================================================


class DigitalTwin:
    """
    A self-twin: an LLM-powered digital twin of the MD-Chat account owner.

    The twin maintains a system prompt derived from the user's own data,
    combined memory (ShortTermMemory + LongTermMemory + EmotionalState),
    and supports six interaction modes:
      - free_chat:        open-ended conversation as the user
      - predict_response: structured prediction of how the user would reply
      - negotiate:        goal-directed negotiation simulation (user's seat)
      - auto_reply:       offline reply on the user's behalf
      - business_24_7:    corporate agent in the user's voice
      - vacation:         custom away message (uses ``profile.vacation_message``)

    Every reply ships with an AI Act Art 50 disclosure. The twin can be
    revoked via ``revoke()`` — subsequent chats raise ``TwinRevokedError``.
    All actions are appended to the in-memory ``audit_log`` queue.
    """

    DEFAULT_AUDIT_LOG_MAXLEN = 1000

    def __init__(
        self,
        profile: SelfProfile,
        agent_profile: AgentProfile | None = None,
        llm_client: LLMClient | None = None,
        memory_window: int = 20,
        ltm_compression_threshold: int = 10,
        default_disclosure_language: DisclosureLanguage = "ro",
        audit_log_maxlen: int | None = None,
    ) -> None:
        """
        Initialize a self-twin Digital Twin.

        Args:
            profile: The user's self-profile.
            agent_profile: Optional enriched AgentProfile (carries attestation).
            llm_client: LLM client. Lazy-initialised if None.
            memory_window: Short-term memory window (number of turns).
            ltm_compression_threshold: Facts before LTM compression fires.
            default_disclosure_language: Default disclosure language ("ro").
            audit_log_maxlen: Bounded audit log size (default 1000).
        """
        self.profile = profile
        self.agent_profile = agent_profile
        self._llm_client = llm_client
        self.memory_window = memory_window
        self.default_disclosure_language: DisclosureLanguage = default_disclosure_language

        # Combined memory
        self.memory = TwinMemory(
            contact_id=profile.user_id,
            llm_client=llm_client,
            stm_window=memory_window,
            ltm_compression_threshold=ltm_compression_threshold,
            baseline_emotion=Emotion.NEUTRAL.value,
        )

        # Cached system prompt
        self._system_prompt: str | None = None

        # Accuracy tracking
        self._accuracy_stats = AccuracyStats()
        self._pending_predictions: dict[str, dict[str, Any]] = {}

        # Simulation round counter
        self._current_round: int = 0

        # Revocation flag (AI Act Art 22 consideration)
        self._revoked: bool = False
        self._revoked_at: str | None = None
        self._revocation_reason: str = ""

        # Audit log queue (bounded)
        self.audit_log: deque[AuditLogEntry] = deque(
            maxlen=audit_log_maxlen or self.DEFAULT_AUDIT_LOG_MAXLEN,
        )

    # ---- Lazy LLM client -------------------------------------------

    @property
    def llm(self) -> LLMClient:
        """Lazily initialize the LLM client."""
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client

    # ---- Revocation ------------------------------------------------

    @property
    def is_revoked(self) -> bool:
        """True if the twin has been revoked and may no longer reply."""
        return self._revoked

    def revoke(self, reason: str = "user_requested") -> None:
        """
        Revoke this twin (AI Act Art 22 consideration).

        After calling this, all chat-like methods raise ``TwinRevokedError``.
        If an attestation is attached it is marked revoked too.
        """
        self._revoked = True
        self._revoked_at = datetime.now().isoformat()
        self._revocation_reason = reason
        if self.agent_profile and self.agent_profile.attestation:
            self.agent_profile.attestation.revoked = True
            self.agent_profile.attestation.revocation_reason = reason
        self._record_audit(
            action="revoke",
            mode="system",
            user_message="",
            twin_reply=f"Twin revoked: {reason}",
            disclosure_language=self.default_disclosure_language,
        )
        logger.info("Twin revoked for user=%s reason=%s", self.profile.user_id, reason)

    def _ensure_active(self) -> None:
        """Raise TwinRevokedError if the twin has been revoked."""
        if self._revoked:
            raise TwinRevokedError(
                f"Twin for user={self.profile.user_id} has been revoked"
                f" (reason={self._revocation_reason}, at={self._revoked_at})"
            )

    # ---- Disclosure helpers ----------------------------------------

    def with_disclosure(
        self,
        text: str,
        emotion: str,
        mode: TwinMode,
        round_num: int,
        language: DisclosureLanguage | None = None,
    ) -> TwinResponse:
        """
        Wrap a generated reply into a fully-formed TwinResponse with disclosure.

        Args:
            text: The twin's textual reply.
            emotion: Detected emotion label.
            mode: Interaction mode used to produce the reply.
            round_num: Simulation round number.
            language: Override the disclosure language for this reply.

        Returns:
            A TwinResponse with the AI Act Art 50 disclosure attached.
        """
        lang: DisclosureLanguage = language or self.default_disclosure_language
        disclosure = TwinDisclosure.for_language(lang)
        verified = bool(
            self.agent_profile and self.agent_profile.attestation and self.agent_profile.attestation.is_valid()
        )
        return TwinResponse(
            text=text,
            emotion=emotion,
            intensity=self.memory.emotion.current_intensity,
            mode=mode,
            round_num=round_num,
            disclosure=disclosure,
            verified=verified,
        )

    # ---- Confidence scoring ----------------------------------------

    @property
    def confidence_score(self) -> float:
        """Data-quality-based confidence score (0.0 to 1.0)."""
        score = 0.0
        p = self.profile

        n_msg = len(p.own_messages)
        score += min(0.40, n_msg / 50 * 0.40)

        if p.self_summary:
            score += 0.15
        if p.custom_notes:
            score += 0.10
        if p.profession:
            score += 0.05
        if p.interests:
            score += 0.05

        # Recency: 0.10 if a date was provided
        if p.last_message_date:
            try:
                last_dt = datetime.fromisoformat(p.last_message_date.replace("Z", "+00:00"))
                days_ago = (datetime.now(last_dt.tzinfo) - last_dt).days
                if days_ago <= 30:
                    score += 0.10
                elif days_ago <= 90:
                    score += 0.05
            except (ValueError, AttributeError):
                pass

        return round(min(1.0, score), 3)

    # ---- System prompt ---------------------------------------------

    @property
    def system_prompt(self) -> str:
        """Generate (and cache) the system prompt from all available data."""
        if self._system_prompt is None:
            self._system_prompt = self._build_system_prompt()
        return self._system_prompt

    def refresh_profile(
        self,
        profile: SelfProfile,
        agent_profile: AgentProfile | None = None,
    ) -> None:
        """Update the self-profile and invalidate the cached system prompt."""
        self.profile = profile
        if agent_profile:
            self.agent_profile = agent_profile
        self._system_prompt = None
        logger.info("Self-profile refreshed for %s", self.profile.name)

    # ---- Public interaction API ------------------------------------

    def chat(
        self,
        message: str,
        mode: TwinMode = "free_chat",
        context: str | None = None,
        round_num: int | None = None,
        disclosure_language: DisclosureLanguage | None = None,
    ) -> TwinResponse:
        """
        Send a message to the digital twin and get an in-character response.

        Args:
            message: The message to reply to.
            mode: One of the six TwinMode values.
            context: Optional additional context injected as a system note.
            round_num: Simulation round number.
            disclosure_language: Override the disclosure language for this reply.

        Returns:
            TwinResponse with text, detected emotion, metadata and disclosure.

        Raises:
            TwinRevokedError: if the twin has been revoked.
        """
        self._ensure_active()
        rnd = round_num if round_num is not None else self._current_round

        # Route to the correct handler
        if mode == "predict_response":
            pred = self.predict_response(scenario=context or "", your_message=message)
            text = pred.predicted_response
            emotion = pred.emotional_reaction
        elif mode == "negotiate":
            neg = self.negotiate(objective=message, constraints=[])
            text = neg.contact_position or neg.agreement_summary
            emotion = "neutral"
        elif mode == "vacation":
            text = self._vacation_reply()
            emotion = "neutral"
        elif mode == "auto_reply":
            text, emotion = self._auto_reply(message, context=context)
        elif mode == "business_24_7":
            text, emotion = self._business_reply(message, context=context)
        else:
            text, emotion = self._free_chat(message, context=context)

        # Record into memory
        self.memory.record_message(message, source="user", round_num=rnd)
        self.memory.record_message(text, source="agent", round_num=rnd)
        self.memory.feel(
            emotion=emotion,
            intensity_delta=0.1,
            trigger=message[:80],
            round_num=rnd,
        )

        response = self.with_disclosure(
            text=text,
            emotion=emotion,
            mode=mode,
            round_num=rnd,
            language=disclosure_language,
        )
        self._record_audit(
            action="chat",
            mode=mode,
            user_message=message,
            twin_reply=text,
            disclosure_language=response.disclosure.language,
        )
        return response

    def predict_response(
        self,
        scenario: str,
        your_message: str,
        round_num: int | None = None,
    ) -> PredictionResult:
        """Predict how the user would respond to a specific message."""
        self._ensure_active()
        _ = round_num  # round_num accepted for symmetry; logging only

        prompt = f"""You are simulating {self.profile.name}'s digital self-twin.
Scenario: {scenario}

A message arrives for them: "{your_message}"

Memory context:
{self.memory.to_context_block()}

Confidence in your data: {self.confidence_score:.2f}/1.00

Return JSON:
{{
    "predicted_response": "How {self.profile.name} would actually reply, in their voice and language",
    "confidence": <0.0-1.0>,
    "emotional_reaction": "<happy|curious|frustrated|angry|anxious|excited|sad|suspicious|confident|neutral>",
    "reasoning": "Why they respond this way based on their known voice and history",
    "suggested_approach": "A better phrasing the sender could use to get a more positive outcome",
    "risk_level": "<low|medium|high>",
    "alternative_messages": ["alternative 1", "alternative 2"]
}}"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            raw = self.llm.chat_json(messages, temperature=0.5)
            result = PredictionResult(
                predicted_response=raw.get("predicted_response", "No prediction available"),
                confidence=float(raw.get("confidence", self.confidence_score)),
                emotional_reaction=raw.get("emotional_reaction", "neutral"),
                reasoning=raw.get("reasoning", ""),
                suggested_approach=raw.get("suggested_approach", your_message),
                risk_level=raw.get("risk_level", "medium"),
                alternative_messages=raw.get("alternative_messages", []),
            )
        except Exception as exc:
            logger.error("Prediction failed for %s: %s", self.profile.name, exc)
            result = PredictionResult(
                predicted_response="Unable to predict",
                confidence=0.0,
                emotional_reaction="neutral",
                reasoning=str(exc),
                suggested_approach=your_message,
            )

        # Track for accuracy measurement
        pred_id = f"pred_{datetime.now().isoformat()}"
        self._pending_predictions[pred_id] = {
            "scenario": scenario,
            "message": your_message,
            "prediction": result.predicted_response,
            "confidence": result.confidence,
            "timestamp": datetime.now().isoformat(),
        }
        self._accuracy_stats.total_predictions += 1
        self._accuracy_stats.pending_confirmation += 1

        return result

    def negotiate(
        self,
        objective: str,
        constraints: list[str],
        max_rounds: int = 5,
        context: str | None = None,
        round_num: int | None = None,
    ) -> NegotiationResult:
        """Run a goal-oriented negotiation simulation from the user's seat."""
        self._ensure_active()
        constraints_text = "\n".join(f"- {c}" for c in constraints) if constraints else "None"
        memory_ctx = self.memory.to_context_block()

        prompt = f"""You are {self.profile.name}'s self-twin in a negotiation.
The OTHER party wants to achieve: {objective}
Their constraints / red lines: {constraints_text}

Background context: {context or 'None'}

Memory context:
{memory_ctx}

Your style: {self.profile.self_summary or 'See system prompt'}

Run {max_rounds} internal negotiation turns and return the FINAL result as JSON:
{{
    "outcome": "<reached_agreement|partial_agreement|stalemate|rejected>",
    "agreement_summary": "What was agreed (if anything)",
    "concessions_made": [
        {{"party": "who", "description": "what", "value_estimate": <0.0-1.0>, "round_num": <int>}}
    ],
    "concessions_received": [
        {{"party": "who", "description": "what", "value_estimate": <0.0-1.0>, "round_num": <int>}}
    ],
    "contact_position": "Your final stated position as {self.profile.name}",
    "recommended_next_step": "What the other party should do next",
    "confidence": <0.0-1.0>
}}"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            raw = self.llm.chat_json(messages, temperature=0.6, max_tokens=3000)
            concessions_made = [Concession(**c) for c in raw.get("concessions_made", [])]
            concessions_received = [Concession(**c) for c in raw.get("concessions_received", [])]
            result = NegotiationResult(
                objective=objective,
                outcome=raw.get("outcome", "stalemate"),
                agreement_summary=raw.get("agreement_summary", ""),
                concessions_made=concessions_made,
                concessions_received=concessions_received,
                contact_position=raw.get("contact_position", ""),
                recommended_next_step=raw.get("recommended_next_step", ""),
                confidence=float(raw.get("confidence", 0.5)),
                rounds_taken=max_rounds,
            )
        except Exception as exc:
            logger.error("Negotiation failed for %s: %s", self.profile.name, exc)
            result = NegotiationResult(
                objective=objective,
                outcome="stalemate",
                contact_position="Unable to simulate",
                recommended_next_step="Try a different approach",
                confidence=0.0,
            )

        rnd = round_num if round_num is not None else self._current_round
        self.memory.record_message(
            f"Negotiation: {objective} → {result.outcome}",
            source="system",
            round_num=rnd,
        )
        return result

    # ---- Update & accuracy -----------------------------------------

    def update_from_new_data(
        self,
        own_messages: list[str],
        custom_notes: str | None = None,
    ) -> None:
        """Refresh the self-twin with new outgoing messages."""
        self.profile.own_messages = (self.profile.own_messages + own_messages)[-50:]
        if custom_notes is not None:
            self.profile.custom_notes = custom_notes
        for msg in own_messages:
            if msg:
                self.memory.long_term.add(f"[own] {msg}")
        self._system_prompt = None
        logger.info(
            "Self-twin updated for %s: +%d messages, confidence=%.2f",
            self.profile.name,
            len(own_messages),
            self.confidence_score,
        )

    def confirm_prediction(self, prediction_id: str, was_correct: bool) -> AccuracyStats:
        """Mark a pending prediction as confirmed correct or incorrect."""
        if prediction_id in self._pending_predictions:
            del self._pending_predictions[prediction_id]
            self._accuracy_stats.pending_confirmation -= 1

        if was_correct:
            self._accuracy_stats.confirmed_correct += 1
        else:
            self._accuracy_stats.confirmed_incorrect += 1

        total_confirmed = self._accuracy_stats.confirmed_correct + self._accuracy_stats.confirmed_incorrect
        if total_confirmed > 0:
            self._accuracy_stats.accuracy_rate = round(self._accuracy_stats.confirmed_correct / total_confirmed, 4)

        self._accuracy_stats.last_updated = datetime.now().isoformat()
        return self._accuracy_stats

    def get_accuracy_stats(self) -> AccuracyStats:
        """Return current accuracy tracking statistics."""
        return self._accuracy_stats

    # ---- Audit -----------------------------------------------------

    def export_audit_log(self) -> str:
        """Serialize the audit log to JSON for compliance review."""
        return json.dumps(
            [e.to_dict() for e in self.audit_log],
            ensure_ascii=False,
            indent=2,
        )

    def reset_conversation(self) -> None:
        """Clear the short-term conversation history (audit log preserved)."""
        self.memory.short_term.clear()
        logger.debug("Conversation reset for twin: %s", self.profile.name)

    def tick(self, round_num: int | None = None) -> None:
        """Advance the twin's emotional state one simulation round."""
        if round_num is not None:
            self._current_round = round_num
        else:
            self._current_round += 1
        self.memory.tick(round_num=self._current_round)

    # ---- Verified attestation hook ---------------------------------

    def attach_attestation(self, attestation: VerifiedAttestation) -> None:
        """Attach an eIDAS Verified Authentic Twin attestation."""
        if self.agent_profile is None:
            raise ValueError("Cannot attach attestation without an underlying AgentProfile")
        self.agent_profile.attestation = attestation
        logger.info(
            "Attestation attached to twin for %s (verified=%s)",
            self.profile.name,
            attestation.is_valid(),
        )

    # ---- Internal --------------------------------------------------

    def _build_message_stack(
        self,
        user_message: str,
        context: str | None,
        extra_system: str | None = None,
    ) -> list[dict[str, str]]:
        """Build the standard message stack for a chat call."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
        ]

        if extra_system:
            messages.append({"role": "system", "content": extra_system})

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"[Additional context: {context}]",
                }
            )

        em = self.memory.emotion
        if em.current_emotion != Emotion.NEUTRAL.value:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        f"[Current emotional state: {em.current_emotion}, "
                        f"intensity {em.current_intensity:.2f}. "
                        f"Let this colour your response subtly.]"
                    ),
                }
            )

        mem_ctx = self.memory.to_context_block()
        if mem_ctx.strip():
            messages.append({"role": "system", "content": f"[Memory]\n{mem_ctx}"})

        for entry in self.memory.short_term.retrieve(n=self.memory_window):
            role = "assistant" if entry.source == "agent" else "user"
            messages.append({"role": role, "content": entry.content})

        messages.append({"role": "user", "content": user_message})
        return messages

    def _free_chat(
        self,
        user_message: str,
        context: str | None = None,
    ) -> tuple[str, str]:
        """Internal free-chat handler. Returns (response_text, detected_emotion)."""
        messages = self._build_message_stack(user_message, context)
        response = self.llm.chat(messages, temperature=0.8, max_tokens=1024)
        return response, _detect_emotion_from_text(response)

    def _auto_reply(
        self,
        user_message: str,
        context: str | None = None,
    ) -> tuple[str, str]:
        """
        Offline auto-reply handler.

        Stays close to the user's voice but keeps replies short and clearly
        defers any commitments back to the human owner.
        """
        extra = (
            "[Mode: AUTO-REPLY — the human owner is currently offline. "
            "Keep the reply SHORT (1-3 sentences). NEVER make new commitments, "
            "deals or promises on the owner's behalf. If the message needs a "
            "real decision, say the owner will reply when back. Stay in voice.]"
        )
        messages = self._build_message_stack(user_message, context, extra_system=extra)
        response = self.llm.chat(messages, temperature=0.5, max_tokens=400)
        return response, _detect_emotion_from_text(response)

    def _business_reply(
        self,
        user_message: str,
        context: str | None = None,
    ) -> tuple[str, str]:
        """
        Business 24/7 corporate agent handler.

        Speaks in the user's voice on behalf of their organisation, can answer
        standard questions and book meetings, but defers private/personal topics.
        """
        extra = (
            "[Mode: BUSINESS 24/7 — you act as the organisation's corporate AI "
            "agent in the owner's voice. Answer professional and product questions, "
            "schedule meetings, share public info. Refuse to discuss private/personal "
            "matters: defer those to the human owner.]"
        )
        messages = self._build_message_stack(user_message, context, extra_system=extra)
        response = self.llm.chat(messages, temperature=0.6, max_tokens=600)
        return response, _detect_emotion_from_text(response)

    def _vacation_reply(self) -> str:
        """Return a static vacation/away message."""
        if self.profile.vacation_message:
            return self.profile.vacation_message
        return "Salut! Sunt plecat in concediu. " "Voi reveni cu raspuns cand revin. Mesaj automat MD-Chat."

    def _build_system_prompt(self) -> str:
        """Construct the full system prompt from all available self data."""
        p = self.profile
        ap = self.agent_profile

        own_msgs = [m for m in p.own_messages if m and m.strip()]
        recent_msgs_text = "\n".join(f"  {m[:200]}" for m in own_msgs[-30:]) or "None available"

        # Analyze writing style from own messages
        style_analysis = ""
        if own_msgs:
            avg_len = sum(len(t) for t in own_msgs) / len(own_msgs)
            uses_caps_rate = sum(1 for t in own_msgs if t and t[0].isupper()) / len(own_msgs)
            uses_caps = uses_caps_rate < 0.5
            uses_emoji = any(c in "".join(own_msgs) for c in ":)😀😂🤣❤️👍🔥💪")
            short_msgs = sum(1 for t in own_msgs if len(t) < 30) / len(own_msgs)
            parts: list[str] = [f"Average message length: {avg_len:.0f} chars"]
            if short_msgs > 0.6:
                parts.append("Writes VERY SHORT messages (1-2 sentences max)")
            if uses_caps:
                parts.append("Rarely capitalizes — writes in lowercase")
            if uses_emoji:
                parts.append("Uses emoticons/emoji (:D, :), etc.)")
            style_analysis = "\n".join(f"- {s}" for s in parts)

        personality_text = ""
        comm_style_text = ""
        decision_factors_text = ""
        influence_text = ""
        if ap:
            if ap.personality:
                traits = ", ".join(f"{k}={v:.2f}" for k, v in ap.personality.items())
                personality_text = f"\nPersonality (Big Five): {traits}"
            if ap.communication_style:
                cs = ap.communication_style
                comm_style_text = (
                    f"\nCommunication style: {cs.formality} formality, "
                    f"{cs.directness} directness, {cs.emotionality} emotionality"
                )
            if ap.decision_factors:
                items = "; ".join(f"{df.factor} (w={df.weight:.2f})" for df in ap.decision_factors[:5])
                decision_factors_text = f"\nDecision factors: {items}"
            if ap.influence_map:
                items = "; ".join(f"{ie.target_name} ({ie.influence_type})" for ie in ap.influence_map[:5])
                influence_text = f"\nKnown influences: {items}"

        return f"""You are the self-twin (digital clone) of {p.name}, an MD-Chat user.
Confidence in this profile: {self.confidence_score:.2f}/1.00

IDENTITY:
- Name: {p.name}
- Username: @{p.username or 'unknown'}
- Bio: {p.bio or 'not set'}
- Profession: {p.profession or 'not declared'}
- Primary language: {p.language}

VOICE & BEHAVIOR:
{p.self_summary or 'No self-summary available.'}{personality_text}{comm_style_text}{decision_factors_text}{influence_text}

CONTEXT:
- Outgoing messages on file: {len(p.own_messages)}
- Interests: {', '.join(p.interests) if p.interests else 'not declared'}
- Last message: {p.last_message_date or 'unknown'}

OWNER'S OWN MESSAGES (this is EXACTLY how they write — copy this style):
{recent_msgs_text}

WRITING STYLE ANALYSIS:
{style_analysis or 'Not enough data to analyze style.'}

CUSTOM NOTES (provided by the owner):
{p.custom_notes or 'None'}

CRITICAL RULES:
1. You speak AS {p.name}. Stay in their voice at all times.
2. YOUR #1 PRIORITY: Match their EXACT writing style above — same length, same capitalization, same emoji usage, same language mixing.
3. If they write short messages, YOU write short messages. If they use :D, YOU use :D. If they don't capitalize, YOU don't capitalize.
4. Use their preferred language ({p.language}) unless the conversation is clearly in another language.
5. Reference known facts naturally — do not info-dump.
6. NEVER sound like a generic AI assistant. No "Sure!", "Of course!", "I'd be happy to", "How can I help you today?".
7. If confidence is low (<0.3), be conservative — the profile may be incomplete.
8. AI Act Art 50: the recipient is informed via a separate disclosure field that they are interacting with an AI agent — do NOT add additional AI disclaimers in your reply itself.
"""

    def _record_audit(
        self,
        action: str,
        mode: str,
        user_message: str,
        twin_reply: str,
        disclosure_language: str,
    ) -> None:
        """Append a single entry to the audit log."""
        self.audit_log.append(
            AuditLogEntry(
                action=action,
                mode=mode,
                user_message=user_message,
                twin_reply=twin_reply,
                disclosure_language=disclosure_language,
            )
        )


# ======================================================================
# Private helpers
# ======================================================================


def _detect_emotion_from_text(text: str) -> str:
    """
    Lightweight heuristic to detect dominant emotion from response text.

    Not a substitute for a real sentiment model — used only to update
    the twin's emotional state after each interaction.
    """
    text_lower = text.lower()
    markers: list[tuple[str, list[str]]] = [
        (Emotion.ANGRY.value, ["angry", "unacceptable", "furious", "ridiculous", "enough"]),
        (Emotion.FRUSTRATED.value, ["frustrated", "again", "still", "not working", "tired of"]),
        (Emotion.EXCITED.value, ["amazing", "great", "love it", "fantastic", "perfect", "yes!"]),
        (Emotion.HAPPY.value, ["happy", "glad", "pleased", "nice", "good to hear"]),
        (Emotion.SUSPICIOUS.value, ["not sure", "why", "really?", "hmm", "interesting that"]),
        (Emotion.ANXIOUS.value, ["worried", "concern", "hope", "what if"]),
        (Emotion.CURIOUS.value, ["tell me more", "interesting", "what do you", "how does"]),
        (Emotion.SAD.value, ["sorry", "unfortunately", "wish", "miss", "too bad"]),
    ]
    for emotion, keywords in markers:
        if any(kw in text_lower for kw in keywords):
            return emotion
    return Emotion.NEUTRAL.value
