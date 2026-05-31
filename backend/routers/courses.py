from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status

from backend.db.supabase import execute, fetch_all, fetch_one
from backend.db.vector import delete_course_chunks
from backend.flows.document_extract_flow import extract_text_from_bytes
from backend.flows.index_flow import index_course_content, trigger_index_course
from backend.flows.storage_flow import COURSE_BUCKET, upload_request_file_with_content
from backend.middleware.jwt_auth import get_current_user
from backend.models.courses import CourseCreate, CourseUpdate

router = APIRouter()


def _normalize_uuid(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    clean = value.strip()
    if not clean:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} is required",
        )
    try:
        return str(UUID(clean))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be a valid UUID",
        ) from exc


def _slug_code(value: str, prefix: str = "MOD") -> str:
    slug = re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")
    return (slug or prefix)[:40]


def _unique_module_code(base: str) -> str:
    code = _slug_code(base)
    candidate = code
    index = 1
    while fetch_one("SELECT id FROM modules WHERE code = %(code)s", {"code": candidate}):
        index += 1
        candidate = f"{code[:35]}-{index}"
    return candidate


def _infer_upload_filiere_id(fields: dict[str, str], user: dict[str, Any]) -> str:
    if fields.get("filiere_id"):
        return str(_normalize_uuid(fields.get("filiere_id"), "filiere_id"))

    if (user.get("role") or "").lower() == "teacher" and user.get("teacher_id"):
        row = fetch_one(
            """
            SELECT filiere_id
            FROM modules
            WHERE teacher_id = %(teacher_id)s AND filiere_id IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"teacher_id": user["teacher_id"]},
        )
        if row and row.get("filiere_id"):
            return str(row["filiere_id"])

    rows = fetch_all("SELECT id FROM filieres ORDER BY created_at DESC LIMIT 2")
    if len(rows) == 1:
        return str(rows[0]["id"])
    if rows:
        return str(rows[0]["id"])

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="No filiere exists. Create a filiere first or provide filiere_id.",
    )


def _create_upload_module(fields: dict[str, str], user: dict[str, Any], fallback_title: str) -> str:
    filiere_id = _infer_upload_filiere_id(fields, user)
    module_name = (fields.get("module_name") or fallback_title).strip()
    if not module_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="module_name or title is required to auto-create a module",
        )
    module_code = fields.get("module_code") or _unique_module_code(module_name)
    semester = int(fields.get("semester") or 1)

    row = fetch_one(
        """
        INSERT INTO modules (filiere_id, teacher_id, name, code, semester, description)
        VALUES (%(filiere_id)s, %(teacher_id)s, %(name)s, %(code)s, %(semester)s, %(description)s)
        RETURNING *
        """,
        {
            "filiere_id": filiere_id,
            "teacher_id": user.get("teacher_id") if user.get("role") == "teacher" else None,
            "name": module_name,
            "code": module_code,
            "semester": semester,
            "description": fields.get("module_description"),
        },
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to auto-create module")
    return str(row["id"])


def _require_teacher_or_admin(user: dict[str, Any]) -> None:
    if (user.get("role") or "").lower() not in {"teacher", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher role required")


def _require_teacher_profile(user: dict[str, Any]) -> str:
    _require_teacher_or_admin(user)
    teacher_id = user.get("teacher_id")
    if user.get("role") == "teacher" and not teacher_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher profile missing")
    return str(teacher_id) if teacher_id else str(user["sub"])


def _assert_course_write_access(course_id: str, user: dict[str, Any]) -> dict[str, Any]:
    row = fetch_one(
        """
        SELECT id, uploaded_by
        FROM courses
        WHERE id = %(id)s
        """,
        {"id": course_id},
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    role = (user.get("role") or "").lower()
    if role == "admin":
        return dict(row)
    if role == "teacher" and str(row.get("uploaded_by")) == str(user.get("teacher_id")):
        return dict(row)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course write access denied")


def _assert_teacher_can_use_module(module_id: str | None, user: dict[str, Any]) -> None:
    module_id = _normalize_uuid(module_id, "module_id")
    if not module_id or (user.get("role") or "").lower() != "teacher":
        return
    owns_module = fetch_one(
        "SELECT id FROM modules WHERE id = %(module_id)s AND teacher_id = %(teacher_id)s",
        {"module_id": module_id, "teacher_id": user.get("teacher_id")},
    )
    if not owns_module:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Module not assigned")


def _assert_teacher_can_use_filiere(filiere_id: str | None, user: dict[str, Any]) -> None:
    filiere_id = _normalize_uuid(filiere_id, "filiere_id")
    if not filiere_id or (user.get("role") or "").lower() != "teacher":
        return
    owns_filiere = fetch_one(
        """
        SELECT id
        FROM modules
        WHERE filiere_id = %(filiere_id)s AND teacher_id = %(teacher_id)s
        LIMIT 1
        """,
        {"filiere_id": filiere_id, "teacher_id": user.get("teacher_id")},
    )
    if not owns_filiere:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Filiere not assigned")


def _resolve_module_filiere(module_id: str) -> str | None:
    row = fetch_one("SELECT filiere_id FROM modules WHERE id = %(id)s", {"id": module_id})
    if not row:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="module_id not found")
    return str(row["filiere_id"]) if row.get("filiere_id") else None


def _course_audience_payload(payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    scope = payload.get("visibility_scope") or "module"
    if scope not in {"public", "filiere", "module"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid visibility_scope")

    module_id = _normalize_uuid(payload.get("module_id"), "module_id") if payload.get("module_id") else None
    filiere_id = _normalize_uuid(payload.get("filiere_id"), "filiere_id") if payload.get("filiere_id") else None

    if scope == "public":
        filiere_id = None
        module_id = None
    elif scope == "filiere":
        if not filiere_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="filiere_id is required")
        module_id = None
        _assert_teacher_can_use_filiere(filiere_id, user)
    else:
        if not module_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="module_id is required")
        _assert_teacher_can_use_module(module_id, user)
        filiere_id = _resolve_module_filiere(module_id) or filiere_id

    return {"visibility_scope": scope, "module_id": module_id, "filiere_id": filiere_id}


def _accessibility_label(scope: str | None, module_name: str | None = None, filiere_name: str | None = None) -> str:
    if scope == "public":
        return "Public"
    if scope == "filiere":
        return f"Class: {filiere_name}" if filiere_name else "Specific class"
    if scope == "module":
        return f"Module: {module_name}" if module_name else "Specific module"
    return "Specific audience"


@router.get("")
def list_courses(
    user: dict[str, Any] = Depends(get_current_user),
    module_id: str | None = Query(default=None),
    file_type: str | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT
          c.id,
          c.module_id,
          c.uploaded_by,
          c.title,
          c.description,
          c.file_url,
          c.file_type,
          c.index_status,
          COALESCE(c.visibility_scope, 'module') AS visibility_scope,
          c.filiere_id,
          c.created_at,
          m.name AS module_name,
          m.code AS module_code,
          COALESCE(cf.name, f.name) AS filiere_name,
          COALESCE(cf.code, f.code) AS filiere_code,
          e.first_name AS teacher_first_name,
          e.last_name AS teacher_last_name,
          e.teacher_code AS teacher_code,
          CONCAT_WS(' ', e.first_name, e.last_name) AS uploader_name,
          'teacher' AS uploader_role
        FROM courses c
        LEFT JOIN modules m ON m.id = c.module_id
        LEFT JOIN filieres f ON f.id = m.filiere_id
        LEFT JOIN filieres cf ON cf.id = c.filiere_id
        LEFT JOIN enseignants e ON e.id = c.uploaded_by
        WHERE (%(module_id)s::uuid IS NULL OR c.module_id = %(module_id)s::uuid)
          AND (
            %(role)s = 'admin'
            OR COALESCE(c.visibility_scope, 'module') = 'public'
            OR (%(role)s = 'teacher' AND c.uploaded_by = %(teacher_id)s::uuid)
            OR (
              %(role)s = 'teacher'
              AND (
                m.teacher_id = %(teacher_id)s::uuid
                OR c.filiere_id IN (
                  SELECT DISTINCT filiere_id
                  FROM modules
                  WHERE teacher_id = %(teacher_id)s::uuid
                    AND filiere_id IS NOT NULL
                )
              )
            )
            OR (
              %(role)s = 'student'
              AND (
                c.filiere_id = %(filiere_id)s::uuid
                OR m.filiere_id = %(filiere_id)s::uuid
              )
            )
          )
          AND (%(file_type)s::text IS NULL OR c.file_type::text = %(file_type)s::text)
          AND (
            %(search)s::text IS NULL
            OR c.title ILIKE %(search_pattern)s::text
            OR c.description ILIKE %(search_pattern)s::text
            OR m.name ILIKE %(search_pattern)s::text
          )
        ORDER BY c.created_at DESC
        LIMIT %(limit)s
        """,
        {
            "module_id": module_id,
            "role": (user.get("role") or "").lower(),
            "teacher_id": user.get("teacher_id"),
            "filiere_id": user.get("filiere_id"),
            "file_type": file_type,
            "search": search,
            "search_pattern": f"%{search}%" if search else None,
            "limit": limit,
        },
    )
    return [dict(row) for row in rows]


@router.get("/modules")
def list_course_modules(
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    role = (user.get("role") or "").lower()
    if role not in {"teacher", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher or admin role required")

    rows = fetch_all(
        """
        SELECT
          m.id,
          m.name,
          m.code,
          m.semester,
          m.teacher_id,
          m.filiere_id,
          f.name AS filiere_name
        FROM modules m
        LEFT JOIN filieres f ON f.id = m.filiere_id
        WHERE (%(is_admin)s = TRUE OR m.teacher_id = %(teacher_id)s)
        ORDER BY m.semester, m.name
        """,
        {
            "is_admin": role == "admin",
            "teacher_id": user.get("teacher_id"),
        },
    )
    return [dict(row) for row in rows]


@router.get("/filieres")
def list_course_filieres(
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    role = (user.get("role") or "").lower()
    if role not in {"teacher", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher or admin role required")
    rows = fetch_all(
        """
        SELECT DISTINCT f.id, f.name, f.code, d.name AS department_name
        FROM filieres f
        LEFT JOIN departments d ON d.id = f.department_id
        LEFT JOIN modules m ON m.filiere_id = f.id
        WHERE (%(is_admin)s = TRUE OR m.teacher_id = %(teacher_id)s)
        ORDER BY f.name
        """,
        {"is_admin": role == "admin", "teacher_id": user.get("teacher_id")},
    )
    return [dict(row) for row in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseCreate,
    background_tasks: BackgroundTasks,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_teacher_or_admin(user)
    teacher_id = user.get("teacher_id")
    if user.get("role") == "teacher" and not teacher_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher profile missing")

    audience = _course_audience_payload(body.model_dump(), user)
    row = fetch_one(
        """
        INSERT INTO courses (
          module_id, filiere_id, visibility_scope, title, description, file_url, file_type, uploaded_by
        )
        VALUES (
          %(module_id)s, %(filiere_id)s, %(visibility_scope)s,
          %(title)s, %(description)s, %(file_url)s, %(file_type)s, %(uploaded_by)s
        )
        RETURNING *
        """,
        {
            **audience,
            "title": body.title,
            "description": body.description,
            "file_url": body.file_url,
            "file_type": body.file_type,
            "uploaded_by": teacher_id,
        },
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create course")

    execute("UPDATE courses SET index_status = 'pending' WHERE id = %(id)s", {"id": row["id"]})
    background_tasks.add_task(trigger_index_course, str(row["id"]))
    return dict(row)


@router.patch("/{course_id}")
async def update_course(
    course_id: str,
    body: CourseUpdate,
    background_tasks: BackgroundTasks,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_teacher_or_admin(user)
    _assert_course_write_access(course_id, user)
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        row = fetch_one("SELECT * FROM courses WHERE id = %(id)s", {"id": course_id})
        return dict(row) if row else {}

    if any(key in payload for key in ("visibility_scope", "module_id", "filiere_id")):
        current = fetch_one(
            "SELECT visibility_scope, module_id, filiere_id FROM courses WHERE id = %(id)s",
            {"id": course_id},
        )
        merged = {**dict(current or {}), **payload}
        payload.update(_course_audience_payload(merged, user))
    sets = ", ".join(f"{key} = %({key})s" for key in payload)
    row = fetch_one(
        f"""
        UPDATE courses
        SET {sets}
        WHERE id = %(id)s
        RETURNING *
        """,
        {**payload, "id": course_id},
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    chunk_count = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM document_chunks
        WHERE source_type = 'course'
          AND source_id = %(id)s::uuid
        """,
        {"id": course_id},
    )
    if chunk_count and chunk_count["count"]:
        execute(
            """
            UPDATE document_chunks
            SET
              title = %(title)s,
              source_name = %(title)s,
              source_url = %(file_url)s,
              module_id = %(module_id)s::uuid,
              filiere_id = %(filiere_id)s::uuid,
              visibility_scope = %(visibility_scope)s,
              file_type = %(file_type)s,
              metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
                'uploaded_by', %(uploaded_by)s::text,
                'uploader_name', COALESCE(
                  (SELECT CONCAT_WS(' ', first_name, last_name) FROM enseignants WHERE id = %(uploaded_by)s::uuid),
                  %(uploader_name)s::text
                ),
                'uploader_role', 'teacher',
                'accessibility', %(accessibility)s::text
              )
            WHERE source_type = 'course'
              AND source_id = %(id)s::uuid
            """,
            {
                "id": course_id,
                "title": row.get("title"),
                "file_url": row.get("file_url"),
                "module_id": row.get("module_id"),
                "filiere_id": row.get("filiere_id"),
                "visibility_scope": row.get("visibility_scope") or "module",
                "file_type": row.get("file_type"),
                "uploaded_by": row.get("uploaded_by"),
                "uploader_name": user.get("email") if user.get("role") == "admin" else None,
                "accessibility": _accessibility_label(row.get("visibility_scope")),
            },
        )
    else:
        execute("UPDATE courses SET index_status = 'pending' WHERE id = %(id)s", {"id": course_id})
        background_tasks.add_task(trigger_index_course, course_id)
    return dict(row)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    _require_teacher_or_admin(user)
    _assert_course_write_access(course_id, user)
    delete_course_chunks(course_id)
    execute("DELETE FROM courses WHERE id = %(id)s", {"id": course_id})


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_course_file(
    request: Request,
    background_tasks: BackgroundTasks,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    owner_id = _require_teacher_profile(user)
    upload, content = await upload_request_file_with_content(
        request,
        bucket=COURSE_BUCKET,
        prefix=f"{owner_id}/course-files",
    )
    fields = upload.get("fields") or {}
    title = fields.get("title") or upload["filename"]
    description = fields.get("description")
    file_type = fields.get("file_type") or upload["filename"].split(".")[-1].lower()
    visibility_scope = fields.get("visibility_scope") or "module"
    module_id = (
        _normalize_uuid(fields.get("module_id"), "module_id")
        if fields.get("module_id")
        else _create_upload_module(fields, user, title) if visibility_scope == "module" else None
    )
    audience = _course_audience_payload(
        {
            "visibility_scope": visibility_scope,
            "module_id": module_id,
            "filiere_id": fields.get("filiere_id"),
        },
        user,
    )
    row = fetch_one(
        """
        INSERT INTO courses (
          module_id, filiere_id, visibility_scope,
          title, description, file_url, file_type, uploaded_by, index_status
        )
        VALUES (
          %(module_id)s, %(filiere_id)s, %(visibility_scope)s,
          %(title)s, %(description)s, %(file_url)s, %(file_type)s, %(uploaded_by)s, 'pending'
        )
        RETURNING *
        """,
        {
            **audience,
            "title": title,
            "description": description,
            "file_url": upload["public_url"],
            "file_type": file_type,
            "uploaded_by": user.get("teacher_id"),
        },
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create course from upload")

    extracted_text = extract_text_from_bytes(
        filename=upload["filename"],
        content=content,
        content_type=upload.get("content_type"),
    )
    background_tasks.add_task(index_course_content, str(row["id"]), extracted_text)
    response: dict[str, Any] = {
        "ok": True,
        "upload": upload,
        "course": dict(row),
        "indexing": {
            "scheduled": True,
            "content_chars": len(extracted_text),
            "source": "uploaded_file",
        },
    }

    return response
