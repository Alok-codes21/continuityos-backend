
import os

from flask import Flask


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "development-only-change-this"
    )

    from app.routes.health import health_bp
    from app.web.routes import web_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(web_bp)

    return app
