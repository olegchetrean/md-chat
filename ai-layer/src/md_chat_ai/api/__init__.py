"""Flask application factory."""

from __future__ import annotations

import logging

from flask import Flask

from ..security import register_security
from .health import bp as health_bp

logger = logging.getLogger(__name__)


def create_app(
    *,
    register_identity: bool = True,
    register_auth: bool = True,
    register_eevidence: bool = True,
) -> Flask:
    app = Flask(__name__)

    # Core health endpoints — always on.
    app.register_blueprint(health_bp, url_prefix="/api")

    # Security middleware — error handler at minimum.
    try:
        register_security(app)
    except Exception:  # pragma: no cover
        logger.exception("security middleware failed to register; continuing")

    # Phone OTP + TOTP MFA + PIN backup.
    if register_auth:
        try:
            from .auth import bp as auth_bp

            app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
        except Exception:  # pragma: no cover
            logger.exception("auth blueprint failed to register; continuing")

    # eEvidence Regulation (EU 2023/1543) production order portal.
    if register_eevidence:
        try:
            from .eevidence import bp as eevidence_bp

            app.register_blueprint(eevidence_bp, url_prefix="/api/v1/legal/eevidence")
        except Exception:  # pragma: no cover
            logger.exception("eevidence blueprint failed to register; continuing")

    # MPass SAML SP + OIDC bridge + MSign client.
    if register_identity:
        try:
            from .identity import register_identity_routes

            register_identity_routes(app)
        except Exception:  # pragma: no cover
            logger.exception("identity routes failed to register; continuing")

    return app
