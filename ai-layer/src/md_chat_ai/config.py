"""Configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Runtime configuration for md-chat-ai."""

    port: int = int(os.getenv("AI_LAYER_PORT", "5002"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Neo4j
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")

    # Router by MP — internal AI gateway
    router_base: str = os.getenv("ROUTER_API_BASE", "https://api.megapromoting.com/v1")
    router_key: str = os.getenv("ROUTER_API_KEY", "")

    # Synapse
    synapse_hs_url: str = os.getenv("SYNAPSE_HS_URL", "http://synapse:8008")
    synapse_as_token: str = os.getenv("SYNAPSE_AS_TOKEN", "")

    # Infobip — phone verification
    infobip_base: str = os.getenv("INFOBIP_BASE_URL", "https://api.infobip.com")
    infobip_key: str = os.getenv("INFOBIP_API_KEY", "")
    infobip_sender: str = os.getenv("INFOBIP_SENDER_ID", "MDChat")

    # AI Act Art 50 disclosure
    ai_disclosure_ro: str = os.getenv("AI_DISCLOSURE_TEXT_RO", "Sunteti in legatura cu un agent AI MD-Chat.")
    ai_disclosure_ru: str = os.getenv("AI_DISCLOSURE_TEXT_RU", "Vy obshchaetes s AI-agentom MD-Chat.")
    ai_disclosure_en: str = os.getenv("AI_DISCLOSURE_TEXT_EN", "You are interacting with an MD-Chat AI agent.")

    # Mode
    dev_mode: bool = os.getenv("NODE_ENV", "production").lower() in {"development", "dev"}

    @property
    def is_configured(self) -> bool:
        """Whether minimal required configuration is present."""
        return bool(self.neo4j_password and self.router_key)


CONFIG = Config()
