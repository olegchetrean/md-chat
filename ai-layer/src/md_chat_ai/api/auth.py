"""Flask blueprint exposing MD-Chat authentication endpoints.

Routes (mounted under ``/api/v1/auth`` when registered by the application
factory — NOT yet wired in ``api/__init__.py``; that is a deliberate manual
step pending review):

- ``POST /phone/send-code``  body: ``{phone_number, country_code}``
- ``POST /phone/verify``     body: ``{phone_number, country_code, code}``
- ``POST /mfa/setup``        body: ``{account_name}``
- ``POST /mfa/verify``       body: ``{secret, code}``
- ``POST /pin/setup``        body: ``{user_id, pin, wrapped_keys_b64}``
- ``POST /pin/recover``      body: ``{user_id, pin}``

All hot-path PII (phone numbers, codes, PINs) is hashed or AEAD-wrapped
before any persistence. PII is never logged. Responses use ``error`` codes,
not free-form messages, to keep i18n / disclosure clean.

Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import base64

from flask import Blueprint, jsonify, request

from ..auth import phone_verification, pin_backup, totp_mfa

bp = Blueprint("auth", __name__)


def _bad(msg: str, status: int = 400):
    return jsonify({"ok": False, "error": msg}), status


# ---------------------------------------------------------------------------
# Phone verification.
# ---------------------------------------------------------------------------


@bp.post("/phone/send-code")
def phone_send_code():
    data = request.get_json(silent=True) or {}
    phone = data.get("phone_number")
    country = data.get("country_code")
    user_id = data.get("user_id") or request.headers.get("X-User-Id")
    if not phone or not country or not user_id:
        return _bad("missing_fields")
    accept_lang = request.headers.get("Accept-Language")
    result = phone_verification.send_phone_verification_code_sync(
        user_id=user_id,
        phone_number=phone,
        country_code=country,
        accept_language=accept_lang,
    )
    if result.ok:
        return jsonify({"ok": True}), 200
    status = 429 if result.error in {"cooldown_active", "too_many_requests"} else 400
    payload: dict = {"ok": False, "error": result.error}
    if result.cooldown_until is not None:
        payload["cooldown_until"] = result.cooldown_until
    return jsonify(payload), status


@bp.post("/phone/verify")
def phone_verify():
    data = request.get_json(silent=True) or {}
    code = data.get("code")
    user_id = data.get("user_id") or request.headers.get("X-User-Id")
    if not code or not user_id:
        return _bad("missing_fields")
    result = phone_verification.verify_phone_code_sync(user_id=user_id, code=code)
    if result.ok:
        return jsonify({"ok": True}), 200
    status = 429 if result.error == "too_many_attempts" else 400
    return jsonify({"ok": False, "error": result.error}), status


# ---------------------------------------------------------------------------
# TOTP MFA.
# ---------------------------------------------------------------------------


@bp.post("/mfa/setup")
def mfa_setup():
    data = request.get_json(silent=True) or {}
    account_name = data.get("account_name") or data.get("user_id")
    if not account_name:
        return _bad("missing_account_name")
    bundle = totp_mfa.setup_mfa(account_name)
    return (
        jsonify(
            {
                "ok": True,
                "qr_uri": bundle.qr_uri,
                "secret": bundle.secret,
                "backup_codes": bundle.backup_codes,
                # Caller persists these hashes; raw codes returned only once.
                "backup_hashes": bundle.backup_hashes,
            }
        ),
        200,
    )


@bp.post("/mfa/verify")
def mfa_verify():
    data = request.get_json(silent=True) or {}
    secret = data.get("secret")
    code = data.get("code")
    if not secret or not code:
        return _bad("missing_fields")
    backup_hashes = data.get("backup_hashes") or []
    if totp_mfa.verify_totp(secret, code):
        return jsonify({"ok": True, "method": "totp"}), 200
    # Try as backup code if backup_hashes were supplied.
    if backup_hashes:
        used, remaining = totp_mfa.verify_backup_code(code, list(backup_hashes))
        if used:
            return (
                jsonify({"ok": True, "method": "backup", "remaining_hashes": remaining}),
                200,
            )
    return _bad("invalid_code", 401)


# ---------------------------------------------------------------------------
# PIN backup (Signal SVR3-pattern stub — local wrap/unwrap only).
# ---------------------------------------------------------------------------


@bp.post("/pin/setup")
def pin_setup():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or request.headers.get("X-User-Id")
    pin = data.get("pin")
    wrapped_b64 = data.get("wrapped_keys_b64") or data.get("plaintext_keys_b64")
    if not user_id or not pin or not wrapped_b64:
        return _bad("missing_fields")
    try:
        plaintext = base64.b64decode(wrapped_b64)
    except Exception:
        return _bad("invalid_base64")
    bundle = pin_backup.wrap_keys(pin, plaintext)
    pin_backup.store_bundle(user_id, bundle)
    return jsonify({"ok": True, "bundle": bundle.to_json()}), 201


@bp.post("/pin/recover")
def pin_recover():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or request.headers.get("X-User-Id")
    pin = data.get("pin")
    if not user_id or not pin:
        return _bad("missing_fields")
    bundle = pin_backup.load_bundle(user_id)
    if bundle is None:
        return _bad("not_found", 404)
    try:
        plaintext = pin_backup.unwrap_keys(pin, bundle)
    except pin_backup.InvalidPin:
        return _bad("invalid_pin", 401)
    return (
        jsonify(
            {
                "ok": True,
                "wrapped_keys_b64": base64.b64encode(plaintext).decode("ascii"),
            }
        ),
        200,
    )
