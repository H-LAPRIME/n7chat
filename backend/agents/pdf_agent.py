from __future__ import annotations

import asyncio
from typing import Any, Literal

from backend.tools.pdf_tool import build_bulletin_pdf, build_notes_pdf
from backend.tools.sql_tool import get_student_absences, get_student_notes, get_student_profile


ReportType = Literal["notes", "bulletin"]


def _tool_result(tool_obj: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if hasattr(tool_obj, "invoke"):
        return tool_obj.invoke(payload)
    return tool_obj(**payload)


def _infer_report_type(message: str, explicit_type: str | None = None) -> ReportType:
    if explicit_type in ("notes", "bulletin"):
        return explicit_type  # type: ignore[return-value]
    lowered = message.lower()
    if any(word in lowered for word in ["bulletin", "absence", "absences"]):
        return "bulletin"
    return "notes"


def build_pdf_report_sync(
    message: str,
    user: dict[str, Any] | None = None,
    report_type: str | None = None,
    data_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user = user or {}
    data_context = data_context or {}
    sql_context = data_context.get("sql", {}) if isinstance(data_context, dict) else {}
    student = user.get("student") or {}
    student_id = user.get("student_id") or student.get("id")
    user_id = user.get("sub") or user.get("id")
    selected_type = _infer_report_type(message, report_type)

    try:
        profile_context = sql_context.get("profile")
        if isinstance(profile_context, dict) and profile_context.get("data"):
            student = profile_context["data"]
        elif user_id:
            profile = _tool_result(get_student_profile, {"user_id": user_id})
            if profile.get("ok") and profile.get("data"):
                student = profile["data"]
        if not student:
            student = user

        notes_result = sql_context.get("notes")
        if not isinstance(notes_result, dict):
            notes_result = (
                _tool_result(get_student_notes, {"student_id": student_id})
                if student_id
                else {"data": []}
            )

        absences_result = sql_context.get("absences")
        if not isinstance(absences_result, dict):
            absences_result = (
                _tool_result(get_student_absences, {"student_id": student_id})
                if student_id
                else {"data": []}
            )

        notes = notes_result.get("data") or []
        absences = absences_result.get("data") or []

        if selected_type == "bulletin":
            file_path = build_bulletin_pdf(student, notes, absences)
        else:
            file_path = build_notes_pdf(student, notes)

        return {
            "ok": True,
            "answer": f"Le PDF {selected_type} est pret: {file_path}",
            "artifact": {"type": selected_type, "file_path": file_path},
            "data": {"student": student, "notes": notes, "absences": absences},
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "answer": f"Je n'ai pas pu generer le PDF: {exc}",
            "artifact": None,
            "data": {},
            "error": str(exc),
        }


async def run_pdf_agent(
    message: str,
    user: dict[str, Any] | None = None,
    report_type: str | None = None,
    data_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        build_pdf_report_sync,
        message,
        user or {},
        report_type,
        data_context or {},
    )
