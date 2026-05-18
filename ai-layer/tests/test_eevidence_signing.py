"""Tests for the eEvidence audit-log Ed25519 signing layer.

These tests cover the two modules added in the audit-log hardening sprint:

* :mod:`md_chat_ai.eevidence.keys` — keypair generation, on-disk storage with
  ``0600`` permissions, JWK export, multi-kid keystore.
* :mod:`md_chat_ai.eevidence.signing` — JWS (RFC 7515) compact serialisation,
  canonical JSON, tamper detection, key rotation, third-party verification.

No external network calls; only filesystem under ``tmp_path``.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import replace

import pytest

from md_chat_ai.eevidence.audit import AuditRegister
from md_chat_ai.eevidence.keys import (
    KeyNotFoundError,
    KeyPermissionsError,
    KeyStore,
    generate_keypair,
    load_private_key,
    public_jwk,
    public_key_from_jwk,
    write_private_key,
)
from md_chat_ai.eevidence.signing import (
    JWS_ALG,
    JWS_TYP,
    SignedAuditEntry,
    canonical_json,
    sign_entry,
    verify_jws,
    verify_signed_entry,
    verify_with_public_key,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def register() -> AuditRegister:
    r = AuditRegister()
    r.append(
        event_type="order_received",
        ticket_id="EE-2026-0001",
        actor="portal:authority",
        details={"member_state": "RO", "urgency_level": "standard"},
    )
    r.append(
        event_type="order_responded",
        ticket_id="EE-2026-0001",
        actor="operator:dpo",
        details={"refusal_grounds": [], "response_hash": "deadbeef"},
    )
    return r


@pytest.fixture()
def keystore() -> KeyStore:
    ks = KeyStore()
    ks.register_signing_key("mpass-audit-1", generate_keypair())
    return ks


# ---------------------------------------------------------------------------
# 1. Sign + verify roundtrip
# ---------------------------------------------------------------------------


def test_sign_verify_roundtrip(register: AuditRegister, keystore: KeyStore) -> None:
    entry = register.all()[0]
    signed = sign_entry(entry, keystore)
    assert isinstance(signed, SignedAuditEntry)
    assert signed.kid == "mpass-audit-1"
    assert signed.jws.count(".") == 2

    result = verify_signed_entry(signed, keystore)
    assert result.valid, result.reason
    assert bool(result) is True


def test_sign_verify_all_entries(register: AuditRegister, keystore: KeyStore) -> None:
    for entry in register.all():
        signed = sign_entry(entry, keystore)
        assert verify_signed_entry(signed, keystore)


# ---------------------------------------------------------------------------
# 2. Tamper detection — any field change fails verification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,new_value",
    [
        ("ticket_id", "EE-2026-9999"),
        ("actor", "attacker:rogue"),
        ("event_type", "order_refused"),
        ("timestamp", "2099-01-01T00:00:00.000+00:00"),
        ("entry_hash", "0" * 64),
        ("previous_hash", "f" * 64),
    ],
)
def test_tamper_any_field_breaks_verification(
    register: AuditRegister, keystore: KeyStore, field: str, new_value: str
) -> None:
    entry = register.all()[0]
    signed = sign_entry(entry, keystore)

    tampered_entry = replace(entry, **{field: new_value})
    tampered = SignedAuditEntry(entry=tampered_entry, kid=signed.kid, jws=signed.jws)

    result = verify_signed_entry(tampered, keystore)
    assert not result.valid
    # Either the chain hash check or the payload field comparison should fire.
    assert any(token in result.reason for token in ("payload_field_mismatch", "entry_chain_hash_mismatch"))


def test_tamper_details_dict_breaks_verification(
    register: AuditRegister, keystore: KeyStore
) -> None:
    entry = register.all()[0]
    signed = sign_entry(entry, keystore)

    tampered_entry = replace(entry, details={"member_state": "FR", "urgency_level": "emergency"})
    tampered = SignedAuditEntry(entry=tampered_entry, kid=signed.kid, jws=signed.jws)
    result = verify_signed_entry(tampered, keystore)
    assert not result.valid


def test_tamper_jws_signature_byte_breaks_verification(
    register: AuditRegister, keystore: KeyStore
) -> None:
    entry = register.all()[0]
    signed = sign_entry(entry, keystore)

    header_b64, payload_b64, sig_b64 = signed.jws.split(".")
    # Flip the first character of the signature segment.
    flipped = ("A" if sig_b64[0] != "A" else "B") + sig_b64[1:]
    tampered_jws = f"{header_b64}.{payload_b64}.{flipped}"
    tampered = SignedAuditEntry(entry=signed.entry, kid=signed.kid, jws=tampered_jws)

    result = verify_signed_entry(tampered, keystore)
    assert not result.valid
    assert "ed25519_invalid_signature" in result.reason or "malformed" in result.reason


# ---------------------------------------------------------------------------
# 3. Multiple kids supported simultaneously
# ---------------------------------------------------------------------------


def test_multiple_kids_supported(register: AuditRegister) -> None:
    ks = KeyStore()
    ks.register_signing_key("mpass-audit-1", generate_keypair())
    sig_with_first = sign_entry(register.all()[0], ks)

    ks.register_signing_key("mpass-audit-2", generate_keypair())
    sig_with_second = sign_entry(register.all()[1], ks)

    assert sig_with_first.kid == "mpass-audit-1"
    assert sig_with_second.kid == "mpass-audit-2"
    assert verify_signed_entry(sig_with_first, ks)
    assert verify_signed_entry(sig_with_second, ks)


# ---------------------------------------------------------------------------
# 4. Wrong public key → verify fails
# ---------------------------------------------------------------------------


def test_wrong_public_key_fails(register: AuditRegister, keystore: KeyStore) -> None:
    entry = register.all()[0]
    signed = sign_entry(entry, keystore)

    other_ks = KeyStore()
    other_ks.register_signing_key("mpass-audit-1", generate_keypair())

    result = verify_signed_entry(signed, other_ks)
    assert not result.valid
    assert result.reason == "ed25519_invalid_signature"


def test_unknown_kid_fails(register: AuditRegister, keystore: KeyStore) -> None:
    entry = register.all()[0]
    signed = sign_entry(entry, keystore)

    isolated = KeyStore()
    isolated.register_signing_key("different-kid", generate_keypair())

    result = verify_signed_entry(signed, isolated)
    assert not result.valid
    assert result.reason.startswith("unknown_kid:")


# ---------------------------------------------------------------------------
# 5. Key rotation: old kid signature still verifies after rotation
# ---------------------------------------------------------------------------


def test_key_rotation_preserves_old_signatures(register: AuditRegister) -> None:
    ks = KeyStore()
    ks.register_signing_key("mpass-audit-1", generate_keypair())
    old_sig = sign_entry(register.all()[0], ks)

    new_key = generate_keypair()
    ks.rotate("mpass-audit-2", new_key)

    # Active kid now mpass-audit-2 — old signature must still verify.
    assert ks.active_kid == "mpass-audit-2"
    assert verify_signed_entry(old_sig, ks)

    # Brand-new signature uses the new key.
    new_sig = sign_entry(register.all()[1], ks)
    assert new_sig.kid == "mpass-audit-2"
    assert verify_signed_entry(new_sig, ks)


def test_rotation_strips_private_material_from_retired_kid(register: AuditRegister) -> None:
    """After rotation the retired kid must be verify-only — defence-in-depth."""

    ks = KeyStore()
    ks.register_signing_key("mpass-audit-1", generate_keypair())
    ks.rotate("mpass-audit-2", generate_keypair())

    retired = ks.get("mpass-audit-1")
    assert retired.private_key is None
    assert retired.public_key is not None


# ---------------------------------------------------------------------------
# 6. File permission enforcement on key generation
# ---------------------------------------------------------------------------


def test_write_private_key_has_0600_permissions(tmp_path) -> None:
    key = generate_keypair()
    target = tmp_path / "audit.pem"
    written = write_private_key(target, key)

    mode = stat.S_IMODE(os.stat(written).st_mode)
    assert mode == 0o600, f"expected 0o600, got {oct(mode)}"

    # Round-trip load works.
    loaded = load_private_key(written)
    assert loaded.public_key().public_bytes_raw() == key.public_key().public_bytes_raw()


def test_load_refuses_world_readable_key(tmp_path) -> None:
    key = generate_keypair()
    target = tmp_path / "loose.pem"
    write_private_key(target, key)
    os.chmod(target, 0o644)  # simulate accidental chmod

    with pytest.raises(KeyPermissionsError):
        load_private_key(target)


def test_load_refuses_group_readable_key(tmp_path) -> None:
    key = generate_keypair()
    target = tmp_path / "group.pem"
    write_private_key(target, key)
    os.chmod(target, 0o640)

    with pytest.raises(KeyPermissionsError):
        load_private_key(target)


def test_load_missing_key_raises(tmp_path) -> None:
    with pytest.raises(KeyNotFoundError):
        load_private_key(tmp_path / "nope.pem")


def test_load_from_disk_round_trip(tmp_path, register: AuditRegister) -> None:
    key = generate_keypair()
    target = tmp_path / "audit.pem"
    write_private_key(target, key)

    ks = KeyStore()
    ks.load_from_disk("mpass-audit-fs", target)

    signed = sign_entry(register.all()[0], ks)
    assert signed.kid == "mpass-audit-fs"
    assert verify_signed_entry(signed, ks)


# ---------------------------------------------------------------------------
# 7. Canonical JSON: stable across runs, NFC normalisation, no whitespace drift
# ---------------------------------------------------------------------------


def test_canonical_json_stable_across_runs() -> None:
    payload = {
        "z": 1,
        "a": "alpha",
        "m": {"y": 2, "x": [3, 1, 2]},
        "details": {"unicode": "café", "ascii": "ok"},
    }
    out1 = canonical_json(payload)
    out2 = canonical_json(payload)
    out3 = canonical_json(payload)
    assert out1 == out2 == out3
    # No whitespace anywhere.
    assert b" " not in out1
    assert b"\n" not in out1
    # Keys sorted.
    decoded = json.loads(out1.decode("utf-8"))
    assert list(decoded.keys()) == sorted(decoded.keys())


def test_canonical_json_normalises_nfc() -> None:
    # 'é' encoded two ways: precomposed (NFC) and decomposed (NFD).
    nfc = "café"  # é U+00E9
    nfd = "café"  # e + combining acute
    assert canonical_json({"x": nfc}) == canonical_json({"x": nfd})


def test_canonical_json_no_nan_inf() -> None:
    with pytest.raises(ValueError):
        canonical_json({"bad": float("nan")})


# ---------------------------------------------------------------------------
# 8. JWS structure conforms to RFC 7515 + interop with public key alone
# ---------------------------------------------------------------------------


def test_jws_header_structure(register: AuditRegister, keystore: KeyStore) -> None:
    signed = sign_entry(register.all()[0], keystore)
    header_b64, _payload_b64, _sig_b64 = signed.jws.split(".")
    import base64

    padding = "=" * (-len(header_b64) % 4)
    header = json.loads(base64.urlsafe_b64decode(header_b64 + padding).decode("utf-8"))
    assert header == {"alg": JWS_ALG, "typ": JWS_TYP, "kid": "mpass-audit-1"}


def test_third_party_can_verify_with_public_key_only(
    register: AuditRegister, keystore: KeyStore
) -> None:
    """The whole point: a court verifier with only the JWK can verify."""

    entry = register.all()[0]
    signed = sign_entry(entry, keystore)

    # Export public key as JWK, then re-import on the "verifier side".
    active = keystore.active()
    jwk = public_jwk(active.public_key, kid=active.kid)
    rebuilt_pub = public_key_from_jwk(jwk)

    assert verify_with_public_key(signed.jws, rebuilt_pub)


def test_jwks_published_set_round_trips(keystore: KeyStore) -> None:
    keystore.register_signing_key("mpass-audit-2", generate_keypair())
    jwks = keystore.jwks()
    assert "keys" in jwks
    assert {k["kid"] for k in jwks["keys"]} == {"mpass-audit-1", "mpass-audit-2"}
    for entry in jwks["keys"]:
        assert entry["kty"] == "OKP"
        assert entry["crv"] == "Ed25519"
        assert entry["alg"] == "EdDSA"
        assert entry["use"] == "sig"
        # public_key_from_jwk must accept it.
        pub = public_key_from_jwk(entry)
        assert pub is not None


# ---------------------------------------------------------------------------
# 9. Malformed JWS inputs are rejected cleanly (no exception bubbling)
# ---------------------------------------------------------------------------


def test_malformed_jws_returns_failure(register: AuditRegister, keystore: KeyStore) -> None:
    entry = register.all()[0]
    result = verify_jws("not-a-jws", expected_entry=entry, keystore=keystore)
    assert not result.valid
    assert result.reason == "malformed_jws_segments"


def test_jws_wrong_alg_rejected(register: AuditRegister, keystore: KeyStore) -> None:
    import base64

    entry = register.all()[0]
    signed = sign_entry(entry, keystore)
    _, payload_b64, sig_b64 = signed.jws.split(".")
    fake_header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": JWS_TYP, "kid": "mpass-audit-1"}).encode()
    ).rstrip(b"=").decode("ascii")
    forged = f"{fake_header}.{payload_b64}.{sig_b64}"
    result = verify_jws(forged, expected_entry=entry, keystore=keystore)
    assert not result.valid
    assert result.reason.startswith("unsupported_alg")


# ---------------------------------------------------------------------------
# 10. pyjwt interop sanity — produced JWS should be parsable by pyjwt
# ---------------------------------------------------------------------------


def test_pyjwt_can_decode_our_jws(register: AuditRegister, keystore: KeyStore) -> None:
    """Third-party auditors typically reach for pyjwt — make sure that works."""

    import jwt as pyjwt  # type: ignore[import-untyped]
    from cryptography.hazmat.primitives import serialization

    entry = register.all()[0]
    signed = sign_entry(entry, keystore)

    active = keystore.active()
    public_pem = active.public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    decoded = pyjwt.decode(
        signed.jws,
        key=public_pem,
        algorithms=["EdDSA"],
        options={"verify_aud": False, "verify_exp": False, "verify_iat": False, "verify_signature": True},
    )
    assert decoded["entry_id"] == str(entry.sequence)
    assert decoded["event_type"] == entry.event_type
    assert decoded["sha256_chain_hash"] == entry.entry_hash
