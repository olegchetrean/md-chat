"""
Digital Twin engine for MD-Chat (self-twin mode).

Derived from Cronberry (Mega Promoting SRL), Apache 2.0.

Public API:
    DigitalTwin, TwinResponse, TwinDisclosure, PredictionResult,
    NegotiationResult, SelfProfile, AgentProfile, VerifiedAttestation,
    MdChatProfileGenerator, MessageOptimizer, TwinMemory, Emotion,
    PromiseStatus.
"""

from __future__ import annotations

from .digital_twin import (
    AccuracyStats,
    Concession,
    DigitalTwin,
    NegotiationResult,
    PredictionResult,
    SelfProfile,
    TwinDisclosure,
    TwinResponse,
    VerifiedAttestation,
)
from .memory import (
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
)
from .message_optimizer import (
    MessageOptimizer,
    MessageVariant,
    OptimizationResult,
    VariantTestResult,
)
from .profile_generator import (
    AgentProfile,
    CommunicationStyle,
    DecisionFactor,
    InfluenceEdge,
    MdChatProfileGenerator,
    ProfileGenerator,
    ResponsePattern,
)

__all__ = [
    "AccuracyStats",
    "AgentProfile",
    "CommunicationStyle",
    "Concession",
    "DecisionFactor",
    "DigitalTwin",
    "Emotion",
    "EmotionalState",
    "InfluenceEdge",
    "LongTermMemory",
    "MdChatProfileGenerator",
    "MemoryEntry",
    "MessageOptimizer",
    "MessageVariant",
    "NegotiationResult",
    "OptimizationResult",
    "PredictionResult",
    "ProfileGenerator",
    "Promise",
    "PromiseMemory",
    "PromiseStatus",
    "RelationshipMemory",
    "RelationshipState",
    "ResponsePattern",
    "SelfProfile",
    "ShortTermMemory",
    "TwinDisclosure",
    "TwinMemory",
    "TwinResponse",
    "VariantTestResult",
    "VerifiedAttestation",
]
