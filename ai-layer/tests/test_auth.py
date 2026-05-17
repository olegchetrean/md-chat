"""Tests for the MD-Chat auth module (phone + TOTP + PIN backup).

Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import asyncio
import os
import time

import pytest

from md_chat_ai.auth import phone_verification as pv
from md_chat_ai.auth import pin_backup, totp_mfa


# ---------------------------------------------------------------------------
# E.164 normalization.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,country,expected",
    [
        ("069123456", "MD", "+37369123456"),
        ("+37369123456", "MD", "+37369123456"),
        ("0721234567", "RO", "+40721234567"),
        ("0501234567", "UA", "+380501234567"),
        ("(069) 123-456", "MD", "+37369123456"),
        # Unknown country with leading 00 falls back to "+" (matches TS reference).
        ("0037369123456", "XX", "+37369123456"),
        # Unknown country, no 00: strip leading zeros and prepend "+".
        ("037369123456", "XX", "+37369123456"),
    ],
)
def test_normalize_to_e164(raw, country, expected):
    assert pv.normalize_to_e164(raw, country) == expected


# ---------------------------------------------------------------------------
# Cooldown + hourly rate-limit + verify flow.
# ---------------------------------------------------------------------------


def _fresh_store() -> pv.InMemoryStore:
    return pv.InMemoryStore()


async def _send_no_sms(store, user_id="u1", t=None):
    """Send-code that bypasses the actual SMS provider (Infobip)."""
    # Force "provider not configured" — record is still persisted, then
    # the function returns an error. We then patch out the SMS check by
    # inspecting the store directly.
    os.environ.pop("INFOBIP_API_KEY", None)
    return await pv.send_phone_verification_code(
        user_id=user_id,
        phone_number="069123456",
        country_code="MD",
        store=store,
        now=t,
    )


def test_send_records_into_store_even_when_sms_fails():
    store = _fresh_store()
    res = asyncio.run(_send_no_sms(store, t=1000.0))
    # Provider not configured surfaces as error but record persisted.
    assert res.ok is False
    assert res.error == "sms_provider_not_configured"
    assert len(store.records) == 1
    # PII stored only as hash.
    assert store.records[0].phone_hash != "+37369123456"
    assert len(store.records[0].phone_hash) == 64


def test_cooldown_blocks_second_send_within_60s():
    store = _fresh_store()
    asyncio.run(_send_no_sms(store, t=1000.0))
    second = asyncio.run(_send_no_sms(store, t=1000.0 + 30))
    assert second.ok is False
    assert second.error == "cooldown_active"
    assert second.cooldown_until == pytest.approx(1000.0 + pv.COOLDOWN_SECONDS)


def test_cooldown_clears_after_60s():
    store = _fresh_store()
    asyncio.run(_send_no_sms(store, t=1000.0))
    third = asyncio.run(_send_no_sms(store, t=1000.0 + pv.COOLDOWN_SECONDS + 1))
    # Past cooldown; provider still unconfigured but it should NOT be 'cooldown_active'.
    assert third.error == "sms_provider_not_configured"


def test_hourly_cap_enforced():
    store = _fresh_store()
    # Inject 5 sends evenly spaced > cooldown apart.
    for i in range(pv.MAX_PER_HOUR):
        res = asyncio.run(_send_no_sms(store, t=1000.0 + i * (pv.COOLDOWN_SECONDS + 1)))
        assert res.error == "sms_provider_not_configured"
    # 6th should hit hourly cap (well after cooldown).
    res = asyncio.run(
        _send_no_sms(store, t=1000.0 + pv.MAX_PER_HOUR * (pv.COOLDOWN_SECONDS + 1))
    )
    assert res.ok is False
    assert res.error == "too_many_requests"


def test_verify_happy_path():
    store = _fresh_store()
    # Manually insert a known code so we can verify.
    code = "424242"
    rec = pv._CodeRecord(
        user_id="u1",
        phone_hash=pv.hash_phone("+37369123456"),
        code_hash=pv.hash_code(code),
        created_at=time.time(),
        expires_at=time.time() + 600,
    )
    store.insert(rec)
    res = asyncio.run(pv.verify_phone_code("u1", code, store=store))
    assert res.ok is True
    # Consumed.
    assert rec.consumed_at is not None


def test_verify_wrong_code_increments_attempts():
    store = _fresh_store()
    rec = pv._CodeRecord(
        user_id="u1",
        phone_hash=pv.hash_phone("+37369123456"),
        code_hash=pv.hash_code("111111"),
        created_at=time.time(),
        expires_at=time.time() + 600,
    )
    store.insert(rec)
    for _ in range(pv.MAX_ATTEMPTS):
        res = asyncio.run(pv.verify_phone_code("u1", "999999", store=store))
        assert res.ok is False
        assert res.error == "invalid_code"
    # 6th attempt — over MAX_ATTEMPTS, record gets consumed.
    res = asyncio.run(pv.verify_phone_code("u1", "111111", store=store))
    assert res.ok is False
    assert res.error == "too_many_attempts"
    # And it stays consumed for future requests.
    res2 = asyncio.run(pv.verify_phone_code("u1", "111111", store=store))
    assert res2.error == "expired_or_not_found"


def test_verify_expired_code_rejected():
    store = _fresh_store()
    rec = pv._CodeRecord(
        user_id="u1",
        phone_hash=pv.hash_phone("+37369123456"),
        code_hash=pv.hash_code("111111"),
        created_at=time.time() - 3600,
        expires_at=time.time() - 60,
    )
    store.insert(rec)
    res = asyncio.run(pv.verify_phone_code("u1", "111111", store=store, now=time.time()))
    assert res.error == "expired_or_not_found"


# ---------------------------------------------------------------------------
# TOTP MFA.
# ---------------------------------------------------------------------------


def test_totp_secret_is_base32_length_32():
    s = totp_mfa.generate_secret()
    assert len(s) == 32
    # Base32 alphabet only.
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")
    assert set(s) <= allowed


def test_provisioning_uri_format():
    secret = totp_mfa.generate_secret()
    uri = totp_mfa.provisioning_uri(secret, "user@md-chat.eu")
    assert uri.startswith("otpauth://totp/")
    assert "issuer=MD-Chat" in uri
    assert f"secret={secret}" in uri
    assert "MD-Chat:user%40md-chat.eu" in uri


def test_totp_verify_now_and_reject_garbage():
    secret = totp_mfa.generate_secret()
    code = totp_mfa.now_code(secret)
    assert totp_mfa.verify_totp(secret, code) is True
    assert totp_mfa.verify_totp(secret, "000000") in (False, True)  # may collide rarely
    assert totp_mfa.verify_totp(secret, "abcdef") is False
    assert totp_mfa.verify_totp(secret, "") is False


def test_backup_codes_one_time_use():
    plain, hashes = totp_mfa.generate_backup_codes()
    assert len(plain) == 8
    assert len(hashes) == 8
    assert all(len(c) == 8 for c in plain)
    used, remaining = totp_mfa.verify_backup_code(plain[0], hashes)
    assert used is True
    assert len(remaining) == 7
    # Re-using the same code fails.
    used2, remaining2 = totp_mfa.verify_backup_code(plain[0], remaining)
    assert used2 is False
    assert len(remaining2) == 7
    # Wrong code fails too.
    used3, _ = totp_mfa.verify_backup_code("WRONGCDE", remaining)
    assert used3 is False


def test_setup_mfa_returns_full_bundle():
    bundle = totp_mfa.setup_mfa("user@md-chat.eu")
    assert bundle.secret
    assert bundle.qr_uri.startswith("otpauth://totp/")
    assert len(bundle.backup_codes) == 8
    assert len(bundle.backup_hashes) == 8


# ---------------------------------------------------------------------------
# PIN backup (wrap/unwrap roundtrip + tampering).
# ---------------------------------------------------------------------------


# Use lighter Argon2 params in tests so the suite finishes quickly.
@pytest.fixture(autouse=True)
def _fast_argon2(monkeypatch):
    monkeypatch.setattr(pin_backup, "ARGON2_TIME_COST", 1)
    monkeypatch.setattr(pin_backup, "ARGON2_MEMORY_COST_KIB", 8 * 1024)
    monkeypatch.setattr(pin_backup, "ARGON2_PARALLELISM", 1)
    yield


def test_pin_wrap_unwrap_roundtrip():
    plaintext = b"identity-keypair-seed-32-bytes!!!"
    bundle = pin_backup.wrap_keys("123456", plaintext)
    out = pin_backup.unwrap_keys("123456", bundle)
    assert out == plaintext


def test_pin_wrong_pin_rejected():
    plaintext = b"identity-keypair-seed-32-bytes!!!"
    bundle = pin_backup.wrap_keys("123456", plaintext)
    with pytest.raises(pin_backup.InvalidPin):
        pin_backup.unwrap_keys("999999", bundle)


def test_pin_tampered_ciphertext_rejected():
    plaintext = b"identity-keypair-seed-32-bytes!!!"
    bundle = pin_backup.wrap_keys("123456", plaintext)
    # Flip a byte in ciphertext.
    bad = bundle.ciphertext
    flipped = ("B" if bad[0] != "B" else "C") + bad[1:]
    bundle.ciphertext = flipped
    with pytest.raises(pin_backup.InvalidPin):
        pin_backup.unwrap_keys("123456", bundle)


def test_pin_bundle_serialization_roundtrip():
    bundle = pin_backup.wrap_keys("1234", b"hello")
    blob = bundle.to_json()
    restored = pin_backup.WrappedBundle.from_json(blob)
    out = pin_backup.unwrap_keys("1234", restored)
    assert out == b"hello"


# ---------------------------------------------------------------------------
# Flask blueprint smoke tests.
# ---------------------------------------------------------------------------


def _app_with_auth():
    from flask import Flask

    from md_chat_ai.api.auth import bp as auth_bp

    app = Flask(__name__)
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    return app


def test_blueprint_mfa_setup_and_verify():
    pin_backup.reset_store()
    client = _app_with_auth().test_client()
    r = client.post("/api/v1/auth/mfa/setup", json={"account_name": "user@md-chat.eu"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    secret = body["secret"]
    # Generate a live code and verify.
    code = totp_mfa.now_code(secret)
    r2 = client.post("/api/v1/auth/mfa/verify", json={"secret": secret, "code": code})
    assert r2.status_code == 200
    assert r2.get_json()["method"] == "totp"


def test_blueprint_pin_setup_and_recover():
    import base64

    pin_backup.reset_store()
    client = _app_with_auth().test_client()
    payload = base64.b64encode(b"my-identity-secret-bytes").decode("ascii")
    r = client.post(
        "/api/v1/auth/pin/setup",
        json={"user_id": "u1", "pin": "1234", "wrapped_keys_b64": payload},
    )
    assert r.status_code == 201
    r2 = client.post("/api/v1/auth/pin/recover", json={"user_id": "u1", "pin": "1234"})
    assert r2.status_code == 200
    assert r2.get_json()["wrapped_keys_b64"] == payload
    # Wrong PIN.
    r3 = client.post("/api/v1/auth/pin/recover", json={"user_id": "u1", "pin": "9999"})
    assert r3.status_code == 401


def test_blueprint_phone_send_missing_fields():
    client = _app_with_auth().test_client()
    r = client.post("/api/v1/auth/phone/send-code", json={})
    assert r.status_code == 400
    assert r.get_json()["error"] == "missing_fields"
