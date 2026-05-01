"""
backend/app/__init__.py
────────────────────────
Flask application factory.
"""

from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO

from config import Config

socketio = SocketIO()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Extensions ────────────────────────────────────────────
    CORS(app, origins=[app.config["FRONTEND_URL"]])
    limiter.init_app(app)
    socketio.init_app(app, cors_allowed_origins=app.config["FRONTEND_URL"])

    # ── Blueprints ────────────────────────────────────────────
    from app.routes.auth_routes import auth_bp
    from app.routes.chat_routes import chat_bp
    from app.routes.document_routes import documents_bp
    from app.routes.course_routes import courses_bp
    from app.routes.analytics_routes import analytics_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(documents_bp, url_prefix="/documents")
    app.register_blueprint(courses_bp, url_prefix="/courses")
    app.register_blueprint(analytics_bp, url_prefix="/analytics")

    return app
