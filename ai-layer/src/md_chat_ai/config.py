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

    # MPass / MSign — Moldova government identity (eIDAS-aspiring)
    # AGE = Agentia de Guvernare Electronica (e-Government Agency) onboarding.
    mpass_sp_entity_id: str = os.getenv(
        "MPASS_SP_ENTITY_ID", "https://msg.md-chat.eu/saml/sp"
    )
    mpass_sp_acs_url: str = os.getenv(
        "MPASS_SP_ACS_URL", "https://msg.md-chat.eu/api/v1/identity/saml/acs"
    )
    mpass_sp_slo_url: str = os.getenv(
        "MPASS_SP_SLO_URL", "https://msg.md-chat.eu/api/v1/identity/saml/slo"
    )
    mpass_sp_cert_path: str = os.getenv("MPASS_SP_CERT_PATH", "/etc/md-chat/mpass/sp.crt")
    mpass_sp_key_path: str = os.getenv("MPASS_SP_KEY_PATH", "/etc/md-chat/mpass/sp.key")
    mpass_idp_metadata_url: str = os.getenv(
        "MPASS_IDP_METADATA_URL", "https://mpass.gov.md/Metadata"
    )
    mpass_idp_metadata_path: str = os.getenv("MPASS_IDP_METADATA_PATH", "")

    # Release IDNP only after a second, explicit consent step. GDPR Art 5(1)(c).
    mpass_release_idnp_default: bool = os.getenv("MPASS_RELEASE_IDNP", "false").lower() == "true"

    # OIDC bridge — issuer URL clients trust.
    oidc_issuer: str = os.getenv("OIDC_ISSUER", "https://msg.md-chat.eu")
    oidc_signing_key_path: str = os.getenv(
        "OIDC_SIGNING_KEY_PATH", "/etc/md-chat/oidc/signing.pem"
    )
    oidc_signing_kid: str = os.getenv("OIDC_SIGNING_KID", "mpass-bridge-1")
    oidc_id_token_ttl: int = int(os.getenv("OIDC_ID_TOKEN_TTL", "600"))
    oidc_code_ttl: int = int(os.getenv("OIDC_CODE_TTL", "120"))

    # MSign SOAP endpoint (qualified signatures).
    msign_wsdl_url: str = os.getenv(
        "MSIGN_WSDL_URL", "https://msign.gov.md/services/sign?wsdl"
    )
    msign_client_id: str = os.getenv("MSIGN_CLIENT_ID", "")
    msign_client_secret: str = os.getenv("MSIGN_CLIENT_SECRET", "")
    msign_timeout: int = int(os.getenv("MSIGN_TIMEOUT", "30"))

    # Mode
    dev_mode: bool = os.getenv("NODE_ENV", "production").lower() in {"development", "dev"}

    @property
    def is_configured(self) -> bool:
        """Whether minimal required configuration is present."""
        return bool(self.neo4j_password and self.router_key)


CONFIG = Config()
