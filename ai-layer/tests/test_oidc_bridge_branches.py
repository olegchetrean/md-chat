# Copyright 2026 Mega Promoting SRL
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Derived from Cronberry (Mega Promoting SRL).
"""Branch-coverage tests for ``identity.oidc_bridge``.

Covers:
- bad / expired / reused authorization codes
- PKCE verifier mismatch + S256-only enforcement
- JWKS handling (no key configured → empty key set)
- malformed SAML response handling (missing pending state, unknown client)
- bearer-token expiry / unknown token
- discovery doc shape edges
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time

import pytest

from md_chat_ai.identity import (
    LOA,
    AttributeReleasePolicy,
    MPassAttributes,
    OIDCBridge,
    OIDCError,
    build_discovery_document,
)
from md_chat_ai.identity.oidc_bridge import (
    AuthorizationCode,
    OIDCClaims,
    _hashed_sub,
    _unsafe_dev_token,
    _verify_pkce,
)

REDIRECT = "https://msg.md-chat.eu/_synapse/client/oidc/callback"


def _bridge(allow_idnp: bool = False, secret: str | None = "s3cret") -> OIDCBridge:
    bridge = OIDCBridge(issuer="https://msg.md-chat.eu", signing_key_pem=None)
    bridge.register_client(
        "synapse",
        redirect_uris=[REDIRECT],
        client_secret=secret,
        allow_idnp=allow_idnp,
    )
    return bridge


def _begin(bridge: OIDCBridge, **kw) -> str:
    """Helper — start an authorization, return relay_state."""
    defaults = dict(
        client_id="synapse",
        redirect_uri=REDIRECT,
        scope="openid",
        state="state-xyz",
    )
    defaults.update(kw)
    env = bridge.begin_authorization(**defaults)
    return env["relay_state"]


# ---------------------------------------------------------------------------
# Authorize — error paths
# ---------------------------------------------------------------------------


def test_authorize_missing_openid_scope_rejected():
    bridge = _bridge()
    with pytest.raises(OIDCError) as exc:
        bridge.begin_authorization(
            client_id="synapse",
            redirect_uri=REDIRECT,
            scope="profile_minimized",
            state="x",
        )
    assert exc.value.error == "invalid_scope"


def test_authorize_unsupported_pkce_method_rejected():
    bridge = _bridge()
    with pytest.raises(OIDCError) as exc:
        bridge.begin_authorization(
            client_id="synapse",
            redirect_uri=REDIRECT,
            scope="openid",
            state="x",
            code_challenge="abc",
            code_challenge_method="plain",
        )
    assert exc.value.error == "invalid_request"


def test_authorize_idnp_allowed_when_client_permits():
    bridge = _bridge(allow_idnp=True)
    env = bridge.begin_authorization(
        client_id="synapse",
        redirect_uri=REDIRECT,
        scope="openid idnp",
        state="x",
        request_idnp=True,
    )
    assert "relay_state" in env
    assert set(env["scopes"]) == {"openid", "idnp"}


def test_authorize_records_pending_state():
    bridge = _bridge()
    relay = _begin(bridge, nonce="abc", code_challenge="cha", code_challenge_method="S256")
    pending = bridge._pending_authorizations[relay]
    assert pending["nonce"] == "abc"
    assert pending["code_challenge"] == "cha"
    assert pending["code_challenge_method"] == "S256"


# ---------------------------------------------------------------------------
# Callback — error paths
# ---------------------------------------------------------------------------


def test_complete_authorization_unknown_relay_state_rejected():
    bridge = _bridge()
    attrs = MPassAttributes(verified=True, name_id="nid", loa=LOA.LOA1)
    with pytest.raises(OIDCError) as exc:
        bridge.complete_authorization(relay_state="garbage-relay", saml_attributes=attrs)
    assert exc.value.error == "invalid_request"


def test_complete_authorization_pops_pending_state():
    """Relay state is single-use; pending mapping is removed on success."""
    bridge = _bridge()
    relay = _begin(bridge)
    attrs = MPassAttributes(verified=True, name_id="nid", loa=LOA.LOA1)
    bridge.complete_authorization(relay_state=relay, saml_attributes=attrs)
    # Second attempt must fail since state was popped.
    with pytest.raises(OIDCError):
        bridge.complete_authorization(relay_state=relay, saml_attributes=attrs)


def test_complete_authorization_with_idnp_policy_includes_idnp():
    bridge = _bridge(allow_idnp=True)
    relay = _begin(
        bridge,
        client_id="synapse",
        redirect_uri=REDIRECT,
        scope="openid idnp",
        state="s",
        request_idnp=True,
    )
    attrs = MPassAttributes(
        verified=True,
        idnp="2002001234567",
        given_name="Ion",
        loa=LOA.LOA3,
        name_id="nid",
    )
    code, redirect, state = bridge.complete_authorization(relay_state=relay, saml_attributes=attrs)
    assert state == "s"
    record = bridge.codes[code]
    assert record.claims["idnp"] == "2002001234567"


# ---------------------------------------------------------------------------
# Token exchange — error paths
# ---------------------------------------------------------------------------


def test_token_unknown_code_rejected():
    bridge = _bridge()
    with pytest.raises(OIDCError) as exc:
        bridge.exchange_code(
            code="never-issued",
            client_id="synapse",
            client_secret="s3cret",
            redirect_uri=REDIRECT,
        )
    assert exc.value.error == "invalid_grant"


def test_token_expired_code_rejected():
    bridge = _bridge()
    relay = _begin(bridge)
    attrs = MPassAttributes(verified=True, name_id="nid", loa=LOA.LOA1)
    code, _, _ = bridge.complete_authorization(relay_state=relay, saml_attributes=attrs)
    # Force the code to be expired.
    record = bridge.codes[code]
    record.expires_at = time.time() - 1
    with pytest.raises(OIDCError) as exc:
        bridge.exchange_code(
            code=code,
            client_id="synapse",
            client_secret="s3cret",
            redirect_uri=REDIRECT,
        )
    assert exc.value.error == "invalid_grant"
    # And the code was purged.
    assert code not in bridge.codes


def test_token_client_mismatch_rejected():
    bridge = _bridge()
    bridge.register_client("other", redirect_uris=[REDIRECT], client_secret="x")
    relay = _begin(bridge)
    attrs = MPassAttributes(verified=True, name_id="nid", loa=LOA.LOA1)
    code, _, _ = bridge.complete_authorization(relay_state=relay, saml_attributes=attrs)
    with pytest.raises(OIDCError) as exc:
        bridge.exchange_code(
            code=code,
            client_id="other",
            client_secret="x",
            redirect_uri=REDIRECT,
        )
    assert exc.value.error == "invalid_grant"


def test_token_redirect_uri_mismatch_rejected():
    bridge = _bridge()
    relay = _begin(bridge)
    attrs = MPassAttributes(verified=True, name_id="nid", loa=LOA.LOA1)
    code, _, _ = bridge.complete_authorization(relay_state=relay, saml_attributes=attrs)
    with pytest.raises(OIDCError) as exc:
        bridge.exchange_code(
            code=code,
            client_id="synapse",
            client_secret="s3cret",
            redirect_uri="https://evil.example/cb",
        )
    assert exc.value.error == "invalid_grant"


def test_token_pkce_verifier_required_when_challenge_set():
    bridge = _bridge()
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(b"verifierA" * 5).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    relay = _begin(bridge, code_challenge=challenge, code_challenge_method="S256")
    attrs = MPassAttributes(verified=True, name_id="nid", loa=LOA.LOA1)
    code, _, _ = bridge.complete_authorization(relay_state=relay, saml_attributes=attrs)
    with pytest.raises(OIDCError) as exc:
        bridge.exchange_code(
            code=code,
            client_id="synapse",
            client_secret="s3cret",
            redirect_uri=REDIRECT,
        )
    assert exc.value.error == "invalid_grant"


def test_token_pkce_mismatch_rejected():
    bridge = _bridge()
    verifier = "verifierA" * 5
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    relay = _begin(bridge, code_challenge=challenge, code_challenge_method="S256")
    attrs = MPassAttributes(verified=True, name_id="nid", loa=LOA.LOA1)
    code, _, _ = bridge.complete_authorization(relay_state=relay, saml_attributes=attrs)
    with pytest.raises(OIDCError) as exc:
        bridge.exchange_code(
            code=code,
            client_id="synapse",
            client_secret="s3cret",
            redirect_uri=REDIRECT,
            code_verifier="WRONG-VERIFIER",
        )
    assert exc.value.error == "invalid_grant"


def test_token_pkce_matching_verifier_accepted():
    bridge = _bridge()
    verifier = "verifierA" * 5
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    relay = _begin(bridge, code_challenge=challenge, code_challenge_method="S256")
    attrs = MPassAttributes(verified=True, name_id="nid", loa=LOA.LOA1)
    code, _, _ = bridge.complete_authorization(relay_state=relay, saml_attributes=attrs)
    body = bridge.exchange_code(
        code=code,
        client_id="synapse",
        client_secret="s3cret",
        redirect_uri=REDIRECT,
        code_verifier=verifier,
    )
    assert body["token_type"] == "Bearer"


def test_token_no_client_secret_required_when_not_set():
    bridge = _bridge(secret=None)
    relay = _begin(bridge)
    attrs = MPassAttributes(verified=True, name_id="nid", loa=LOA.LOA1)
    code, _, _ = bridge.complete_authorization(relay_state=relay, saml_attributes=attrs)
    body = bridge.exchange_code(
        code=code,
        client_id="synapse",
        client_secret=None,
        redirect_uri=REDIRECT,
    )
    assert "id_token" in body


# ---------------------------------------------------------------------------
# userinfo — error paths
# ---------------------------------------------------------------------------


def test_userinfo_unknown_token_rejected():
    bridge = _bridge()
    with pytest.raises(OIDCError) as exc:
        bridge.userinfo("no-such-token")
    assert exc.value.error == "invalid_token"


def test_userinfo_expired_token_purges_and_raises():
    bridge = _bridge()
    relay = _begin(bridge)
    attrs = MPassAttributes(verified=True, name_id="nid", loa=LOA.LOA1)
    code, _, _ = bridge.complete_authorization(relay_state=relay, saml_attributes=attrs)
    body = bridge.exchange_code(
        code=code,
        client_id="synapse",
        client_secret="s3cret",
        redirect_uri=REDIRECT,
    )
    access = body["access_token"]
    # Force expiry.
    bridge.tokens[access].exp = int(time.time()) - 1
    with pytest.raises(OIDCError) as exc:
        bridge.userinfo(access)
    assert exc.value.error == "invalid_token"
    assert access not in bridge.tokens


# ---------------------------------------------------------------------------
# JWKS — error paths
# ---------------------------------------------------------------------------


def test_jwks_empty_when_no_signing_key():
    bridge = _bridge()
    assert bridge.jwks() == {"keys": []}


def test_jwks_returns_empty_on_invalid_pem():
    bridge = OIDCBridge(issuer="https://x", signing_key_pem="-----BEGIN RSA PRIVATE KEY-----\nBROKEN\n-----END RSA PRIVATE KEY-----")
    assert bridge.jwks() == {"keys": []}


def test_jwks_valid_key_publishes_kid():
    """Generate a real RSA key on the fly and assert JWKS shape."""
    pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    bridge = OIDCBridge(issuer="https://x", signing_key_pem=pem, signing_kid="kid-abc")
    jwks = bridge.jwks()
    assert len(jwks["keys"]) == 1
    assert jwks["keys"][0]["kid"] == "kid-abc"
    assert jwks["keys"][0]["alg"] == "RS256"
    assert jwks["keys"][0]["kty"] == "RSA"


# ---------------------------------------------------------------------------
# Discovery doc
# ---------------------------------------------------------------------------


def test_discovery_doc_trailing_slash_stripped():
    doc = build_discovery_document("https://msg.md-chat.eu///")
    assert doc["issuer"] == "https://msg.md-chat.eu"
    assert doc["jwks_uri"].endswith("/oidc/jwks.json")


def test_discovery_includes_pkce_s256_only():
    doc = build_discovery_document("https://x")
    assert doc["code_challenge_methods_supported"] == ["S256"]


# ---------------------------------------------------------------------------
# Helpers — verify, sub hash, unsafe dev token
# ---------------------------------------------------------------------------


def test_verify_pkce_constant_time_returns_false_on_mismatch():
    assert _verify_pkce("a", "b") is False


def test_hashed_sub_is_deterministic_and_prefixed():
    a = _hashed_sub("seed-1")
    b = _hashed_sub("seed-1")
    assert a == b
    assert a.startswith("mpass-")
    assert len(a) == len("mpass-") + 24


def test_unsafe_dev_token_uses_none_alg():
    tok = _unsafe_dev_token({"sub": "x"})
    parts = tok.split(".")
    assert len(parts) == 3
    header = parts[0]
    decoded = base64.urlsafe_b64decode(header + "=" * (-len(header) % 4))
    assert b'"alg":"none"' in decoded


# ---------------------------------------------------------------------------
# OIDCError + AuthorizationCode + OIDCClaims helpers
# ---------------------------------------------------------------------------


def test_oidc_error_as_dict():
    err = OIDCError("invalid_grant", "code expired")
    d = err.as_dict()
    assert d["error"] == "invalid_grant"
    assert d["error_description"] == "code expired"


def test_authorization_code_is_expired_helper():
    rec = AuthorizationCode(
        code="abc",
        client_id="synapse",
        redirect_uri=REDIRECT,
        claims={},
        expires_at=time.time() - 1,
    )
    assert rec.is_expired() is True
    rec2 = AuthorizationCode(
        code="def",
        client_id="synapse",
        redirect_uri=REDIRECT,
        claims={},
        expires_at=time.time() + 100,
    )
    assert rec2.is_expired() is False


def test_oidc_claims_as_dict_skips_none_optionals():
    claims = OIDCClaims(
        sub="sub-1",
        acr="md.gov.mpass.loa2",
        iss="https://x",
        iss_idp="https://mpass.gov.md",
        iat=10,
        exp=20,
    )
    d = claims.as_dict()
    assert "verified" not in d
    assert "age_band" not in d
    assert "prenume" not in d


def test_oidc_claims_as_dict_includes_extras():
    claims = OIDCClaims(
        sub="sub-1",
        acr="x",
        iss="i",
        iss_idp="ip",
        iat=10,
        exp=20,
        verified=True,
        age_band="26-35",
        prenume="Ion",
        email="ion@x.md",
        extra={"custom_claim": "yes"},
    )
    d = claims.as_dict()
    assert d["verified"] is True
    assert d["age_band"] == "26-35"
    assert d["custom_claim"] == "yes"


# ---------------------------------------------------------------------------
# Malformed / missing pending state at callback
# ---------------------------------------------------------------------------


def test_callback_with_empty_attributes_still_produces_code():
    """Even minimal SAML attrs (no name_id) must yield a code with hashed sub."""
    bridge = _bridge()
    relay = _begin(bridge)
    attrs = MPassAttributes(loa=LOA.LOA1)  # no name_id
    code, _, _ = bridge.complete_authorization(relay_state=relay, saml_attributes=attrs)
    body = bridge.exchange_code(
        code=code,
        client_id="synapse",
        client_secret="s3cret",
        redirect_uri=REDIRECT,
    )
    # sub will be derived via _hashed_sub
    access = body["access_token"]
    info = bridge.userinfo(access)
    assert info["sub"].startswith("mpass-")
