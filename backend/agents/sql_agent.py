"""SQL agent.

Thin async wrapper around the LLM task in ``backend.tasks.sql_llm_task``.
Responsible for:
  - Collecting structured SQL context via tool calls (profile, notes, absences…).
  - Passing that context to ``answer_from_sql_task`` for the Mistral answer.
  - Exposing the async ``run_sql_agent`` entry-point consumed by the graph.

All Mistral client logic and prompts live in ``backend.tasks.sql_llm_task``.
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.middleware.access_control import enforce_student_scope
from backend.tasks.sql_llm_task import answer_from_sql_task
from backend.tools.format_tool import to_bullet_list, to_markdown_table, truncate_for_chat
from backend.tools.sql_tool import (
    get_filiere_modules,
    get_student_absences,
    get_student_notes,
    get_student_profile,
    get_upcoming_events,
    get_user_notifications,
)


# ---------------------------------------------------------------------------
# Tool helper
# ---------------------------------------------------------------------------


def _tool_result(tool_obj: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if hasattr(tool_obj, "invoke"):
        return tool_obj.invoke(payload)
    return tool_obj(**payload)


# ---------------------------------------------------------------------------
# Context collection
# ---------------------------------------------------------------------------


def collect_sql_context(intent: str, user: dict[str, Any]) -> dict[str, Any]:
    """Fetch relevant Supabase data based on *intent* and *user* context."""
    student = user.get("student") or {}
    student_id = user.get("student_id") or student.get("id")
    user_id = user.get("sub") or user.get("id")
    filiere_id = user.get("filiere_id") or student.get("filiere_id")

    data: dict[str, Any] = {}
    if user_id:
        data["profile"] = _tool_result(get_student_profile, {"user_id": user_id})

    if intent == "notes":
        data["notes"] = (
            _tool_result(get_student_notes, {"student_id": student_id})
            if student_id
            else {"ok": False, "error": "student_id is required", "data": []}
        )
    elif intent == "absence":
        data["absences"] = (
            _tool_result(get_student_absences, {"student_id": student_id})
            if student_id
            else {"ok": False, "error": "student_id is required", "data": []}
        )
    elif intent == "emploi_du_temps":
        if filiere_id:
            data["modules"] = _tool_result(
                get_filiere_modules,
                {"filiere_id": filiere_id, "semester": user.get("semester")},
            )
        else:
            data["modules"] = {"ok": False, "error": "filiere_id is required", "data": []}
        data["events"] = _tool_result(get_upcoming_events, {"limit": 20})
    elif intent == "profile":
        if filiere_id:
            data["modules"] = _tool_result(
                get_filiere_modules,
                {"filiere_id": filiere_id, "semester": user.get("semester")},
            )
        else:
            data["modules"] = {"ok": False, "error": "filiere_id is required", "data": []}
    elif intent == "pdf_report":
        data["notes"] = (
            _tool_result(get_student_notes, {"student_id": student_id})
            if student_id
            else {"ok": False, "error": "student_id is required", "data": []}
        )
        data["absences"] = (
            _tool_result(get_student_absences, {"student_id": student_id})
            if student_id
            else {"ok": False, "error": "student_id is required", "data": []}
        )
    else:
        if user_id:
            data["notifications"] = _tool_result(
                get_user_notifications,
                {"user_id": user_id, "unread_only": False},
            )

    return data


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _rows(result: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    data = result.get("data") or []
    return data if isinstance(data, list) else []


def format_sql_context(intent: str, data: dict[str, Any]) -> str:
    """Format collected SQL context as Markdown before it reaches the LLM."""
    if intent == "notes":
        return to_markdown_table(
            _rows(data.get("notes")),
            ["module_name", "exam_type", "score", "coefficient", "published_at"],
            empty_message="_Aucune note trouvee._",
        )

    if intent == "absence":
        return to_markdown_table(
            _rows(data.get("absences")),
            ["date", "module_name", "module_code", "justified", "justification_file"],
            empty_message="_Aucune absence trouvee._",
        )

    if intent == "emploi_du_temps":
        modules = to_markdown_table(
            _rows(data.get("modules")),
            ["module_name", "module_code", "semester", "teacher_first_name", "teacher_last_name"],
            empty_message="_Aucun module trouve._",
        )
        events = to_markdown_table(
            _rows(data.get("events")),
            ["title", "event_type", "start_date", "end_date", "location"],
            empty_message="_Aucun evenement a venir._",
        )
        return truncate_for_chat(f"### Modules\n{modules}\n\n### Evenements\n{events}")

    if intent == "pdf_report":
        notes = to_markdown_table(
            _rows(data.get("notes")),
            ["module_name", "exam_type", "score", "coefficient", "published_at"],
            empty_message="_Aucune note trouvee pour le PDF._",
        )
        absences = to_markdown_table(
            _rows(data.get("absences")),
            ["date", "module_name", "justified"],
            empty_message="_Aucune absence trouvee pour le PDF._",
        )
        return truncate_for_chat(f"### Notes\n{notes}\n\n### Absences\n{absences}")

    notifications = _rows(data.get("notifications"))
    if notifications:
        return to_bullet_list(
            notifications,
            "title",
            ["message", "type", "created_at"],
            empty_message="_Aucune notification._",
        )

    modules = _rows(data.get("modules"))
    if modules:
        return to_markdown_table(
            modules,
            ["module_name", "module_code", "semester", "teacher_first_name", "teacher_last_name"],
        )

    return "_Aucune donnee structuree a formater._"


# ---------------------------------------------------------------------------
# Sync runner (calls task layer)
# ---------------------------------------------------------------------------


def answer_from_sql_sync(
    message: str,
    intent: str,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user = user or {}
    raw_data = collect_sql_context(intent, user)
    # Hard filter: strip any rows that don't belong to this user
    data = enforce_student_scope(user, raw_data)
    data["formatted_context"] = format_sql_context(intent, data)
    return answer_from_sql_task(message, intent, user, data)


# ---------------------------------------------------------------------------
# Async entry-point (used by graph nodes and routers)
# ---------------------------------------------------------------------------


async def run_sql_agent(
    message: str,
    intent: str,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(answer_from_sql_sync, message, intent, user or {})
