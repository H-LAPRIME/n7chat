from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from backend.db.supabase import fetch_all, fetch_one, get_connection

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, **_: Any):
        if func is None:
            return lambda wrapped: wrapped
        return func


DEFAULT_LIMIT = 50
MAX_LIMIT = 200
READ_ONLY_PREFIXES = ("select", "with", "show", "explain")
DANGEROUS_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|call|do)\b",
    re.IGNORECASE,
)
IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, UUID, Decimal)):
        return str(value)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _success(rows: Sequence[Mapping[str, Any]], query: str) -> dict[str, Any]:
    data = [_jsonable(dict(row)) for row in rows]
    return {
        "ok": True,
        "row_count": len(data),
        "data": data,
        "sql": query,
        "error": None,
    }


def _failure(error: Exception | str, query: str | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "row_count": 0,
        "data": [],
        "sql": query,
        "error": str(error),
    }


def _normalize_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    return max(1, min(int(limit), MAX_LIMIT))


def _validate_identifier(identifier: str) -> str:
    if not IDENTIFIER.match(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")
    return identifier


def _validate_read_only_sql(query: str) -> str:
    cleaned = query.strip().rstrip(";")
    lowered = cleaned.lower()
    if not lowered.startswith(READ_ONLY_PREFIXES):
        raise ValueError("Only read-only SQL queries are allowed.")
    if ";" in cleaned:
        raise ValueError("Only one SQL statement is allowed.")
    if DANGEROUS_SQL.search(cleaned):
        raise ValueError("Dangerous SQL keyword detected.")
    return cleaned


@tool
def run_readonly_sql(
    query: str,
    params: dict[str, Any] | None = None,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Run a safe read-only PostgreSQL query and return rows for the agent."""
    try:
        safe_query = _validate_read_only_sql(query)
        safe_limit = _normalize_limit(limit)
        wrapped_query = f"SELECT * FROM ({safe_query}) AS agent_query LIMIT {safe_limit}"

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL statement_timeout = '8s'")
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute(wrapped_query, params or {})
                rows = cur.fetchall()

        return _success(rows, wrapped_query)
    except Exception as exc:
        return _failure(exc, query)


@tool
def get_database_schema() -> dict[str, Any]:
    """Return public table columns so the SQL agent can plan valid queries."""
    query = """
    SELECT
      table_name,
      column_name,
      data_type,
      udt_name,
      is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position
    """
    try:
        rows = fetch_all(query)
        tables: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            table_name = row["table_name"]
            tables.setdefault(table_name, []).append(
                {
                    "name": row["column_name"],
                    "type": row["udt_name"] or row["data_type"],
                    "nullable": row["is_nullable"] == "YES",
                }
            )
        return {"ok": True, "tables": tables, "error": None}
    except Exception as exc:
        return {"ok": False, "tables": {}, "error": str(exc)}


@tool
def list_table_rows(
    table: str,
    limit: int = DEFAULT_LIMIT,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Read rows from one public table using a validated table name."""
    try:
        table_name = _validate_identifier(table)
        safe_limit = _normalize_limit(limit)
        order_sql = ""
        if order_by:
            direction = "DESC" if descending else "ASC"
            order_sql = f" ORDER BY {_validate_identifier(order_by)} {direction}"
        query = f"SELECT * FROM {table_name}{order_sql} LIMIT %(limit)s"
        rows = fetch_all(query, {"limit": safe_limit})
        return _success(rows, query)
    except Exception as exc:
        return _failure(exc)


@tool
def get_student_profile(user_id: str) -> dict[str, Any]:
    """Return a student profile with filiere and level details by user id."""
    query = """
    SELECT
      s.*,
      f.name AS filiere_name,
      f.code AS filiere_code,
      l.name AS level_name
    FROM students s
    LEFT JOIN filieres f ON f.id = s.filiere_id
    LEFT JOIN levels l ON l.id = s.level_id
    WHERE s.user_id = %(user_id)s
    """
    try:
        row = fetch_one(query, {"user_id": user_id})
        return {"ok": True, "data": _jsonable(row), "error": None}
    except Exception as exc:
        return {"ok": False, "data": None, "error": str(exc)}


@tool
def get_student_notes(student_id: str) -> dict[str, Any]:
    """Return notes for a student with module and teacher context."""
    query = """
    SELECT
      n.id,
      n.exam_type,
      n.score,
      n.coefficient,
      n.published_at,
      m.name AS module_name,
      m.code AS module_code,
      e.first_name AS teacher_first_name,
      e.last_name AS teacher_last_name
    FROM notes n
    LEFT JOIN modules m ON m.id = n.module_id
    LEFT JOIN enseignants e ON e.id = n.teacher_id
    WHERE n.student_id = %(student_id)s
    ORDER BY n.published_at DESC
    """
    try:
        rows = fetch_all(query, {"student_id": student_id})
        return _success(rows, query)
    except Exception as exc:
        return _failure(exc, query)


@tool
def get_student_absences(student_id: str) -> dict[str, Any]:
    """Return absences for a student with module information."""
    query = """
    SELECT
      a.id,
      a.date,
      a.justified,
      a.justification_file,
      m.name AS module_name,
      m.code AS module_code
    FROM absences a
    LEFT JOIN modules m ON m.id = a.module_id
    WHERE a.student_id = %(student_id)s
    ORDER BY a.date DESC
    """
    try:
        rows = fetch_all(query, {"student_id": student_id})
        return _success(rows, query)
    except Exception as exc:
        return _failure(exc, query)


@tool
def get_teacher_modules(teacher_id: str) -> dict[str, Any]:
    """Return modules taught by one teacher."""
    query = """
    SELECT
      m.id,
      m.name,
      m.code,
      m.semester,
      m.coefficient,
      m.credits,
      f.name AS filiere_name,
      f.code AS filiere_code
    FROM modules m
    LEFT JOIN filieres f ON f.id = m.filiere_id
    WHERE m.teacher_id = %(teacher_id)s
    ORDER BY m.semester, m.name
    """
    try:
        rows = fetch_all(query, {"teacher_id": teacher_id})
        return _success(rows, query)
    except Exception as exc:
        return _failure(exc, query)


@tool
def get_filiere_modules(filiere_id: str, semester: int | None = None) -> dict[str, Any]:
    """Return modules for a filiere, optionally filtered by semester."""
    query = """
    SELECT
      m.id,
      m.name,
      m.code,
      m.semester,
      m.coefficient,
      m.credits,
      e.first_name AS teacher_first_name,
      e.last_name AS teacher_last_name
    FROM modules m
    LEFT JOIN enseignants e ON e.id = m.teacher_id
    WHERE m.filiere_id = %(filiere_id)s
      AND (%(semester)s::int IS NULL OR m.semester = %(semester)s::int)
    ORDER BY m.semester, m.name
    """
    try:
        rows = fetch_all(query, {"filiere_id": filiere_id, "semester": semester})
        return _success(rows, query)
    except Exception as exc:
        return _failure(exc, query)


@tool
def get_upcoming_events(
    limit: int = DEFAULT_LIMIT,
    filiere_id: str | None = None,
    is_staff: bool = False,
) -> dict[str, Any]:
    """Return upcoming school events, exams, holidays, meetings, and conferences."""
    query = """
    SELECT
      id,
      title,
      description,
      event_type,
      start_date,
      end_date,
      location
    FROM events
    WHERE start_date >= CURRENT_TIMESTAMP
      AND (
        %(is_staff)s = TRUE
        OR visibility_scope = 'public'
        OR filiere_id = %(filiere_id)s::uuid
        OR module_id IN (SELECT id FROM modules WHERE filiere_id = %(filiere_id)s::uuid)
      )
    ORDER BY start_date ASC
    LIMIT %(limit)s
    """
    try:
        rows = fetch_all(
            query,
            {
                "limit": _normalize_limit(limit),
                "filiere_id": filiere_id,
                "is_staff": is_staff,
            },
        )
        return _success(rows, query)
    except Exception as exc:
        return _failure(exc, query)


@tool
def get_user_notifications(user_id: str, unread_only: bool = False) -> dict[str, Any]:
    """Return notifications for one user."""
    query = """
    SELECT id, title, message, type, is_read, created_at
    FROM notifications
    WHERE user_id = %(user_id)s
      AND (%(unread_only)s = FALSE OR is_read = FALSE)
    ORDER BY created_at DESC
    """
    try:
        rows = fetch_all(query, {"user_id": user_id, "unread_only": unread_only})
        return _success(rows, query)
    except Exception as exc:
        return _failure(exc, query)


SQL_TOOLS = [
    run_readonly_sql,
    get_database_schema,
    list_table_rows,
    get_student_profile,
    get_student_notes,
    get_student_absences,
    get_teacher_modules,
    get_filiere_modules,
    get_upcoming_events,
    get_user_notifications,
]


def query_notes(student_id: str) -> list[dict[str, Any]]:
    """Legacy helper kept for existing imports."""
    query = """
    SELECT
      n.score,
      n.exam_type,
      n.coefficient,
      n.published_at,
      m.name AS module_name,
      m.code AS module_code
    FROM notes n
    LEFT JOIN modules m ON m.id = n.module_id
    WHERE n.student_id = %(student_id)s
    ORDER BY n.published_at DESC
    """
    return [_jsonable(row) for row in fetch_all(query, {"student_id": student_id})]


def query_absences(student_id: str) -> list[dict[str, Any]]:
    """Legacy helper kept for existing imports."""
    query = """
    SELECT
      a.date,
      a.justified,
      a.justification_file,
      m.name AS module_name,
      m.code AS module_code
    FROM absences a
    LEFT JOIN modules m ON m.id = a.module_id
    WHERE a.student_id = %(student_id)s
    ORDER BY a.date DESC
    """
    return [_jsonable(row) for row in fetch_all(query, {"student_id": student_id})]


def query_modules(
    teacher_id: str | None = None,
    filiere_id: str | None = None,
) -> list[dict[str, Any]]:
    """Legacy helper kept for existing imports."""
    query = """
    SELECT
      m.id,
      m.name,
      m.code,
      m.semester,
      m.credits,
      f.name AS filiere_name,
      f.code AS filiere_code
    FROM modules m
    LEFT JOIN filieres f ON f.id = m.filiere_id
    WHERE (%(teacher_id)s::uuid IS NULL OR m.teacher_id = %(teacher_id)s::uuid)
      AND (%(filiere_id)s::uuid IS NULL OR m.filiere_id = %(filiere_id)s::uuid)
    ORDER BY m.semester, m.name
    """
    return [
        _jsonable(row)
        for row in fetch_all(query, {"teacher_id": teacher_id, "filiere_id": filiere_id})
    ]


def query_student_profile(user_id: str) -> dict[str, Any] | None:
    """Legacy helper kept for existing imports."""
    query = """
    SELECT
      s.*,
      f.name AS filiere_name,
      f.code AS filiere_code,
      l.name AS level_name
    FROM students s
    LEFT JOIN filieres f ON f.id = s.filiere_id
    LEFT JOIN levels l ON l.id = s.level_id
    WHERE s.user_id = %(user_id)s
    """
    row = fetch_one(query, {"user_id": user_id})
    return _jsonable(row) if row else None


def query_events(
    module_ids: list[str] | None = None,
    upcoming_only: bool = True,
) -> list[dict[str, Any]]:
    """Legacy helper kept for existing imports.

    The current events table is global and has no module_id column, so module_ids
    is accepted for compatibility but not applied.
    """
    query = """
    SELECT title, event_type, start_date, end_date, location
    FROM events
    WHERE (%(upcoming_only)s = FALSE OR start_date >= CURRENT_TIMESTAMP)
    ORDER BY start_date ASC
    """
    return [_jsonable(row) for row in fetch_all(query, {"upcoming_only": upcoming_only})]


def query_emploi(filiere_id: str, semester: int | None = None) -> list[dict[str, Any]]:
    """Legacy helper kept for existing imports.

    Until a seances/timetable table exists, this returns the filiere modules that
    can be used by calendar formatters as timetable context.
    """
    query = """
    SELECT
      m.name AS module_name,
      m.code AS module_code,
      m.semester,
      e.first_name AS teacher_first_name,
      e.last_name AS teacher_last_name
    FROM modules m
    LEFT JOIN enseignants e ON e.id = m.teacher_id
    WHERE m.filiere_id = %(filiere_id)s
      AND (%(semester)s::int IS NULL OR m.semester = %(semester)s::int)
    ORDER BY m.semester, m.name
    """
    return [
        _jsonable(row)
        for row in fetch_all(query, {"filiere_id": filiere_id, "semester": semester})
    ]
