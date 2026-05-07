"""
Authentication routes: register, login, refresh, logout and password reset.
"""

import random
import string
import os
import tempfile
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_mailman import EmailMessage
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from app import db
from app.auth.jwt_utils import create_access_token, create_refresh_token, decode_token, require_auth
from app.models.user import User
from app.utils.storage import profile_photo_url, upload_profile_photo_to_supabase
from config import Config

auth_bp = Blueprint("auth", __name__)

ALLOWED_AVATAR_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def _allowed_avatar(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS


@auth_bp.post("/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "If the account exists, a code has been sent"}), 200

    code = "".join(random.choices(string.digits, k=6))
    user.reset_code = code
    user.reset_code_expires = datetime.utcnow() + timedelta(minutes=15)
    db.session.commit()

    try:
        msg = EmailMessage(
            subject="Votre code de recuperation - n7chat",
            body=f"Votre code de reinitialisation de mot de passe est : {code}\n\nCe code expirera dans 15 minutes.",
            from_email=Config.MAIL_DEFAULT_SENDER,
            to=[email],
        )
        msg.send()
    except Exception as e:
        print(f"SMTP Error: {e}")
        return jsonify({"error": "Failed to send email. Check SMTP settings."}), 500

    return jsonify({"message": "Password reset code sent"}), 200


@auth_bp.post("/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    code = data.get("code")
    new_password = data.get("new_password")

    if not email or not code or not new_password:
        return jsonify({"error": "Email, code and new password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or user.reset_code != code:
        return jsonify({"error": "Invalid code or email"}), 400

    if not user.reset_code_expires or user.reset_code_expires < datetime.utcnow():
        return jsonify({"error": "The code has expired"}), 400

    user.set_password(new_password)
    user.reset_code = None
    user.reset_code_expires = None
    db.session.commit()

    return jsonify({"message": "Password reset successful"}), 200


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")
    role = data.get("role", "student")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400
    if role not in ("student", "admin"):
        return jsonify({"error": "Invalid role"}), 400

    user = User(email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "A user with this email already exists"}), 409

    return jsonify({"message": "User registered", "user": user.to_dict()}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify(
        {
            "access_token": create_access_token(user.id, user.role),
            "refresh_token": create_refresh_token(user.id),
        }
    ), 200


@auth_bp.post("/refresh")
def refresh():
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

    user = db.session.get(User, payload["sub"])
    if not user:
        return jsonify({"error": "User not found"}), 401

    return jsonify({"access_token": create_access_token(user.id, user.role)}), 200


@auth_bp.post("/logout")
@require_auth
def logout():
    return jsonify({"message": "Logged out"}), 200


@auth_bp.post("/me/avatar")
@require_auth
def upload_avatar():
    user = db.session.get(User, request.current_user.get("sub"))
    if not user:
        return jsonify({"error": "User not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "" or not _allowed_avatar(file.filename):
        return jsonify({"error": "Invalid or missing image file"}), 400

    original = secure_filename(file.filename)
    extension = original.rsplit(".", 1)[1].lower()
    filename = f"{user.id}/avatar.{extension}"
    temp_path = tempfile.gettempdir()
    os.makedirs(temp_path, exist_ok=True)
    local_path = os.path.join(temp_path, f"{user.id}-avatar.{extension}")
    file.save(local_path)

    try:
        user.avatar_url = upload_profile_photo_to_supabase(local_path, filename)
        db.session.commit()
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)

    return jsonify({"message": "Avatar uploaded", "avatar": user.avatar_url}), 200


@auth_bp.get("/me")
@require_auth
def me():
    user = db.session.get(User, request.current_user.get("sub"))
    if not user:
        return jsonify({"error": "User not found"}), 404

    local_name = user.email.split("@", 1)[0].replace(".", " ").replace("_", " ").title()
    return jsonify(
        {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "name": local_name or "Utilisateur n7",
            "bio": "Membre de la communaute n7chat.",
            "avatar": user.avatar_url or profile_photo_url("avatar.png"),
        }
    ), 200
