from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status

from backend.db.supabase import execute, fetch_all, fetch_one
from backend.flows.index_flow import trigger_index_course
from backend.flows.storage_flow import COURSE_BUCKET, upload_request_file
from backend.middleware.jwt_auth import get_current_user
from backend.models.courses import CourseCreate, CourseUpdate

router = APIRouter()

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
    if not module_id or (user.get("role") or "").lower() != "teacher":
        return
    owns_module = fetch_one(
        "SELECT id FROM modules WHERE id = %(module_id)s AND teacher_id = %(teacher_id)s",
        {"module_id": module_id, "teacher_id": user.get("teacher_id")},
    )
    if not owns_module:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Module not assigned")


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
          c.title,
          c.description,
          c.file_url,
          c.file_type,
          c.created_at,
          m.name AS module_name,
          m.code AS module_code,
          f.name AS filiere_name,
          e.first_name AS teacher_first_name,
          e.last_name AS teacher_last_name
        FROM courses c
        LEFT JOIN modules m ON m.id = c.module_id
        LEFT JOIN filieres f ON f.id = m.filiere_id
        LEFT JOIN enseignants e ON e.id = c.uploaded_by
        WHERE (%(module_id)s IS NULL OR c.module_id = %(module_id)s)
          AND (%(file_type)s IS NULL OR c.file_type::text = %(file_type)s)
          AND (
            %(search)s IS NULL
            OR c.title ILIKE %(search_pattern)s
            OR c.description ILIKE %(search_pattern)s
            OR m.name ILIKE %(search_pattern)s
          )
        ORDER BY c.created_at DESC
        LIMIT %(limit)s
        """,
        {
            "module_id": module_id,
            "file_type": file_type,
            "search": search,
            "search_pattern": f"%{search}%" if search else None,
            "limit": limit,
        },
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

    if user.get("role") == "teacher":
        owns_module = fetch_one(
            "SELECT id FROM modules WHERE id = %(module_id)s AND teacher_id = %(teacher_id)s",
            {"module_id": body.module_id, "teacher_id": teacher_id},
        )
        if not owns_module:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Module not assigned")

    row = fetch_one(
        """
        INSERT INTO courses (module_id, title, description, file_url, file_type, uploaded_by)
        VALUES (%(module_id)s, %(title)s, %(description)s, %(file_url)s, %(file_type)s, %(uploaded_by)s)
        RETURNING *
        """,
        {
            "module_id": body.module_id,
            "title": body.title,
            "description": body.description,
            "file_url": body.file_url,
            "file_type": body.file_type,
            "uploaded_by": teacher_id,
        },
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create course")

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

    _assert_teacher_can_use_module(payload.get("module_id"), user)
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
    background_tasks.add_task(trigger_index_course, course_id)
    return dict(row)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    _require_teacher_or_admin(user)
    _assert_course_write_access(course_id, user)
    execute("DELETE FROM courses WHERE id = %(id)s", {"id": course_id})


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_course_file(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    owner_id = _require_teacher_profile(user)
    upload = await upload_request_file(
        request,
        bucket=COURSE_BUCKET,
        prefix=f"{owner_id}/course-files",
    )
    return {"ok": True, "upload": upload}
