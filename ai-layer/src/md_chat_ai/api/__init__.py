"""Flask application factory."""

from __future__ import annotations

from flask import Flask

from .health import bp as health_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(health_bp, url_prefix="/api")
    return app
