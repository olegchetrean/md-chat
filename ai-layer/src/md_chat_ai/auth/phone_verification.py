"""Phone verification — SMS code generation, send via Infobip, verify.

Python port of the Router by MP TypeScript reference at
``apps/api-billing/src/auth/phone-verification.service.ts``.

Conventions:
- SMS body uses GSM-7 alphabet (no diacritice) — UCS-2 doubles the cost.
- API responses / UI strings use diacritice (Romanian standard).
- Phone numbers and codes are hashed (scrypt) before any persistence.
- PII (full phone numbers, codes) never logged in plain.

GDPR: storage layer is expected to hold only ``phone_hash`` and ``code_hash``.
The in-memory store provided here mirrors that contract for tests / dev.

Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import re
import secrets
import time
from dataclasses import dataclass, field

import httpx

# ---------------------------------------------------------------------------
# Constants — kept in sync with the TypeScript reference.
# ---------------------------------------------------------------------------

CODE_EXPIRES_MINUTES = 10
COOLDOWN_SECONDS = 60
MAX_PER_HOUR = 5
MAX_ATTEMPTS = 5

_SCRYPT_SALT = b"phone-verification-salt"
_SCRYPT_N = 16384
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32

# Common dial codes — extend as needed. Fallback assumes user passes raw international.
DIAL_CODES: dict[str, str] = {
    "MD": "+373",
    "RO": "+40",
    "UA": "+380",
    "RU": "+7",
    "US": "+1",
    "CA": "+1",
    "GB": "+44",
    "DE": "+49",
    "FR": "+33",
    "IT": "+39",
    "ES": "+34",
    "PT": "+351",
    "PL": "+48",
    "BG": "+359",
    "HU": "+36",
    "CZ": "+420",
    "SK": "+421",
    "AT": "+43",
    "CH": "+41",
    "BE": "+32",
    "NL": "+31",
    "IE": "+353",
    "GR": "+30",
    "TR": "+90",
    "IL": "+972",
}

# SMS body templates by Accept-Language. GSM-7 only (no diacritice).
_SMS_TEMPLATES: dict[str, str] = {
    "ro": "Codul tau MD-Chat: {code}\nValabil 10 minute.\nDaca nu ai cerut acest cod, ignora.",
    "ru": "Vash kod MD-Chat: {code}\nDeystvitelen 10 minut.\nEsli vy ne zaprashivali, proignoriruyte.",
    "en": "Your MD-Chat code: {code}\nValid for 10 minutes.\nIf you did not request this, ignore.",
}


def _infobip_base_url() -> str:
    return (os.getenv("INFOBIP_BASE_URL") or "https://api.infobip.com").rstrip("/")


def _infobip_api_key() -> str:
    return os.getenv("INFOBIP_API_KEY", "")


def _infobip_sender() -> str:
    return os.getenv("INFOBIP_SENDER_ID", "MDChat")


# ---------------------------------------------------------------------------
# Helpers — normalization, hashing, code generation.
# ---------------------------------------------------------------------------

_NON_DIGIT_PLUS_RE = re.compile(r"[^\d+]")
_LEADING_ZEROS_RE = re.compile(r"^0+")


def normalize_to_e164(phone_number: str, country_code: str) -> str:
    """Normalize a raw phone string to E.164.

    Rules (matches TS reference):
    - Strip everything except digits and ``+``.
    - If starts with ``+`` already, return as-is (assumed international).
    - If starts with ``00``, replace by ``+``.
    - Otherwise lookup country in DIAL_CODES, strip leading zeros, prepend dial.
    - Fallback when country unknown: prepend ``+`` after stripping leading zeros.
    """
    if not phone_number:
        return ""
    digits = _NON_DIGIT_PLUS_RE.sub("", phone_number)
    if digits.startswith("+"):
        return digits
    dial = DIAL_CODES.get(country_code.upper()) if country_code else None
    if not dial:
        if digits.startswith("00"):
            return "+" + digits[2:]
        return "+" + _LEADING_ZEROS_RE.sub("", digits)
    local = _LEADING_ZEROS_RE.sub("", digits)
    return f"{dial}{local}"


def _scrypt(secret: bytes) -> bytes:
    return hashlib.scrypt(
        secret,
        salt=_SCRYPT_SALT,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )


def hash_code(code: str) -> str:
    """scrypt-hash a numeric code, return hex string."""
    return _scrypt(code.encode("utf-8")).hex()


def hash_phone(e164: str) -> str:
    """scrypt-hash a normalized phone number, return hex string. Used for GDPR storage."""
    return _scrypt(e164.encode("utf-8")).hex()


def generate_code() -> str:
    """Generate a 6-digit numeric code in [100000, 999999], uniformly."""
    return str(100000 + secrets.randbelow(900000))


def _constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("ascii"), b.encode("ascii"))


def _pick_sms_body(code: str, accept_language: str | None) -> str:
    if accept_language:
        for tag in accept_language.split(","):
            primary = tag.split(";")[0].strip().lower()[:2]
            if primary in _SMS_TEMPLATES:
                return _SMS_TEMPLATES[primary].format(code=code)
    return _SMS_TEMPLATES["ro"].format(code=code)


# ---------------------------------------------------------------------------
# Result types.
# ---------------------------------------------------------------------------


@dataclass
class SendCodeResult:
    ok: bool
    error: str | None = None
    cooldown_until: float | None = None  # unix timestamp


@dataclass
class VerifyCodeResult:
    ok: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# In-memory store. Production should replace with Postgres-backed store
# implementing the same protocol (see methods).
# ---------------------------------------------------------------------------


@dataclass
class _CodeRecord:
    user_id: str
    phone_hash: str
    code_hash: str
    created_at: float
    expires_at: float
    attempts: int = 0
    consumed_at: float | None = None


@dataclass
class InMemoryStore:
    """Default in-memory backend. Holds only hashed PII (phone, code)."""

    records: list[_CodeRecord] = field(default_factory=list)

    def insert(self, record: _CodeRecord) -> None:
        self.records.append(record)

    def latest_for_user(self, user_id: str) -> _CodeRecord | None:
        candidates = [r for r in self.records if r.user_id == user_id]
        return max(candidates, key=lambda r: r.created_at) if candidates else None

    def latest_active(self, user_id: str, now: float) -> _CodeRecord | None:
        candidates = [r for r in self.records if r.user_id == user_id and r.consumed_at is None and r.expires_at > now]
        return max(candidates, key=lambda r: r.created_at) if candidates else None

    def count_within(self, user_id: str, since: float) -> int:
        return sum(1 for r in self.records if r.user_id == user_id and r.created_at >= since)

    def reset(self) -> None:
        self.records.clear()


# Single module-level store. For multi-tenant deployments, inject your own.
_default_store = InMemoryStore()


def get_store() -> InMemoryStore:
    return _default_store


# ---------------------------------------------------------------------------
# Infobip SMS sender.
# ---------------------------------------------------------------------------


async def _send_sms_via_infobip(
    phone_e164: str,
    code: str,
    accept_language: str | None,
    client: httpx.AsyncClient | None = None,
) -> tuple[bool, str | None]:
    api_key = _infobip_api_key()
    if not api_key:
        return False, "sms_provider_not_configured"

    body = {
        "messages": [
            {
                "destinations": [{"to": phone_e164}],
                "from": _infobip_sender(),
                "text": _pick_sms_body(code, accept_language),
            }
        ]
    }
    url = f"{_infobip_base_url()}/sms/2/text/advanced"
    headers = {
        "Authorization": f"App {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    owns_client = client is None
    cli = client or httpx.AsyncClient(timeout=10.0)
    try:
        try:
            r = await cli.post(url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            return False, f"sms_transport_error:{type(exc).__name__}"
        if r.status_code >= 400:
            return False, f"infobip_http_{r.status_code}"
        return True, None
    finally:
        if owns_client:
            await cli.aclose()


# ---------------------------------------------------------------------------
# Public service functions.
# ---------------------------------------------------------------------------


async def send_phone_verification_code(
    user_id: str,
    phone_number: str,
    country_code: str,
    *,
    accept_language: str | None = None,
    store: InMemoryStore | None = None,
    http_client: httpx.AsyncClient | None = None,
    now: float | None = None,
) -> SendCodeResult:
    """Generate a 6-digit code, persist hash, send via SMS, enforce rate limits."""
    backend = store or _default_store
    t = now if now is not None else time.time()

    e164 = normalize_to_e164(phone_number, country_code)
    if not e164 or len(e164) < 6:
        return SendCodeResult(ok=False, error="invalid_phone_number")

    # Cooldown: 1 send per COOLDOWN_SECONDS.
    latest = backend.latest_for_user(user_id)
    if latest is not None and (t - latest.created_at) < COOLDOWN_SECONDS:
        return SendCodeResult(
            ok=False,
            error="cooldown_active",
            cooldown_until=latest.created_at + COOLDOWN_SECONDS,
        )

    # Hourly rolling limit.
    if backend.count_within(user_id, t - 3600) >= MAX_PER_HOUR:
        return SendCodeResult(ok=False, error="too_many_requests")

    code = generate_code()
    record = _CodeRecord(
        user_id=user_id,
        phone_hash=hash_phone(e164),
        code_hash=hash_code(code),
        created_at=t,
        expires_at=t + CODE_EXPIRES_MINUTES * 60,
    )
    backend.insert(record)

    ok, err = await _send_sms_via_infobip(e164, code, accept_language, client=http_client)
    if not ok:
        return SendCodeResult(ok=False, error=err or "sms_send_failed")
    return SendCodeResult(ok=True)


async def verify_phone_code(
    user_id: str,
    code: str,
    *,
    store: InMemoryStore | None = None,
    now: float | None = None,
) -> VerifyCodeResult:
    """Verify a phone code. Increments ``attempts`` before comparing.

    Returns ``too_many_attempts`` once attempts exceed MAX_ATTEMPTS — the
    record is then marked consumed to prevent further brute-force.
    """
    backend = store or _default_store
    t = now if now is not None else time.time()

    record = backend.latest_active(user_id, t)
    if record is None:
        return VerifyCodeResult(ok=False, error="expired_or_not_found")

    record.attempts += 1
    if record.attempts > MAX_ATTEMPTS:
        record.consumed_at = t
        return VerifyCodeResult(ok=False, error="too_many_attempts")

    candidate = hash_code(code)
    if not _constant_time_eq(candidate, record.code_hash):
        return VerifyCodeResult(ok=False, error="invalid_code")

    record.consumed_at = t
    return VerifyCodeResult(ok=True)


# ---------------------------------------------------------------------------
# Sync convenience wrappers — Flask handlers use these to avoid the async
# context shuffle. They internally drive ``asyncio.run``.
# ---------------------------------------------------------------------------


def send_phone_verification_code_sync(
    user_id: str,
    phone_number: str,
    country_code: str,
    *,
    accept_language: str | None = None,
    store: InMemoryStore | None = None,
) -> SendCodeResult:
    return asyncio.run(
        send_phone_verification_code(
            user_id,
            phone_number,
            country_code,
            accept_language=accept_language,
            store=store,
        )
    )


def verify_phone_code_sync(
    user_id: str,
    code: str,
    *,
    store: InMemoryStore | None = None,
) -> VerifyCodeResult:
    return asyncio.run(verify_phone_code(user_id, code, store=store))
