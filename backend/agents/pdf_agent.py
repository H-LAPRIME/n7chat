"""PDF agent.

Builds a generic report from the conversation context and available data.
The PDF path should not guess a fixed academic template; it should render the
best report it can from the context already collected by the graph.
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.tasks.pdf_llm_task import (
    build_dynamic_report_spec,
    build_pdf_answer,
    build_pdf_error,
    infer_report_type_task,
)
from backend.tools.pdf_tool import render_dynamic_pdf
from backend.tools.sql_tool import get_student_profile


def _tool_result(tool_obj: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if hasattr(tool_obj, "invoke"):
        return tool_obj.invoke(payload)
    return tool_obj(**payload)


def _infer_report_type(message: str, requested_type: str | None = None) -> str:
    return infer_report_type_task(message, requested_type)


def _last_assistant_response(history: list[dict[str, Any]] | None) -> str:
    return next(
        (str(item.get("content", "")) for item in reversed(history or []) if item.get("role") == "assistant"),
        "",
    )


def build_pdf_report_sync(
    message: str,
    user: dict[str, Any] | None = None,
    report_type: str | None = None,
    data_context: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    user = user or {}
    data_context = data_context or {}
    sql_context = data_context.get("sql", {}) if isinstance(data_context, dict) else {}
    student = user.get("student") or {}
    user_id = user.get("sub") or user.get("id")

    selected_type = infer_report_type_task(message, report_type)
    enriched_context = {
        **data_context,
        "last_assistant_response": (
            data_context.get("current_response")
            or data_context.get("last_assistant_response")
            or _last_assistant_response(history)
        ),
    }

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

        report_spec = build_dynamic_report_spec(
            message=message,
            selected_type=selected_type,
            student=student,
            data_context=enriched_context,
        )
        file_path = render_dynamic_pdf(report_spec)

        return build_pdf_answer(selected_type, file_path, report_spec, student, enriched_context)

    except Exception as exc:
        return build_pdf_error(exc)


async def run_pdf_agent(
    message: str,
    user: dict[str, Any] | None = None,
    report_type: str | None = None,
    data_context: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        build_pdf_report_sync,
        message,
        user or {},
        report_type,
        data_context or {},
        history or [],
    )
