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
from flask_mailman import Mail
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()
socketio = SocketIO()
limiter = Limiter(key_func=get_remote_address)
mail = Mail()


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Extensions ────────────────────────────────────────────
    CORS(app, origins=[app.config["FRONTEND_URL"]])
    db.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app, cors_allowed_origins=app.config["FRONTEND_URL"])
    mail.init_app(app)

    with app.app_context():
        from app.models.user import User
        db.create_all()

    # ── Blueprints ────────────────────────────────────────────
    from app.routes.auth_routes import auth_bp
    from app.routes.chat_routes import chat_bp
    from app.routes.document_routes import documents_bp
    from app.routes.course_routes import courses_bp
    from app.routes.analytics_routes import analytics_bp
    from app.routes.notification_routes import notifications_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(documents_bp, url_prefix="/documents")
    app.register_blueprint(courses_bp, url_prefix="/courses")
    app.register_blueprint(analytics_bp, url_prefix="/analytics")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")

    return app
