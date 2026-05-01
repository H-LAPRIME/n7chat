"""
backend/app/routes/auth_routes.py
───────────────────────────────────
/auth  — register, login, refresh, logout
"""

from flask import Blueprint, request, jsonify
from app.auth.jwt_utils import create_access_token, create_refresh_token, decode_token, require_auth

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    """
    POST /auth/register
    Body: { "email": str, "password": str, "role": "student"|"admin" }
    Admin-only role assignment handled by middleware in production.
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")
    role = data.get("role", "student")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400
    if role not in ("student", "admin"):
        return jsonify({"error": "Invalid role"}), 400

    # TODO: persist user to DB (User model)
    return jsonify({"message": "User registered", "email": email, "role": role}), 201


@auth_bp.post("/login")
def login():
    """
    POST /auth/login
    Body: { "email": str, "password": str }
    Returns access_token + refresh_token.
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    # TODO: validate against DB, fetch user_id and role
    user_id = "placeholder-user-id"
    role = "student"

    return jsonify(
        {
            "access_token": create_access_token(user_id, role),
            "refresh_token": create_refresh_token(user_id),
        }
    ), 200


@auth_bp.post("/refresh")
def refresh():
    """
    POST /auth/refresh
    Header: Authorization: Bearer <refresh_token>
    Returns new access_token.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Refresh token required"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            return jsonify({"error": "Invalid token type"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    # TODO: fetch role from DB by payload["sub"]
    role = "student"
    return jsonify({"access_token": create_access_token(payload["sub"], role)}), 200


@auth_bp.post("/logout")
@require_auth
def logout():
    """
    POST /auth/logout
    Invalidates the refresh token (DB-side blacklist TODO).
    """
    # TODO: add refresh token to blacklist in Redis/DB
    return jsonify({"message": "Logged out"}), 200
