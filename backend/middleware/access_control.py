"""Role-based data access control for the n7chat backend.

This module is the **single source of truth** for what data a role may see.
It is used by:
  - ``backend.agents.sql_agent``  – scrubs tool results before they reach the LLM.
  - ``backend.tasks.sql_llm_task`` – injects an access policy into the system prompt.
  - ``backend.tasks.rag_llm_task`` – injects an access policy into the system prompt.

Design principles
-----------------
* **Two enforcement layers**: tool-level (hard filter on returned data) +
  LLM-prompt-level (explicit rules the model must follow).
* **Whitelist sensitive tables**: any table/column not in the sensitive set is
  considered public and accessible to all authenticated roles.
* **Student scope is identity-bound**: a student's ``student_id`` comes from their
  JWT claim – it is never taken from the user's own message.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Sensitivity catalogue  (derived from db/schema.sql)
# ---------------------------------------------------------------------------

# Tables whose rows are private to the student they belong to.
# Key = table name, value = the column that links a row to a student.
STUDENT_PRIVATE_TABLES: dict[str, str] = {
    "notes": "student_id",
    "absences": "student_id",
    "generated_reports": "user_id",   # user_id == JWT sub for students
    "notifications": "user_id",
    "conversations": "user_id",
    "messages": "conversation_id",    # transitive via conversation.user_id
}

# Columns inside `students` that are personal and must never be shown for
# other students (even if a student row is somehow fetched).
STUDENT_PERSONAL_COLUMNS: frozenset[str] = frozenset(
    {
        "password_hash",
        "birth_date",
        "gender",
        "phone",
        "address",
        "email",
    }
)

# Tables whose rows are private to the specific user (any role).
USER_PRIVATE_TABLES: dict[str, str] = {
    "refresh_tokens": "user_id",
    "users": "id",             # password_hash, email – never expose raw
}

# Tables that are completely public (all authenticated users).
PUBLIC_TABLES: frozenset[str] = frozenset(
    {
        "departments",
        "levels",
        "filieres",
        "modules",
        "courses",
        "events",
        "enseignants",          # name, specialization, office only (see strip below)
        "document_chunks",
        "course_chunks",
    }
)

# Columns to strip from enseignants rows before sending to students
# (personal contact info a student doesn't need).
ENSEIGNANT_PRIVATE_COLUMNS: frozenset[str] = frozenset({"phone"})


# ---------------------------------------------------------------------------
# Access policy builder (injected into LLM prompts)
# ---------------------------------------------------------------------------


def build_access_policy(user: dict[str, Any]) -> dict[str, Any]:
    """Return an access-policy dict that is serialised into each LLM system prompt.

    Parameters
    ----------
    user:
        Decoded JWT payload / user profile dict.  Expected keys:
        ``role`` (str), ``sub`` / ``id`` (UUID str), ``student_id`` (UUID str).

    Returns
    -------
    dict with keys ``role``, ``own_student_id``, ``rules``, ``forbidden``.
    """
    role: str = (user.get("role") or "student").lower()
    student_id: str | None = _resolve_student_id(user)
    user_id: str | None = user.get("sub") or user.get("id")

    if role == "student":
        rules = [
            "You may only show data that belongs to this specific student.",
            f"Allowed student_id: {student_id or '(not set)'}.",
            "NEVER return notes, absences, or profile data for any other student.",
            "NEVER reveal another student's name, code, birth_date, phone, address, or gender.",
            "Only public or explicitly assigned/audience-scoped modules, events, courses, documents, enseignants, and filieres are accessible.",
            "Enseignant phone numbers must be omitted from answers.",
            "Never reference refresh_tokens, password_hash, or raw users table data.",
        ]
        forbidden = [
            "notes of other students",
            "absences of other students",
            "personal profile data of other students",
            "rattrapages / exam scores of other students",
            "notifications of other users",
            "generated_reports of other users",
            "refresh_tokens",
            "users.password_hash",
            "users.email (other users)",
        ]
    elif role in ("teacher", "enseignant"):
        rules = [
            "You may show module data only for modules this teacher is assigned to.",
            "You may show notes/absences only for students in your own modules.",
            "Only public or explicitly assigned/audience-scoped events, courses, documents, filieres, and departments are accessible.",
            "Never show personal student data (phone, address, birth_date) to teachers.",
            "Never reference refresh_tokens or password_hash.",
        ]
        forbidden = [
            "student personal details (phone, address, birth_date, gender)",
            "notes in modules not assigned to this teacher",
            "refresh_tokens",
            "users.password_hash",
        ]
    else:  # admin – full SQL access, no chatbot per spec
        rules = ["Admin role: full read access."]
        forbidden = ["refresh_tokens.token (raw value)", "users.password_hash"]

    return {
        "role": role,
        "own_student_id": student_id,
        "own_user_id": user_id,
        "rules": rules,
        "forbidden_data": forbidden,
    }


# ---------------------------------------------------------------------------
# Tool-level enforcement helpers
# ---------------------------------------------------------------------------


def _resolve_student_id(user: dict[str, Any]) -> str | None:
    """Extract the authenticated user's own student_id from JWT claims."""
    student = user.get("student") or {}
    return user.get("student_id") or student.get("id") or None


def enforce_student_scope(
    user: dict[str, Any],
    data: dict[str, Any],
) -> dict[str, Any]:
    """Scrub any rows in *data* that belong to a student other than *user*.

    This is a **hard filter** applied after tool calls return results, before
    the data is sent to the LLM.  Even if a bug somewhere passes the wrong
    student_id to a tool, this function will strip the offending rows.

    Parameters
    ----------
    user:
        Decoded JWT payload / user profile dict.
    data:
        The collected SQL context dict (keys like ``"notes"``, ``"absences"``,
        ``"profile"``).

    Returns
    -------
    Cleaned data dict (same structure, foreign rows removed).
    """
    role = (user.get("role") or "student").lower()
    if role != "student":
        # Teachers and admins have their own scoping logic; this guard is
        # student-specific.
        return data

    own_student_id = _resolve_student_id(user)
    own_user_id = user.get("sub") or user.get("id")

    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        cleaned[key] = _scrub_value(key, value, own_student_id, own_user_id)

    return cleaned


def _scrub_value(
    key: str,
    value: Any,
    own_student_id: str | None,
    own_user_id: str | None,
) -> Any:
    """Recursively scrub a single data entry."""
    if not isinstance(value, dict):
        return value

    # Tool result dict: has "data" list of rows
    if "data" in value and isinstance(value["data"], list):
        scrubbed_rows = [
            row
            for row in value["data"]
            if _row_is_allowed(key, row, own_student_id, own_user_id)
        ]
        return {**value, "data": scrubbed_rows, "row_count": len(scrubbed_rows)}

    # Profile result dict: has "data" as a single dict
    if key == "profile" and isinstance(value.get("data"), dict):
        row = value["data"]
        if not _row_is_allowed("students", row, own_student_id, own_user_id):
            return {"ok": False, "data": None, "error": "access_denied"}
        return {**value, "data": _strip_personal_columns(row)}

    return value


def _row_is_allowed(
    key: str,
    row: dict[str, Any],
    own_student_id: str | None,
    own_user_id: str | None,
) -> bool:
    """Return True if *row* is accessible to the current student."""
    # Notes and absences must belong to the student
    if key in ("notes", "absences"):
        row_student_id = str(row.get("student_id") or "")
        if own_student_id and row_student_id and row_student_id != str(own_student_id):
            return False

    # Notifications and reports must belong to the user
    if key in ("notifications", "generated_reports", "conversations"):
        row_user_id = str(row.get("user_id") or "")
        if own_user_id and row_user_id and row_user_id != str(own_user_id):
            return False

    # Completely block raw users / refresh_tokens rows
    if key in ("users", "refresh_tokens"):
        return False

    return True


def _strip_personal_columns(row: dict[str, Any]) -> dict[str, Any]:
    """Remove personal columns from a students row."""
    return {k: v for k, v in row.items() if k not in STUDENT_PERSONAL_COLUMNS}


def strip_enseignant_private_columns(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove private columns (phone) from enseignant rows."""
    return [
        {k: v for k, v in row.items() if k not in ENSEIGNANT_PRIVATE_COLUMNS}
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Convenience: access policy as a compact string for prompts
# ---------------------------------------------------------------------------


def access_policy_text(user: dict[str, Any]) -> str:
    """Return a short, LLM-readable access policy block."""
    policy = build_access_policy(user)
    lines = [
        f"[ACCESS POLICY]",
        f"Role: {policy['role']}",
    ]
    if policy.get("own_student_id"):
        lines.append(f"Authorised student_id: {policy['own_student_id']}")
    lines.append("Rules:")
    for rule in policy["rules"]:
        lines.append(f"  - {rule}")
    lines.append("Forbidden data (never include in answers):")
    for item in policy["forbidden_data"]:
        lines.append(f"  ✗ {item}")
    return "\n".join(lines)
