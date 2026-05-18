"""Flask blueprint exposing the Digital Twin engine over HTTP.

Endpoints (mounted under ``/api/v1/twin`` by the application factory):

* ``POST /api/v1/twin/<user_id>/chat``        — converse with the twin.
* ``GET  /api/v1/twin/<user_id>/profile``     — read the twin profile.
* ``POST /api/v1/twin/<user_id>/profile``     — create / update the twin profile.
* ``POST /api/v1/twin/<user_id>/revoke``      — revoke the twin (AI Act Art 22).
* ``GET  /api/v1/twin/<user_id>/audit-log``   — last 100 audit entries
                                                 (internal-token guarded).
* ``POST /api/v1/twin/<user_id>/attest``      — eIDAS attest (Sprint 6 stub).

Behavioural contract:

* Every endpoint returns a uniform envelope ``{"ok", "data", "error"}``.
* ``chat`` answers carry the AI Act Article 50 disclosure in
  ``data.response.disclosure`` AND a top-level ``data.disclosure`` mirror
  so naive consumers (SMS / voice gateways) cannot strip it off.
* Validation failures → 400, missing twin → 404, revoked twin → 410 Gone,
  rate-limit breach → 429 with ``Retry-After``.
* Per-(user, IP) namespaced rate limiting via ``security.get_limiter()``
  with namespace ``twin-chat`` on the chat endpoint.
* Audit-log readout requires ``X-MDChat-Internal-Token`` matching the
  ``TWIN_INTERNAL_TOKEN`` (or ``EEVIDENCE_INTERNAL_TOKEN`` fallback) env var.
* Logging is PII-conscious: we never log the full user message body, only
  a fingerprint (length + sha256 prefix) and the resolved mode.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from collections.abc import Callable
from functools import wraps
from threading import Lock
from typing import Any, Literal

from flask import Blueprint, Response, current_app, jsonify, request
from pydantic import BaseModel, Field, ValidationError, field_validator

from ..agents.digital_twin import (
    DigitalTwin,
    SelfProfile,
    TwinDisclosure,
    TwinRevokedError,
)
from ..agents.profile_generator import AgentProfile, VerifiedAttestation
from ..security import get_disclosure, get_limiter
from ..security.rate_limiter import NamespaceLimit

logger = logging.getLogger(__name__)

bp = Blueprint("twin", __name__)


# ---------------------------------------------------------------------------
# In-memory twin registry — Sprint T2 will swap this for a DB-backed store.
# ---------------------------------------------------------------------------


class _TwinRegistry:
    """Process-local twin store keyed by user_id.

    Thread-safe via a single lock; access volume is low (one twin per user,
    cached for the lifetime of the worker). The DB persistence layer landing
    in T2 will subclass this same surface (``get``/``put``/``drop``).
    """

    def __init__(self) -> None:
        self._twins: dict[str, DigitalTwin] = {}
        self._lock = Lock()

    def get(self, user_id: str) -> DigitalTwin | None:
        with self._lock:
            return self._twins.get(user_id)

    def put(self, user_id: str, twin: DigitalTwin) -> None:
        with self._lock:
            self._twins[user_id] = twin

    def drop(self, user_id: str) -> None:
        with self._lock:
            self._twins.pop(user_id, None)

    def clear(self) -> None:
        with self._lock:
            self._twins.clear()


_REGISTRY = _TwinRegistry()


def get_registry() -> _TwinRegistry:
    """Return the module-level twin registry (used by tests for cleanup)."""

    return _REGISTRY


# ---------------------------------------------------------------------------
# Pydantic input schemas
# ---------------------------------------------------------------------------


TwinModeLiteral = Literal[
    "free_chat",
    "auto_reply",
    "business_24_7",
    "vacation",
    "predict_response",
    "negotiate",
]

DisclosureLanguageLiteral = Literal["ro", "ru", "en"]


class ChatRequest(BaseModel):
    """Body schema for ``POST /<user_id>/chat``."""

    message: str = Field(..., min_length=1, max_length=10_000)
    mode: TwinModeLiteral = Field(default="free_chat")
    language: DisclosureLanguageLiteral = Field(default="ro")
    context: str | None = Field(default=None, max_length=4_000)

    @field_validator("message")
    @classmethod
    def _strip_message(cls, v: str) -> str:
        v2 = v.strip()
        if not v2:
            raise ValueError("message must not be empty after stripping whitespace")
        return v2


class ProfileRequest(BaseModel):
    """Body schema for ``POST /<user_id>/profile`` — builds a SelfProfile.

    ``user_id`` from the body is ignored if present — the URL ``user_id`` wins.
    """

    name: str = Field(..., min_length=1, max_length=200)
    username: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=2_000)
    self_summary: str | None = Field(default=None, max_length=4_000)
    own_messages: list[str] = Field(default_factory=list)
    language: DisclosureLanguageLiteral = Field(default="ro")
    custom_notes: str = Field(default="", max_length=4_000)
    interests: list[str] = Field(default_factory=list)
    profession: str | None = Field(default=None, max_length=200)
    last_message_date: str | None = Field(default=None, max_length=64)
    vacation_message: str | None = Field(default=None, max_length=1_000)

    @field_validator("own_messages")
    @classmethod
    def _trim_messages(cls, v: list[str]) -> list[str]:
        # Cap at 200 to keep the LLM prompt bounded.
        if len(v) > 200:
            raise ValueError("own_messages must contain at most 200 entries")
        return [m for m in v if isinstance(m, str)]


class RevokeRequest(BaseModel):
    """Body schema for ``POST /<user_id>/revoke``."""

    reason: str = Field(default="user_requested", max_length=500)


class AttestRequest(BaseModel):
    """Body schema for ``POST /<user_id>/attest``.

    Sprint 6 will plug full MSign signature verification in here. For now
    we accept the signature blob and stash it on the AgentProfile so the
    rest of the response pipeline can flip the ``verified`` flag.
    """

    issuer: str = Field(default="self", max_length=200)
    subject_did: str = Field(..., min_length=3, max_length=400)
    signature: str = Field(..., min_length=8, max_length=8_192)
    signature_alg: str = Field(default="EdDSA", max_length=40)
    issued_at: str | None = Field(default=None, max_length=64)
    expires_at: str | None = Field(default=None, max_length=64)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _envelope(
    *,
    ok: bool,
    data: Any = None,
    error: str | None = None,
    status: int = 200,
    extra_headers: dict[str, str] | None = None,
) -> tuple[Response, int]:
    """Wrap a payload in the canonical ``{ok, data, error}`` envelope."""

    body: dict[str, Any] = {"ok": ok, "data": data, "error": error}
    resp = jsonify(body)
    if extra_headers:
        for k, v in extra_headers.items():
            resp.headers[k] = v
    return resp, status


def _validation_error(exc: ValidationError) -> tuple[Response, int]:
    # `errors(include_url=False)` can embed raw Exception objects under
    # `ctx.error` which json.dumps refuses to serialise. Stringify defensively.
    safe_details: list[dict[str, Any]] = []
    for err in exc.errors(include_url=False):
        safe = {k: v for k, v in err.items() if k != "ctx"}
        ctx = err.get("ctx")
        if isinstance(ctx, dict):
            safe["ctx"] = {ck: (str(cv) if isinstance(cv, Exception) else cv) for ck, cv in ctx.items()}
        safe_details.append(safe)
    return _envelope(
        ok=False,
        error="validation_failed",
        data={"details": safe_details},
        status=400,
    )


def _msg_fingerprint(message: str) -> str:
    """A PII-safe fingerprint for log lines (length + sha256 prefix)."""

    digest = hashlib.sha256(message.encode("utf-8", "replace")).hexdigest()[:12]
    return f"len={len(message)} sha256={digest}"


def _client_identifier(user_id: str) -> str:
    """Stable identifier for rate-limit bucket: user_id + remote IP."""

    remote = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or "unknown"
    return f"{user_id}|{remote}"


def _get_llm_client():
    """Resolve the LLMClient: test override via app config, else lazy real one."""

    override = current_app.config.get("LLM_CLIENT") if current_app else None
    if override is not None:
        return override
    # Lazy-construct so importing this module never opens a network client.
    from ..llm.client import LLMClient

    return LLMClient()


def _expected_token() -> str:
    return os.getenv("TWIN_INTERNAL_TOKEN") or os.getenv("EEVIDENCE_INTERNAL_TOKEN", "")


def require_internal_token(func: Callable[..., Any]) -> Callable[..., Any]:
    """Reject requests missing or mismatched on the internal-only header."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        expected = _expected_token()
        if not expected:
            return _envelope(
                ok=False,
                error="internal_token_not_configured",
                status=503,
            )
        provided = request.headers.get("X-MDChat-Internal-Token", "")
        if not hmac.compare_digest(provided, expected):
            return _envelope(ok=False, error="unauthorized", status=401)
        return func(*args, **kwargs)

    return wrapper


def _build_self_profile(user_id: str, body: ProfileRequest) -> SelfProfile:
    return SelfProfile(
        user_id=user_id,
        name=body.name,
        username=body.username,
        bio=body.bio,
        self_summary=body.self_summary,
        own_messages=list(body.own_messages),
        language=body.language,
        custom_notes=body.custom_notes,
        interests=list(body.interests),
        profession=body.profession,
        last_message_date=body.last_message_date,
        vacation_message=body.vacation_message,
    )


def _build_agent_profile(user_id: str, body: ProfileRequest) -> AgentProfile:
    """Minimal AgentProfile so the twin can carry attestation later.

    The full enrichment (Big Five, decision factors, etc.) is produced by
    ``MdChatProfileGenerator`` in a separate batch pipeline.
    """

    # ``agent_id`` is a numeric handle on AgentProfile; we hash user_id into
    # a stable int so re-creating the profile yields the same handle.
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    agent_id = int(digest[:12], 16)
    return AgentProfile(
        agent_id=agent_id,
        username=body.username or user_id,
        display_name=body.name,
        bio=body.bio or "",
        persona=body.self_summary or "",
        profession=body.profession,
        interests=list(body.interests),
        language=body.language,
        message_count=len(body.own_messages),
        source_user_id=user_id,
    )


def _twin_profile_view(twin: DigitalTwin) -> dict[str, Any]:
    """Read-only projection of the twin profile for ``GET /profile``."""

    p = twin.profile
    return {
        "user_id": p.user_id,
        "name": p.name,
        "username": p.username,
        "bio": p.bio,
        "self_summary": p.self_summary,
        "language": p.language,
        "custom_notes": p.custom_notes,
        "interests": list(p.interests),
        "profession": p.profession,
        "last_message_date": p.last_message_date,
        "vacation_message": p.vacation_message,
        "own_messages_count": len(p.own_messages),
        "confidence_score": twin.confidence_score,
        "is_revoked": twin.is_revoked,
        "verified": bool(
            twin.agent_profile
            and twin.agent_profile.attestation
            and twin.agent_profile.attestation.is_valid()
        ),
        "agent_profile": twin.agent_profile.to_dict() if twin.agent_profile else None,
    }


def _serialize_chat_response(response, language: str) -> dict[str, Any]:
    """Serialize TwinResponse + add a top-level mirror of the AI Act disclosure."""

    payload = response.model_dump(mode="json")
    # Belt-and-braces: even if a downstream consumer dives straight for
    # `data.text`, surface the disclosure as a sibling field so AI Act Art 50
    # cannot be silently stripped.
    disclosure = payload.get("disclosure") or TwinDisclosure.for_language(language).model_dump(mode="json")
    disclosure_singleton = get_disclosure()
    disclosure["eu_ai_act_art50"] = True
    disclosure["ai_system"] = "md-chat-twin"
    disclosure["is_ai_generated"] = True
    # Backfill text from the singleton if for some reason it was empty.
    if not disclosure.get("text"):
        disclosure["text"] = disclosure_singleton.disclosure_text(language)
    return {
        "response": payload,
        "disclosure": disclosure,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.post("/<user_id>/chat")
def chat(user_id: str):
    """Send a message to the user's digital twin and return a TwinResponse."""

    # 1. Parse / validate body.
    raw = request.get_json(silent=True) or {}
    try:
        body = ChatRequest.model_validate(raw)
    except ValidationError as exc:
        return _validation_error(exc)

    # 2. Look up the twin.
    twin = _REGISTRY.get(user_id)
    if twin is None:
        return _envelope(ok=False, error="twin_not_found", status=404)
    if twin.is_revoked:
        return _envelope(ok=False, error="twin_revoked", status=410)

    # 3. Rate limit by (user, IP).
    limiter = get_limiter()
    rl = limiter.check("twin-chat", _client_identifier(user_id))
    if not rl.allowed:
        return _envelope(
            ok=False,
            error="rate_limited",
            data=rl.as_dict(),
            status=429,
            extra_headers={"Retry-After": str(int(rl.retry_after) + 1)},
        )

    # 4. Wire the right LLM client (test override or lazy real).
    if twin._llm_client is None:  # noqa: SLF001 — public attr not exposed
        twin._llm_client = _get_llm_client()  # noqa: SLF001

    # 5. Run the twin. Never log the message content itself.
    logger.info(
        "twin.chat user=%s mode=%s lang=%s fp=[%s]",
        user_id,
        body.mode,
        body.language,
        _msg_fingerprint(body.message),
    )
    try:
        response = twin.chat(
            message=body.message,
            mode=body.mode,
            context=body.context,
            disclosure_language=body.language,
        )
    except TwinRevokedError:
        return _envelope(ok=False, error="twin_revoked", status=410)
    except Exception as exc:  # noqa: BLE001
        logger.exception("twin.chat failed user=%s: %s", user_id, exc)
        return _envelope(ok=False, error="twin_chat_failed", status=500)

    return _envelope(
        ok=True,
        data=_serialize_chat_response(response, body.language),
        status=200,
    )


@bp.get("/<user_id>/profile")
def get_profile(user_id: str):
    """Return the twin profile (read-only)."""

    twin = _REGISTRY.get(user_id)
    if twin is None:
        return _envelope(ok=False, error="twin_not_found", status=404)
    return _envelope(ok=True, data=_twin_profile_view(twin), status=200)


@bp.post("/<user_id>/profile")
def upsert_profile(user_id: str):
    """Create or update the twin profile for ``user_id``."""

    raw = request.get_json(silent=True) or {}
    try:
        body = ProfileRequest.model_validate(raw)
    except ValidationError as exc:
        return _validation_error(exc)

    self_profile = _build_self_profile(user_id, body)
    agent_profile = _build_agent_profile(user_id, body)

    existing = _REGISTRY.get(user_id)
    if existing is None:
        twin = DigitalTwin(
            profile=self_profile,
            agent_profile=agent_profile,
            llm_client=_get_llm_client(),
            default_disclosure_language=body.language,
        )
        _REGISTRY.put(user_id, twin)
        status = 201
        action = "created"
    else:
        if existing.is_revoked:
            return _envelope(ok=False, error="twin_revoked", status=410)
        existing.refresh_profile(self_profile, agent_profile)
        twin = existing
        status = 200
        action = "updated"

    logger.info("twin.profile %s user=%s confidence=%.2f", action, user_id, twin.confidence_score)
    return _envelope(ok=True, data=_twin_profile_view(twin), status=status)


@bp.post("/<user_id>/revoke")
def revoke(user_id: str):
    """Revoke the twin (AI Act Art 22 — right not to be subject to automation)."""

    twin = _REGISTRY.get(user_id)
    if twin is None:
        return _envelope(ok=False, error="twin_not_found", status=404)

    raw = request.get_json(silent=True) or {}
    try:
        body = RevokeRequest.model_validate(raw)
    except ValidationError as exc:
        return _validation_error(exc)

    if not twin.is_revoked:
        twin.revoke(reason=body.reason)
    logger.info("twin.revoke user=%s reason=%s", user_id, body.reason)
    return _envelope(ok=True, data=None, status=204)


@bp.get("/<user_id>/audit-log")
@require_internal_token
def audit_log(user_id: str):
    """Return the last 100 audit-log entries for the twin (compliance review)."""

    twin = _REGISTRY.get(user_id)
    if twin is None:
        return _envelope(ok=False, error="twin_not_found", status=404)
    entries = [e.to_dict() for e in list(twin.audit_log)[-100:]]
    return _envelope(
        ok=True,
        data={
            "user_id": user_id,
            "count": len(entries),
            "entries": entries,
            "is_revoked": twin.is_revoked,
        },
        status=200,
    )


@bp.post("/<user_id>/attest")
def attest(user_id: str):
    """eIDAS-attest the twin profile (Sprint 6 stub).

    Today: validates the input, stashes the attestation on the twin and
    returns 202 Accepted. Full MSign signature verification + QTSP chain
    landing in Sprint 6.
    """

    twin = _REGISTRY.get(user_id)
    if twin is None:
        return _envelope(ok=False, error="twin_not_found", status=404)
    if twin.is_revoked:
        return _envelope(ok=False, error="twin_revoked", status=410)
    if twin.agent_profile is None:
        return _envelope(
            ok=False,
            error="agent_profile_missing",
            data={"hint": "POST /profile first so attestation has a carrier"},
            status=409,
        )

    raw = request.get_json(silent=True) or {}
    try:
        body = AttestRequest.model_validate(raw)
    except ValidationError as exc:
        return _validation_error(exc)

    attestation = VerifiedAttestation(
        issuer=body.issuer,
        subject_did=body.subject_did,
        signature_alg=body.signature_alg,
        signature=body.signature,
        issued_at=body.issued_at,
        expires_at=body.expires_at,
    )
    twin.attach_attestation(attestation)
    logger.info(
        "twin.attest user=%s issuer=%s alg=%s valid=%s",
        user_id,
        body.issuer,
        body.signature_alg,
        attestation.is_valid(),
    )
    return _envelope(
        ok=True,
        data={
            "attestation": attestation.to_dict(),
            "verified": attestation.is_valid(),
            "verification_pending_sprint6": True,
        },
        status=202,
    )


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _set_twin_chat_limit(capacity: int, window_seconds: float) -> None:
    """Test-only hook: tighten the twin-chat namespace for burst tests."""

    get_limiter().set_namespace("twin-chat", NamespaceLimit(capacity, window_seconds))
