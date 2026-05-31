from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from backend.db.supabase import execute, fetch_all, fetch_one
from backend.flows.storage_flow import (
    LOGO_BUCKET,
    PROFILE_BUCKET,
    download_storage_file,
    public_storage_url,
    upload_request_file,
)
from backend.middleware.jwt_auth import get_current_user
from backend.models.profile import StudentProfileUpdate, TeacherProfileUpdate

router = APIRouter()


def _fresh_profile(user: dict[str, Any]) -> dict[str, Any]:
    role = (user.get("role") or "").lower()
    if role == "student":
        row = fetch_one(
            """
            SELECT
              s.phone,
              s.address,
              s.photo_url,
              s.student_code,
              s.filiere_id,
              s.level_id,
              f.name AS filiere_name,
              f.code AS filiere_code,
              l.name AS level_name
            FROM students s
            LEFT JOIN filieres f ON f.id = s.filiere_id
            LEFT JOIN levels l ON l.id = s.level_id
            WHERE s.user_id = %(user_id)s
            """,
            {"user_id": user["sub"]},
        )
        modules = []
        if row and row.get("filiere_id"):
            modules = fetch_all(
                """
                SELECT
                  m.id,
                  m.name,
                  m.code,
                  m.semester,
                  e.first_name AS teacher_first_name,
                  e.last_name AS teacher_last_name
                FROM modules m
                LEFT JOIN enseignants e ON e.id = m.teacher_id
                WHERE m.filiere_id = %(filiere_id)s
                ORDER BY m.semester, m.name
                """,
                {"filiere_id": row["filiere_id"]},
            )
        details = dict(row) if row else {}
        details["assigned_modules"] = [dict(item) for item in modules]
        details["assigned_module_count"] = len(modules)
    elif role == "teacher":
        row = fetch_one(
            """
            SELECT phone, office, photo_url, teacher_code, id AS teacher_id
            FROM enseignants
            WHERE user_id = %(user_id)s
            """,
            {"user_id": user["sub"]},
        )
        modules = []
        filieres = []
        if row and row.get("teacher_id"):
            modules = fetch_all(
                """
                SELECT
                  m.id,
                  m.name,
                  m.code,
                  m.semester,
                  m.filiere_id,
                  f.name AS filiere_name,
                  f.code AS filiere_code
                FROM modules m
                LEFT JOIN filieres f ON f.id = m.filiere_id
                WHERE m.teacher_id = %(teacher_id)s
                ORDER BY f.name, m.semester, m.name
                """,
                {"teacher_id": row["teacher_id"]},
            )
            filieres = fetch_all(
                """
                SELECT DISTINCT f.id, f.name, f.code
                FROM filieres f
                JOIN modules m ON m.filiere_id = f.id
                WHERE m.teacher_id = %(teacher_id)s
                ORDER BY f.name
                """,
                {"teacher_id": row["teacher_id"]},
            )
        details = dict(row) if row else {}
        details["assigned_modules"] = [dict(item) for item in modules]
        details["assigned_filieres"] = [dict(item) for item in filieres]
        details["assigned_module_count"] = len(modules)
        details["assigned_filiere_count"] = len(filieres)
    else:
        details = {}

    return {**user, **details}


@router.get("/me")
def get_profile(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return _fresh_profile(user)


@router.get("/assets/logo")
def get_platform_logo() -> dict[str, Any]:
    return {
        "ok": True,
        "bucket": LOGO_BUCKET,
        "path": "logo_enset.png",
        "public_url": public_storage_url(LOGO_BUCKET, "logo_enset.png"),
        "download_url": "/profile/assets/logo_enset.png",
    }


@router.get("/assets/logo_enset.png")
def get_platform_logo_file() -> Response:
    return Response(
        content=download_storage_file(LOGO_BUCKET, "logo_enset.png"),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.patch("/me")
def update_profile(
    body: StudentProfileUpdate | TeacherProfileUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    role = (user.get("role") or "").lower()
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        return user

    if role == "student":
        allowed = {key: payload[key] for key in ("phone", "address") if key in payload}
        if not allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No editable fields")
        sets = ", ".join(f"{key} = %({key})s" for key in allowed)
        execute(
            f"UPDATE students SET {sets} WHERE user_id = %(user_id)s",
            {**allowed, "user_id": user["sub"]},
        )
    elif role == "teacher":
        allowed = {key: payload[key] for key in ("phone", "office") if key in payload}
        if not allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No editable fields")
        sets = ", ".join(f"{key} = %({key})s" for key in allowed)
        execute(
            f"UPDATE enseignants SET {sets} WHERE user_id = %(user_id)s",
            {**allowed, "user_id": user["sub"]},
        )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No editable fields for this account type")

    return {**_fresh_profile(user), "updated": True}


@router.post("/photo", status_code=status.HTTP_201_CREATED)
async def upload_profile_photo(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    role = (user.get("role") or "").lower()
    if role not in {"student", "teacher"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No editable profile photo for this account type",
        )

    upload = await upload_request_file(
        request,
        bucket=PROFILE_BUCKET,
        prefix=f"{user['sub']}/photos",
        max_bytes=15 * 1024 * 1024,
        allowed_content_type_prefixes=("image/",),
    )
    if role == "student":
        execute(
            "UPDATE students SET photo_url = %(photo_url)s WHERE user_id = %(user_id)s",
            {"photo_url": upload["public_url"], "user_id": user["sub"]},
        )
    elif role == "teacher":
        execute(
            "UPDATE enseignants SET photo_url = %(photo_url)s WHERE user_id = %(user_id)s",
            {"photo_url": upload["public_url"], "user_id": user["sub"]},
        )

    return {
        "ok": True,
        "upload": upload,
        "profile": {**_fresh_profile(user), "photo_url": upload["public_url"]},
    }
