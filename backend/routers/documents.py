from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from backend.flows.document_extract_flow import extract_text_from_bytes
from backend.flows.index_flow import index_admin_document_upload
from backend.flows.storage_flow import DOCUMENT_BUCKET, upload_request_file_with_content
from backend.middleware.jwt_auth import get_current_user

router = APIRouter()


def _require_admin(user: dict[str, Any]) -> None:
    if (user.get("role") or "").lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_admin_document(
    request: Request,
    background_tasks: BackgroundTasks,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_admin(user)
    upload, content = await upload_request_file_with_content(
        request,
        bucket=DOCUMENT_BUCKET,
        prefix=f"admin/{user['sub']}",
    )
    fields = upload.get("fields") or {}
    title = fields.get("title") or upload["filename"]
    description = fields.get("description")
    file_type = fields.get("file_type") or upload["filename"].split(".")[-1].lower()
    extracted_text = extract_text_from_bytes(
        filename=upload["filename"],
        content=content,
        content_type=upload.get("content_type"),
    )
    background_tasks.add_task(
        index_admin_document_upload,
        storage_path=upload["path"],
        public_url=upload["public_url"],
        title=title,
        content=extracted_text,
        file_type=file_type,
        uploaded_by=user["sub"],
        description=description,
    )
    return {
        "ok": True,
        "upload": upload,
        "indexing": {
            "scheduled": True,
            "source_type": "admin_document",
            "content_chars": len(extracted_text),
        },
    }
