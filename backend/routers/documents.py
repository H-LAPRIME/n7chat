from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.flows.storage_flow import DOCUMENT_BUCKET, upload_request_file
from backend.middleware.jwt_auth import get_current_user

router = APIRouter()


def _require_admin(user: dict[str, Any]) -> None:
    if (user.get("role") or "").lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_admin_document(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_admin(user)
    upload = await upload_request_file(
        request,
        bucket=DOCUMENT_BUCKET,
        prefix=f"admin/{user['sub']}",
    )
    return {"ok": True, "upload": upload}
