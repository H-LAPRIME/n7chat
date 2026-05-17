from __future__ import annotations

import asyncio
import json
from os import environ
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from backend.tools.sql_tool import (
    get_filiere_modules,
    get_student_absences,
    get_student_notes,
    get_student_profile,
    get_upcoming_events,
    get_user_notifications,
)


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")

DEFAULT_MODEL = environ.get("MISTRAL_MODEL", "mistral-large-latest")


SYSTEM_PROMPT = """
You are the n7chat SQL agent.

You answer using structured Supabase data only. Speak in clear French.
If required identifiers are missing, state what is missing.
Keep answers concise and useful for a university student or teacher.
"""


def _mistral_client():
    api_key = environ.get("MISTRAL_KEY_SQL")
    if not api_key:
        raise RuntimeError("MISTRAL_KEY_SQL is missing from backend/.env")

    try:
        from mistralai import Mistral
    except ImportError:
        from mistralai.client import Mistral

    return Mistral(api_key=api_key)


def _extract_content(response: Any) -> str:
    try:
        return response.choices[0].message.content or ""
    except Exception:
        return str(response)


def _tool_result(tool_obj: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if hasattr(tool_obj, "invoke"):
        return tool_obj.invoke(payload)
    return tool_obj(**payload)


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, indent=2)


def collect_sql_context(intent: str, user: dict[str, Any]) -> dict[str, Any]:
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


def answer_from_sql_sync(
    message: str,
    intent: str,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user = user or {}
    data = collect_sql_context(intent, user)
    prompt = (
        f"Intent: {intent}\n"
        f"Question: {message}\n"
        f"User: {_json_dump(user)}\n"
        f"Supabase data:\n{_json_dump(data)}"
    )

    try:
        response = _mistral_client().chat.complete(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        answer = _extract_content(response).strip()
        return {"ok": True, "answer": answer, "data": data, "error": None}
    except Exception as exc:
        return {
            "ok": False,
            "answer": f"Je n'ai pas pu interroger l'agent SQL: {exc}",
            "data": data,
            "error": str(exc),
        }


async def run_sql_agent(
    message: str,
    intent: str,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(answer_from_sql_sync, message, intent, user or {})
