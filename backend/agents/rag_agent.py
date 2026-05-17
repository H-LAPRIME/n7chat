from __future__ import annotations

import asyncio
import json
from os import environ
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from backend.tools.rag_tool import search_document_content


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")

DEFAULT_MODEL = environ.get("MISTRAL_MODEL", "mistral-large-latest")


SYSTEM_PROMPT = """
You are the n7chat RAG agent.

Use only retrieved context from indexed documents. Documents can be courses,
timetables, news, administrative documents, events, or other school material.
If the context is insufficient, say that clearly and suggest what document is needed.
Answer in French.
"""


def _mistral_client():
    api_key = environ.get("MISTRAL_KEY_RAG")
    if not api_key:
        raise RuntimeError("MISTRAL_KEY_RAG is missing from backend/.env")

    from mistralai import Mistral

    return Mistral(api_key=api_key)


def _extract_content(response: Any) -> str:
    try:
        return response.choices[0].message.content or ""
    except Exception:
        return str(response)


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, indent=2)


def answer_from_documents_sync(
    message: str,
    user: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user = user or {}
    filters = filters or {}
    search = search_document_content(
        query=message,
        top_k=int(filters.get("top_k", 5)),
        source_type=filters.get("source_type"),
        source_id=filters.get("source_id"),
        module_id=filters.get("module_id") or user.get("module_id"),
        user_id=filters.get("user_id") or user.get("sub") or user.get("id"),
        filiere=filters.get("filiere") or user.get("filiere_name"),
        file_type=filters.get("file_type"),
    )

    prompt = (
        f"Question: {message}\n"
        f"Search filters: {_json_dump(filters)}\n"
        f"Context:\n{search.get('context', '')}\n"
        f"Matches:\n{_json_dump(search.get('data', []))}"
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
        return {
            "ok": True,
            "answer": answer,
            "context": search.get("context", ""),
            "sources": search.get("data", []),
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "answer": f"Je n'ai pas pu interroger l'agent RAG: {exc}",
            "context": search.get("context", ""),
            "sources": search.get("data", []),
            "error": str(exc),
        }


async def run_rag_agent(
    message: str,
    user: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(answer_from_documents_sync, message, user or {}, filters or {})
