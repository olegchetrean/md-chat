"""Flask application factory."""

from __future__ import annotations

import logging

from flask import Flask

from .health import bp as health_bp

logger = logging.getLogger(__name__)


def create_app(*, register_identity: bool = True) -> Flask:
    app = Flask(__name__)
    app.register_blueprint(health_bp, url_prefix="/api")
    if register_identity:
        try:
            from .identity import register_identity_routes

            register_identity_routes(app)
        except Exception:  # pragma: no cover — keep boot alive in dev
            logger.exception("identity routes failed to register; continuing")
    return app
