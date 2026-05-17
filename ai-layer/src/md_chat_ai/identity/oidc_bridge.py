"""OpenID Connect bridge in front of MPass SAML.

Synapse and most modern relying parties (mobile apps, browser clients)
speak OpenID Connect, not SAML. This module hosts a minimal OIDC OP
(Provider) that turns each successful MPass SAML assertion into a
signed JWT ID token that downstream clients can verify.

Endpoints exposed (full URLs are built by :mod:`md_chat_ai.api.identity`):

* ``GET  /.well-known/openid-configuration`` — discovery
* ``GET  /oidc/authorize`` — kicks off the SAML SSO flow
* ``POST /api/v1/identity/saml/acs`` — SAML AssertionConsumerService;
  exchanges the SAML response for a short-lived authorization code
* ``POST /oidc/token`` — exchanges the code for an ID token
* ``GET  /oidc/userinfo`` — returns claims for a valid bearer token

Token signing
-------------
ID tokens are signed RS256 with a key loaded from disk. The same key
is published at the JWKS endpoint so Synapse can verify tokens.

This module is intentionally self-contained: tokens, codes and JWKS
are all generated locally; we never proxy MPass tokens. The IdP
identity travels in the ``iss_idp`` claim.

License: Apache 2.0.
"""

from __future__ import annotations

import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping

from .mpass_saml import (
    AttributeReleasePolicy,
    MPassAttributes,
    saml_attributes_to_oidc_claims,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Discovery document
# ---------------------------------------------------------------------------


def build_discovery_document(issuer: str) -> dict[str, Any]:
    """Return the JSON body for ``/.well-known/openid-configuration``.

    The shape is intentionally minimal: we list what we actually
    implement. Synapse only needs ``issuer``, ``authorization_endpoint``,
    ``token_endpoint``, ``userinfo_endpoint`` and ``jwks_uri``.
    """
    issuer = issuer.rstrip("/")
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oidc/authorize",
        "token_endpoint": f"{issuer}/oidc/token",
        "userinfo_endpoint": f"{issuer}/oidc/userinfo",
        "jwks_uri": f"{issuer}/oidc/jwks.json",
        "end_session_endpoint": f"{issuer}/oidc/logout",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "scopes_supported": [
            "openid",
            "profile_minimized",
            "age_band",
            "idnp",  # only granted via second-consent flow
        ],
        "claims_supported": [
            "sub",
            "iss",
            "aud",
            "exp",
            "iat",
            "acr",
            "verified",
            "age_band",
            "prenume",
            "iss_idp",
        ],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
        ],
        "code_challenge_methods_supported": ["S256"],
        "ui_locales_supported": ["ro", "ru", "en"],
    }


# ---------------------------------------------------------------------------
# In-memory code & token state (production replaces with Redis)
# ---------------------------------------------------------------------------


@dataclass
class AuthorizationCode:
    """A one-shot code issued at the SAML callback and burned at /token."""

    code: str
    client_id: str
    redirect_uri: str
    claims: Mapping[str, Any]
    expires_at: float
    nonce: str | None = None
    code_challenge: str | None = None
    code_challenge_method: str | None = None
    used: bool = False

    def is_expired(self, *, now: float | None = None) -> bool:
        return (now or time.time()) >= self.expires_at


@dataclass
class OIDCClaims:
    """Claims surfaced to the relying party after token exchange."""

    sub: str
    acr: str
    iss: str
    iss_idp: str
    iat: int
    exp: int
    verified: bool | None = None
    age_band: str | None = None
    prenume: str | None = None
    email: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        out = {
            "sub": self.sub,
            "iss": self.iss,
            "iss_idp": self.iss_idp,
            "acr": self.acr,
            "iat": self.iat,
            "exp": self.exp,
        }
        if self.verified is not None:
            out["verified"] = self.verified
        if self.age_band is not None:
            out["age_band"] = self.age_band
        if self.prenume is not None:
            out["prenume"] = self.prenume
        if self.email is not None:
            out["email"] = self.email
        out.update(dict(self.extra))
        return out


class OIDCError(Exception):
    """Raised for protocol-level errors (invalid_grant, invalid_request, …)."""

    def __init__(self, error: str, description: str = "") -> None:
        super().__init__(description or error)
        self.error = error
        self.description = description

    def as_dict(self) -> dict[str, str]:
        return {"error": self.error, "error_description": self.description}


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------


class OIDCBridge:
    """Stateful glue between MPass SAML and downstream OIDC clients.

    The bridge is deliberately small. Authorization codes and bearer
    tokens are held in-memory; replace ``codes`` / ``tokens`` with a
    Redis-backed mapping in production to survive process restarts.
    """

    def __init__(
        self,
        *,
        issuer: str,
        signing_key_pem: str | None = None,
        signing_kid: str = "mpass-bridge-1",
        id_token_ttl: int = 600,
        code_ttl: int = 120,
        registered_clients: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.signing_key_pem = signing_key_pem
        self.signing_kid = signing_kid
        self.id_token_ttl = id_token_ttl
        self.code_ttl = code_ttl
        self.codes: MutableMapping[str, AuthorizationCode] = {}
        self.tokens: MutableMapping[str, OIDCClaims] = {}
        self._clients: dict[str, dict[str, Any]] = {
            cid: dict(meta) for cid, meta in (registered_clients or {}).items()
        }

    # -- client registration ---------------------------------------------

    def register_client(
        self,
        client_id: str,
        *,
        redirect_uris: list[str],
        client_secret: str | None = None,
        allow_idnp: bool = False,
    ) -> None:
        """Register a relying party (Synapse, mobile, ...).

        ``allow_idnp=True`` only flips the *capability* — the user still
        has to consent through the second flow before IDNP is released.
        """
        self._clients[client_id] = {
            "redirect_uris": list(redirect_uris),
            "client_secret": client_secret,
            "allow_idnp": bool(allow_idnp),
        }

    def _require_client(self, client_id: str) -> dict[str, Any]:
        try:
            return self._clients[client_id]
        except KeyError as exc:
            raise OIDCError("invalid_client", f"unknown client_id {client_id!r}") from exc

    # -- authorize -------------------------------------------------------

    def begin_authorization(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: str,
        nonce: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
        request_idnp: bool = False,
    ) -> dict[str, Any]:
        """Validate an /authorize request and return what the SAML layer needs.

        We don't redirect here; the Flask route does that. We return a
        plain dict so the route remains the one place that talks HTTP.
        """
        client = self._require_client(client_id)
        if redirect_uri not in client["redirect_uris"]:
            raise OIDCError("invalid_redirect_uri", redirect_uri)
        scopes = set(scope.split())
        if "openid" not in scopes:
            raise OIDCError("invalid_scope", "missing openid")
        if request_idnp and not client.get("allow_idnp"):
            raise OIDCError("access_denied", "client not permitted to request IDNP")
        if code_challenge_method and code_challenge_method != "S256":
            raise OIDCError("invalid_request", "PKCE method must be S256")

        relay_state = secrets.token_urlsafe(32)
        # We stash the authorize parameters keyed by relay state — the
        # SAML callback will look them back up.
        self._pending_authorizations[relay_state] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "request_idnp": request_idnp,
            "policy_purpose": "msign_qualified_signature" if request_idnp else "chat_account_provisioning",
            "issued_at": time.time(),
        }
        return {"relay_state": relay_state, "scopes": list(scopes)}

    # mapping kept lazy so the dataclass __init__ does not need to be
    # extended every time a new field is added.
    @property
    def _pending_authorizations(self) -> MutableMapping[str, dict[str, Any]]:
        if not hasattr(self, "_pending_state"):
            self._pending_state: MutableMapping[str, dict[str, Any]] = {}
        return self._pending_state

    # -- callback --------------------------------------------------------

    def complete_authorization(
        self,
        *,
        relay_state: str,
        saml_attributes: MPassAttributes,
    ) -> tuple[str, str, str]:
        """Convert a successful SAML response into an OIDC authorization code.

        Returns ``(code, redirect_uri, state)`` — the caller (Flask
        route) builds the redirect with these.
        """
        pending = self._pending_authorizations.pop(relay_state, None)
        if pending is None:
            raise OIDCError("invalid_request", "unknown or expired relay state")

        policy = AttributeReleasePolicy(purpose=pending["policy_purpose"])
        if pending["request_idnp"]:
            policy = policy.with_idnp(purpose=pending["policy_purpose"])
        claims = saml_attributes_to_oidc_claims(saml_attributes, policy)

        code_value = secrets.token_urlsafe(32)
        self.codes[code_value] = AuthorizationCode(
            code=code_value,
            client_id=pending["client_id"],
            redirect_uri=pending["redirect_uri"],
            claims=claims,
            expires_at=time.time() + self.code_ttl,
            nonce=pending["nonce"],
            code_challenge=pending["code_challenge"],
            code_challenge_method=pending["code_challenge_method"],
        )
        return code_value, pending["redirect_uri"], pending["state"]

    # -- token -----------------------------------------------------------

    def exchange_code(
        self,
        *,
        code: str,
        client_id: str,
        client_secret: str | None,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> dict[str, Any]:
        """Burn an authorization code and return the token response body."""
        client = self._require_client(client_id)
        record = self.codes.get(code)
        if record is None or record.used:
            raise OIDCError("invalid_grant", "unknown or already-used code")
        if record.is_expired():
            del self.codes[code]
            raise OIDCError("invalid_grant", "code expired")
        if record.client_id != client_id:
            raise OIDCError("invalid_grant", "client mismatch")
        if record.redirect_uri != redirect_uri:
            raise OIDCError("invalid_grant", "redirect_uri mismatch")

        expected_secret = client.get("client_secret")
        if expected_secret and client_secret != expected_secret:
            raise OIDCError("invalid_client", "bad client_secret")

        if record.code_challenge:
            if not code_verifier:
                raise OIDCError("invalid_grant", "PKCE verifier required")
            if not _verify_pkce(code_verifier, record.code_challenge):
                raise OIDCError("invalid_grant", "PKCE verification failed")

        record.used = True
        now = int(time.time())
        claims = dict(record.claims)
        sub = claims.pop("sub", None) or _hashed_sub(record.code)
        oidc_claims = OIDCClaims(
            sub=sub,
            iss=self.issuer,
            iss_idp=claims.pop("iss_idp", "https://mpass.gov.md"),
            acr=claims.pop("acr", "md.gov.mpass.loa1"),
            iat=now,
            exp=now + self.id_token_ttl,
            verified=claims.pop("verified", None),
            age_band=claims.pop("age_band", None),
            prenume=claims.pop("prenume", None),
            email=claims.pop("email", None),
            extra=claims,
        )

        id_token = self._sign_id_token(oidc_claims, audience=client_id, nonce=record.nonce)
        access_token = secrets.token_urlsafe(32)
        self.tokens[access_token] = oidc_claims

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.id_token_ttl,
            "id_token": id_token,
            "scope": "openid profile_minimized",
        }

    # -- userinfo --------------------------------------------------------

    def userinfo(self, bearer_token: str) -> dict[str, Any]:
        claims = self.tokens.get(bearer_token)
        if claims is None:
            raise OIDCError("invalid_token", "unknown bearer token")
        if claims.exp < time.time():
            del self.tokens[bearer_token]
            raise OIDCError("invalid_token", "token expired")
        return claims.as_dict()

    # -- JWKS ------------------------------------------------------------

    def jwks(self) -> dict[str, Any]:
        """Publish the public half of the signing key.

        Returns an empty key set if no signing key was provided — the
        dev mode boot path uses this to avoid crashing when keys
        haven't been provisioned yet.
        """
        if not self.signing_key_pem:
            return {"keys": []}
        try:  # pragma: no cover — exercised in integration tests
            from cryptography.hazmat.primitives import serialization
        except ImportError:
            return {"keys": []}
        try:
            key = serialization.load_pem_private_key(
                self.signing_key_pem.encode("utf-8"), password=None
            )
        except Exception:
            logger.exception("oidc: failed to load signing key for JWKS")
            return {"keys": []}
        pub = key.public_key()
        numbers = pub.public_numbers()
        import base64

        def _b64u(n: int) -> str:
            length = (n.bit_length() + 7) // 8
            return base64.urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode("ascii")

        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": self.signing_kid,
                    "n": _b64u(numbers.n),
                    "e": _b64u(numbers.e),
                }
            ]
        }

    # -- internal --------------------------------------------------------

    def _sign_id_token(
        self,
        claims: OIDCClaims,
        *,
        audience: str,
        nonce: str | None,
    ) -> str:
        payload = claims.as_dict()
        payload["aud"] = audience
        if nonce:
            payload["nonce"] = nonce
        if not self.signing_key_pem:
            # Dev fallback — a clearly-unsigned token so that no
            # production verifier accepts it.
            return _unsafe_dev_token(payload)
        try:
            import jwt  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "PyJWT is required to sign ID tokens; install the 'identity' extra"
            ) from exc
        return jwt.encode(
            payload,
            self.signing_key_pem,
            algorithm="RS256",
            headers={"kid": self.signing_kid},
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """RFC 7636 S256 verification."""
    import base64
    import hashlib

    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return secrets.compare_digest(expected, code_challenge)


def _hashed_sub(seed: str) -> str:
    """Deterministic ``sub`` placeholder when MPass omits NameID (testing)."""
    import hashlib

    return "mpass-" + hashlib.sha256(seed.encode("ascii")).hexdigest()[:24]


def _unsafe_dev_token(payload: Mapping[str, Any]) -> str:
    """Emit a token with a 'none' algorithm — DEV ONLY.

    Marked unsafe so that production verifiers (which must require
    RS256) will reject it loudly.
    """
    import base64

    header = {"alg": "none", "kid": "dev-unsigned"}

    def _enc(obj: Mapping[str, Any]) -> str:
        return (
            base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode("utf-8"))
            .rstrip(b"=")
            .decode("ascii")
        )

    return f"{_enc(header)}.{_enc(payload)}."
