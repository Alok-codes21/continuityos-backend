
from flask import Blueprint, jsonify, current_app

health_bp = Blueprint("health", __name__)


@health_bp.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "application": "ContinuityOS",
        "database": "not_configured",
        "message": "Application is running."
    }), 200

