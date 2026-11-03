
import os

from flask import Flask, jsonify
from app.extensions import db, migrate, jwt
from app import models


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-this"),
        SQLALCHEMY_DATABASE_URI=os.getenv(
            "DATABASE_URL", "sqlite:///continuityos.db"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "dev-jwt-only-change-this"),
        JWT_ACCESS_TOKEN_EXPIRES=3600,
        MAX_CONTENT_LENGTH=11 * 1024 * 1024,
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Register API blueprints inside the application factory.
    from app.auth.routes import auth_bp
    from app.projects.routes import projects_bp
    from app.ingestion.routes import ingestion_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(ingestion_bp)

    @app.get("/api/health")
    def health():
        return jsonify({
            "application": "ContinuityOS",
            "status": "running"
        })

    return app
