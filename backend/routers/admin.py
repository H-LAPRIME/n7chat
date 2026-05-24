from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.db.supabase import execute, fetch_all, fetch_one
from backend.middleware.jwt_auth import get_current_user
from backend.models.admin import (
    AdminUserCreate,
    DepartmentCreate,
    FiliereCreate,
    LevelCreate,
    ModuleCreate,
    StudentAssignment,
    StudentCreate,
    TeacherCreate,
    TeacherModuleAssignment,
)

router = APIRouter()


def _require_admin(user: dict[str, Any]) -> None:
    if (user.get("role") or "").lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


def _hash_password(password: str) -> str:
    if password.startswith("dev-"):
        return password
    try:
        from passlib.context import CryptContext

        context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return context.hash(password)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password hashing unavailable: {exc}",
        ) from exc


def _insert_returning(table: str, payload: dict[str, Any]) -> dict[str, Any]:
    columns = list(payload)
    placeholders = ", ".join(f"%({column})s" for column in columns)
    column_sql = ", ".join(columns)
    row = fetch_one(
        f"""
        INSERT INTO {table} ({column_sql})
        VALUES ({placeholders})
        RETURNING *
        """,
        payload,
    )
    if not row:
        raise HTTPException(status_code=500, detail=f"Failed to create {table} row")
    return dict(row)


@router.get("/overview")
def overview(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _require_admin(user)
    return {
        "users": fetch_one("SELECT COUNT(*) AS count FROM users")["count"],
        "students": fetch_one("SELECT COUNT(*) AS count FROM students")["count"],
        "teachers": fetch_one("SELECT COUNT(*) AS count FROM enseignants")["count"],
        "departments": fetch_one("SELECT COUNT(*) AS count FROM departments")["count"],
        "filieres": fetch_one("SELECT COUNT(*) AS count FROM filieres")["count"],
        "modules": fetch_one("SELECT COUNT(*) AS count FROM modules")["count"],
    }


@router.get("/users")
def list_users(
    user: dict[str, Any] = Depends(get_current_user),
    role: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    _require_admin(user)
    rows = fetch_all(
        """
        SELECT id, email, role, is_active, last_login, created_at, updated_at
        FROM users
        WHERE (%(role)s::text IS NULL OR role::text = %(role)s::text)
        ORDER BY created_at DESC
        LIMIT %(limit)s
        """,
        {"role": role, "limit": limit},
    )
    return [dict(row) for row in rows]


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    body: AdminUserCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_admin(user)
    return _insert_returning(
        "users",
        {
            "email": body.email.lower(),
            "password_hash": _hash_password(body.password),
            "role": body.role,
            "is_active": body.is_active,
        },
    )


@router.patch("/users/{user_id}/active")
def set_user_active(
    user_id: str,
    is_active: bool,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_admin(user)
    row = fetch_one(
        """
        UPDATE users
        SET is_active = %(is_active)s, updated_at = NOW()
        WHERE id = %(id)s
        RETURNING id, email, role, is_active
        """,
        {"id": user_id, "is_active": is_active},
    )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)


@router.get("/departments")
def list_departments(user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    _require_admin(user)
    return [dict(row) for row in fetch_all("SELECT * FROM departments ORDER BY name")]


@router.post("/departments", status_code=status.HTTP_201_CREATED)
def create_department(
    body: DepartmentCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_admin(user)
    return _insert_returning("departments", body.model_dump())


@router.get("/levels")
def list_levels(user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    _require_admin(user)
    return [dict(row) for row in fetch_all("SELECT * FROM levels ORDER BY order_number")]


@router.post("/levels", status_code=status.HTTP_201_CREATED)
def create_level(body: LevelCreate, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _require_admin(user)
    return _insert_returning("levels", body.model_dump())


@router.get("/filieres")
def list_filieres(user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    _require_admin(user)
    rows = fetch_all(
        """
        SELECT f.*, d.name AS department_name
        FROM filieres f
        LEFT JOIN departments d ON d.id = f.department_id
        ORDER BY f.name
        """
    )
    return [dict(row) for row in rows]


@router.post("/filieres", status_code=status.HTTP_201_CREATED)
def create_filiere(
    body: FiliereCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_admin(user)
    return _insert_returning("filieres", body.model_dump())


@router.get("/teachers")
def list_teachers(user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    _require_admin(user)
    rows = fetch_all(
        """
        SELECT e.*, u.email, d.name AS department_name
        FROM enseignants e
        JOIN users u ON u.id = e.user_id
        LEFT JOIN departments d ON d.id = e.department_id
        ORDER BY e.created_at DESC
        """
    )
    return [dict(row) for row in rows]


@router.post("/teachers", status_code=status.HTTP_201_CREATED)
def create_teacher(
    body: TeacherCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_admin(user)
    db_user = fetch_one("SELECT role FROM users WHERE id = %(id)s", {"id": body.user_id})
    if not db_user or db_user["role"] != "teacher":
        raise HTTPException(status_code=400, detail="user_id must reference a teacher user")
    return _insert_returning("enseignants", body.model_dump())


@router.get("/students")
def list_students(user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    _require_admin(user)
    rows = fetch_all(
        """
        SELECT s.*, u.email, f.name AS filiere_name, l.name AS level_name
        FROM students s
        JOIN users u ON u.id = s.user_id
        LEFT JOIN filieres f ON f.id = s.filiere_id
        LEFT JOIN levels l ON l.id = s.level_id
        ORDER BY s.created_at DESC
        """
    )
    return [dict(row) for row in rows]


@router.post("/students", status_code=status.HTTP_201_CREATED)
def create_student(
    body: StudentCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_admin(user)
    db_user = fetch_one("SELECT role FROM users WHERE id = %(id)s", {"id": body.user_id})
    if not db_user or db_user["role"] != "student":
        raise HTTPException(status_code=400, detail="user_id must reference a student user")
    return _insert_returning("students", body.model_dump())


@router.patch("/students/{student_id}/assignment")
def assign_student(
    student_id: str,
    body: StudentAssignment,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_admin(user)
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        row = fetch_one("SELECT * FROM students WHERE id = %(id)s", {"id": student_id})
        return dict(row) if row else {}
    sets = ", ".join(f"{key} = %({key})s" for key in payload)
    row = fetch_one(
        f"UPDATE students SET {sets} WHERE id = %(id)s RETURNING *",
        {**payload, "id": student_id},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
    return dict(row)


@router.get("/modules")
def list_modules(user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    _require_admin(user)
    rows = fetch_all(
        """
        SELECT
          m.*,
          f.name AS filiere_name,
          e.first_name AS teacher_first_name,
          e.last_name AS teacher_last_name
        FROM modules m
        LEFT JOIN filieres f ON f.id = m.filiere_id
        LEFT JOIN enseignants e ON e.id = m.teacher_id
        ORDER BY m.semester, m.name
        """
    )
    return [dict(row) for row in rows]


@router.post("/modules", status_code=status.HTTP_201_CREATED)
def create_module(
    body: ModuleCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_admin(user)
    return _insert_returning("modules", body.model_dump())


@router.patch("/modules/{module_id}/teacher")
def assign_teacher_to_module(
    module_id: str,
    body: TeacherModuleAssignment,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_admin(user)
    row = fetch_one(
        """
        UPDATE modules
        SET teacher_id = %(teacher_id)s
        WHERE id = %(id)s
        RETURNING *
        """,
        {"id": module_id, "teacher_id": body.teacher_id},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Module not found")
    return dict(row)


@router.delete("/{table}/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_row(
    table: str,
    row_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    _require_admin(user)
    allowed = {"students", "enseignants", "modules", "filieres", "levels", "departments", "users"}
    if table not in allowed:
        raise HTTPException(status_code=400, detail="Table cannot be deleted from this endpoint")
    execute(f"DELETE FROM {table} WHERE id = %(id)s", {"id": row_id})
