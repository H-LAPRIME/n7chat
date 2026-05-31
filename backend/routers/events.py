from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from backend.db.supabase import execute, fetch_all, fetch_one
from backend.flows.notify_flow import notify_event_created
from backend.middleware.jwt_auth import get_current_user
from backend.models.events import EventCreate, EventUpdate

router = APIRouter()


def _normalize_uuid(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    clean = value.strip()
    if not clean:
        return None
    try:
        return str(UUID(clean))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be a valid UUID",
        ) from exc

def _require_staff(user: dict[str, Any]) -> None:
    if (user.get("role") or "").lower() not in {"teacher", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher or admin role required")


def _assert_event_write_access(event_id: str, user: dict[str, Any]) -> dict[str, Any]:
    row = fetch_one(
        "SELECT id, created_by FROM events WHERE id = %(id)s",
        {"id": event_id},
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    role = (user.get("role") or "").lower()
    if role == "admin" or str(row.get("created_by")) == str(user.get("sub")):
        return dict(row)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Event write access denied")


def _audience_payload(payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    scope = payload.get("visibility_scope") or "public"
    filiere_id = _normalize_uuid(payload.get("filiere_id"), "filiere_id")
    module_id = _normalize_uuid(payload.get("module_id"), "module_id")
    if scope == "public":
        filiere_id = None
        module_id = None
    elif scope == "filiere":
        if not filiere_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="filiere_id is required")
        module_id = None
    elif scope == "module":
        if not module_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="module_id is required")
        module = fetch_one("SELECT filiere_id, teacher_id FROM modules WHERE id = %(id)s", {"id": module_id})
        if not module:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="module_id not found")
        if (user.get("role") or "").lower() == "teacher" and str(module.get("teacher_id")) != str(user.get("teacher_id")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Module not assigned")
        filiere_id = str(module["filiere_id"]) if module.get("filiere_id") else filiere_id
    if scope == "filiere" and (user.get("role") or "").lower() == "teacher":
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
    return {"visibility_scope": scope, "filiere_id": filiere_id, "module_id": module_id}


@router.get("")
def list_events(
    user: dict[str, Any] = Depends(get_current_user),
    upcoming_only: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT id, title, description, event_type, start_date, end_date, location,
               visibility_scope, filiere_id, module_id, created_by, created_at
        FROM events
        WHERE (%(upcoming_only)s = FALSE OR start_date >= CURRENT_TIMESTAMP)
          AND (
            %(role)s = 'admin'
            OR created_by = %(user_id)s::uuid
            OR visibility_scope = 'public'
            OR (
              %(role)s = 'teacher'
              AND (
                module_id IN (SELECT id FROM modules WHERE teacher_id = %(teacher_id)s::uuid)
                OR filiere_id IN (
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
                filiere_id = %(filiere_id)s::uuid
                OR module_id IN (SELECT id FROM modules WHERE filiere_id = %(filiere_id)s::uuid)
              )
            )
          )
        ORDER BY start_date ASC
        LIMIT %(limit)s
        """,
        {
            "upcoming_only": upcoming_only,
            "limit": limit,
            "role": (user.get("role") or "").lower(),
            "user_id": user.get("sub"),
            "teacher_id": user.get("teacher_id"),
            "filiere_id": user.get("filiere_id"),
        },
    )
    return [dict(row) for row in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_event(
    body: EventCreate,
    background_tasks: BackgroundTasks,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_staff(user)
    if body.end_date and body.end_date < body.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must be after start_date")

    audience = _audience_payload(body.model_dump(), user)
    row = fetch_one(
        """
        INSERT INTO events (
          title, description, event_type, start_date, end_date, location,
          visibility_scope, filiere_id, module_id, created_by
        )
        VALUES (
          %(title)s, %(description)s, %(event_type)s, %(start_date)s, %(end_date)s, %(location)s,
          %(visibility_scope)s, %(filiere_id)s, %(module_id)s, %(created_by)s
        )
        RETURNING *
        """,
        {
            "title": body.title,
            "description": body.description,
            "event_type": body.event_type,
            "start_date": body.start_date.replace(tzinfo=None),
            "end_date": body.end_date.replace(tzinfo=None) if body.end_date else None,
            "location": body.location,
            **audience,
            "created_by": user["sub"],
        },
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create event")

    if body.notify_students:
        background_tasks.add_task(notify_event_created, str(row["id"]))
    return dict(row)


@router.patch("/{event_id}")
def update_event(
    event_id: str,
    body: EventUpdate,
    background_tasks: BackgroundTasks,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_staff(user)
    _assert_event_write_access(event_id, user)
    payload = body.model_dump(exclude_unset=True)
    notify_students = bool(payload.pop("notify_students", False))
    if payload.get("start_date") and payload.get("end_date") and payload["end_date"] < payload["start_date"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must be after start_date")
    for key in ("start_date", "end_date"):
        if payload.get(key):
            payload[key] = payload[key].replace(tzinfo=None)

    if any(key in payload for key in ("visibility_scope", "filiere_id", "module_id")):
        current = fetch_one(
            "SELECT visibility_scope, filiere_id, module_id FROM events WHERE id = %(id)s",
            {"id": event_id},
        )
        merged = {**dict(current or {}), **payload}
        audience = _audience_payload(merged, user)
        payload.update(audience)

    if not payload:
        row = fetch_one("SELECT * FROM events WHERE id = %(id)s", {"id": event_id})
        return dict(row) if row else {}

    sets = ", ".join(f"{key} = %({key})s" for key in payload)
    row = fetch_one(
        f"""
        UPDATE events
        SET {sets}
        WHERE id = %(id)s
        RETURNING *
        """,
        {**payload, "id": event_id},
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if notify_students:
        background_tasks.add_task(notify_event_created, event_id)
    return dict(row)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    _require_staff(user)
    _assert_event_write_access(event_id, user)
    execute("DELETE FROM events WHERE id = %(id)s", {"id": event_id})
