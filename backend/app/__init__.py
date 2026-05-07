"""
backend/app/__init__.py
────────────────────────
Flask application factory.
"""

import sys
import os

# Add the project root to sys.path so 'agents' can be imported
# We assume the project root is the parent of the 'backend' directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from flask_mailman import Mail
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

from config import Config

db = SQLAlchemy()
socketio = SocketIO()
limiter = Limiter(key_func=get_remote_address)
mail = Mail()


def _ensure_runtime_columns() -> None:
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "avatar_url" not in user_columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR"))
        db.session.commit()


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Extensions ────────────────────────────────────────────
    CORS(app, origins=[app.config["FRONTEND_URL"]])
    db.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app, cors_allowed_origins=app.config["FRONTEND_URL"])
    mail.init_app(app)

    from app.middleware.logging_middleware import register_logging
    register_logging(app)

    with app.app_context():
        from app.models.user import User
        from app.models.course import Course, Module, Enrollment
        from app.models.document import Document
        from app.models.conversation import ConversationMessage, ConversationMemory
        from app.models.notification import Notification
        db.create_all()
        _ensure_runtime_columns()

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
