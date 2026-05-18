"""Tests for the MPass SAML to OIDC bridge.

These tests cover the pieces of the bridge that do not need the
heavy native dependencies (``python3-saml`` / ``zeep``):

* attribute mapping and IDNP refusal
* OIDC discovery document
* OIDC authorize / callback / token / userinfo round-trip
* PKCE verification
* MSign SOAP serialization and response parsing (via a fake invoker)
* HTTP endpoints in the Flask blueprint

Tests that would otherwise require ``python3-saml`` are skipped when
that library is not installed, so the suite runs cleanly on macOS
without ``libxmlsec1``.
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
from typing import Any

import pytest
from flask import Flask

from md_chat_ai.identity import (
    LOA,
    AttributeReleasePolicy,
    MPassAttributes,
    MSignClient,
    MSignError,
    OIDCBridge,
    OIDCError,
    SignatureRequest,
    SignatureResult,
    build_discovery_document,
    map_birth_year_to_age_band,
    map_loa_to_acr,
    saml_attributes_to_oidc_claims,
)
from md_chat_ai.identity.oidc_bridge import _verify_pkce

# ---------------------------------------------------------------------------
# Attribute mapping
# ---------------------------------------------------------------------------


class TestAttributeMapping:
    def test_birth_year_to_age_band_basic(self):
        today = dt.date(2026, 5, 17)
        assert map_birth_year_to_age_band(2000, now=today) == "26-35"
        assert map_birth_year_to_age_band(2005, now=today) == "18-25"
        assert map_birth_year_to_age_band(1960, now=today) == "65+"
        assert map_birth_year_to_age_band(2015, now=today) == "<18"

    def test_birth_year_unparseable_returns_none(self):
        assert map_birth_year_to_age_band(None) is None
        assert map_birth_year_to_age_band("not-a-year") is None
        assert map_birth_year_to_age_band("") is None

    def test_loa_mapping_known_values(self):
        assert map_loa_to_acr("LOA1") == "md.gov.mpass.loa1"
        assert map_loa_to_acr("LOA2") == "md.gov.mpass.loa2"
        assert map_loa_to_acr("LOA3") == "md.gov.mpass.loa3"
        assert map_loa_to_acr(LOA.LOA3) == "md.gov.mpass.loa3"

    def test_loa_unknown_defaults_to_loa1(self):
        assert map_loa_to_acr(None) == "md.gov.mpass.loa1"
        assert map_loa_to_acr("LOA9000") == "md.gov.mpass.loa1"


class TestSamlToOidcClaims:
    def _sample(self, **overrides: Any) -> MPassAttributes:
        defaults = dict(
            verified=True,
            birth_year=1995,
            given_name="Oleg",
            family_name="Chetrean",
            email="oleg@example.md",
            phone="+37360123456",
            idnp="2002001234567",
            loa=LOA.LOA2,
            name_id="mpass-name-id-xyz",
        )
        defaults.update(overrides)
        return MPassAttributes(**defaults)

    def test_default_policy_refuses_idnp(self):
        attrs = self._sample()
        claims = saml_attributes_to_oidc_claims(attrs, now=dt.date(2026, 5, 17))
        assert "idnp" not in claims
        assert claims["verified"] is True
        assert claims["age_band"] == "26-35"
        assert claims["prenume"] == "Oleg"
        assert claims["acr"] == "md.gov.mpass.loa2"
        assert claims["sub"] == "mpass-name-id-xyz"
        # Family name / email / phone are not in the default released set.
        assert "family_name" not in claims
        assert "email" not in claims
        assert "phone" not in claims

    def test_idnp_release_only_with_explicit_policy(self):
        attrs = self._sample()
        policy = AttributeReleasePolicy().with_idnp(purpose="msign_qualified_signature")
        claims = saml_attributes_to_oidc_claims(attrs, policy=policy, now=dt.date(2026, 5, 17))
        assert claims["idnp"] == "2002001234567"

    def test_idnp_release_requires_purpose(self):
        with pytest.raises(ValueError):
            AttributeReleasePolicy().with_idnp(purpose="")

    def test_attributes_from_saml_response_coerces_types(self):
        raw = {
            "verified": ["true"],
            "birth_year": ["1990"],
            "given_name": ["Maria"],
            "family_name": ["Popescu"],
            "unique_identifier_personal_code": ["1234567890123"],
        }
        attrs = MPassAttributes.from_saml_response(raw, loa="LOA3", name_id="abc")
        assert attrs.verified is True
        assert attrs.birth_year == 1990
        assert attrs.given_name == "Maria"
        assert attrs.idnp == "1234567890123"
        assert attrs.loa == LOA.LOA3


# ---------------------------------------------------------------------------
# OIDC discovery
# ---------------------------------------------------------------------------


class TestDiscovery:
    def test_discovery_document_shape(self):
        doc = build_discovery_document("https://msg.md-chat.eu/")
        assert doc["issuer"] == "https://msg.md-chat.eu"
        assert doc["authorization_endpoint"].endswith("/oidc/authorize")
        assert doc["token_endpoint"].endswith("/oidc/token")
        assert doc["userinfo_endpoint"].endswith("/oidc/userinfo")
        assert doc["jwks_uri"].endswith("/oidc/jwks.json")
        assert "RS256" in doc["id_token_signing_alg_values_supported"]
        assert "openid" in doc["scopes_supported"]
        assert "idnp" in doc["scopes_supported"]
        assert "S256" in doc["code_challenge_methods_supported"]


# ---------------------------------------------------------------------------
# OIDC end-to-end flow (in-memory)
# ---------------------------------------------------------------------------


def _bridge_with_client(allow_idnp: bool = False) -> OIDCBridge:
    bridge = OIDCBridge(issuer="https://msg.md-chat.eu", signing_key_pem=None)
    bridge.register_client(
        "synapse",
        redirect_uris=["https://msg.md-chat.eu/_synapse/client/oidc/callback"],
        client_secret="s3cret",
        allow_idnp=allow_idnp,
    )
    return bridge


class TestOIDCBridge:
    def test_authorize_rejects_unknown_client(self):
        bridge = _bridge_with_client()
        with pytest.raises(OIDCError) as exc:
            bridge.begin_authorization(
                client_id="unknown",
                redirect_uri="https://x/cb",
                scope="openid",
                state="st",
            )
        assert exc.value.error == "invalid_client"

    def test_authorize_rejects_bad_redirect(self):
        bridge = _bridge_with_client()
        with pytest.raises(OIDCError) as exc:
            bridge.begin_authorization(
                client_id="synapse",
                redirect_uri="https://evil.example/cb",
                scope="openid",
                state="st",
            )
        assert exc.value.error == "invalid_redirect_uri"

    def test_authorize_rejects_idnp_when_client_not_allowed(self):
        bridge = _bridge_with_client(allow_idnp=False)
        with pytest.raises(OIDCError) as exc:
            bridge.begin_authorization(
                client_id="synapse",
                redirect_uri="https://msg.md-chat.eu/_synapse/client/oidc/callback",
                scope="openid idnp",
                state="st",
                request_idnp=True,
            )
        assert exc.value.error == "access_denied"

    def test_full_flow_without_idnp(self):
        bridge = _bridge_with_client()
        envelope = bridge.begin_authorization(
            client_id="synapse",
            redirect_uri="https://msg.md-chat.eu/_synapse/client/oidc/callback",
            scope="openid",
            state="opaque-state",
            nonce="nonce-1",
        )
        attrs = MPassAttributes(
            verified=True,
            birth_year=1995,
            given_name="Ion",
            idnp="2002001234567",
            loa=LOA.LOA2,
            name_id="persistent-sub-1",
        )
        code, redirect_uri, state = bridge.complete_authorization(
            relay_state=envelope["relay_state"], saml_attributes=attrs
        )
        assert state == "opaque-state"
        assert redirect_uri.endswith("/oidc/callback")

        body = bridge.exchange_code(
            code=code,
            client_id="synapse",
            client_secret="s3cret",
            redirect_uri="https://msg.md-chat.eu/_synapse/client/oidc/callback",
        )
        assert body["token_type"] == "Bearer"
        assert "id_token" in body
        assert "access_token" in body

        # ID token payload (unsigned dev token = base64 payload).
        header_b64, payload_b64, _ = body["id_token"].split(".")
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        assert payload["sub"] == "persistent-sub-1"
        assert payload["iss"] == "https://msg.md-chat.eu"
        assert payload["aud"] == "synapse"
        assert payload["nonce"] == "nonce-1"
        assert payload["acr"] == "md.gov.mpass.loa2"
        assert payload["age_band"] == "26-35"
        assert payload["prenume"] == "Ion"
        assert payload["verified"] is True
        assert "idnp" not in payload  # critical assertion

        # /userinfo
        userinfo = bridge.userinfo(body["access_token"])
        assert userinfo["sub"] == "persistent-sub-1"
        assert "idnp" not in userinfo

    def test_code_cannot_be_reused(self):
        bridge = _bridge_with_client()
        envelope = bridge.begin_authorization(
            client_id="synapse",
            redirect_uri="https://msg.md-chat.eu/_synapse/client/oidc/callback",
            scope="openid",
            state="x",
        )
        attrs = MPassAttributes(verified=True, name_id="nid", loa=LOA.LOA1)
        code, _, _ = bridge.complete_authorization(relay_state=envelope["relay_state"], saml_attributes=attrs)
        bridge.exchange_code(
            code=code,
            client_id="synapse",
            client_secret="s3cret",
            redirect_uri="https://msg.md-chat.eu/_synapse/client/oidc/callback",
        )
        with pytest.raises(OIDCError) as exc:
            bridge.exchange_code(
                code=code,
                client_id="synapse",
                client_secret="s3cret",
                redirect_uri="https://msg.md-chat.eu/_synapse/client/oidc/callback",
            )
        assert exc.value.error == "invalid_grant"

    def test_wrong_client_secret_rejected(self):
        bridge = _bridge_with_client()
        env = bridge.begin_authorization(
            client_id="synapse",
            redirect_uri="https://msg.md-chat.eu/_synapse/client/oidc/callback",
            scope="openid",
            state="x",
        )
        attrs = MPassAttributes(verified=True, name_id="nid", loa=LOA.LOA1)
        code, _, _ = bridge.complete_authorization(relay_state=env["relay_state"], saml_attributes=attrs)
        with pytest.raises(OIDCError) as exc:
            bridge.exchange_code(
                code=code,
                client_id="synapse",
                client_secret="wrong",
                redirect_uri="https://msg.md-chat.eu/_synapse/client/oidc/callback",
            )
        assert exc.value.error == "invalid_client"


class TestPKCE:
    def test_s256_verifier_round_trip(self):
        verifier = "abc" * 14  # >= 43 chars
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        assert _verify_pkce(verifier, challenge)
        assert not _verify_pkce("wrong", challenge)


# ---------------------------------------------------------------------------
# MSign
# ---------------------------------------------------------------------------


class TestMSign:
    def test_signature_request_payload_shape(self):
        req = SignatureRequest(document=b"hello world", mime_type="application/pdf")
        payload = req.as_soap_payload(client_id="md-chat-client-id")
        assert payload["ClientID"] == "md-chat-client-id"
        assert payload["Document"]["ContentType"] == "application/pdf"
        assert base64.b64decode(payload["Document"]["Content"]) == b"hello world"
        assert payload["SignatureOptions"]["Visible"] is False

    def test_parses_pascalcase_response(self):
        resp = {
            "SignedDocument": base64.b64encode(b"PDF").decode(),
            "SignatureID": "sig-001",
            "CertificateChain": ["cert-1", "cert-2"],
        }
        result = SignatureResult.from_soap_response(resp)
        assert result.signed_document == b"PDF"
        assert result.signature_id == "sig-001"
        assert result.certificate_chain == ("cert-1", "cert-2")

    def test_parses_snakecase_response(self):
        resp = {
            "signed_document": base64.b64encode(b"DOC").decode(),
            "signature_id": "sig-x",
        }
        result = SignatureResult.from_soap_response(resp)
        assert result.signed_document == b"DOC"
        assert result.signature_id == "sig-x"

    def test_missing_signed_document_raises(self):
        with pytest.raises(MSignError):
            SignatureResult.from_soap_response({"SignatureID": "x"})

    def test_client_uses_injected_invoker(self):
        captured: dict[str, Any] = {}

        def fake_invoker(payload: Any) -> dict[str, Any]:
            captured["payload"] = payload
            return {
                "SignedDocument": base64.b64encode(b"signed-pdf").decode(),
                "SignatureID": "sig-42",
            }

        client = MSignClient(
            wsdl_url="https://msign.gov.md/services/sign?wsdl",
            client_id="md-chat",
            invoker=fake_invoker,
        )
        result = client.sign(SignatureRequest(document=b"orig"))
        assert result.signed_document == b"signed-pdf"
        assert result.signature_id == "sig-42"
        assert captured["payload"]["ClientID"] == "md-chat"

    def test_client_without_client_id_refuses(self):
        client = MSignClient(wsdl_url="x", client_id="", invoker=lambda p: {})
        with pytest.raises(MSignError):
            client.sign(SignatureRequest(document=b"x"))


# ---------------------------------------------------------------------------
# Flask blueprint
# ---------------------------------------------------------------------------


def _make_test_app() -> tuple[Flask, OIDCBridge, MSignClient]:
    from md_chat_ai.api.identity import register_identity_routes
    from md_chat_ai.identity.mpass_saml import MPassSamlSP

    app = Flask(__name__)
    bridge = _bridge_with_client(allow_idnp=False)
    sp = MPassSamlSP(
        entity_id="https://msg.md-chat.eu/saml/sp",
        acs_url="https://msg.md-chat.eu/api/v1/identity/saml/acs",
        slo_url="https://msg.md-chat.eu/api/v1/identity/saml/slo",
        sp_cert_path="/nonexistent/sp.crt",
        sp_key_path="/nonexistent/sp.key",
        idp_metadata_url="https://mpass.gov.md/Metadata",
    )

    def fake_invoker(payload: Any) -> dict[str, Any]:
        return {
            "SignedDocument": base64.b64encode(b"signed-by-msign").decode(),
            "SignatureID": "sig-test",
        }

    msign = MSignClient(
        wsdl_url="https://msign.gov.md/services/sign?wsdl",
        client_id="md-chat-test",
        invoker=fake_invoker,
    )
    register_identity_routes(app, bridge=bridge, saml_sp=sp, msign_client=msign)
    return app, bridge, msign


class TestBlueprint:
    def test_discovery_endpoint(self):
        app, _, _ = _make_test_app()
        client = app.test_client()
        resp = client.get("/.well-known/openid-configuration")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["issuer"].startswith("https://msg.md-chat")
        assert "token_endpoint" in data

    def test_jwks_endpoint_returns_empty_when_unsigned(self):
        app, _, _ = _make_test_app()
        client = app.test_client()
        resp = client.get("/oidc/jwks.json")
        assert resp.status_code == 200
        assert resp.get_json() == {"keys": []}

    def test_saml_metadata_endpoint(self):
        app, _, _ = _make_test_app()
        client = app.test_client()
        resp = client.get("/api/v1/identity/saml/metadata")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["entity_id"] == "https://msg.md-chat.eu/saml/sp"
        assert "settings" in data
        assert data["settings"]["sp"]["entityId"] == "https://msg.md-chat.eu/saml/sp"

    def test_msign_endpoint_round_trip(self):
        app, _, _ = _make_test_app()
        client = app.test_client()
        document = base64.b64encode(b"PDF-PLAIN").decode()
        resp = client.post(
            "/api/v1/identity/msign/sign",
            json={"document_b64": document, "mime_type": "application/pdf"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["signature_id"] == "sig-test"
        assert base64.b64decode(data["signed_document_b64"]) == b"signed-by-msign"

    def test_msign_endpoint_rejects_missing_document(self):
        app, _, _ = _make_test_app()
        client = app.test_client()
        resp = client.post("/api/v1/identity/msign/sign", json={})
        assert resp.status_code == 400

    def test_token_endpoint_e2e_via_internal_helper(self):
        from md_chat_ai.api.identity import _test_inject_authorization

        app, bridge, _ = _make_test_app()
        attrs = MPassAttributes(
            verified=True,
            birth_year=1990,
            given_name="Ana",
            loa=LOA.LOA2,
            name_id="ana-sub",
        )
        pending = {
            "client_id": "synapse",
            "redirect_uri": "https://msg.md-chat.eu/_synapse/client/oidc/callback",
            "scopes": {"openid"},
            "state": "state-x",
            "nonce": "nonce-x",
            "code_challenge": None,
            "code_challenge_method": None,
            "request_idnp": False,
            "policy_purpose": "chat_account_provisioning",
            "issued_at": 0,
        }
        code, redirect_uri, state = _test_inject_authorization(app, relay_state="rs-1", attrs=attrs, pending=pending)
        client = app.test_client()
        resp = client.post(
            "/oidc/token",
            data={
                "code": code,
                "client_id": "synapse",
                "client_secret": "s3cret",
                "redirect_uri": redirect_uri,
            },
        )
        assert resp.status_code == 200, resp.data
        body = resp.get_json()
        assert "id_token" in body and "access_token" in body
        # userinfo
        userinfo = client.get(
            "/oidc/userinfo",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        assert userinfo.status_code == 200
        data = userinfo.get_json()
        assert data["prenume"] == "Ana"
        assert "idnp" not in data
