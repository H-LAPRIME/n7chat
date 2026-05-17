"""SQL LLM Task.

Contains the raw Mistral API call that answers structured-data questions.
Imported by backend.agents.sql_agent – keeps the LLM interaction isolated
from context-collection (tool calls) and async-wrapping logic.
"""

from __future__ import annotations

import json
from datetime import datetime
from os import environ
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from backend.middleware.access_control import access_policy_text


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")

DEFAULT_MODEL = environ.get("MISTRAL_MODEL", "mistral-large-latest")

_SYSTEM_PROMPT_BASE = """
You are the n7chat SQL agent.

The current date and time is: {current_date}

You answer using structured Supabase data only. Speak in clear French.
If required identifiers are missing, state what is missing.
Keep answers concise and useful for a university student or teacher.
Prefer the provided Markdown formatted context for tables and lists. You may
add a short explanation before or after it, but do not destroy the table shape.

CRITICAL DATE HANDLING:
Always compare the dates in the data against `{current_date}`. If the user asks for a specific timeframe like "cette semaine" (this week) or "demain" (tomorrow), explicitly state whether there are events in that timeframe. If there are no events in that timeframe, clearly say so, but then YOU SHOULD mention the next upcoming events as a helpful note (e.g. "Tu n'as pas d'examen cette semaine. Cependant, ton prochain examen est le 10 juin").

CRITICAL – you must obey the access policy below at all times:
{access_policy}

If a user asks for data that is marked FORBIDDEN or belongs to another student,
reply politely in French that you can only show their own information.
Do NOT fabricate, infer, or reference any row that is not present in the data
provided to you.
"""


# ---------------------------------------------------------------------------
# Mistral client
# ---------------------------------------------------------------------------


def _mistral_client():
    api_key = environ.get("MISTRAL_KEY_SQL")
    if not api_key:
        raise RuntimeError("MISTRAL_KEY_SQL is missing from backend/.env")

    try:
        from mistralai import Mistral
    except ImportError:
        from mistralai.client import Mistral  # type: ignore[no-redef]

    return Mistral(api_key=api_key)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_content(response: Any) -> str:
    try:
        return response.choices[0].message.content or ""
    except Exception:
        return str(response)


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, indent=2)


# ---------------------------------------------------------------------------
# Public task entry-point
# ---------------------------------------------------------------------------


def answer_from_sql_task(
    message: str,
    intent: str,
    user: dict[str, Any],
    data: dict[str, Any],
) -> dict[str, Any]:
    """Call Mistral with pre-collected *data* and return a structured answer dict.

    Parameters
    ----------
    message:
        The original user question.
    intent:
        Classified intent (e.g. ``"notes"``, ``"absence"``).
    user:
        Decoded JWT payload / user profile dict.
    data:
        SQL context already collected by the agent (profile, notes, absences…).
        Must already be filtered by ``enforce_student_scope``.

    Returns
    -------
    dict with keys ``ok``, ``answer``, ``data``, ``error``.
    """
    # Build access-policy-aware system prompt
    system_prompt = _SYSTEM_PROMPT_BASE.format(
        current_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        access_policy=access_policy_text(user)
    )

    prompt = (
        f"Intent: {intent}\n"
        f"Question: {message}\n"
        f"User role: {(user.get('role') or 'student')}\n"
        f"Formatted context for final answer:\n{data.get('formatted_context', '')}\n"
        f"Supabase data (pre-filtered, belongs to authorised user only):\n"
        f"{_json_dump(data)}"
    )

    try:
        response = _mistral_client().chat.complete(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        answer = _extract_content(response).strip()
        return {"ok": True, "answer": answer, "data": data, "error": None}
    except Exception as exc:
        formatted = data.get("formatted_context")
        fallback_answer = (
            f"{formatted}\n\n_Note: reponse formatee localement car l'agent SQL LLM est indisponible._"
            if formatted
            else f"Je n'ai pas pu interroger l'agent SQL: {exc}"
        )
        return {
            "ok": False,
            "answer": fallback_answer,
            "data": data,
            "error": str(exc),
        }
