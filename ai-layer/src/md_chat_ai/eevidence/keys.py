"""Ed25519 key management for the eEvidence audit log signing chain.

The audit register in :mod:`md_chat_ai.eevidence.audit` is hash-chained, so any
tampering is detectable by *anyone holding the chain*. That is not enough for a
court receiving a sealed evidence bundle under eEvidence Regulation Art. 33(5)
and Art. 31: the court must be able to verify the chain **without trusting our
server**. Therefore every entry is additionally signed with an Ed25519 private
key whose corresponding public key is published as a JWK so a third-party
auditor can verify with any RFC 7515 JWS-aware library.

Operational rules:

* Private keys live on disk as PEM (PKCS#8, unencrypted), permissions ``0600``,
  owner ``md-chat``. The :func:`load_private_key` function refuses to load a
  key whose permissions are looser than ``0600`` — this is a defence against
  accidental ``chmod 0644`` regressions that have historically caused
  CWE-732 incidents in deployed Python services.
* Each key has a *kid* (key identifier) that is recorded on every signature.
  When a key is rotated, the old kid is kept in the keystore so historical
  signatures remain verifiable. Only the *current* kid is used for new
  signatures.
* No symmetric secrets are stored here — Ed25519 verification only requires
  the public key, which is safe to publish.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import base64
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

# Maximum permissions tolerated on a private-key file. ``0600`` = owner rw, no
# group, no world. We compare via bitwise AND so that a key file installed
# with ``0400`` (read-only) is *also* accepted (it is strictly stricter).
_MAX_KEY_PERMS = 0o077  # any bit set outside owner-rw is rejected
_ALLOWED_OWNER_PERMS = 0o600  # owner read+write only


class KeyPermissionsError(RuntimeError):
    """Raised when a private key file has unsafe filesystem permissions."""


class KeyNotFoundError(RuntimeError):
    """Raised when a key file (or kid) cannot be located."""


# ---------------------------------------------------------------------------
# Ed25519 keypair generation
# ---------------------------------------------------------------------------


def generate_keypair() -> Ed25519PrivateKey:
    """Generate a fresh Ed25519 keypair.

    Returns the private key object; the corresponding public key is obtained
    via :meth:`Ed25519PrivateKey.public_key`.
    """

    return Ed25519PrivateKey.generate()


def serialize_private_key(key: Ed25519PrivateKey) -> bytes:
    """Serialize a private key to unencrypted PKCS#8 PEM."""

    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def serialize_public_key(key: Ed25519PublicKey) -> bytes:
    """Serialize a public key to SubjectPublicKeyInfo PEM."""

    return key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def write_private_key(path: str | os.PathLike[str], key: Ed25519PrivateKey) -> Path:
    """Write a private key to ``path`` with ``0600`` permissions.

    The file is created with mode ``0600`` from the outset by using a
    low-level ``os.open`` with explicit mode bits — avoiding the
    open-then-chmod TOCTOU window during which a reader on a multi-tenant
    host could grab the unencrypted key.
    """

    pem = serialize_private_key(key)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # Remove any pre-existing file first so umask races cannot widen perms.
    if target.exists():
        target.unlink()

    fd = os.open(
        str(target),
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        _ALLOWED_OWNER_PERMS,
    )
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(pem)
    except Exception:
        # Best-effort cleanup so we never leave half-written key material on disk.
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        raise

    # Belt-and-suspenders: enforce mode after write in case the filesystem
    # ignored the ``mode`` argument to ``os.open`` (some network filesystems).
    os.chmod(target, _ALLOWED_OWNER_PERMS)
    return target


def _check_permissions(path: Path) -> None:
    """Raise :class:`KeyPermissionsError` if ``path`` is group/world accessible."""

    info = path.stat()
    mode = stat.S_IMODE(info.st_mode)
    if mode & _MAX_KEY_PERMS:
        raise KeyPermissionsError(
            f"Refusing to load private key {path}: permissions {oct(mode)} are too "
            f"permissive (expected {oct(_ALLOWED_OWNER_PERMS)} or stricter). "
            f"Fix with: chmod 0600 {path}"
        )


def load_private_key(path: str | os.PathLike[str]) -> Ed25519PrivateKey:
    """Load an Ed25519 private key from PEM on disk after permission check."""

    target = Path(path)
    if not target.exists():
        raise KeyNotFoundError(f"Private key not found: {target}")
    _check_permissions(target)

    pem = target.read_bytes()
    key = serialization.load_pem_private_key(pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError(
            f"Key at {target} is not Ed25519 (got {type(key).__name__}). "
            "Audit-log signing requires Ed25519 per RFC 8032."
        )
    return key


def derive_public_key(private_key: Ed25519PrivateKey) -> Ed25519PublicKey:
    """Convenience wrapper, kept for API symmetry with verification flows."""

    return private_key.public_key()


# ---------------------------------------------------------------------------
# JWK (RFC 7517) encoding for the EdDSA / OKP curve = Ed25519
# ---------------------------------------------------------------------------


def _b64url(data: bytes) -> str:
    """Base64-url-safe without padding (RFC 7515 §2)."""

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def public_jwk(public_key: Ed25519PublicKey, kid: str) -> dict[str, str]:
    """Return the RFC 8037 JWK representation of an Ed25519 public key."""

    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "alg": "EdDSA",
        "use": "sig",
        "kid": kid,
        "x": _b64url(raw),
    }


def public_jwk_from_pem(pem: bytes, kid: str) -> dict[str, str]:
    """Build a JWK from a PEM-encoded public key (for /jwks endpoints)."""

    key = serialization.load_pem_public_key(pem)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("Public key in PEM is not Ed25519")
    return public_jwk(key, kid=kid)


def public_key_from_jwk(jwk: dict[str, Any]) -> Ed25519PublicKey:
    """Inverse of :func:`public_jwk` — used in verifier flows / unit tests."""

    if jwk.get("kty") != "OKP" or jwk.get("crv") != "Ed25519":
        raise ValueError("JWK is not an Ed25519 OKP key")
    raw_b64 = jwk.get("x")
    if not raw_b64:
        raise ValueError("JWK missing 'x' parameter")
    # Re-pad before decoding.
    padding = "=" * (-len(raw_b64) % 4)
    raw = base64.urlsafe_b64decode(raw_b64 + padding)
    return Ed25519PublicKey.from_public_bytes(raw)


# ---------------------------------------------------------------------------
# Keystore — multi-kid support for rotation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KeyRecord:
    """A loaded keypair plus its kid."""

    kid: str
    private_key: Ed25519PrivateKey | None  # None = verify-only entry
    public_key: Ed25519PublicKey


class KeyStore:
    """In-memory registry of all known audit-signing keys.

    A single :class:`KeyStore` holds *one* currently-active signing kid plus
    any number of retired-but-still-trusted public keys. New entries are
    signed with the active kid; old entries can be verified as long as their
    kid is anywhere in the store.
    """

    def __init__(self) -> None:
        self._records: dict[str, KeyRecord] = {}
        self._active_kid: str | None = None

    # ----------------------------------------------------------- registration

    def register_signing_key(self, kid: str, private_key: Ed25519PrivateKey) -> None:
        """Register a private key and make it the active signer."""

        if not kid:
            raise ValueError("kid must be a non-empty string")
        self._records[kid] = KeyRecord(
            kid=kid,
            private_key=private_key,
            public_key=private_key.public_key(),
        )
        self._active_kid = kid

    def register_verify_only(self, kid: str, public_key: Ed25519PublicKey) -> None:
        """Register a retired key — verify-only, never used for new signatures."""

        if not kid:
            raise ValueError("kid must be a non-empty string")
        # Preserve any existing private material so re-registration as
        # verify-only after rotation does not destroy it.
        existing = self._records.get(kid)
        priv = existing.private_key if existing else None
        self._records[kid] = KeyRecord(kid=kid, private_key=priv, public_key=public_key)

    def load_from_disk(self, kid: str, path: str | os.PathLike[str]) -> None:
        """Load a PEM private key and register it as the active signer."""

        priv = load_private_key(path)
        self.register_signing_key(kid, priv)

    def rotate(self, new_kid: str, new_private_key: Ed25519PrivateKey) -> None:
        """Promote a new kid to active; previous active kid stays verify-only."""

        if self._active_kid is not None:
            prev = self._records[self._active_kid]
            # Strip the private material from the previous record so a single
            # compromised process cannot continue signing with the retired key.
            self._records[self._active_kid] = KeyRecord(
                kid=prev.kid,
                private_key=None,
                public_key=prev.public_key,
            )
        self.register_signing_key(new_kid, new_private_key)

    # --------------------------------------------------------------- accessors

    @property
    def active_kid(self) -> str:
        if self._active_kid is None:
            raise RuntimeError("KeyStore has no active signing kid")
        return self._active_kid

    def active(self) -> KeyRecord:
        return self._records[self.active_kid]

    def get(self, kid: str) -> KeyRecord:
        try:
            return self._records[kid]
        except KeyError as exc:
            raise KeyNotFoundError(f"Unknown kid: {kid}") from exc

    def kids(self) -> list[str]:
        return list(self._records.keys())

    def jwks(self) -> dict[str, list[dict[str, str]]]:
        """JSON Web Key Set (RFC 7517) — safe to publish via an HTTP endpoint."""

        return {"keys": [public_jwk(rec.public_key, kid=rec.kid) for rec in self._records.values()]}


__all__ = [
    "KeyNotFoundError",
    "KeyPermissionsError",
    "KeyRecord",
    "KeyStore",
    "derive_public_key",
    "generate_keypair",
    "load_private_key",
    "public_jwk",
    "public_jwk_from_pem",
    "public_key_from_jwk",
    "serialize_private_key",
    "serialize_public_key",
    "write_private_key",
]
