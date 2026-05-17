from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request, status
from starlette.datastructures import UploadFile

from backend.db.supabase import get_supabase_client

PROFILE_BUCKET = "profiles"
COURSE_BUCKET = "courses"
DOCUMENT_BUCKET = "documents"
LOGO_BUCKET = "logos"

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _clean_filename(filename: str) -> str:
    name = PurePosixPath(filename).name.strip() or "upload"
    name = re.sub(r"[^a-zA-Z0-9._-]+", "-", name)
    return name[:120] or "upload"


def _public_url(bucket: str, storage_path: str) -> str:
    return get_supabase_client().storage.from_(bucket).get_public_url(storage_path)


async def upload_request_file(
    request: Request,
    *,
    bucket: str,
    prefix: str,
    max_bytes: int = MAX_UPLOAD_BYTES,
    required_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Read multipart field ``file`` and upload it to a Supabase Storage bucket."""
    upload, _content = await upload_request_file_with_content(
        request,
        bucket=bucket,
        prefix=prefix,
        max_bytes=max_bytes,
        required_fields=required_fields,
    )
    return upload


async def upload_request_file_with_content(
    request: Request,
    *,
    bucket: str,
    prefix: str,
    max_bytes: int = MAX_UPLOAD_BYTES,
    required_fields: tuple[str, ...] = (),
) -> tuple[dict[str, Any], bytes]:
    """Upload multipart ``file`` and also return its bytes for indexing flows."""
    try:
        form = await request.form()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid multipart upload: {exc}",
        ) from exc

    file = form.get("file")
    if not isinstance(file, UploadFile):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing multipart file field named 'file'",
        )
    missing_fields = [
        field
        for field in required_fields
        if not isinstance(form.get(field), str) or not str(form.get(field)).strip()
    ]
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required multipart fields: {', '.join(missing_fields)}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds {max_bytes} bytes",
        )

    filename = _clean_filename(file.filename or "upload")
    storage_path = f"{prefix.strip('/')}/{uuid4()}-{filename}"
    content_type = file.content_type or "application/octet-stream"

    get_supabase_client().storage.from_(bucket).upload(
        storage_path,
        content,
        {"content-type": content_type, "upsert": "false"},
    )

    return {
        "bucket": bucket,
        "path": storage_path,
        "public_url": _public_url(bucket, storage_path),
        "content_type": content_type,
        "size": len(content),
        "filename": filename,
        "fields": {
            key: value
            for key, value in form.items()
            if key != "file" and isinstance(value, str)
        },
    }, content
