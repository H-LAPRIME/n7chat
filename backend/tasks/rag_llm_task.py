"""RAG LLM Task.

Contains the raw Mistral API call that answers document-search questions.
Imported by backend.agents.rag_agent – keeps the LLM interaction isolated
from retrieval (vector search) and async-wrapping logic.
"""

from __future__ import annotations

import json
from os import environ
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from backend.middleware.access_control import access_policy_text
from backend.tasks.llm_retry import call_with_retry


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")

DEFAULT_MODEL = environ.get("MISTRAL_MODEL", "mistral-large-latest")

_SYSTEM_PROMPT_BASE = """
You are the n7chat RAG agent.

Use only retrieved context from indexed documents. Documents can be courses,
timetables, news, administrative documents, events, or other school material.
If the context is insufficient, say that clearly and suggest what document is needed.
Answer in French.
When multiple accessible documents/courses match the same topic or title,
distinguish them by uploader/teacher and accessibility. Do not merge sources
from different uploaders as if they were one document; mention the available
choices when that helps the student choose the right professor's course.

CRITICAL – you must obey the access policy below at all times:
{access_policy}

If retrieved document chunks contain personal data about other students
(notes, absences, personal details), omit that information entirely from your answer.
Only surface public, non-personal content from the retrieved documents.
"""


# ---------------------------------------------------------------------------
# Mistral client
# ---------------------------------------------------------------------------


def _mistral_client():
    api_key = environ.get("MISTRAL_KEY_RAG")
    if not api_key:
        raise RuntimeError("MISTRAL_KEY_RAG is missing from backend/.env")

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


def answer_from_documents_task(
    message: str,
    filters: dict[str, Any],
    search_result: dict[str, Any],
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call Mistral with pre-fetched *search_result* and return a structured answer dict.

    Parameters
    ----------
    message:
        The original user question.
    filters:
        Search filter metadata (top_k, source_type, etc.).
    search_result:
        Result dict from the vector search tool, expected keys:
        ``context`` (str), ``data`` (list of chunk dicts).
    user:
        Decoded JWT payload / user profile dict (used to build the access policy).

    Returns
    -------
    dict with keys ``ok``, ``answer``, ``context``, ``sources``, ``error``.
    """
    system_prompt = _SYSTEM_PROMPT_BASE.format(
        access_policy=access_policy_text(user or {})
    )

    prompt = (
        f"Question: {message}\n"
        f"Search filters: {_json_dump(filters)}\n"
        f"Context:\n{search_result.get('context', '')}\n"
        f"Matches:\n{_json_dump(search_result.get('data', []))}"
    )

    try:
        response = call_with_retry(
            lambda: _mistral_client().chat.complete(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
        )
        answer = _extract_content(response).strip()
        return {
            "ok": True,
            "answer": answer,
            "context": search_result.get("context", ""),
            "sources": search_result.get("data", []),
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "answer": f"Je n'ai pas pu interroger l'agent RAG: {exc}",
            "context": search_result.get("context", ""),
            "sources": search_result.get("data", []),
            "error": str(exc),
        }
