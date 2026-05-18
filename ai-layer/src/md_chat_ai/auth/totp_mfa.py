"""TOTP MFA — RFC 6238 time-based one-time passwords for MD-Chat.

Wraps ``pyotp`` to:
- generate base32 secrets,
- emit ``otpauth://`` provisioning URIs (consumable by any authenticator),
- mint and verify single-use backup codes (scrypt-hashed at rest).

Backup codes are 8 alphanumeric characters, generated with ``secrets`` and
stored as scrypt hashes. Each verification consumes the matching hash.

Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import string
from collections.abc import Iterable
from dataclasses import dataclass, field

import pyotp

ISSUER = "MD-Chat"
BACKUP_CODE_COUNT = 8
BACKUP_CODE_LENGTH = 8
_BACKUP_CHARS = string.ascii_uppercase + string.digits
_BACKUP_SALT = b"md-chat-backup-code"
_TOTP_DIGITS = 6
_TOTP_INTERVAL = 30


def generate_secret() -> str:
    """Generate a base32 TOTP secret (32 chars = 160 bits)."""
    return pyotp.random_base32()


def provisioning_uri(secret: str, account_name: str) -> str:
    """Build an ``otpauth://totp/...`` URI suitable for QR-code rendering.

    Example: ``otpauth://totp/MD-Chat:user@example.com?secret=ABC...&issuer=MD-Chat``
    """
    totp = pyotp.TOTP(secret, digits=_TOTP_DIGITS, interval=_TOTP_INTERVAL)
    return totp.provisioning_uri(name=account_name, issuer_name=ISSUER)


def _scrypt_backup(code: str) -> str:
    return hashlib.scrypt(
        code.encode("ascii"),
        salt=_BACKUP_SALT,
        n=16384,
        r=8,
        p=1,
        dklen=32,
    ).hex()


def generate_backup_codes(
    count: int = BACKUP_CODE_COUNT,
    length: int = BACKUP_CODE_LENGTH,
) -> tuple[list[str], list[str]]:
    """Return ``(plain_codes, hashes)``.

    The caller MUST present ``plain_codes`` to the user exactly once and
    persist only ``hashes``.
    """
    plain: list[str] = []
    hashes: list[str] = []
    for _ in range(count):
        code = "".join(secrets.choice(_BACKUP_CHARS) for _ in range(length))
        plain.append(code)
        hashes.append(_scrypt_backup(code))
    return plain, hashes


def verify_totp(secret: str, code: str, *, valid_window: int = 1) -> bool:
    """Verify a 6-digit TOTP code. Accepts ``valid_window`` steps of skew."""
    if not code or not code.isdigit():
        return False
    totp = pyotp.TOTP(secret, digits=_TOTP_DIGITS, interval=_TOTP_INTERVAL)
    return totp.verify(code, valid_window=valid_window)


def verify_backup_code(code: str, remaining_hashes: list[str]) -> tuple[bool, list[str]]:
    """Check ``code`` against ``remaining_hashes``.

    On match, returns ``(True, new_remaining)`` with the matching hash removed
    (single-use). On miss, returns ``(False, remaining_hashes)`` unchanged.
    Uses constant-time comparison per candidate hash.
    """
    if not code:
        return False, remaining_hashes
    candidate = _scrypt_backup(code.strip().upper())
    for idx, h in enumerate(remaining_hashes):
        if hmac.compare_digest(candidate, h):
            new_list = remaining_hashes[:idx] + remaining_hashes[idx + 1 :]
            return True, new_list
    return False, remaining_hashes


# ---------------------------------------------------------------------------
# Convenience setup bundle.
# ---------------------------------------------------------------------------


@dataclass
class MfaSetupBundle:
    """Result of ``setup_mfa``. ``backup_codes`` is shown once to the user."""

    secret: str
    qr_uri: str
    backup_codes: list[str]
    backup_hashes: list[str] = field(default_factory=list)


def setup_mfa(account_name: str) -> MfaSetupBundle:
    """Mint a fresh secret + provisioning URI + backup codes for an account."""
    secret = generate_secret()
    uri = provisioning_uri(secret, account_name)
    plain, hashes = generate_backup_codes()
    return MfaSetupBundle(secret=secret, qr_uri=uri, backup_codes=plain, backup_hashes=hashes)


def now_code(secret: str) -> str:
    """Return the TOTP code for *right now*. Useful for tests."""
    return pyotp.TOTP(secret, digits=_TOTP_DIGITS, interval=_TOTP_INTERVAL).now()


def hash_backup_codes(codes: Iterable[str]) -> list[str]:
    """Hash an iterable of plain backup codes (case-insensitive)."""
    return [_scrypt_backup(c.strip().upper()) for c in codes]
