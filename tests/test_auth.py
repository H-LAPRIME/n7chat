"""
tests/test_auth.py
────────────────────
Unit tests for JWT auth utilities and auth routes.
"""

import pytest
from unittest.mock import patch


class TestJWTUtils:
    def test_create_and_decode_access_token(self):
        from flask import Flask
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test_secret"
        app.config["JWT_ACCESS_EXPIRES"] = 3600
        app.config["JWT_REFRESH_EXPIRES"] = 604800

        with app.app_context():
            from backend.app.auth.jwt_utils import create_access_token, decode_token
            token = create_access_token("user-123", "student")
            payload = decode_token(token)
            assert payload["sub"] == "user-123"
            assert payload["role"] == "student"
            assert payload["type"] == "access"

    def test_require_auth_missing_header(self):
        from flask import Flask
        from backend.app.auth.jwt_utils import require_auth

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test_secret"
        app.config["JWT_ACCESS_EXPIRES"] = 3600
        app.config["JWT_REFRESH_EXPIRES"] = 604800

        @app.get("/protected")
        @require_auth
        def protected():
            return "ok"

        with app.test_client() as client:
            response = client.get("/protected")
            assert response.status_code == 401
