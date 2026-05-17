"""MPass SAML to OIDC bridge for MD-Chat.

This package contains the thin identity bridge that allows MD-Chat
(and Synapse, which speaks OIDC but not SAML) to authenticate users
against Moldova's national identity providers:

* **MPass** (https://mpass.gov.md) — SAML 2.0 IdP operated by AGE
  (Agentia de Guvernare Electronica). Provides EVO / mobile-eID /
  USB-token / username-password authentication and returns identity
  attributes plus a LOA (Level of Assurance: LOA1, LOA2, LOA3).

* **MSign** (https://msign.gov.md) — SOAP service for qualified
  electronic signatures (eIDAS-aspiring; not yet eIDAS-notified at
  the time of writing).

The bridge consists of three components:

1. :mod:`md_chat_ai.identity.mpass_saml`
       SAML 2.0 Service Provider that talks to MPass and converts the
       returned SAML assertion into a normalized internal claim dict.

2. :mod:`md_chat_ai.identity.oidc_bridge`
       OpenID Connect OP (Provider) that exposes a discovery document,
       an authorization endpoint that forwards the user to MPass via
       SAML, a callback that issues short-lived authorization codes,
       and token / userinfo endpoints that surface the minimized OIDC
       claim set to Synapse and other downstream clients.

3. :mod:`md_chat_ai.identity.msign_client`
       Thin SOAP wrapper around the MSign WSDL exposed as a small REST
       facade so application code can request a qualified signature
       without learning SOAP.

Data minimization
-----------------
By default the bridge **does not** request or release ``IDNP`` (the
Moldovan national personal code) — GDPR Art. 5(1)(c) data
minimization. Only ``verified`` (boolean), ``age_band`` (coarse
bucket) and ``prenume`` (given name) are released to chat clients.
IDNP can be requested in a second, explicit consent flow scoped to a
specific legal purpose (e.g. signing a qualified document via MSign).

License
-------
Apache License 2.0 — see ``ai-layer/LICENSE``.
"""

from __future__ import annotations

from .mpass_saml import (
    AttributeReleasePolicy,
    LOA,
    MPassAttributes,
    MPassSamlSP,
    map_birth_year_to_age_band,
    map_loa_to_acr,
    saml_attributes_to_oidc_claims,
)
from .msign_client import MSignClient, MSignError, SignatureRequest, SignatureResult
from .oidc_bridge import (
    AuthorizationCode,
    OIDCBridge,
    OIDCClaims,
    OIDCError,
    build_discovery_document,
)

__all__ = [
    "AttributeReleasePolicy",
    "AuthorizationCode",
    "LOA",
    "MPassAttributes",
    "MPassSamlSP",
    "MSignClient",
    "MSignError",
    "OIDCBridge",
    "OIDCClaims",
    "OIDCError",
    "SignatureRequest",
    "SignatureResult",
    "build_discovery_document",
    "map_birth_year_to_age_band",
    "map_loa_to_acr",
    "saml_attributes_to_oidc_claims",
]
