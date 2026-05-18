"""PIN-derived key wrapping — Signal SVR3-pattern stub.

Background:
    Signal's Secure Value Recovery v3 (SVR3) protects a user's master key
    behind a low-entropy PIN by deriving a wrapping key with Argon2id and
    splitting/attesting trust across multiple TEEs (Intel SGX, AWS Nitro,
    Apple Secure Enclave). This file implements ONLY the local PIN-derived
    wrap/unwrap step. The multi-TEE attestation + secret-share splitting
    is a separate (future) module.

This module:
    1. Derives a 32-byte wrapping key from PIN + per-user salt using Argon2id
       (high cost parameters appropriate for client-side execution).
    2. Wraps the user's identity/private material with AES-256-GCM
       (authenticated encryption; tag prevents tampering).
    3. Unwraps only with the correct PIN — any tampering or wrong PIN
       raises ``InvalidPin``.

GDPR:
    The server SHOULD store only ``(salt, nonce, ciphertext, kdf_params)``.
    The PIN itself never leaves the client (in the full SVR3 design) and
    in this stub we only ever receive it transiently for wrap/unwrap.

Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
from dataclasses import dataclass

from argon2.exceptions import VerifyMismatchError  # noqa: F401  (re-export shape)
from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Argon2id parameters — tuned for client-side cost.
# 64 MB memory, 3 iterations, 4 lanes is OWASP's 2023 recommended baseline.
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST_KIB = 64 * 1024  # 64 MiB
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32  # AES-256 wrapping key
ARGON2_SALT_LEN = 16

AES_KEY_LEN = 32
AES_NONCE_LEN = 12


class InvalidPin(Exception):
    """Raised when unwrap fails (wrong PIN, tampered ciphertext, etc.)."""


@dataclass
class WrappedBundle:
    """Persisted blob. All fields are base64url-encoded ASCII strings."""

    salt: str
    nonce: str
    ciphertext: str
    # KDF parameters frozen at wrap-time so a future tuning change doesn't
    # break existing bundles.
    kdf_time_cost: int = ARGON2_TIME_COST
    kdf_memory_cost: int = ARGON2_MEMORY_COST_KIB
    kdf_parallelism: int = ARGON2_PARALLELISM

    def to_json(self) -> str:
        return json.dumps(
            {
                "v": 1,
                "salt": self.salt,
                "nonce": self.nonce,
                "ciphertext": self.ciphertext,
                "kdf": {
                    "t": self.kdf_time_cost,
                    "m": self.kdf_memory_cost,
                    "p": self.kdf_parallelism,
                },
            },
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, data: str) -> WrappedBundle:
        obj = json.loads(data)
        kdf = obj.get("kdf", {})
        return cls(
            salt=obj["salt"],
            nonce=obj["nonce"],
            ciphertext=obj["ciphertext"],
            kdf_time_cost=int(kdf.get("t", ARGON2_TIME_COST)),
            kdf_memory_cost=int(kdf.get("m", ARGON2_MEMORY_COST_KIB)),
            kdf_parallelism=int(kdf.get("p", ARGON2_PARALLELISM)),
        )


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _derive_key(
    pin: str,
    salt: bytes,
    *,
    time_cost: int = ARGON2_TIME_COST,
    memory_cost: int = ARGON2_MEMORY_COST_KIB,
    parallelism: int = ARGON2_PARALLELISM,
) -> bytes:
    if not pin:
        raise InvalidPin("empty_pin")
    return hash_secret_raw(
        secret=pin.encode("utf-8"),
        salt=salt,
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
        hash_len=ARGON2_HASH_LEN,
        type=Type.ID,
    )


def wrap_keys(pin: str, plaintext_keys: bytes) -> WrappedBundle:
    """Encrypt ``plaintext_keys`` under a PIN-derived key.

    ``plaintext_keys`` is opaque to this module — typically a serialized
    identity keypair or Signal master key.
    """
    if not isinstance(plaintext_keys, (bytes, bytearray)):
        raise TypeError("plaintext_keys must be bytes")
    salt = os.urandom(ARGON2_SALT_LEN)
    key = _derive_key(pin, salt)
    nonce = secrets.token_bytes(AES_NONCE_LEN)
    ct = AESGCM(key).encrypt(nonce, bytes(plaintext_keys), associated_data=b"md-chat-pin-v1")
    return WrappedBundle(salt=_b64(salt), nonce=_b64(nonce), ciphertext=_b64(ct))


def unwrap_keys(pin: str, bundle: WrappedBundle) -> bytes:
    """Decrypt a bundle, returning the original plaintext.

    Raises ``InvalidPin`` on any failure (wrong PIN, tampered ciphertext).
    """
    try:
        salt = _b64d(bundle.salt)
        nonce = _b64d(bundle.nonce)
        ct = _b64d(bundle.ciphertext)
    except (ValueError, KeyError) as exc:
        raise InvalidPin(f"malformed_bundle:{exc}") from exc

    key = _derive_key(
        pin,
        salt,
        time_cost=bundle.kdf_time_cost,
        memory_cost=bundle.kdf_memory_cost,
        parallelism=bundle.kdf_parallelism,
    )
    try:
        return AESGCM(key).decrypt(nonce, ct, associated_data=b"md-chat-pin-v1")
    except Exception as exc:  # cryptography raises InvalidTag, etc.
        raise InvalidPin("unwrap_failed") from exc


# ---------------------------------------------------------------------------
# Minimal in-memory persistence (per-user). Replace with Postgres in prod.
# ---------------------------------------------------------------------------


_pin_store: dict[str, str] = {}


def store_bundle(user_id: str, bundle: WrappedBundle) -> None:
    _pin_store[user_id] = bundle.to_json()


def load_bundle(user_id: str) -> WrappedBundle | None:
    raw = _pin_store.get(user_id)
    return WrappedBundle.from_json(raw) if raw else None


def reset_store() -> None:
    _pin_store.clear()
