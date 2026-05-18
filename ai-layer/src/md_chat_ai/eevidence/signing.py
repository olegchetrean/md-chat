"""Ed25519 / JWS signing wrapper for the eEvidence audit log.

We do **not** mutate :class:`md_chat_ai.eevidence.audit.AuditEntry`. Instead,
this module composes a :class:`SignedAuditEntry` that carries:

* the original ``AuditEntry`` (unchanged, hash-chained — see ``audit.py``),
* a JWS (RFC 7515) compact serialization signing a canonical projection of the
  entry's load-bearing fields,
* the ``kid`` of the public key needed to verify.

The signature input is:

    entry_id || sha256_chain_hash || timestamp_iso8601 || event_type ||
    payload_json_canonical

Where:

* ``entry_id`` = the entry's monotonic sequence number (decimal string).
* ``sha256_chain_hash`` = ``entry.entry_hash`` (the chain hash already computed
  by ``audit.AuditRegister``).
* ``timestamp_iso8601`` = ``entry.timestamp``.
* ``event_type`` = ``entry.event_type``.
* ``payload_json_canonical`` = canonical JSON of
  ``{ticket_id, actor, details}`` — UTF-8 NFC normalized, sorted keys, no
  whitespace (RFC 8785-style canonicalisation but constrained to the audit
  payload subset; full RFC 8785 has corner cases we do not need).

The JWS payload itself is a JSON object embedding all those fields so the
verifier can reconstruct the input without consulting our database.
``alg = EdDSA``, ``typ = "mdchat-audit+jws"``.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import base64
import json
import unicodedata
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .audit import AuditEntry
from .keys import KeyNotFoundError, KeyStore

# RFC 7515 §4.1.9: ``typ`` is a hint for the application that consumes the JWS.
JWS_TYP = "mdchat-audit+jws"
JWS_ALG = "EdDSA"


# ---------------------------------------------------------------------------
# Canonical JSON
# ---------------------------------------------------------------------------


def _nfc(value: Any) -> Any:
    """Recursively Unicode-NFC-normalize all strings inside a JSON tree."""

    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, dict):
        return {_nfc(k): _nfc(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_nfc(v) for v in value]
    if isinstance(value, tuple):
        return [_nfc(v) for v in value]
    return value


def canonical_json(payload: dict[str, Any]) -> bytes:
    """Deterministic, whitespace-free, NFC-normalized JSON encoding.

    * Keys sorted lexicographically at every level.
    * No whitespace anywhere (``separators=(",", ":")``).
    * Non-ASCII preserved as-is (``ensure_ascii=False``) after NFC normalize.
    * UTF-8 encoded.

    This implementation is **not** RFC 8785 — JCS handles number canonicalisation
    that we do not need (we only emit integers and strings). It *is* stable
    across CPython 3.11+ runs: ``json.dumps`` is deterministic for a given
    input under ``sort_keys=True``.
    """

    normalized = _nfc(payload)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Base64url helpers (RFC 7515 §2)
# ---------------------------------------------------------------------------


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(token: str) -> bytes:
    padding = "=" * (-len(token) % 4)
    return base64.urlsafe_b64decode(token + padding)


# ---------------------------------------------------------------------------
# Signed entry data class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignedAuditEntry:
    """An :class:`AuditEntry` plus an Ed25519 JWS over its canonical projection.

    Frozen — both the underlying entry and the signature are immutable.
    """

    entry: AuditEntry
    """The original hash-chained audit entry."""

    kid: str
    """Key identifier (kid) of the signing key."""

    jws: str
    """RFC 7515 compact-serialisation JWS: ``<header>.<payload>.<signature>``."""

    def to_dict(self) -> dict[str, Any]:
        return {"entry": self.entry.to_dict(), "kid": self.kid, "jws": self.jws}


# ---------------------------------------------------------------------------
# Verification result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of verifying a :class:`SignedAuditEntry`."""

    valid: bool
    reason: str = ""

    def __bool__(self) -> bool:
        return self.valid


# ---------------------------------------------------------------------------
# Signature payload builder
# ---------------------------------------------------------------------------


def _build_payload(entry: AuditEntry) -> dict[str, Any]:
    """Return the dict that ends up inside the JWS payload."""

    return {
        "entry_id": str(entry.sequence),
        "sha256_chain_hash": entry.entry_hash,
        "timestamp_iso8601": entry.timestamp,
        "event_type": entry.event_type,
        "payload_json_canonical": canonical_json(
            {
                "ticket_id": entry.ticket_id,
                "actor": entry.actor,
                "details": dict(entry.details),
            }
        ).decode("utf-8"),
    }


def _build_signing_input(entry: AuditEntry) -> tuple[str, str, dict[str, Any]]:
    """Build header + payload + canonical JSON payload for an entry."""

    payload = _build_payload(entry)
    return JWS_TYP, JWS_ALG, payload


# ---------------------------------------------------------------------------
# Sign
# ---------------------------------------------------------------------------


def sign_entry(entry: AuditEntry, keystore: KeyStore) -> SignedAuditEntry:
    """Sign an :class:`AuditEntry` with the currently-active key in ``keystore``.

    Produces a compact-serialisation JWS as defined in RFC 7515 §7.1.
    """

    active = keystore.active()
    if active.private_key is None:
        raise RuntimeError(
            f"Active kid {active.kid!r} has no private key loaded — "
            "this keystore is verify-only and cannot sign new entries."
        )
    return _sign_with_key(entry, kid=active.kid, private_key=active.private_key)


def _sign_with_key(
    entry: AuditEntry,
    *,
    kid: str,
    private_key: Ed25519PrivateKey,
) -> SignedAuditEntry:
    typ, alg, payload = _build_signing_input(entry)
    header = {"alg": alg, "typ": typ, "kid": kid}

    header_b64 = _b64url_encode(canonical_json(header))
    payload_b64 = _b64url_encode(canonical_json(payload))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = private_key.sign(signing_input)
    sig_b64 = _b64url_encode(signature)

    jws = f"{header_b64}.{payload_b64}.{sig_b64}"
    return SignedAuditEntry(entry=entry, kid=kid, jws=jws)


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def verify_signed_entry(signed: SignedAuditEntry, keystore: KeyStore) -> VerificationResult:
    """Verify a :class:`SignedAuditEntry` against ``keystore``.

    Returns a :class:`VerificationResult`. The ``valid`` flag is ``False`` if
    *any* of the following fails:

    * The JWS is structurally malformed.
    * The ``kid`` is unknown to the keystore.
    * The Ed25519 signature does not verify against the public key for that kid.
    * The JWS payload does not match what we would re-derive from
      ``signed.entry`` (i.e. the entry has been tampered with after signing).
    * The underlying entry's own ``entry_hash`` does not recompute (sanity
      defence — the chain integrity is the audit module's job, but a verifier
      that only sees a single signed entry still wants this check).
    """

    return verify_jws(signed.jws, expected_entry=signed.entry, keystore=keystore)


def verify_jws(
    jws: str,
    *,
    expected_entry: AuditEntry | None,
    keystore: KeyStore,
) -> VerificationResult:
    """Verify a compact-serialisation JWS produced by :func:`sign_entry`.

    If ``expected_entry`` is given, the decoded JWS payload is compared
    field-by-field against the entry. Pass ``None`` only when verifying a
    JWS produced by another party where you trust the embedded payload — in
    our codepath this is always called *with* an ``expected_entry``.
    """

    parts = jws.split(".")
    if len(parts) != 3:
        return VerificationResult(False, "malformed_jws_segments")

    header_b64, payload_b64, sig_b64 = parts

    try:
        header_raw = _b64url_decode(header_b64)
        payload_raw = _b64url_decode(payload_b64)
        signature = _b64url_decode(sig_b64)
    except Exception:
        return VerificationResult(False, "malformed_jws_base64")

    try:
        header = json.loads(header_raw.decode("utf-8"))
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception:
        return VerificationResult(False, "malformed_jws_json")

    if header.get("alg") != JWS_ALG:
        return VerificationResult(False, f"unsupported_alg:{header.get('alg')!r}")
    if header.get("typ") != JWS_TYP:
        return VerificationResult(False, f"unexpected_typ:{header.get('typ')!r}")

    kid = header.get("kid")
    if not kid:
        return VerificationResult(False, "missing_kid")

    try:
        record = keystore.get(kid)
    except KeyNotFoundError:
        return VerificationResult(False, f"unknown_kid:{kid}")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    try:
        record.public_key.verify(signature, signing_input)
    except InvalidSignature:
        return VerificationResult(False, "ed25519_invalid_signature")
    except Exception as exc:  # pragma: no cover — defensive
        return VerificationResult(False, f"verify_error:{type(exc).__name__}")

    if expected_entry is not None:
        # Confirm chain integrity for the standalone entry.
        if not expected_entry.verify():
            return VerificationResult(False, "entry_chain_hash_mismatch")

        # Confirm the JWS payload describes the entry we think it does.
        rebuilt = _build_payload(expected_entry)
        for key, expected in rebuilt.items():
            if payload.get(key) != expected:
                return VerificationResult(False, f"payload_field_mismatch:{key}")

    return VerificationResult(True, "ok")


# ---------------------------------------------------------------------------
# pyjwt interop: some auditors prefer the canonical pyjwt API
# ---------------------------------------------------------------------------


def verify_with_public_key(
    jws: str,
    public_key: Ed25519PublicKey,
) -> VerificationResult:
    """Verify using a raw Ed25519 public key (no keystore lookup).

    Useful for third-party auditors who only have the published JWK / PEM and
    don't want to build a :class:`KeyStore`. They can construct an
    :class:`Ed25519PublicKey` from the JWK via
    :func:`md_chat_ai.eevidence.keys.public_key_from_jwk` and pass it here.
    """

    parts = jws.split(".")
    if len(parts) != 3:
        return VerificationResult(False, "malformed_jws_segments")
    header_b64, payload_b64, sig_b64 = parts
    try:
        signature = _b64url_decode(sig_b64)
    except Exception:
        return VerificationResult(False, "malformed_jws_base64")
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    try:
        public_key.verify(signature, signing_input)
    except InvalidSignature:
        return VerificationResult(False, "ed25519_invalid_signature")
    return VerificationResult(True, "ok")


__all__ = [
    "JWS_ALG",
    "JWS_TYP",
    "SignedAuditEntry",
    "VerificationResult",
    "canonical_json",
    "sign_entry",
    "verify_jws",
    "verify_signed_entry",
    "verify_with_public_key",
]
