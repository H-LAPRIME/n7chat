from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from psycopg.types.json import Jsonb

from backend.db.supabase import fetch_all, fetch_one, get_supabase_client
from backend.db.vector import delete_document_chunks
from backend.flows.document_extract_flow import extract_text_from_bytes
from backend.flows.index_flow import index_admin_document_upload, resolve_admin_document_source_type
from backend.flows.storage_flow import DOCUMENT_BUCKET, upload_request_file_with_content
from backend.middleware.jwt_auth import get_current_user
from backend.models.courses import AdminDocumentUpdate

router = APIRouter()


def _require_admin(user: dict[str, Any]) -> None:
    if (user.get("role") or "").lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


def _normalize_optional_uuid(value: str | None, field_name: str) -> str | None:
    if value is None or not str(value).strip():
        return None
    try:
        return str(UUID(str(value).strip()))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field_name} must be a valid UUID") from exc


def _normalize_source_id(source_id: str) -> str:
    try:
        return str(UUID(source_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="source_id must be a valid UUID") from exc


def _document_or_404(source_id: str) -> dict[str, Any]:
    source_id = _normalize_source_id(source_id)
    row = fetch_one(
        """
        SELECT
          source_id,
          source_type,
          source_url,
          title,
          file_type,
          visibility_scope,
          filiere_id,
          module_id,
          metadata,
          created_at
        FROM document_chunks
        WHERE source_table = 'storage.documents'
          AND source_id = %(source_id)s::uuid
        ORDER BY chunk_index ASC, created_at ASC
        LIMIT 1
        """,
        {"source_id": source_id},
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return dict(row)


def _document_response(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata") or {}
    return {
        "id": str(row["source_id"]),
        "source_id": str(row["source_id"]),
        "title": row.get("title"),
        "description": metadata.get("description"),
        "document_category": metadata.get("document_category") or row.get("source_type"),
        "source_type": row.get("source_type"),
        "file_url": row.get("source_url"),
        "file_type": row.get("file_type"),
        "visibility_scope": row.get("visibility_scope"),
        "filiere_id": str(row["filiere_id"]) if row.get("filiere_id") else None,
        "module_id": str(row["module_id"]) if row.get("module_id") else None,
        "storage_path": metadata.get("storage_path"),
        "uploaded_by": metadata.get("uploaded_by"),
        "uploader_name": metadata.get("uploader_name"),
        "uploader_role": metadata.get("uploader_role"),
        "accessibility": metadata.get("accessibility"),
        "chunk_count": row.get("chunk_count", 1),
        "created_at": row.get("created_at"),
    }


@router.get("")
def list_admin_documents(
    user: dict[str, Any] = Depends(get_current_user),
    limit: int = 100,
) -> list[dict[str, Any]]:
    _require_admin(user)
    rows = fetch_all(
        """
        SELECT
          source_id,
          source_type,
          source_url,
          title,
          file_type,
          visibility_scope,
          filiere_id,
          module_id,
          metadata,
          MIN(created_at) AS created_at,
          COUNT(*) AS chunk_count
        FROM document_chunks
        WHERE source_table = 'storage.documents'
        GROUP BY
          source_id, source_type, source_url, title, file_type,
          visibility_scope, filiere_id, module_id, metadata
        ORDER BY MIN(created_at) DESC
        LIMIT %(limit)s
        """,
        {"limit": limit},
    )
    return [_document_response(dict(row)) for row in rows]


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
    document_category = fields.get("document_category") or fields.get("category") or "admin_document"
    visibility_scope = fields.get("visibility_scope") or "public"
    filiere_id = fields.get("filiere_id") or None
    module_id = fields.get("module_id") or None
    source_type = resolve_admin_document_source_type(document_category)
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
        uploader_name=user.get("email") or "Admin",
        description=description,
        document_category=document_category,
        visibility_scope=visibility_scope,
        filiere_id=filiere_id,
        module_id=module_id,
    )
    return {
        "ok": True,
        "upload": upload,
        "indexing": {
            "scheduled": True,
            "source_type": source_type,
            "document_category": document_category,
            "visibility_scope": visibility_scope,
            "filiere_id": filiere_id,
            "module_id": module_id,
            "content_chars": len(extracted_text),
        },
    }


@router.patch("/{source_id}")
def update_admin_document(
    source_id: str,
    body: AdminDocumentUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_admin(user)
    source_id = _normalize_source_id(source_id)
    current = _document_or_404(source_id)
    metadata = dict(current.get("metadata") or {})
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        return _document_response(current)

    title = payload.get("title", current.get("title"))
    description = payload.get("description", metadata.get("description"))
    document_category = payload.get("document_category", metadata.get("document_category") or current.get("source_type"))
    source_type = resolve_admin_document_source_type(document_category)
    visibility_scope = payload.get("visibility_scope", current.get("visibility_scope") or "public")
    filiere_id = _normalize_optional_uuid(payload.get("filiere_id", current.get("filiere_id")), "filiere_id")
    module_id = _normalize_optional_uuid(payload.get("module_id", current.get("module_id")), "module_id")

    if visibility_scope == "public":
        filiere_id = None
        module_id = None
    elif visibility_scope == "filiere":
        module_id = None
    elif visibility_scope == "module":
        filiere_id = None
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="visibility_scope must be public, filiere, or module")

    metadata.update(
        {
            "description": description,
            "document_category": document_category,
            "visibility_scope": visibility_scope,
            "filiere_id": filiere_id,
            "module_id": module_id,
        }
    )
    row = fetch_one(
        """
        UPDATE document_chunks
        SET
          source_type = %(source_type)s,
          title = %(title)s,
          source_name = %(title)s,
          visibility_scope = %(visibility_scope)s,
          filiere_id = %(filiere_id)s::uuid,
          module_id = %(module_id)s::uuid,
          metadata = %(metadata)s::jsonb
        WHERE source_table = 'storage.documents'
          AND source_id = %(source_id)s::uuid
        RETURNING
          source_id, source_type, source_url, title, file_type, visibility_scope,
          filiere_id, module_id, metadata, created_at
        """,
        {
            "source_id": source_id,
            "source_type": source_type,
            "title": title,
            "visibility_scope": visibility_scope,
            "filiere_id": filiere_id,
            "module_id": module_id,
            "metadata": Jsonb(metadata),
        },
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    response = _document_response(dict(row))
    response["updated"] = True
    return response


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_document(
    source_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    _require_admin(user)
    source_id = _normalize_source_id(source_id)
    current = _document_or_404(source_id)
    storage_path = (current.get("metadata") or {}).get("storage_path")
    deleted = delete_document_chunks(source_id=source_id)
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if storage_path:
        try:
            get_supabase_client().storage.from_(DOCUMENT_BUCKET).remove([storage_path])
        except Exception:
            pass
