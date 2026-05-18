"""Health and readiness endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from flask import Blueprint, jsonify

from .. import __version__
from ..config import CONFIG

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    return jsonify(
        {
            "status": "healthy",
            "service": "md-chat-ai",
            "version": __version__,
            "timestamp": datetime.now(UTC).isoformat(),
            "config": {
                "neo4j_configured": bool(CONFIG.neo4j_password),
                "router_configured": bool(CONFIG.router_key),
                "infobip_configured": bool(CONFIG.infobip_key),
            },
            "ai_act_disclosure": True,
        }
    )


@bp.get("/ready")
def ready():
    if not CONFIG.is_configured:
        return jsonify({"ready": False, "reason": "config_incomplete"}), 503
    return jsonify({"ready": True})
