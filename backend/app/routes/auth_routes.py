"""
backend/app/routes/auth_routes.py
───────────────────────────────────
/auth  — register, login, refresh, logout
"""

import random
import string
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, url_for
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from app.auth.jwt_utils import create_access_token, create_refresh_token, decode_token, require_auth
from app import mail, db
from app.models.user import User
from flask_mailman import EmailMessage
from config import Config

auth_bp = Blueprint("auth", __name__)

# Serializer for password reset tokens
serializer = URLSafeTimedSerializer(Config.SECRET_KEY)


@auth_bp.post("/forgot-password")
def forgot_password():
    """
    POST /auth/forgot-password
    Body: { "email": str }
    Sends a 6-digit reset code via SMTP.
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        # We return 200 even if user doesn't exist for security (avoid enumeration)
        return jsonify({"message": "If the account exists, a code has been sent"}), 200

    # Generate 6-digit code
    code = ''.join(random.choices(string.digits, k=6))
    user.reset_code = code
    user.reset_code_expires = datetime.utcnow() + timedelta(minutes=15) # Code valid for 15 min
    db.session.commit()

    try:
        msg = EmailMessage(
            subject="Votre code de récupération - n7chat",
            body=f"Votre code de réinitialisation de mot de passe est : {code}\n\nCe code expirera dans 15 minutes.",
            from_email=Config.MAIL_DEFAULT_SENDER,
            to=[email]
        )
        msg.send()
    except Exception as e:
        print(f"SMTP Error: {e}")
        return jsonify({"error": "Failed to send email. Check SMTP settings."}), 500

    return jsonify({"message": "Password reset code sent"}), 200


@auth_bp.post("/reset-password")
def reset_password():
    """
    POST /auth/reset-password
    Body: { "email": str, "code": str, "new_password": str }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    code = data.get("code")
    new_password = data.get("new_password")

    if not email or not code or not new_password:
        return jsonify({"error": "Email, code and new password are required"}), 400

    user = User.query.filter_by(email=email).first()
    
    if not user or user.reset_code != code:
        return jsonify({"error": "Invalid code or email"}), 400

    if user.reset_code_expires < datetime.utcnow():
        return jsonify({"error": "The code has expired"}), 400

    # Success
    user.set_password(new_password)
    user.reset_code = None
    user.reset_code_expires = None
    db.session.commit()

    return jsonify({"message": "Password reset successful"}), 200


@auth_bp.post("/register")
# ... (rest of the existing routes)
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
    role = "admin" if email == "admin@n7chat.com" else "student"

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


@auth_bp.get("/me")
@require_auth
def me():
    """
    GET /auth/me
    Returns current user info from token.
    """
    # Use request.current_user set by @require_auth decorator
    user_data = request.current_user
    role = user_data.get("role", "student")
    user_id = user_data.get("sub", "unknown")
    
    email = "admin@n7chat.com" if role == "admin" else "student@n7chat.com"
    
    return jsonify({
        "id": user_id,
        "email": email,
        "role": role,
        "name": "Utilisateur n7",
        "bio": "Étudiant passionné à l'ENSEEIHT.",
        "avatar": "https://irvagmkpuxdeuckhawbv.supabase.co/storage/v1/object/public/profiles/avatar.png"
    }), 200
