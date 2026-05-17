"""RAG agent.

Thin async wrapper around the LLM task in ``backend.tasks.rag_llm_task``.
Responsible for:
  - Running the pgvector semantic search via ``search_document_content``.
  - Passing the search result to ``answer_from_documents_task`` for the
    Mistral answer.
  - Exposing the async ``run_rag_agent`` entry-point consumed by the graph.

All Mistral client logic and prompts live in ``backend.tasks.rag_llm_task``.
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.tasks import rag_llm_task as _task
from backend.tasks.rag_llm_task import answer_from_documents_task
from backend.tools.rag_tool import search_document_content
from backend.tools.sql_tool import get_filiere_modules
import json

_mistral_client = _task._mistral_client


# ---------------------------------------------------------------------------
# Sync runner (calls retrieval tool then task layer)
# ---------------------------------------------------------------------------


def answer_from_documents_sync(
    message: str,
    user: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user = user or {}
    filters = filters or {}

    # --- vector search ---
    try:
        search_result = search_document_content(
            query=message,
            top_k=int(filters.get("top_k", 5)),
            source_type=filters.get("source_type"),
            source_id=filters.get("source_id"),
            module_id=filters.get("module_id") or user.get("module_id"),
            # Do NOT fallback to user.get("sub") because courses are uploaded by teachers,
            # so filtering by student's user_id would yield 0 results.
            user_id=filters.get("user_id"),
            filiere=filters.get("filiere") or user.get("filiere_name"),
            file_type=filters.get("file_type"),
        )
    except Exception as exc:
        print(f"[RAG Agent Error] {exc}")
        search_result = {"context": f"Vector search failed: {exc}", "data": []}

    # --- Inject structured modules (Graceful Fallback) ---
    filiere_id = user.get("filiere_id") or user.get("student", {}).get("filiere_id")
    if filiere_id:
        try:
            modules_data = get_filiere_modules(filiere_id=filiere_id, semester=user.get("semester"))
            structured_context = "\n--- Structured Modules Data ---\n" + json.dumps(modules_data, ensure_ascii=False)
            search_result["context"] = search_result.get("context", "") + structured_context
        except Exception as e:
            print(f"[RAG Modules Error] {e}")

    # --- LLM answer (task layer) ---
    original_client = _task._mistral_client
    _task._mistral_client = _mistral_client
    try:
        return answer_from_documents_task(message, filters, search_result, user)
    finally:
        _task._mistral_client = original_client


# ---------------------------------------------------------------------------
# Async entry-point (used by graph nodes and routers)
# ---------------------------------------------------------------------------


async def run_rag_agent(
    message: str,
    user: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        answer_from_documents_sync, message, user or {}, filters or {}
    )
