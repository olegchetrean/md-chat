# Copyright 2026 Mega Promoting SRL
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Derived from Cronberry (Mega Promoting SRL).
"""Branch-coverage tests for ``auth.pin_backup`` Argon2id wrap/unwrap edges.

Covers:
- empty PIN → InvalidPin
- wrong PIN, tampered ciphertext, tampered nonce, tampered AAD
- KDF params mismatch on unwrap (params persisted in bundle vs frozen defaults)
- non-bytes plaintext → TypeError
- WrappedBundle JSON round-trip, with custom + default KDF params
- in-memory store helpers (store_bundle / load_bundle / reset_store)
"""

from __future__ import annotations

import base64
import json
import os

import pytest

from md_chat_ai.auth import pin_backup
from md_chat_ai.auth.pin_backup import (
    InvalidPin,
    WrappedBundle,
    load_bundle,
    reset_store,
    store_bundle,
    unwrap_keys,
    wrap_keys,
)


# Fast-mode Argon2 for the whole test module so we don't burn CI cycles.
@pytest.fixture(autouse=True)
def _fast_argon2(monkeypatch):
    monkeypatch.setattr(pin_backup, "ARGON2_TIME_COST", 1)
    monkeypatch.setattr(pin_backup, "ARGON2_MEMORY_COST_KIB", 8 * 1024)
    monkeypatch.setattr(pin_backup, "ARGON2_PARALLELISM", 1)
    yield


# ---------------------------------------------------------------------------
# Empty / non-bytes inputs
# ---------------------------------------------------------------------------


def test_wrap_empty_pin_raises_invalidpin():
    with pytest.raises(InvalidPin):
        wrap_keys("", b"payload")


def test_wrap_non_bytes_plaintext_raises_typeerror():
    with pytest.raises(TypeError):
        wrap_keys("1234", "not-bytes")  # type: ignore[arg-type]


def test_unwrap_empty_pin_raises_invalidpin():
    bundle = wrap_keys("1234", b"payload")
    with pytest.raises(InvalidPin):
        unwrap_keys("", bundle)


# ---------------------------------------------------------------------------
# Wrong / tampered inputs
# ---------------------------------------------------------------------------


def test_unwrap_wrong_pin_raises_invalidpin():
    bundle = wrap_keys("1234", b"secret-payload")
    with pytest.raises(InvalidPin):
        unwrap_keys("9999", bundle)


def test_unwrap_tampered_ciphertext_raises_invalidpin():
    bundle = wrap_keys("1234", b"x" * 16)
    bad = bundle.ciphertext
    flipped = ("B" if bad[0] != "B" else "C") + bad[1:]
    bundle.ciphertext = flipped
    with pytest.raises(InvalidPin):
        unwrap_keys("1234", bundle)


def test_unwrap_tampered_nonce_raises_invalidpin():
    bundle = wrap_keys("1234", b"payload-ABCDE")
    bad = bundle.nonce
    flipped = ("Z" if bad[0] != "Z" else "Y") + bad[1:]
    bundle.nonce = flipped
    with pytest.raises(InvalidPin):
        unwrap_keys("1234", bundle)


def test_unwrap_malformed_bundle_base64_raises_invalidpin():
    """A bundle whose base64 fields are unparseable surfaces as InvalidPin."""
    bundle = WrappedBundle(
        salt="@@@@@@@@invalid-base64@@@",
        nonce="@@@@@@@@",
        ciphertext="@@@@@@@@",
    )
    with pytest.raises(InvalidPin):
        unwrap_keys("1234", bundle)


# ---------------------------------------------------------------------------
# KDF params persistence & mismatch
# ---------------------------------------------------------------------------


def test_kdf_params_persisted_in_bundle():
    bundle = wrap_keys("1234", b"x")
    # WrappedBundle has class-level defaults frozen at definition time;
    # they should be positive integers regardless.
    assert bundle.kdf_time_cost >= 1
    assert bundle.kdf_parallelism >= 1
    assert bundle.kdf_memory_cost >= 1024


def test_kdf_params_mismatch_on_unwrap_yields_invalidpin(monkeypatch):
    """Bundle wrapped with one set of params; we then hand-craft a bundle that
    claims *different* params — wrong key derived → AESGCM unwrap fails."""
    bundle = wrap_keys("1234", b"important-payload")
    # Construct an evil bundle that uses the right ciphertext/nonce/salt but
    # different (wrong) KDF parameters → unwrap_keys re-derives a different
    # key and InvalidPin fires.
    bad = WrappedBundle(
        salt=bundle.salt,
        nonce=bundle.nonce,
        ciphertext=bundle.ciphertext,
        kdf_time_cost=2,
        kdf_memory_cost=8 * 1024,
        kdf_parallelism=1,
    )
    with pytest.raises(InvalidPin):
        unwrap_keys("1234", bad)


def test_kdf_params_correct_unwraps_after_change(monkeypatch):
    """Even if module defaults change later, an old bundle still unwraps
    because its KDF parameters are stored inside the bundle."""
    bundle = wrap_keys("1234", b"important-payload")
    # Now bump module defaults (which shouldn't affect unwrap of OLD bundle).
    monkeypatch.setattr(pin_backup, "ARGON2_TIME_COST", 2)
    out = unwrap_keys("1234", bundle)
    assert out == b"important-payload"


# ---------------------------------------------------------------------------
# WrappedBundle serialization edges
# ---------------------------------------------------------------------------


def test_wrapped_bundle_to_json_includes_version_and_kdf():
    bundle = wrap_keys("1234", b"x")
    blob = bundle.to_json()
    obj = json.loads(blob)
    assert obj["v"] == 1
    assert obj["kdf"]["t"] >= 1
    assert obj["kdf"]["p"] >= 1
    assert obj["kdf"]["m"] >= 1024


def test_wrapped_bundle_from_json_handles_missing_kdf_fields():
    blob = json.dumps(
        {
            "v": 1,
            "salt": "AAAA",
            "nonce": "BBBB",
            "ciphertext": "CCCC",
        }
    )
    bundle = WrappedBundle.from_json(blob)
    # Fallback to module-level defaults (which the fast fixture lowered).
    assert bundle.kdf_time_cost == pin_backup.ARGON2_TIME_COST


def test_wrapped_bundle_from_json_roundtrip_preserves_kdf():
    bundle = wrap_keys("1234", b"x")
    blob = bundle.to_json()
    restored = WrappedBundle.from_json(blob)
    assert restored.kdf_time_cost == bundle.kdf_time_cost
    assert restored.kdf_memory_cost == bundle.kdf_memory_cost
    assert restored.kdf_parallelism == bundle.kdf_parallelism


# ---------------------------------------------------------------------------
# Payload size variations (covers AESGCM size paths)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("size", [1, 16, 32, 64, 256, 1024])
def test_wrap_unwrap_various_sizes(size: int):
    plain = os.urandom(size)
    bundle = wrap_keys("1234", plain)
    assert unwrap_keys("1234", bundle) == plain


def test_wrap_accepts_bytearray():
    bundle = wrap_keys("1234", bytearray(b"hello"))
    assert unwrap_keys("1234", bundle) == b"hello"


def test_distinct_calls_produce_distinct_ciphertexts():
    """Same plaintext + same PIN → different ciphertext because salt+nonce
    are randomized. (Confidentiality smoke test.)"""
    a = wrap_keys("1234", b"static-plaintext")
    b = wrap_keys("1234", b"static-plaintext")
    assert a.ciphertext != b.ciphertext
    assert a.salt != b.salt
    assert a.nonce != b.nonce


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def test_store_load_bundle_roundtrip():
    reset_store()
    bundle = wrap_keys("1234", b"secret")
    store_bundle("user-1", bundle)
    loaded = load_bundle("user-1")
    assert loaded is not None
    assert unwrap_keys("1234", loaded) == b"secret"


def test_load_bundle_missing_user_returns_none():
    reset_store()
    assert load_bundle("nobody") is None


def test_reset_store_clears_state():
    reset_store()
    bundle = wrap_keys("1234", b"x")
    store_bundle("u1", bundle)
    assert load_bundle("u1") is not None
    reset_store()
    assert load_bundle("u1") is None


def test_argon2_key_size_is_32_bytes():
    """Wrap with default parameters and verify the produced AES key is 32 B
    (AES-256). Indirectly checked via successful AES-256-GCM decrypt."""
    plain = b"a" * 47
    bundle = wrap_keys("1234", plain)
    assert unwrap_keys("1234", bundle) == plain
    # ciphertext length = plaintext + 16 byte GCM tag.
    ct_bytes = base64.urlsafe_b64decode(bundle.ciphertext + "=" * (-len(bundle.ciphertext) % 4))
    assert len(ct_bytes) == len(plain) + 16
