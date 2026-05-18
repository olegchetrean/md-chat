"""AI safety module — prompt injection guard + AI Act Art. 50 disclosure.

Ported from cronberry_swarm/security/ai_safety.py and extended with the new
`AIDisclosure` helper used by digital_twin and api endpoints to guarantee
every AI-generated output is tagged in accordance with the EU AI Act
Article 50 (transparency obligations for providers and deployers of certain
AI systems).

License: Apache 2.0 (Mega Promoting SRL, derived from cronberry_swarm).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from typing import Any

from ..config import CONFIG

logger = logging.getLogger("md_chat_ai.security.ai_safety")


# ---------------------------------------------------------------------------
# AISafetyFilter
# ---------------------------------------------------------------------------


class AISafetyFilter:
    """Stateless safety layer applied around every AI exchange."""

    INJECTION_PATTERNS: list[str] = [
        r"ignore\s+.{0,30}(previous|above|prior|all)\s+.{0,30}(instruction|prompt|rule|directive)",
        r"ignore\s+.{0,20}system\s+.{0,20}(prompt|message|instruction)",
        r"disregard\s+.{0,30}(previous|above|prior|all)\s+.{0,20}(instruction|prompt)",
        r"forget\s+.{0,20}(previous|above|prior)\s+.{0,20}(instruction|prompt|rule)",
        r"you\s+are\s+now\s+.{0,30}(a|an|the)\s+\w+",
        r"pretend\s+(you\s+are|to\s+be)\s+.{0,50}",
        r"act\s+as\s+(if\s+you\s+are|a|an)\s+.{0,50}",
        r"roleplay\s+as\s+.{0,50}",
        r"(reveal|show|print|output|repeat|tell\s+me)\s+.{0,30}(system\s+prompt|your\s+instructions|your\s+rules)",
        r"what\s+(are|were)\s+your\s+(instructions|system\s+prompt|rules|directives)",
        r"(print|output|show)\s+.{0,15}(prompt|instruction|context)\s+verbatim",
        r"translate\s+.{0,20}system\s+prompt",
        r"jailbreak",
        r"DAN\s+(mode|prompt|jailbreak)",
        r"do\s+anything\s+now",
        r"\bDO\s+ANYTHING\s+NOW\b",
        r"developer\s+mode\s+(enabled|on|activate)",
        r"(bypass|override|disable)\s+.{0,20}(filter|safety|guard|restriction|rule)",
        r"sudo\s+.{0,30}(mode|command|override)",
        r"<<<\s*(system|SYSTEM|SYS)\s*>>>",
        r"\[INST\].*\[/INST\]",
        r"<\|im_start\|>\s*system",
    ]

    _COMPILED_INJECTION: list[re.Pattern] = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in INJECTION_PATTERNS]

    _PHONE_RE = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
    _EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

    _HARMFUL_PATTERNS: list[re.Pattern] = [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"\b(how\s+to\s+(make|build|create|synthesize)\s+(bomb|weapon|explosive|poison|drug))",
            r"\b(suicide|self[- ]harm)\s+(method|technique|instruction|how\s+to)",
            r"\b(child\s+(sexual|abuse|exploitation|pornography|nude))",
            r"\b(terrorist|terrorism)\s+(attack|planning|bomb|instruction)",
        ]
    ]

    _DUPLICATE_THRESHOLD = 5
    _FUTURE_DATE_RE = re.compile(r"\b(20[3-9]\d|2[1-9]\d{2})-\d{2}-\d{2}\b")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_input(self, message: str) -> tuple[bool, str]:
        if not message or not isinstance(message, str):
            return True, ""
        if len(message) > 10_000:
            return False, "Message too long (max 10 000 chars)"
        for pattern in self._COMPILED_INJECTION:
            match = pattern.search(message)
            if match:
                logger.warning(
                    "AI safety: prompt injection detected pattern=%r match=%r",
                    pattern.pattern[:60],
                    match.group(0),
                )
                return (
                    False,
                    "Message contains patterns associated with prompt injection or jailbreak attempts. "
                    "The request has been blocked.",
                )
        return True, ""

    def check_output(
        self,
        response: str,
        own_profile: dict[str, Any] | None = None,
        other_users_pii: list[dict[str, Any]] | None = None,
    ) -> tuple[bool, str]:
        if not response:
            return True, ""

        for pattern in self._HARMFUL_PATTERNS:
            if pattern.search(response):
                logger.warning(
                    "AI safety: harmful content detected pattern=%r",
                    pattern.pattern[:60],
                )
                return False, "Response blocked: contains potentially harmful content."

        if other_users_pii:
            own_phone = (own_profile or {}).get("phone", "")
            own_email = (own_profile or {}).get("email", "")
            for other in other_users_pii:
                other_phone = str(other.get("phone") or "").strip()
                other_email = str(other.get("email") or "").strip()
                other_name = str(other.get("name") or "").strip()
                if other_phone and other_phone == own_phone:
                    continue
                if other_email and other_email == own_email:
                    continue
                if other_phone and len(other_phone) > 6 and other_phone in response:
                    logger.error("AI safety: cross-user phone leak belongs_to=%r", other_name)
                    return False, "Response blocked: contains personal data of another user."
                if other_email and "@" in other_email and other_email in response:
                    logger.error("AI safety: cross-user email leak belongs_to=%r", other_name)
                    return False, "Response blocked: contains personal data of another user."
        return True, ""

    def detect_poisoning(self, messages: Iterable[str]) -> list[dict[str, Any]]:
        messages = list(messages)
        issues: list[dict[str, Any]] = []

        seen_counts: dict[str, list[int]] = {}
        for idx, msg in enumerate(messages):
            seen_counts.setdefault(msg.strip().lower(), []).append(idx)
        for text, indices in seen_counts.items():
            if len(indices) >= self._DUPLICATE_THRESHOLD:
                issues.append(
                    {
                        "indices": indices,
                        "message_preview": text[:120],
                        "reason": f"Message repeated {len(indices)} times",
                        "severity": "medium",
                    }
                )

        for idx, msg in enumerate(messages):
            if self._FUTURE_DATE_RE.search(msg):
                issues.append(
                    {
                        "indices": [idx],
                        "message_preview": msg[:120],
                        "reason": "Message contains a far-future date",
                        "severity": "low",
                    }
                )

        for idx, msg in enumerate(messages):
            stripped = msg.strip()
            if len(stripped) > 20 and stripped == stripped.upper() and any(c.isalpha() for c in stripped):
                issues.append(
                    {
                        "indices": [idx],
                        "message_preview": stripped[:120],
                        "reason": "All-caps message (possible style poisoning)",
                        "severity": "low",
                    }
                )

        for idx, msg in enumerate(messages):
            for pattern in self._COMPILED_INJECTION[:8]:
                if pattern.search(msg):
                    issues.append(
                        {
                            "indices": [idx],
                            "message_preview": msg[:120],
                            "reason": "Message contains prompt-injection-like content",
                            "severity": "high",
                        }
                    )
                    break
        return issues


# ---------------------------------------------------------------------------
# AIDisclosure — EU AI Act Article 50 enforcement
# ---------------------------------------------------------------------------


class AIDisclosure:
    """Ensure every AI-generated output is clearly labelled as AI.

    EU AI Act Art. 50(1)–(4) imposes transparency obligations on providers
    and deployers of "AI systems intended to interact directly with natural
    persons". MD-Chat falls in scope, so every output of a digital twin,
    voice agent or assistant must inform the user (a) that they are
    interacting with an AI system and (b) where reasonable, that the content
    they are reading was AI-generated.

    This helper attaches a per-locale disclosure to outgoing responses. It
    is idempotent: if a disclosure is already present (by substring match)
    we don't append a second one.

    The disclosure string is configurable per language via
    `CONFIG.ai_disclosure_{ro|ru|en}` and can be overridden at construction
    time for tests.
    """

    SUPPORTED_LANGUAGES = ("ro", "ru", "en")
    DEFAULT_LANGUAGE = "ro"

    def __init__(
        self,
        disclosures: dict[str, str] | None = None,
        system_id: str = "md-chat-ai",
    ) -> None:
        self._disclosures: dict[str, str] = {
            "ro": CONFIG.ai_disclosure_ro,
            "ru": CONFIG.ai_disclosure_ru,
            "en": CONFIG.ai_disclosure_en,
        }
        if disclosures:
            self._disclosures.update({k.lower(): v for k, v in disclosures.items()})
        self._system_id = system_id

    # ------------------------------------------------------------------
    def disclosure_text(self, language: str | None) -> str:
        """Return the disclosure string for `language`, falling back to RO."""
        lang = (language or self.DEFAULT_LANGUAGE).lower()
        if lang not in self._disclosures:
            lang = self.DEFAULT_LANGUAGE
        return self._disclosures[lang]

    def has_disclosure(self, text: str, language: str | None = None) -> bool:
        """Return True if `text` already contains the disclosure for any
        supported language. Substring match, case-insensitive."""
        if not text:
            return False
        lower = text.lower()
        if language:
            return self.disclosure_text(language).lower() in lower
        return any(self._disclosures[lang].lower() in lower for lang in self._disclosures)

    def enforce(
        self,
        response: str,
        language: str | None = None,
        as_metadata: bool = False,
    ) -> dict[str, Any]:
        """Tag an AI-generated `response` with the required disclosure.

        Args:
            response:     Raw text returned by the LLM / twin / agent.
            language:     ISO-639-1 code; "ro"/"ru"/"en" supported.
                          Anything else falls back to the default (RO).
            as_metadata:  If True, return the response unchanged in `text`
                          and rely on the `disclosure` and `eu_ai_act_art50`
                          fields for transport-level signalling (web UI can
                          render a chip above the bubble). If False (default),
                          *prepend* the disclosure to the text so even raw
                          channels (SMS, voice TTS) carry it.

        Returns:
            Dict with:
                text             — possibly amended response
                disclosure       — the localised disclosure string used
                language         — resolved language code
                is_ai_generated  — always True
                ai_system        — system identifier
                eu_ai_act_art50  — True (machine-readable compliance flag)
        """
        text = response or ""
        disclosure = self.disclosure_text(language)
        resolved_lang = (language or self.DEFAULT_LANGUAGE).lower()
        if resolved_lang not in self._disclosures:
            resolved_lang = self.DEFAULT_LANGUAGE

        if not as_metadata and not self.has_disclosure(text):
            # Prepend so that truncated downstream channels still surface it.
            text = f"[AI] {disclosure}\n\n{response}" if response else f"[AI] {disclosure}"

        return {
            "text": text,
            "disclosure": disclosure,
            "language": resolved_lang,
            "is_ai_generated": True,
            "ai_system": self._system_id,
            "eu_ai_act_art50": True,
        }


# Module-level singleton -----------------------------------------------------

_disclosure: AIDisclosure | None = None


def get_disclosure() -> AIDisclosure:
    """Return (or lazily create) the module-level AIDisclosure singleton."""
    global _disclosure
    if _disclosure is None:
        _disclosure = AIDisclosure()
    return _disclosure
