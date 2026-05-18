"""HTTP routes for the MPass SAML to OIDC bridge.

The blueprint is mounted under ``/api/v1/identity`` by
:func:`md_chat_ai.api.create_app`. Sister routes for OIDC discovery
(``/.well-known/openid-configuration``) and the OIDC endpoints
(``/oidc/...``) are registered at the application root.

License: Apache 2.0.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from flask import Blueprint, Flask, jsonify, redirect, request

from ..config import CONFIG
from ..identity import (
    MPassAttributes,
    MPassSamlSP,
    MSignClient,
    MSignError,
    OIDCBridge,
    OIDCError,
    SignatureRequest,
    build_discovery_document,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Blueprint factories
# ---------------------------------------------------------------------------


def _load_signing_key() -> str | None:
    path = CONFIG.oidc_signing_key_path
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        logger.warning("oidc: unable to read signing key at %s", path)
        return None


def _build_saml_sp() -> MPassSamlSP:
    return MPassSamlSP(
        entity_id=CONFIG.mpass_sp_entity_id,
        acs_url=CONFIG.mpass_sp_acs_url,
        slo_url=CONFIG.mpass_sp_slo_url,
        sp_cert_path=CONFIG.mpass_sp_cert_path,
        sp_key_path=CONFIG.mpass_sp_key_path,
        idp_metadata_url=CONFIG.mpass_idp_metadata_url,
        idp_metadata_path=CONFIG.mpass_idp_metadata_path,
    )


def _build_bridge() -> OIDCBridge:
    return OIDCBridge(
        issuer=CONFIG.oidc_issuer,
        signing_key_pem=_load_signing_key(),
        signing_kid=CONFIG.oidc_signing_kid,
        id_token_ttl=CONFIG.oidc_id_token_ttl,
        code_ttl=CONFIG.oidc_code_ttl,
    )


def register_identity_routes(
    app: Flask,
    *,
    bridge: OIDCBridge | None = None,
    saml_sp: MPassSamlSP | None = None,
    msign_client: MSignClient | None = None,
) -> None:
    """Wire the identity blueprint plus the OIDC root endpoints into ``app``.

    Splitting setup from a single :func:`create_app` factory lets tests
    pass in fake collaborators (in-memory MPass, fake MSign invoker)
    without touching disk or the network.
    """
    bridge = bridge or _build_bridge()
    saml_sp = saml_sp or _build_saml_sp()
    msign_client = msign_client or MSignClient.from_config(CONFIG)

    app.extensions["mpass_bridge"] = bridge
    app.extensions["mpass_saml_sp"] = saml_sp
    app.extensions["msign_client"] = msign_client

    app.register_blueprint(_build_blueprint(), url_prefix="/api/v1/identity")
    app.register_blueprint(_build_oidc_root_blueprint())


# ---------------------------------------------------------------------------
# /api/v1/identity blueprint — SAML SP endpoints + MSign REST facade
# ---------------------------------------------------------------------------


def _build_blueprint() -> Blueprint:
    bp = Blueprint("identity", __name__)

    @bp.get("/saml/metadata")
    def saml_metadata() -> Any:
        sp: MPassSamlSP = _ext("mpass_saml_sp")
        return jsonify(
            {
                "entity_id": sp.entity_id,
                "acs_url": sp.acs_url,
                "slo_url": sp.slo_url,
                "idp_metadata_url": sp.idp_metadata_url,
                "settings": sp.settings_dict(),
            }
        )

    @bp.post("/saml/acs")
    def saml_acs() -> Any:
        """SAML AssertionConsumerService — exchanges assertion for OIDC code."""
        sp: MPassSamlSP = _ext("mpass_saml_sp")
        bridge: OIDCBridge = _ext("mpass_bridge")
        relay_state = request.form.get("RelayState", "")
        if not relay_state:
            return jsonify({"error": "missing RelayState"}), 400
        try:
            attrs = sp.process_response(_request_data())
        except Exception as exc:
            logger.exception("saml/acs: response invalid")
            return jsonify({"error": "invalid_saml_response", "detail": str(exc)}), 400
        try:
            code, redirect_uri, state = bridge.complete_authorization(relay_state=relay_state, saml_attributes=attrs)
        except OIDCError as exc:
            return jsonify(exc.as_dict()), 400
        sep = "&" if "?" in redirect_uri else "?"
        return redirect(f"{redirect_uri}{sep}code={code}&state={state}", code=302)

    @bp.post("/msign/sign")
    def msign_sign() -> Any:
        """REST wrapper around MSign — accepts JSON ``{document_b64, mime_type}``."""
        client: MSignClient = _ext("msign_client")
        payload = request.get_json(silent=True) or {}
        doc_b64 = payload.get("document_b64")
        mime = payload.get("mime_type", "application/pdf")
        if not doc_b64:
            return jsonify({"error": "document_b64 is required"}), 400
        import base64

        try:
            document = base64.b64decode(doc_b64)
        except Exception:
            return jsonify({"error": "document_b64 is not valid base64"}), 400
        try:
            result = client.sign(SignatureRequest(document=document, mime_type=mime, purpose="md-chat"))
        except MSignError as exc:
            return jsonify({"error": "msign_failure", "detail": str(exc)}), 502
        return jsonify(
            {
                "signature_id": result.signature_id,
                "signed_document_b64": base64.b64encode(result.signed_document).decode("ascii"),
                "certificate_chain": list(result.certificate_chain),
            }
        )

    return bp


# ---------------------------------------------------------------------------
# Root-level OIDC blueprint — discovery, authorize, token, userinfo, jwks
# ---------------------------------------------------------------------------


def _build_oidc_root_blueprint() -> Blueprint:
    bp = Blueprint("oidc", __name__)

    @bp.get("/.well-known/openid-configuration")
    def discovery() -> Any:
        return jsonify(build_discovery_document(CONFIG.oidc_issuer))

    @bp.get("/oidc/jwks.json")
    def jwks() -> Any:
        bridge: OIDCBridge = _ext("mpass_bridge")
        return jsonify(bridge.jwks())

    @bp.get("/oidc/authorize")
    def authorize() -> Any:
        bridge: OIDCBridge = _ext("mpass_bridge")
        sp: MPassSamlSP = _ext("mpass_saml_sp")
        try:
            envelope = bridge.begin_authorization(
                client_id=request.args["client_id"],
                redirect_uri=request.args["redirect_uri"],
                scope=request.args.get("scope", "openid"),
                state=request.args.get("state", ""),
                nonce=request.args.get("nonce"),
                code_challenge=request.args.get("code_challenge"),
                code_challenge_method=request.args.get("code_challenge_method"),
                request_idnp="idnp" in request.args.get("scope", "").split(),
            )
        except OIDCError as exc:
            return jsonify(exc.as_dict()), 400
        except KeyError as exc:
            return jsonify({"error": "invalid_request", "missing": str(exc)}), 400
        try:
            saml_env = sp.build_authn_request(_request_data(), relay_state=envelope["relay_state"])
        except Exception as exc:
            logger.exception("oidc/authorize: failed to build SAML AuthnRequest")
            return jsonify({"error": "saml_failure", "detail": str(exc)}), 500
        return redirect(saml_env.redirect_url, code=302)

    @bp.post("/oidc/token")
    def token() -> Any:
        bridge: OIDCBridge = _ext("mpass_bridge")
        form = request.form
        try:
            body = bridge.exchange_code(
                code=form["code"],
                client_id=form["client_id"],
                client_secret=form.get("client_secret"),
                redirect_uri=form["redirect_uri"],
                code_verifier=form.get("code_verifier"),
            )
        except OIDCError as exc:
            return jsonify(exc.as_dict()), 400
        except KeyError as exc:
            return jsonify({"error": "invalid_request", "missing": str(exc)}), 400
        return jsonify(body)

    @bp.get("/oidc/userinfo")
    def userinfo() -> Any:
        bridge: OIDCBridge = _ext("mpass_bridge")
        auth = request.headers.get("Authorization", "")
        if not auth.lower().startswith("bearer "):
            return jsonify({"error": "invalid_request"}), 401
        token_value = auth.split(None, 1)[1].strip()
        try:
            return jsonify(bridge.userinfo(token_value))
        except OIDCError as exc:
            return jsonify(exc.as_dict()), 401

    return bp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ext(name: str) -> Any:
    from flask import current_app

    try:
        return current_app.extensions[name]
    except KeyError as exc:  # pragma: no cover — wired by register_identity_routes
        raise RuntimeError(f"identity extension {name!r} not registered") from exc


def _request_data() -> dict[str, Any]:
    """Build the ``OneLogin_Saml2_Auth`` request dict from Flask's request."""
    return {
        "https": "on" if request.scheme == "https" else "off",
        "http_host": request.host,
        "server_port": request.environ.get("SERVER_PORT", ""),
        "script_name": request.path,
        "get_data": request.args.to_dict(),
        "post_data": request.form.to_dict(),
    }


# ---------------------------------------------------------------------------
# Convenience for tests / explicit registration
# ---------------------------------------------------------------------------


# Public test seam: a lightweight callback that builds an
# authorization code from a fake MPassAttributes object so the test
# suite can exercise /oidc/token without driving a real SAML flow.
def _test_inject_authorization(
    app: Flask,
    *,
    relay_state: str,
    attrs: MPassAttributes,
    pending: dict[str, Any],
) -> tuple[str, str, str]:
    bridge: OIDCBridge = app.extensions["mpass_bridge"]
    bridge._pending_authorizations[relay_state] = pending  # type: ignore[attr-defined]
    return bridge.complete_authorization(relay_state=relay_state, saml_attributes=attrs)
