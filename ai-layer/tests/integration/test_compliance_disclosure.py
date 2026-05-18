"""Compliance tests — EU AI Act Article 50 (transparency / disclosure).

Article 50(1) of Regulation (EU) 2024/1689 (the AI Act) requires
providers of AI systems that interact with natural persons to ensure
that those persons are informed that they are interacting with an AI
system. Member-state implementations (Moldova's Law 195/2024 mirrors
this) enforce the same surface.

These tests verify the *surface area* — that the disclosure strings
configured via environment variables are reachable through the config
module and exposed via the health endpoint metadata. They do NOT verify
that every chat reply embeds the disclosure (that is enforced by unit
tests in the agents/ module).
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.compliance]


# Canonical disclosure strings — must match conftest.SAFE_ENV.
EXPECTED_DISCLOSURES = {
    "ro": "Sunteti in legatura cu un agent AI MD-Chat.",
    "ru": "Vy obshchaetes s AI-agentom MD-Chat.",
    "en": "You are interacting with an MD-Chat AI agent.",
}


def test_config_exposes_disclosure_strings():
    """The CONFIG dataclass MUST expose ro/ru/en disclosure strings."""
    from md_chat_ai.config import CONFIG

    assert CONFIG.ai_disclosure_ro == EXPECTED_DISCLOSURES["ro"]
    assert CONFIG.ai_disclosure_ru == EXPECTED_DISCLOSURES["ru"]
    assert CONFIG.ai_disclosure_en == EXPECTED_DISCLOSURES["en"]


@pytest.mark.parametrize("lang", ["ro", "ru", "en"])
def test_disclosure_non_empty(lang):
    """Each disclosure string MUST be non-empty (no silent disablement)."""
    from md_chat_ai.config import CONFIG

    value = getattr(CONFIG, f"ai_disclosure_{lang}")
    assert isinstance(value, str)
    assert len(value.strip()) >= 10, f"{lang} disclosure suspiciously short"


def test_health_advertises_ai_act_disclosure(client):
    """The health endpoint MUST advertise the AI Act flag."""
    response = client.get("/api/health")
    data = response.get_json()
    assert data.get("ai_act_disclosure") is True, (
        "health payload missing ai_act_disclosure=True — AI Act Art 50 "
        "transparency MUST be observable from the health surface"
    )


def test_disclosure_strings_mention_ai():
    """Disclosure strings MUST mention 'AI' (literal) for clarity."""
    from md_chat_ai.config import CONFIG

    for lang in ("ro", "ru", "en"):
        text = getattr(CONFIG, f"ai_disclosure_{lang}")
        assert "AI" in text or "ai" in text.lower(), f"{lang} disclosure '{text}' MUST reference AI explicitly"


def test_idnp_release_default_is_false():
    """GDPR Art 5(1)(c) data minimisation — IDNP must NOT be released by default.

    Moldovan IDNP is a national identification number. The MPass bridge
    MUST require explicit, separable consent before passing it to
    relying parties. Default ``False`` is the secure baseline.
    """
    from md_chat_ai.config import CONFIG

    assert (
        CONFIG.mpass_release_idnp_default is False
    ), "MPASS_RELEASE_IDNP default MUST be false (GDPR data minimisation)"


def test_oidc_issuer_uses_https():
    """OIDC issuer URL MUST be HTTPS in non-dev configuration."""
    from md_chat_ai.config import CONFIG

    assert CONFIG.oidc_issuer.startswith("https://"), "OIDC issuer MUST use HTTPS — OIDC Core spec + GDPR Art 32"


def test_mpass_metadata_url_uses_https():
    """MPass IdP metadata MUST be loaded over HTTPS to prevent SAML XSW."""
    from md_chat_ai.config import CONFIG

    assert CONFIG.mpass_idp_metadata_url.startswith(
        "https://"
    ), "MPASS_IDP_METADATA_URL MUST use HTTPS to prevent metadata tampering"
