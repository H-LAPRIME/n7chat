from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.db.supabase import execute, fetch_one
from backend.flows.storage_flow import PROFILE_BUCKET, upload_request_file
from backend.middleware.jwt_auth import get_current_user
from backend.models.profile import StudentProfileUpdate, TeacherProfileUpdate

router = APIRouter()


@router.get("/me")
def get_profile(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return user


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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile update not allowed")

    refreshed = fetch_one("SELECT id FROM users WHERE id = %(id)s", {"id": user["sub"]})
    return {**user, "updated": bool(refreshed)}


@router.post("/photo", status_code=status.HTTP_201_CREATED)
async def upload_profile_photo(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    upload = await upload_request_file(
        request,
        bucket=PROFILE_BUCKET,
        prefix=f"{user['sub']}/photos",
        max_bytes=5 * 1024 * 1024,
    )
    return {"ok": True, "upload": upload}
