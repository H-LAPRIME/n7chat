"""JWT Authentication Middleware.

Provides the FastAPI dependency ``get_current_user`` which:
  1. Extracts the Bearer token from the Authorization header.
  2. Verifies the JWT signature using ``JWT_SECRET`` from .env.
  3. Fetches the role-specific profile (student or enseignant) from Supabase
     and merges it into the user dict so downstream agents have all context
     they need (student_id, filiere_id, semester, teacher_id, …).

The user dict returned always contains at minimum:
  - ``sub``        : UUID of the user (from JWT)
  - ``email``      : user email
  - ``role``       : "student" | "teacher" | "admin"
  - ``is_active``  : bool

For students it also contains:
  - ``student_id`` : students.id UUID
  - ``filiere_id`` : students.filiere_id UUID
  - ``filiere_name``: name of the filière
  - ``level_id``   : students.level_id UUID
  - ``semester``   : derived from level order_number (optional)

For enseignants it also contains:
  - ``teacher_id`` : enseignants.id UUID
  - ``department_id``
"""

from __future__ import annotations

import logging
from os import environ
from pathlib import Path
from typing import Any

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.db.supabase import fetch_one

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=True)

ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _jwt_secret() -> str:
    secret = environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is missing from backend/.env")
    return secret


def _decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT, raising HTTP 401 on any failure."""
    try:
        payload = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _fetch_student_profile(user_id: str) -> dict[str, Any]:
    """Return enriched student row (with filière and level) or empty dict."""
    try:
        row = fetch_one(
            """
            SELECT
              s.id            AS student_id,
              s.filiere_id,
              s.level_id,
              s.student_code,
              s.first_name,
              s.last_name,
              s.phone,
              s.address,
              s.status,
              f.name          AS filiere_name,
              f.code          AS filiere_code,
              l.name          AS level_name,
              l.order_number  AS level_order
            FROM students s
            LEFT JOIN filieres f ON f.id = s.filiere_id
            LEFT JOIN levels   l ON l.id = s.level_id
            WHERE s.user_id = %(user_id)s
            """,
            {"user_id": user_id},
        )
        return _cast_uuids_to_strings(dict(row)) if row else {}
    except Exception as exc:
        logger.warning("Could not fetch student profile for %s: %s", user_id, exc)
        return {}


def _fetch_teacher_profile(user_id: str) -> dict[str, Any]:
    """Return enseignant row or empty dict."""
    try:
        row = fetch_one(
            """
            SELECT
              e.id             AS teacher_id,
              e.teacher_code,
              e.first_name,
              e.last_name,
              e.phone,
              e.specialization,
              e.department_id,
              e.office
            FROM enseignants e
            WHERE e.user_id = %(user_id)s
            """,
            {"user_id": user_id},
        )
        return _cast_uuids_to_strings(dict(row)) if row else {}
    except Exception as exc:
        logger.warning("Could not fetch teacher profile for %s: %s", user_id, exc)
        return {}


def _cast_uuids_to_strings(data: dict[str, Any]) -> dict[str, Any]:
    import uuid
    for k, v in data.items():
        if isinstance(v, uuid.UUID):
            data[k] = str(v)
    return data


def _enrich_user(payload: dict[str, Any]) -> dict[str, Any]:
    """Build the full user context dict from JWT payload + DB profile."""
    user_id: str = payload["sub"]
    role: str = (payload.get("role") or "student").lower()

    base: dict[str, Any] = {
        "sub": user_id,
        "id": user_id,          # alias kept for backward compat
        "email": payload.get("email", ""),
        "role": role,
        "is_active": payload.get("is_active", True),
    }

    if role == "student":
        profile = _fetch_student_profile(user_id)
        if profile:
            # Derive a rough semester from level order_number (1→S1/S2, 2→S3/S4 …)
            level_order: int | None = profile.get("level_order")
            semester: int | None = (
                (level_order * 2 - 1) if level_order else None  # first sem of year
            )
            base.update(profile)
            base["semester"] = semester
    elif role in ("teacher", "enseignant"):
        profile = _fetch_teacher_profile(user_id)
        base.update(profile)
        base["role"] = "teacher"   # normalise to "teacher"

    return base


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict[str, Any]:
    """FastAPI dependency — decode token and return the enriched user dict.

    Raises HTTP 401 if the token is missing, expired, or invalid.
    Raises HTTP 403 if the user account is inactive.
    """
    payload = _decode_token(credentials.credentials)

    user = _enrich_user(payload)

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact administration.",
        )

    return user
