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


def public_storage_url(bucket: str, storage_path: str) -> str:
    return _public_url(bucket, storage_path)


def download_storage_file(bucket: str, storage_path: str) -> bytes:
    content = get_supabase_client().storage.from_(bucket).download(storage_path)
    return bytes(content)


async def upload_request_file(
    request: Request,
    *,
    bucket: str,
    prefix: str,
    max_bytes: int = MAX_UPLOAD_BYTES,
    required_fields: tuple[str, ...] = (),
    allowed_content_types: tuple[str, ...] = (),
    allowed_content_type_prefixes: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Read multipart field ``file`` and upload it to a Supabase Storage bucket."""
    upload, _content = await upload_request_file_with_content(
        request,
        bucket=bucket,
        prefix=prefix,
        max_bytes=max_bytes,
        required_fields=required_fields,
        allowed_content_types=allowed_content_types,
        allowed_content_type_prefixes=allowed_content_type_prefixes,
    )
    return upload


async def upload_request_file_with_content(
    request: Request,
    *,
    bucket: str,
    prefix: str,
    max_bytes: int = MAX_UPLOAD_BYTES,
    required_fields: tuple[str, ...] = (),
    allowed_content_types: tuple[str, ...] = (),
    allowed_content_type_prefixes: tuple[str, ...] = (),
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
    content_type_allowed = (
        not allowed_content_types
        or content_type in allowed_content_types
        or any(content_type.startswith(prefix) for prefix in allowed_content_type_prefixes)
    )
    if not content_type_allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {content_type}",
        )

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
