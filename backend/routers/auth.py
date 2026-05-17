from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from os import environ
from pathlib import Path
from typing import Any

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status

from backend.db.supabase import execute, fetch_one
from backend.middleware.jwt_auth import ALGORITHM, get_current_user
from backend.models.auth import (
    ACCESS_TOKEN_MINUTES,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")

router = APIRouter()

REFRESH_TOKEN_DAYS = 30


def _jwt_secret() -> str:
    secret = environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is missing from backend/.env")
    return secret


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify an admin-created password hash.

    Supports bcrypt via passlib when installed. A constant-time plain compare is
    accepted only for development seed placeholders, so local demos keep working.
    """
    if password_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            from passlib.context import CryptContext

            context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return bool(context.verify(password, password_hash))
        except Exception:
            return False

    if password_hash.startswith("dev-"):
        return hmac.compare_digest(password, password_hash)

    return False


def _access_token_for(user: dict[str, Any]) -> str:
    now = _utcnow()
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "is_active": bool(user.get("is_active", True)),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=ALGORITHM)


def _store_refresh_token(user_id: str) -> str:
    token = secrets.token_urlsafe(48)
    expires_at = _utcnow() + timedelta(days=REFRESH_TOKEN_DAYS)
    execute(
        """
        INSERT INTO refresh_tokens (user_id, token, expires_at, revoked)
        VALUES (%(user_id)s, %(token)s, %(expires_at)s, FALSE)
        """,
        {
            "user_id": user_id,
            "token": _hash_refresh_token(token),
            "expires_at": expires_at.replace(tzinfo=None),
        },
    )
    return token


def _issue_tokens(user: dict[str, Any]) -> TokenResponse:
    return TokenResponse(
        access_token=_access_token_for(user),
        refresh_token=_store_refresh_token(str(user["id"])),
    )


def _fetch_active_user(user_id: str) -> dict[str, Any]:
    user = fetch_one(
        """
        SELECT id, email, role, is_active
        FROM users
        WHERE id = %(id)s
        """,
        {"id": user_id},
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    return dict(user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    user = fetch_one(
        """
        SELECT id, email, password_hash, role, is_active
        FROM users
        WHERE email = %(email)s
        """,
        {"email": body.email.lower()},
    )
    if not user or not _verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    execute(
        "UPDATE users SET last_login = NOW(), updated_at = NOW() WHERE id = %(id)s",
        {"id": user["id"]},
    )
    return _issue_tokens(dict(user))


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest) -> TokenResponse:
    token_hash = _hash_refresh_token(body.refresh_token)
    stored = fetch_one(
        """
        SELECT id, user_id, expires_at, revoked
        FROM refresh_tokens
        WHERE token = %(token)s
        """,
        {"token": token_hash},
    )
    if not stored or stored.get("revoked"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    expires_at = stored["expires_at"]
    if expires_at.replace(tzinfo=timezone.utc) <= _utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    execute(
        "UPDATE refresh_tokens SET revoked = TRUE WHERE id = %(id)s",
        {"id": stored["id"]},
    )
    user = _fetch_active_user(str(stored["user_id"]))
    return _issue_tokens(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    body: LogoutRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    execute(
        """
        UPDATE refresh_tokens
        SET revoked = TRUE
        WHERE token = %(token)s AND user_id = %(user_id)s
        """,
        {"token": _hash_refresh_token(body.refresh_token), "user_id": user["sub"]},
    )


@router.get("/me")
def auth_me(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return user
